"""Path normalization and sandbox enforcement."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from geomcp.config import GeoMCPConfig
from geomcp.exceptions import InvalidPathError, PermissionDenied


def _resolved_absolute(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        raise InvalidPathError(f"Absolute path required: {path}")
    try:
        return candidate.resolve(strict=False)
    except OSError as exc:
        raise InvalidPathError(f"Cannot resolve path {path}: {exc}") from exc


def _inside(path: Path, roots: Iterable[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


class PathSandbox:
    """Fail-closed read/write path policy."""

    def __init__(self, config: GeoMCPConfig):
        values = config.section("paths")
        self.read_roots = tuple(_resolved_absolute(p) for p in values["read_roots"])
        self.write_roots = tuple(_resolved_absolute(p) for p in values["write_roots"])

    def resolve_for_read(self, path: str | Path) -> Path:
        resolved = _resolved_absolute(path)
        if not _inside(resolved, self.read_roots):
            raise PermissionDenied(f"Read path is outside allowed roots: {resolved}")
        return resolved

    def resolve_for_write(self, path: str | Path) -> Path:
        resolved = _resolved_absolute(path)
        if not _inside(resolved, self.write_roots):
            raise PermissionDenied(f"Write path is outside allowed roots: {resolved}")
        return resolved
