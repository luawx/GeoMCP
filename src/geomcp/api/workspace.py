"""Workspace/Data Region Python API."""
from __future__ import annotations

from pathlib import Path

from geomcp.config import load_config
from geomcp.exceptions import GeoMCPError
from geomcp.models import ApiResult, fail, ok
from geomcp.services.workspaces import WorkspaceManager


def list_workspaces(*, config_dir: str | Path | None = None) -> ApiResult:
    try:
        config = load_config(config_dir)
        return ok(WorkspaceManager(config).list())
    except (GeoMCPError, OSError, ValueError, TypeError) as exc:
        return fail(type(exc).__name__.upper(), str(exc))


__all__ = ["list_workspaces"]
