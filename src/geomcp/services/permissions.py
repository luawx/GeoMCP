"""Fail-closed filesystem permission policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geomcp.config import load_config
from geomcp.exceptions import PermissionDenied
from .paths import is_within, resolve_path


@dataclass(frozen=True, slots=True)
class PathPolicy:
    read_roots: tuple[Path, ...]
    write_roots: tuple[Path, ...]
    default_policy: str = "deny"
    allowed_capabilities: frozenset[str] = frozenset()
    denied_capabilities: frozenset[str] = frozenset()

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> "PathPolicy":
        cfg = config or load_config()
        permissions = cfg["permissions"]
        return cls(
            read_roots=tuple(Path(p).expanduser().resolve(strict=False) for p in cfg["paths"]["read_roots"]),
            write_roots=tuple(Path(p).expanduser().resolve(strict=False) for p in cfg["paths"]["write_roots"]),
            default_policy=str(permissions.get("default_policy", "deny")),
            allowed_capabilities=frozenset(str(x) for x in permissions.get("allowed_capabilities", [])),
            denied_capabilities=frozenset(str(x) for x in permissions["denied_capabilities"]),
        )

    def assert_capability_allowed(self, capability: str) -> None:
        if self.default_policy not in {"deny", "allow"}:
            raise PermissionDenied("Capability policy is invalid; refusing operation")
        if capability in self.denied_capabilities:
            raise PermissionDenied(f"Capability is disabled by policy: {capability}")
        if self.default_policy == "deny" and capability not in self.allowed_capabilities:
            raise PermissionDenied(f"Capability is not explicitly allowed: {capability}")

    def validate_read(self, path: str | Path) -> Path:
        self.assert_capability_allowed("filesystem.read")
        resolved = resolve_path(path, must_exist=True)
        if not any(is_within(resolved, root) for root in self.read_roots):
            raise PermissionDenied(f"Read path is outside allowed roots: {resolved}")
        return resolved

    def validate_write(self, path: str | Path) -> Path:
        self.assert_capability_allowed("filesystem.write")
        resolved = resolve_path(path, must_exist=False)
        if not any(is_within(resolved, root) for root in self.write_roots):
            raise PermissionDenied(f"Write path is outside writable roots: {resolved}")
        return resolved

    def can_read(self, path: str | Path) -> bool:
        try:
            self.validate_read(path)
            return True
        except Exception:
            return False

    def can_write(self, path: str | Path) -> bool:
        try:
            self.validate_write(path)
            return True
        except Exception:
            return False


def inspect_path(path: str | Path, *, policy: PathPolicy | None = None) -> dict[str, Any]:
    active = policy or PathPolicy.from_config()
    active.assert_capability_allowed("filesystem.inspect")
    resolved = active.validate_read(path)
    stat = resolved.stat()
    return {
        "path": str(path),
        "resolved_path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "is_dir": resolved.is_dir(),
        "size_bytes": stat.st_size,
        "read_allowed": True,
        "write_allowed": active.can_write(resolved),
    }
