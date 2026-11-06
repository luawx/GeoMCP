"""Generate isolated synthetic station/DAS picking examples; optionally run real jobs.

    python scripts/picking_demo.py --output-dir D:/scratch/picking-demo --run

Requires an installed GeoMCP with the picking extra. Refuses existing output dirs.
These pulses test plumbing, not scientific detection quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path


def generate(directory: Path) -> dict:
    import h5py
    import numpy as np
    import yaml
    from obspy import Trace, UTCDateTime

    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    config = directory / 'config'
    inputs = directory / 'inputs'
    outputs = directory / 'outputs'
    runtime = directory / 'runtime'
    for path in (config, inputs, outputs, runtime):
        path.mkdir()

    def write_json(path, data):
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def checksum(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    signal = np.zeros(1000, dtype=np.float64)
    signal[300:330] = 5
    with h5py.File(inputs / 'das.h5', 'w') as stream:
        stream['data'] = np.stack([signal, signal])
    files = []
    for component in ('E', 'N', 'Z'):
        path = inputs / (component + '.mseed')
        trace = Trace(signal.copy(), header=dict(network='XX', station='DEMO', location='',
            channel='HH' + component, starttime=UTCDateTime('2026-11-06T00:00:00Z'), sampling_rate=100))
        trace.write(str(path), format='MSEED')
        files.append(dict(path=path.name, sha256=checksum(path), receiver_id='station0',
            component=component, network='XX', station='DEMO', location='', channel='HH' + component))
    receivers = inputs / 'receivers.csv'
    receivers.write_text('receiver_id,data_kind,network,station,location,channel_id,longitude_deg,latitude_deg,elevation_m,valid_from,valid_to\n'
        'station0,station,XX,DEMO,,,110,30,0,2026-01-01T00:00:00Z,2027-01-01T00:00:00Z\n'
        'das0,das,,,,0,110,30,0,2026-01-01T00:00:00Z,2027-01-01T00:00:00Z\n'
        'das1,das,,,,1,110.001,30,0,2026-01-01T00:00:00Z,2027-01-01T00:00:00Z\n', encoding='utf-8')
    write_json(inputs / 'geometry.json', dict(schema_version='1.0', geometry_id='demo-geometry',
        crs='EPSG:4326', axis_order='longitude,latitude', vertical_datum='WGS84',
        receivers_ref='receivers.csv', receivers_sha256=checksum(receivers)))
    base = dict(start_time='2026-11-06T00:00:00Z', end_time='2026-11-06T00:00:10Z',
        sampling_rate_hz=100, sample_count=1000, geometry_id='demo-geometry', gaps=[], bad_receivers=[])
    for name, waveform in {
        'station': dict(base, waveform_id='station-demo', data_kind='station', format='mseed', files=files,
            quantity='velocity', unit='m/s', receiver_ids=['station0'], components=['E', 'N', 'Z'], format_options={}),
        'das': dict(base, waveform_id='das-demo', data_kind='das', format='hdf5',
            files=[dict(path='das.h5', sha256=checksum(inputs / 'das.h5'))], quantity='strain_rate',
            unit='1/s', receiver_ids=['das0', 'das1'], components=[],
            format_options=dict(dataset='data', axis_order='channel,time', channel_ids=['0', '1'])),
    }.items():
        write_json(inputs / (name + '.json'), dict(schema_version='1.0', manifest_id=name,
            geometry_id='demo-geometry', waveforms=[waveform]))
    configuration = {
        'geomcp.yaml': dict(name='Isolated synthetic picking demo', runtime_dir=str(runtime), outputs_dir=str(outputs)),
        'paths.yaml': dict(read_roots=[str(directory)], write_roots=[str(runtime), str(outputs)]),
        'permissions.yaml': dict(default_policy='deny', raw_data_write=False,
            allowed_capabilities=['filesystem.read', 'filesystem.write', 'picking.read', 'picking.prepare',
                'picking.run', 'job.status', 'job.result', 'job.cancel'],
            denied_capabilities=['delete', 'recursive_delete', 'arbitrary_shell', 'arbitrary_ssh']),
        'executors.yaml': dict(default_executor='cpu', cpu=dict(node='local', max_workers=1, timeout=30, dispatch_timeout=5), gpu=dict(enabled=False)),
        'rag.yaml': dict(enabled=False),
        'workspaces.yaml': dict(workspaces={}),
        'picking.yaml': dict(limits=dict(max_input_bytes=1000000, max_samples=10000, max_receivers=10,
            max_block_points=5000, max_picks=100, max_output_bytes=1000000),
            execution_profiles={'demo-cpu': dict(enabled=True, executor='cpu', concurrency=1, timeout=30), 'import-cpu': dict(enabled=True, executor='cpu', concurrency=1, timeout=30)},
            presets={'synthetic-stalta': dict(version='1', backend_id='stalta', execution_profile_id='demo-cpu',
                parameters=dict(algorithm=dict(sta_s=.1, lta_s=1., min_trigger_s=0., max_trigger_s=3.)))})}
    for name, data in configuration.items():
        (config / name).write_text(yaml.safe_dump(data), encoding='utf-8')
    return {'directory': str(directory), 'config_dir': str(config),
        'manifests': [str(inputs / (name + '.json')) for name in ('station', 'das')],
        'geometry_ref': str(inputs / 'geometry.json')}


def run_demo(example: dict) -> list[dict]:
    from geomcp.services.picking import PickingService
    from geomcp.jobs.manager import JobManager
    service = PickingService(config_dir=example['config_dir'])
    manager = JobManager(config_dir=example['config_dir'])
    deadline = time.monotonic() + 60
    results = []
    for manifest in example['manifests']:
        prepared = service.prepare(manifest, example['geometry_ref'], 'synthetic-stalta', preset_version='1')
        if not service.validate(prepared['prepared_ref'])['valid']:
            raise RuntimeError('Synthetic prepared input failed validation')
        submitted = service.run(prepared['prepared_ref'])
        while True:
            result = service.result(submitted['job_id'])
            if result['status'] == 'completed':
                results.append(result)
                break
            if result['status'] in {'failed', 'cancelled'}:
                raise RuntimeError(f"Synthetic job did not complete: {manager.store.get(submitted['job_id']).error}")
            if time.monotonic() >= deadline:
                manager.cancel(submitted['job_id'])
                raise TimeoutError('Synthetic jobs exceeded 60 second deadline')
            time.sleep(.1)
    submitted = service.import_picks(results[0]['artifacts']['picks'], example['geometry_ref'], format='external_csv')
    while True:
        result = service.result(submitted['job_id'])
        if result['status'] == 'completed':
            example['import_result'] = result
            break
        if result['status'] in {'failed', 'cancelled'}:
            raise RuntimeError(f"Synthetic import failed: {manager.store.get(submitted['job_id']).error}")
        if time.monotonic() >= deadline:
            manager.cancel(submitted['job_id'])
            raise TimeoutError('Synthetic import exceeded deadline')
        time.sleep(.1)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    example = generate(args.output_dir)
    if args.run:
        example['results'] = run_demo(example)
    print(json.dumps(example, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
