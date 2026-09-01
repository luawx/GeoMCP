"""System-level Python API."""

from __future__ import annotations

from pathlib import Path

from geomcp import __version__
from geomcp.config import get_config_dir, load_config, validate_config
from geomcp.exceptions import GeoMCPError
from geomcp.models import ApiResult, fail, ok


def status(config_dir: str | Path | None = None) -> ApiResult:
    try:
        config = load_config(config_dir)
        return ok(
            {
                "name": config["geomcp"].get("name", "GeoMCP"),
                "version": __version__,
                "config_valid": True,
                "config_dir": str(get_config_dir(config_dir)),
                "control_node": config["geomcp"].get("control_node"),
                "gpu_node": config["geomcp"].get("gpu_node"),
            }
        )
    except GeoMCPError as exc:
        return fail(type(exc).__name__.upper(), str(exc))


def config_snapshot(config_dir: str | Path | None = None) -> ApiResult:
    try:
        return ok(load_config(config_dir))
    except GeoMCPError as exc:
        return fail(type(exc).__name__.upper(), str(exc))


def validate(config_dir: str | Path | None = None) -> ApiResult:
    try:
        config = load_config(config_dir)
        validate_config(config)
        return ok({"valid": True, "config_dir": str(get_config_dir(config_dir))})
    except GeoMCPError as exc:
        return fail(type(exc).__name__.upper(), str(exc))
