from __future__ import annotations
from geomcp.exceptions import GeoMCPError
from geomcp.models import fail, ok
from geomcp.services.picking import PickingService


def _call(method, *args, config_dir=None, **kwargs):
    try:
        return ok(getattr(PickingService(config_dir=config_dir), method)(*args, **kwargs))
    except (GeoMCPError, OSError, ValueError, TypeError, KeyError) as exc:
        return fail(type(exc).__name__.upper(), str(exc))


def backends(*, config_dir=None): return _call('backends', config_dir=config_dir)
def presets(backend_id=None, *, config_dir=None): return _call('presets', backend_id, config_dir=config_dir)
def inspect(waveform_manifest_ref, *, config_dir=None, **kwargs): return _call('inspect', waveform_manifest_ref, config_dir=config_dir, **kwargs)
def prepare(waveform_manifest_ref, geometry_ref, preset_id, *, config_dir=None, **kwargs): return _call('prepare', waveform_manifest_ref, geometry_ref, preset_id, config_dir=config_dir, **kwargs)
def validate(prepared_ref, *, config_dir=None, **kwargs): return _call('validate', prepared_ref, config_dir=config_dir, **kwargs)
def run(prepared_ref, *, config_dir=None, **kwargs): return _call('run', prepared_ref, config_dir=config_dir, **kwargs)
def result(job_id, *, config_dir=None, **kwargs): return _call('result', job_id, config_dir=config_dir, **kwargs)
def import_picks(input_ref, geometry_ref, *, config_dir=None, **kwargs): return _call('import_picks', input_ref, geometry_ref, config_dir=config_dir, **kwargs)
