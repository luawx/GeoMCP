"""Python system API."""

from __future__ import annotations

from pathlib import Path

from geomcp.config import GeoMCPConfig
from geomcp.services.system import status as service_status

from .result import APIResult, failure, success


def status(config_dir: str | Path | None = None) -> APIResult:
    try:
        config = GeoMCPConfig.load(config_dir)
        return success(service_status(config))
    except Exception as exc:
        return failure(exc)
