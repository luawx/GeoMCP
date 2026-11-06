"""Permission checked picking orchestration and immutable preparation snapshots."""
from __future__ import annotations
import csv
import hashlib
import hmac
import secrets
import json
import uuid
from pathlib import Path
from geomcp.config import load_config, outputs_dir, runtime_dir
from geomcp.exceptions import ScientificToolError, ConfigurationError, GeoMCPError
from geomcp.services.permissions import PathPolicy
from geomcp.services.workspaces import WorkspaceManager


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


class PickingService:
    def __init__(self, *, config_dir=None):
        self.config = load_config(config_dir)
        self.config_dir = self.config['_meta']['config_dir']
        self.policy = PathPolicy.from_config(self.config)
        self.workspaces = WorkspaceManager(self.config, policy=self.policy)
        self.settings = self.config.get('picking', {})
        self.limits = self.settings.get('limits', {})

    @staticmethod
    def _core():
        from geomcp.scientific import picking
        return picking

    def _read(self, ref, workspace=None):
        return self.workspaces.resolve_read(workspace, ref) if workspace else self.policy.validate_read(ref)

    def _nested(self, workspace):
        def check(path):
            resolved = self.policy.validate_read(path)
            if workspace:
                root = self.workspaces.get(workspace).read_root
                if resolved != root and root not in resolved.parents:
                    from geomcp.exceptions import PermissionDenied
                    raise PermissionDenied('Nested reference escapes workspace')
            return resolved
        return check

    def _output(self, output_path, workspace, run_id):
        if workspace:
            path = self.workspaces.resolve_write(workspace, output_path or f'location/{run_id}')
        else:
            path = self.policy.validate_write(output_path or outputs_dir(self.config) / 'location' / run_id)
        if path.exists():
            raise ScientificToolError('Output directory already exists')
        return path

    @staticmethod
    def _limit(value):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise ScientificToolError('preview_limit must be an integer between 0 and 100')
        return value

    def _sign(self, value):
        # Private server state; never exposed through the picking API.
        key_path = self.policy.validate_write(runtime_dir(self.config) / 'picking-signing.key')
        key_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with key_path.open('xb') as stream:
                stream.write(secrets.token_bytes(32))
        except FileExistsError:
            pass
        return hmac.new(key_path.read_bytes(), _digest(value).encode(), hashlib.sha256).hexdigest()

    def _registration(self, preset_id, preset_version=None):
        preset = self.settings.get('presets', {}).get(preset_id)
        if not preset or (preset_version is not None and str(preset.get('version')) != str(preset_version)):
            raise ConfigurationError('Unknown picking preset/version')
        backend = preset['backend_id']
        if backend not in {'stalta', 'phasenet', 'phasenet_das'}:
            raise ConfigurationError('Unregistered picking backend')
        profile = self.settings.get('execution_profiles', {}).get(preset.get('execution_profile_id'))
        required = {'max_input_bytes', 'max_samples', 'max_receivers', 'max_block_points', 'max_picks', 'max_output_bytes'}
        if not profile or not profile.get('enabled', False) or not required <= self.limits.keys():
            raise ConfigurationError('Picking execution profile or required limits are not enabled')
        if (isinstance(profile.get('concurrency'), bool) or not isinstance(profile.get('concurrency'), int) or profile['concurrency'] < 1
                or isinstance(profile.get('timeout'), bool) or not isinstance(profile.get('timeout'), (int, float)) or not 0 < profile['timeout'] <= 86400):
            raise ConfigurationError('Picking profile requires positive concurrency and bounded timeout')
        if any(isinstance(self.limits[k], bool) or not isinstance(self.limits[k], int) or self.limits[k] <= 0 for k in required):
            raise ConfigurationError('Picking resource limits must be positive integers')
        model = self.settings.get('models', {}).get(preset.get('model_id'))
        if backend != 'stalta' and (not model or not model.get('enabled', False)):
            raise ConfigurationError('Model is not registered and enabled')
        if model:
            if model.get('backend_id', backend) != backend:
                raise ConfigurationError('Model backend does not match preset')
            model = dict(model)
            model.setdefault('model_id', preset.get('model_id'))
            for key in ('python', 'source_dir'):
                if not model.get(key):
                    raise ConfigurationError('Model environment registration is incomplete')
                self.policy.validate_read(model[key])
            weights = model.get('weights')
            if not isinstance(weights, str) or not weights:
                raise ConfigurationError('Model weights must be a registered file or checkpoint prefix string')
            candidate = Path(weights).expanduser()
            parent = self.policy.validate_read(candidate.parent)
            candidate = parent / candidate.name
            weight_files = [candidate] if candidate.is_file() else sorted(parent.glob(candidate.name + '.*'))
            if not weight_files or any(not path.is_file() for path in weight_files):
                raise ConfigurationError('Model checkpoint files are missing')
            checksums = model.get('sha256', {})
            if not isinstance(checksums, dict) or not checksums:
                raise ConfigurationError('Model weights and SHA256 registration required')
            for weight in weight_files:
                path = self.policy.validate_read(weight)
                if not checksums.get(str(weight)) and not checksums.get(str(path)):
                    raise ConfigurationError('Model weight SHA256 missing')
            for ref, expected in checksums.items():
                path = self.policy.validate_read(ref)
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(block)
                if digest.hexdigest() != expected:
                    raise ScientificToolError('Registered model file checksum mismatch')
        executor = profile.get('executor', 'cpu')
        if executor not in {'cpu', 'gpu'} or backend == 'stalta' and executor != 'cpu':
            raise ConfigurationError('Unsupported picking executor')
        return preset, profile, model

    def backends(self):
        self.policy.assert_capability_allowed('picking.read')
        rows = []
        for name in ('stalta', 'phasenet', 'phasenet_das'):
            available = False
            for key, preset in self.settings.get('presets', {}).items():
                if preset.get('backend_id') == name:
                    try:
                        self._registration(key)
                        available = True
                    except ConfigurationError:
                        pass
            rows.append({'backend_id': name, 'available': available, 'scientific_acceptance': 'not_completed', 'reason': None if available else 'No enabled registered preset'})
        return {'backends': rows}

    def presets(self, backend_id=None):
        self.policy.assert_capability_allowed('picking.read')
        return {'presets': [{'preset_id': k, **{f: v.get(f) for f in ('version', 'backend_id', 'parameters')}} for k, v in self.settings.get('presets', {}).items() if backend_id is None or v.get('backend_id') == backend_id][:100]}

    def inspect(self, waveform_manifest_ref, *, geometry_ref=None, workspace=None, preview_limit=20):
        self.policy.assert_capability_allowed('picking.read')
        self._limit(preview_limit)
        path = self._read(waveform_manifest_ref, workspace)
        return self._core().inspect(path, validate_read=self._nested(workspace), limits=self.limits)

    def prepare(self, waveform_manifest_ref, geometry_ref, preset_id, *, preset_version=None, overrides=None, output_path=None, workspace=None):
        self.policy.assert_capability_allowed('picking.prepare')
        preset, profile, model = self._registration(preset_id, preset_version)
        inputs = self._core().prepare_inputs(self._read(waveform_manifest_ref, workspace), self._read(geometry_ref, workspace), validate_read=self._nested(workspace), limits=self.limits)
        parameters = self._core().resolve_parameters(preset, overrides or {}, backend_id=preset['backend_id'], limits=self.limits)
        self._validate_compatibility(inputs, parameters['effective'], preset['backend_id'], model)
        run_id = uuid.uuid4().hex
        output = self._output(output_path, workspace, run_id)
        prepared = {'schema_version': '1.0', 'run_id': run_id, 'workspace': workspace, 'inputs': inputs, 'waveform_manifest_path': str(self._read(waveform_manifest_ref, workspace)), 'geometry_path': str(self._read(geometry_ref, workspace)), 'parameters': parameters['effective'], 'parameter_sources': parameters['sources'], 'overrides': overrides or {}, 'effective_parameters': parameters['effective'], 'backend_id': preset['backend_id'], 'preset_id': preset_id, 'preset_version': str(preset.get('version')), 'model': model, 'execution_profile': profile, 'limits': self.limits, 'configuration_fingerprint': _digest(self.settings), 'output_dir': str(output)}
        prepared['fingerprint'] = self._sign(prepared)
        output.mkdir(parents=True)
        _write(output / 'parameters.json', parameters)
        _write(output / 'prepared.json', prepared)
        return {'run_id': run_id, 'prepared_ref': self._ref(output / 'prepared.json', workspace), 'parameters': parameters}

    @staticmethod
    def _validate_compatibility(inputs, parameters, backend, model):
        preprocessing = parameters.get('preprocessing', {})
        for waveform in inputs.get('waveforms', []):
            kind = waveform['data_kind']
            if backend == 'phasenet' and kind != 'station' or backend == 'phasenet_das' and kind != 'das':
                raise ScientificToolError('Backend input data kind is incompatible')
            rate = waveform['sampling_rate_hz']
            target = preprocessing.get('target_sampling_rate_hz')
            if target is not None and target != rate:
                raise ScientificToolError('Resampling requires a separately preprocessed input')
            band = preprocessing.get('bandpass_hz')
            if band is not None and band[1] >= rate / 2:
                raise ScientificToolError('Bandpass exceeds Nyquist')
            if model:
                for field in ('quantity', 'unit', 'sampling_rate_hz'):
                    if model.get(field) != waveform.get(field):
                        raise ScientificToolError('Model input mismatch: ' + field)
                if backend == 'phasenet' and model.get('components') != waveform.get('components'):
                    raise ScientificToolError('Model component order mismatch')
            elif backend == 'stalta' and kind == 'station':
                component = parameters.get('algorithm', {}).get('station_component')
                if component not in waveform.get('components', []):
                    raise ScientificToolError('Selected STA/LTA component is missing')

    def _ref(self, path, workspace):
        return str(path.relative_to(self.workspaces.get(workspace).write_root)) if workspace else str(path)

    def _prepared(self, prepared_ref, workspace=None):
        path = self._read(prepared_ref, workspace)
        if path.stat().st_size > 1024 * 1024:
            raise ScientificToolError('Prepared snapshot is too large')
        value = json.loads(path.read_text(encoding='utf-8'))
        signature = value.pop('fingerprint', None)
        if not isinstance(signature, str) or not hmac.compare_digest(signature, self._sign(value)):
            raise ScientificToolError('Prepared snapshot fingerprint mismatch')
        value['fingerprint'] = signature
        if value.get('workspace') != workspace or value['configuration_fingerprint'] != _digest(self.settings):
            raise ScientificToolError('Picking configuration changed; prepare again')
        if self.policy.validate_write(value['output_dir']) != path.parent:
            raise ScientificToolError('Prepared output directory mismatch')
        self._registration(value['preset_id'], value['preset_version'])
        current = self._core().prepare_inputs(Path(value['waveform_manifest_path']), Path(value['geometry_path']), validate_read=self._nested(workspace), limits=self.limits)
        if _digest(current) != _digest(value['inputs']):
            raise ScientificToolError('Picking inputs changed; prepare again')
        return value

    def validate(self, prepared_ref, *, workspace=None):
        self.policy.assert_capability_allowed('picking.read')
        try:
            value = self._prepared(prepared_ref, workspace)
            return {'valid': True, 'errors': [], 'warnings': [], 'run_id': value['run_id']}
        except ScientificToolError as exc:
            return {'valid': False, 'errors': [str(exc)], 'warnings': []}

    def run(self, prepared_ref, *, workspace=None):
        self.policy.assert_capability_allowed('picking.run')
        value = self._prepared(prepared_ref, workspace)
        from geomcp.jobs.manager import JobManager
        executor = value['execution_profile'].get('executor', 'cpu')
        record = JobManager(config_dir=self.config_dir).submit(task_type=f"picking.{value['backend_id']}.{executor}", executor=executor, tool='picking.run', input={'config_dir': self.config_dir, 'prepared_ref': str(self._read(prepared_ref, workspace)), 'workspace': workspace}, parameters={})
        return {'job_id': record.job_id, 'run_id': value['run_id'], 'status': record.status}

    def result(self, job_id, *, preview_limit=20):
        self.policy.assert_capability_allowed('picking.read')
        self.policy.assert_capability_allowed('job.result')
        self._limit(preview_limit)
        from geomcp.jobs import JobStore
        job = JobStore(runtime_dir(self.config)).get(job_id)
        result = {'job_id': job_id, 'status': job.status}
        if job.status in {'failed', 'cancelled'}:
            result['error'] = job.error
        if job.status == 'completed':
            result.update(job.output or {})
            # Result references remain subject to read policy.
            if result.get('manifest_ref'):
                self.policy.validate_read(result['manifest_ref'])
            for ref in result.get('artifacts', {}).values():
                self.policy.validate_read(ref)
            picks = result.get('artifacts', {}).get('picks')
            preview = []
            truncated = False
            if picks:
                with Path(picks).open(encoding='utf-8-sig', newline='') as stream:
                    for index, row in enumerate(csv.DictReader(stream)):
                        if index >= preview_limit or len(json.dumps({'result': result, 'preview': preview + [row]}).encode()) > 60 * 1024:
                            truncated = True
                            break
                        preview.append(row)
            result.update(preview=preview, truncated=truncated)
            if len(json.dumps(result).encode()) > 64 * 1024:
                result = {'job_id': job_id, 'status': job.status, 'manifest_ref': result.get('manifest_ref'), 'truncated': True}
        return result

    def import_picks(self, input_ref, geometry_ref, *, format='csv', mapping=None, output_path=None, workspace=None):
        self.policy.assert_capability_allowed('picking.prepare')
        self.policy.assert_capability_allowed('picking.run')
        if format not in {'csv', 'external_csv'}:
            raise ScientificToolError('Only csv pick imports are supported')
        profile = self.settings.get('execution_profiles', {}).get('import-cpu', {})
        if (not profile.get('enabled') or profile.get('executor', 'cpu') != 'cpu'
                or isinstance(profile.get('concurrency'), bool) or not isinstance(profile.get('concurrency'), int) or profile['concurrency'] < 1
                or isinstance(profile.get('timeout'), bool) or not isinstance(profile.get('timeout'), (int, float)) or not 0 < profile['timeout'] <= 86400):
            raise ConfigurationError('Import execution profile must be explicitly enabled with timeout and concurrency')
        source = self._read(input_ref, workspace)
        geometry = self._read(geometry_ref, workspace)
        if not self.limits or source.stat().st_size + geometry.stat().st_size > self.limits.get('max_input_bytes', 0):
            raise ConfigurationError('Import resource limits missing or exceeded')
        from geomcp.scientific.picking.contracts import validate_geometry
        geometry_data, _, geometry_references = validate_geometry(geometry, self._nested(workspace), self.limits)
        receivers = Path(geometry_references[1]['path'])
        if sum(p.stat().st_size for p in (source, geometry, receivers)) > self.limits['max_input_bytes']:
            raise ScientificToolError('Import byte limit exceeded')
        references = [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in (source, geometry, receivers)]
        with source.open(encoding='utf-8-sig', newline='') as stream:
            header = csv.DictReader(stream).fieldnames
        if not header:
            raise ScientificToolError('Import CSV header is missing')
        run_id = uuid.uuid4().hex
        output = self._output(output_path, workspace, run_id)
        from geomcp.jobs.manager import JobManager
        record = JobManager(config_dir=self.config_dir).submit(task_type='picking.import.cpu', tool='picking.import', input={'config_dir': self.config_dir, 'input_path': str(source), 'geometry_path': str(geometry), 'output_dir': str(output), 'workspace': workspace, 'mapping': mapping, 'fingerprint': _digest(self.settings), 'references': references}, parameters={})
        return {'job_id': record.job_id, 'run_id': output.name, 'status': record.status}


def execute_worker(input_data, parameters, *, task_type):
    if parameters:
        raise ScientificToolError('Picking worker accepts no parameter overrides')
    service = PickingService(config_dir=input_data['config_dir'])
    service.policy.assert_capability_allowed('picking.run')
    if task_type == 'picking.import.cpu':
        if input_data['fingerprint'] != _digest(service.settings):
            raise ScientificToolError('Picking configuration changed')
        service.policy.assert_capability_allowed('picking.prepare')
        for reference in input_data['references']:
            path = service._nested(input_data.get('workspace'))(reference['path'])
            if hashlib.sha256(path.read_bytes()).hexdigest() != reference['sha256']:
                raise ScientificToolError('Import inputs changed after submission')
        output = service.policy.validate_write(input_data['output_dir'])
        if output.exists():
            raise ScientificToolError('Import output already exists')
        return service._core().import_picks(service._read(input_data['input_path']), service._read(input_data['geometry_path']), output, validate_read=service._nested(input_data.get('workspace')), limits=service.limits, mapping=input_data.get('mapping'), expected_references=input_data['references'], job_id=input_data.get('_job_id'))
    value = service._prepared(input_data['prepared_ref'], None) if not input_data.get('workspace') else service._prepared(service._ref(Path(input_data['prepared_ref']), input_data['workspace']), input_data['workspace'])
    value['job_id'] = input_data.get('_job_id')
    expected = f"picking.{value['backend_id']}.{value['execution_profile'].get('executor', 'cpu')}"
    if task_type != expected:
        raise ScientificToolError('Picking worker task does not match preparation')
    return service._core().execute(value, Path(value['output_dir']), validate_read=service._nested(value.get('workspace')))
