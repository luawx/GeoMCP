"""Read-only filesystem inspection service."""

from __future__ import annotations

from pathlib import Path

from geomcp.config import GeoMCPConfig
from geomcp.services.paths import PathSandbox
from geomcp.services.permissions import PermissionService


def inspect_path(path: str | Path, config: GeoMCPConfig) -> dict[str, object]:
    PermissionService(config).require("inspect")
    resolved = PathSandbox(config).resolve_for_read(path)
    exists = resolved.exists()
    kind = "missing"
    size: int | None = None
    if exists:
        if resolved.is_file():
            kind = "file"
            size = resolved.stat().st_size
        elif resolved.is_dir():
            kind = "directory"
        elif resolved.is_symlink():
            kind = "symlink"
        else:
            kind = "other"
    return {
        "path": str(resolved),
        "exists": exists,
        "type": kind,
        "size_bytes": size,
    }
