"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .exceptions import ConfigurationError

CONFIG_FILES = ("geomcp.yaml", "paths.yaml", "permissions.yaml", "executors.yaml", "rag.yaml")


def default_config_dir() -> Path:
    env = os.getenv("GEOMCP_CONFIG_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "config"


@dataclass(frozen=True)
class GeoMCPConfig:
    config_dir: Path
    values: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, config_dir: str | Path | None = None) -> "GeoMCPConfig":
        root = Path(config_dir).expanduser().resolve() if config_dir else default_config_dir()
        values: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        for filename in CONFIG_FILES:
            path = root / filename
            if not path.is_file():
                missing.append(filename)
                continue
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError) as exc:
                raise ConfigurationError(f"Failed to load {path}: {exc}") from exc
            if not isinstance(data, dict):
                raise ConfigurationError(f"{path} must contain a YAML mapping")
            values[path.stem] = data
        if missing:
            raise ConfigurationError(
                f"Missing configuration files in {root}: {', '.join(missing)}"
            )
        config = cls(config_dir=root, values=values)
        config.validate()
        return config

    def validate(self) -> None:
        paths = self.values.get("paths", {})
        read_roots = paths.get("read_roots")
        write_roots = paths.get("write_roots")
        if not isinstance(read_roots, list) or not read_roots:
            raise ConfigurationError("paths.read_roots must be a non-empty list")
        if not isinstance(write_roots, list) or not write_roots:
            raise ConfigurationError("paths.write_roots must be a non-empty list")
        for name, roots in (("read_roots", read_roots), ("write_roots", write_roots)):
            if not all(isinstance(item, str) and Path(item).is_absolute() for item in roots):
                raise ConfigurationError(f"paths.{name} must contain absolute paths only")

        resolved_reads = [Path(item).expanduser().resolve(strict=False) for item in read_roots]
        for item in write_roots:
            write_root = Path(item).expanduser().resolve(strict=False)
            if not any(write_root == read_root or read_root in write_root.parents for read_root in resolved_reads):
                raise ConfigurationError(
                    f"write root must be contained by a read root: {write_root}"
                )

        capabilities = self.values.get("permissions", {}).get("capabilities", {})
        if not isinstance(capabilities, dict):
            raise ConfigurationError("permissions.capabilities must be a mapping")
        forbidden = ("delete", "recursive_delete", "arbitrary_shell", "arbitrary_ssh")
        enabled = [name for name in forbidden if capabilities.get(name) is True]
        if enabled:
            raise ConfigurationError(
                "Unsafe capabilities must remain disabled: " + ", ".join(enabled)
            )

    def section(self, name: str) -> dict[str, Any]:
        try:
            return self.values[name]
        except KeyError as exc:
            raise ConfigurationError(f"Unknown configuration section: {name}") from exc
