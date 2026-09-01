"""System-level service functions."""

from __future__ import annotations

import platform

from geomcp import __version__
from geomcp.config import GeoMCPConfig
from geomcp.services.permissions import PermissionService


def status(config: GeoMCPConfig) -> dict[str, object]:
    PermissionService(config).ensure_safe_defaults()
    project = config.section("geomcp").get("project", {})
    return {
        "name": project.get("name", "GeoMCP"),
        "version": __version__,
        "python": platform.python_version(),
        "config_dir": str(config.config_dir),
        "control_node": project.get("control_node"),
        "gpu_node": project.get("gpu_node"),
        "steps_completed": [1, 2, 3, 4, 5],
    }
