from pathlib import Path
from geomcp.services.picking import PickingService
from geomcp.config import load_config


def test_optional_picking(config_factory):
    directory, *_ = config_factory()
    assert load_config(directory)['picking'] == {}


def test_discovery_denied(config_factory):
    import pytest
    from geomcp.exceptions import PermissionDenied
    directory, *_ = config_factory()
    with pytest.raises(PermissionDenied):
        PickingService(config_dir=directory).backends()


def test_registry():
    from geomcp.worker.registry import build_task_registry
    registry = build_task_registry()
    for task in ['stalta.cpu', 'phasenet.cpu', 'phasenet.gpu', 'phasenet_das.cpu', 'phasenet_das.gpu', 'import.cpu']:
        assert registry.get('picking.' + task).executor == task.rsplit('.', 1)[1]


def test_prepare_rejects_mutation(config_factory, monkeypatch):
    import json
    import yaml
    from types import SimpleNamespace
    directory, root, runtime, outputs = config_factory()
    permissions = yaml.safe_load((directory / 'permissions.yaml').read_text())
    permissions['allowed_capabilities'] += ['picking.read', 'picking.prepare', 'picking.run']
    (directory / 'permissions.yaml').write_text(yaml.safe_dump(permissions))
    settings = {'presets': {'demo': {'version': '1', 'backend_id': 'stalta', 'execution_profile_id': 'cpu', 'parameters': {}}}, 'execution_profiles': {'cpu': {'enabled': True, 'executor': 'cpu', 'concurrency': 1, 'timeout': 60}}, 'limits': {k: 100 for k in ('max_input_bytes', 'max_samples', 'max_receivers', 'max_block_points', 'max_picks', 'max_output_bytes')}}
    (directory / 'picking.yaml').write_text(yaml.safe_dump(settings))
    source = root / 'waveforms.json'
    geometry = root / 'geometry.json'
    source.write_text('{}')
    geometry.write_text('{}')
    core = SimpleNamespace(prepare_inputs=lambda a, b, **kw: {'source': a.read_text(), 'geometry': b.read_text()}, resolve_parameters=lambda *a, **kw: {'effective': {}, 'sources': {}})
    monkeypatch.setattr(PickingService, '_core', staticmethod(lambda: core))
    service = PickingService(config_dir=directory)
    prepared = service.prepare(source, geometry, 'demo')
    assert service.validate(prepared['prepared_ref'])['valid']
    source.write_text('{"changed": true}')
    assert not service.validate(prepared['prepared_ref'])['valid']
    source.write_text('{}')
    snapshot = json.loads(Path(prepared['prepared_ref']).read_text())
    snapshot['parameters'] = {'algorithm': {'threshold_on': 100}}
    Path(prepared['prepared_ref']).write_text(json.dumps(snapshot))
    assert not service.validate(prepared['prepared_ref'])['valid']



def test_picking_worker_rejects_unknown_fields():
    import pytest
    from geomcp.exceptions import WorkerError
    from geomcp.worker.registry import build_task_registry
    task = build_task_registry().get('picking.stalta.cpu')
    valid = {'config_dir': '/fixed/config', 'prepared_ref': '/fixed/prepared.json', 'workspace': None}
    task.validate(valid, {})
    with pytest.raises(WorkerError):
        task.validate({**valid, 'executable': 'injected'}, {})
    with pytest.raises(WorkerError):
        task.validate(valid, {'algorithm': {}})


def test_cancel_removes_published_manifest(config_factory):
    import json
    from geomcp.jobs import JobStore
    from geomcp.worker.runtime import cancel_local_job
    directory, root, runtime, outputs = config_factory()
    output = outputs / 'location' / 'cancelled-run'
    output.mkdir(parents=True)
    prepared = output / 'prepared.json'
    prepared.write_text('{}')
    manifest = output / 'manifest.json'
    manifest.write_text(json.dumps({'status':'completed'}))
    store = JobStore(runtime)
    job = store.create(tool='picking.run', task_type='picking.stalta.cpu', executor='cpu', input={'config_dir':str(directory),'prepared_ref':str(prepared),'workspace':None}, parameters={})
    assert cancel_local_job(job.job_id, config_dir=directory)
    assert store.get(job.job_id).status == 'cancelled'
    assert not manifest.exists()


def test_registration_accepts_checkpoint_prefix(config_factory):
    import hashlib
    import yaml
    directory, root, *_ = config_factory()
    source = root / 'source'
    source.mkdir()
    python = root / 'python.exe'
    python.write_bytes(b'python')
    prefix = root / 'model.ckpt'
    files = [root / 'model.ckpt.index', root / 'model.ckpt.data-00000-of-00001']
    for path in files:
        path.write_bytes(b'checkpoint')
    model = {'enabled':True,'backend_id':'phasenet','python':str(python),'source_dir':str(source),'weights':str(prefix),'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    settings = {'models':{'model':model},'presets':{'demo':{'backend_id':'phasenet','model_id':'model','execution_profile_id':'cpu','version':'1'}},'execution_profiles':{'cpu':{'enabled':True,'executor':'cpu','timeout':60,'concurrency':1}},'limits':{k:100 for k in ('max_input_bytes','max_samples','max_receivers','max_block_points','max_picks','max_output_bytes')}}
    (directory / 'picking.yaml').write_text(yaml.safe_dump(settings))
    assert PickingService(config_dir=directory)._registration('demo')[2]['weights'] == str(prefix)


def test_prepare_compatibility_rejects_scientific_mismatch():
    import pytest
    from geomcp.exceptions import ScientificToolError
    waveform = {'data_kind':'station','sampling_rate_hz':100,'quantity':'velocity','unit':'m/s','components':['E','N','Z']}
    inputs = {'waveforms':[waveform]}
    parameters = {'preprocessing':{'target_sampling_rate_hz':None}}
    model = {'sampling_rate_hz':100,'quantity':'velocity','unit':'m/s','components':['E','N','Z']}
    PickingService._validate_compatibility(inputs, parameters, 'phasenet', model)
    for field, bad in [('sampling_rate_hz',50),('unit','counts'),('quantity','strain'),('components',['Z','N','E'])]:
        with pytest.raises(ScientificToolError):
            PickingService._validate_compatibility(inputs, parameters, 'phasenet', {**model,field:bad})
    with pytest.raises(ScientificToolError, match='Resampling'):
        PickingService._validate_compatibility(inputs, {'preprocessing':{'target_sampling_rate_hz':50}}, 'phasenet', model)
    with pytest.raises(ScientificToolError, match='data kind'):
        PickingService._validate_compatibility(inputs, parameters, 'phasenet_das', model)
