from __future__ import annotations
from geomcp.exceptions import GeoMCPError
from geomcp.models import ApiResult, fail, ok
from geomcp.services.das import DASService

def _call(method: str, *args, config_dir=None, **kwargs) -> ApiResult:
    try: return ok(getattr(DASService(config_dir=config_dir), method)(*args, **kwargs))
    except (GeoMCPError, OSError, ValueError, TypeError) as exc: return fail(type(exc).__name__.upper(), str(exc))

def inspect(path, *, workspace=None, config_dir=None): return _call("inspect", path, workspace=workspace, config_dir=config_dir)
def read_window(path, *, config_dir=None, **kwargs): return _call("read_window", path, config_dir=config_dir, **kwargs)
def bandpass(path, *, freqmin, freqmax, config_dir=None, **kwargs): return _call("bandpass", path, freqmin=freqmin, freqmax=freqmax, config_dir=config_dir, **kwargs)
def rms(path, *, config_dir=None, **kwargs): return _call("rms", path, config_dir=config_dir, **kwargs)
def plot(path, *, config_dir=None, **kwargs): return _call("plot", path, config_dir=config_dir, **kwargs)
__all__=["inspect","read_window","bandpass","rms","plot"]
