"""Exercise the downloadable example through actual worker subprocesses."""
import json
from pathlib import Path
import subprocess
import sys
import pytest

pytest.importorskip("h5py")
pytest.importorskip("obspy")


def test_picking_demo_generates_and_runs_isolated_jobs(tmp_path):
    directory = tmp_path / 'demo'
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'picking_demo.py'
    result = subprocess.run([sys.executable, str(script), '--output-dir', str(directory), '--run'],
        capture_output=True, text=True, check=True, timeout=65)
    example = json.loads(result.stdout)
    assert [item['summary']['pick_count'] for item in example['results']] == [1, 2]
    assert all(item['status'] == 'completed' for item in example['results'])
    assert all(row['phase'] == 'unknown' for item in example['results'] for row in item['preview'])
    assert example['import_result']['summary']['pick_count'] == 1
    assert example['import_result']['status'] == 'completed'
    for item in example['results']:
        manifest = json.loads(Path(item['manifest_ref']).read_text(encoding='utf-8'))
        assert manifest['job_id'] == item['job_id']
    assert (directory / 'inputs' / 'das.h5').is_file()
    assert (directory / 'inputs' / 'Z.mseed').is_file()
    before = (directory / 'config' / 'permissions.yaml').read_bytes()
    repeated = subprocess.run([sys.executable, str(script), '--output-dir', str(directory)],
        capture_output=True, text=True, timeout=10)
    assert repeated.returncode != 0
    assert (directory / 'config' / 'permissions.yaml').read_bytes() == before
