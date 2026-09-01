"""Filesystem Python API. All access is permission-gated."""

from __future__ import annotations

from pathlib import Path

from geomcp.config import load_config
from geomcp.exceptions import GeoMCPError
from geomcp.models import ApiResult, fail, ok
from geomcp.services.permissions import PathPolicy, inspect_path


def inspect(path: str | Path, *, config_dir: str | Path | None = None) -> ApiResult:
    try:
        policy = PathPolicy.from_config(load_config(config_dir))
        return ok(inspect_path(path, policy=policy))
    except (GeoMCPError, OSError) as exc:
        return fail(type(exc).__name__.upper(), str(exc))
