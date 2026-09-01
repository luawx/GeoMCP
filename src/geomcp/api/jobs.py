"""Stable Python API for Job Manager operations."""
from __future__ import annotations
from pathlib import Path
from geomcp.exceptions import GeoMCPError
from geomcp.models import ApiResult, fail, ok
from geomcp.services.jobs import JobService

def _call(method: str, *args, config_dir=None, **kwargs) -> ApiResult:
    try: return ok(getattr(JobService(config_dir=config_dir), method)(*args, **kwargs))
    except (GeoMCPError, OSError, ValueError) as exc: return fail(type(exc).__name__.upper(), str(exc))

def list_jobs(*, limit: int=100, status: str | None=None, config_dir: str | Path | None=None) -> ApiResult: return _call("list", limit=limit, status=status, config_dir=config_dir)
def status(job_id: str, *, config_dir: str | Path | None=None) -> ApiResult: return _call("status", job_id, config_dir=config_dir)
def result(job_id: str, *, config_dir: str | Path | None=None) -> ApiResult: return _call("result", job_id, config_dir=config_dir)
def logs(job_id: str, *, config_dir: str | Path | None=None) -> ApiResult: return _call("logs", job_id, config_dir=config_dir)
def cancel(job_id: str, *, config_dir: str | Path | None=None) -> ApiResult: return _call("cancel", job_id, config_dir=config_dir)

__all__ = ["list_jobs", "status", "result", "logs", "cancel"]
