"""Workspace/Data Region resolver layered on top of PathPolicy."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geomcp.config import load_config
from geomcp.exceptions import InvalidPathError, PermissionDenied
from geomcp.services.paths import is_within
from geomcp.services.permissions import PathPolicy


@dataclass(frozen=True, slots=True)
class Workspace:
    name: str
    read_root: Path
    write_root: Path
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "read_root": str(self.read_root),
            "write_root": str(self.write_root),
        }


class WorkspaceManager:
    def __init__(self, config: dict[str, Any] | None = None, *, policy: PathPolicy | None = None):
        self.config = config or load_config()
        self.policy = policy or PathPolicy.from_config(self.config)
        raw = self.config["workspaces"]["workspaces"]
        self._workspaces = {
            name: Workspace(
                name=name,
                description=str(spec.get("description", "")),
                read_root=Path(spec["read_root"]).expanduser().resolve(strict=False),
                write_root=Path(spec["write_root"]).expanduser().resolve(strict=False),
            )
            for name, spec in raw.items()
        }

    def list(self) -> list[dict[str, Any]]:
        self.policy.assert_capability_allowed("workspace.list")
        return [self._workspaces[name].to_dict() for name in sorted(self._workspaces)]

    def get(self, name: str) -> Workspace:
        if not name or name not in self._workspaces:
            raise InvalidPathError(f"Unknown workspace: {name}")
        return self._workspaces[name]

    @staticmethod
    def _relative(path: str | Path) -> Path:
        if path is None or str(path).strip() == "":
            raise InvalidPathError("Workspace path must not be empty")
        candidate = Path(path).expanduser()
        if candidate.is_absolute():
            raise InvalidPathError("Workspace paths must be relative; omit workspace to use an absolute path")
        return candidate

    def resolve_read(self, workspace: str, path: str | Path) -> Path:
        region = self.get(workspace)
        relative = self._relative(path)
        resolved = self.policy.validate_read(region.read_root / relative)
        if not is_within(resolved, region.read_root):
            raise PermissionDenied(f"Read path escapes workspace {workspace}: {resolved}")
        return resolved

    def resolve_write(self, workspace: str, path: str | Path) -> Path:
        region = self.get(workspace)
        relative = self._relative(path)
        resolved = self.policy.validate_write(region.write_root / relative)
        if not is_within(resolved, region.write_root):
            raise PermissionDenied(f"Write path escapes workspace {workspace}: {resolved}")
        return resolved
