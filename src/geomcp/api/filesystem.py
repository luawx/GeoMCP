"""Python filesystem API."""

from __future__ import annotations

from pathlib import Path

from geomcp.config import GeoMCPConfig
from geomcp.services.filesystem import inspect_path as service_inspect_path

from .result import APIResult, failure, success


def inspect(path: str | Path, config_dir: str | Path | None = None) -> APIResult:
    try:
        config = GeoMCPConfig.load(config_dir)
        return success(service_inspect_path(path, config))
    except Exception as exc:
        return failure(exc)
