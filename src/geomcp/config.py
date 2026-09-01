"""Central configuration loading and validation."""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any
import yaml
from .exceptions import ConfigurationError

CONFIG_FILES = ("geomcp.yaml", "paths.yaml", "permissions.yaml", "executors.yaml", "rag.yaml", "workspaces.yaml")

def find_project_root(start: str | Path | None = None) -> Path:
    if env_root := os.getenv("GEOMCP_HOME"):
        return Path(env_root).expanduser().resolve()
    origin = Path(start).expanduser().resolve() if start else Path(__file__).resolve()
    if origin.is_file(): origin = origin.parent
    for candidate in (origin, *origin.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "config").is_dir(): return candidate
    return Path.cwd().resolve()

def get_config_dir(config_dir: str | Path | None = None) -> Path:
    if config_dir is not None: return Path(config_dir).expanduser().resolve()
    if env_dir := os.getenv("GEOMCP_CONFIG_DIR"): return Path(env_dir).expanduser().resolve()
    return (find_project_root() / "config").resolve()

def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file(): raise ConfigurationError(f"Required configuration file is missing: {path}")
    try: value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc: raise ConfigurationError(f"Failed to read configuration file {path}: {exc}") from exc
    if value is None: return {}
    if not isinstance(value, dict): raise ConfigurationError(f"Configuration file must contain a mapping: {path}")
    return value

def load_config(config_dir: str | Path | None = None) -> dict[str, Any]:
    directory = get_config_dir(config_dir)
    config = {Path(name).stem: _load_yaml(directory / name) for name in CONFIG_FILES}
    config["_meta"] = {"config_dir": str(directory), "project_root": str(find_project_root())}
    validate_config(config)
    return config

def _resolved_roots(values: list[Any]) -> tuple[Path, ...]:
    return tuple(Path(str(value)).expanduser().resolve(strict=False) for value in values)

def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents

def validate_config(config: dict[str, Any]) -> None:
    try:
        read_roots = config["paths"]["read_roots"]; write_roots = config["paths"]["write_roots"]
        permissions = config["permissions"]; denied = permissions["denied_capabilities"]
    except (KeyError, TypeError) as exc: raise ConfigurationError(f"Missing required configuration key: {exc}") from exc
    default_policy = permissions.get("default_policy", "deny"); allowed = permissions.get("allowed_capabilities", [])
    if not isinstance(read_roots, list) or not read_roots: raise ConfigurationError("paths.read_roots must be a non-empty list")
    if not isinstance(write_roots, list) or not write_roots: raise ConfigurationError("paths.write_roots must be a non-empty list")
    if default_policy not in {"deny", "allow"}: raise ConfigurationError("permissions.default_policy must be 'deny' or 'allow'")
    if not isinstance(allowed, list): raise ConfigurationError("permissions.allowed_capabilities must be a list")
    if not isinstance(denied, list): raise ConfigurationError("permissions.denied_capabilities must be a list")
    overlap = set(map(str, allowed)) & set(map(str, denied))
    if overlap: raise ConfigurationError(f"Capabilities cannot be both allowed and denied: {', '.join(sorted(overlap))}")

    read_bounds = _resolved_roots(read_roots)
    write_bounds = _resolved_roots(write_roots)
    workspace_cfg = config.get("workspaces", {})
    workspaces = workspace_cfg.get("workspaces", {}) if isinstance(workspace_cfg, dict) else None
    if not isinstance(workspaces, dict) or not workspaces:
        raise ConfigurationError("workspaces.workspaces must be a non-empty mapping")
    for name, spec in workspaces.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            raise ConfigurationError(f"Invalid workspace name: {name!r}")
        if not isinstance(spec, dict):
            raise ConfigurationError(f"Workspace {name} must be a mapping")
        read_root = spec.get("read_root")
        write_root = spec.get("write_root")
        if not isinstance(read_root, str) or not read_root.strip():
            raise ConfigurationError(f"Workspace {name} is missing read_root")
        if not isinstance(write_root, str) or not write_root.strip():
            raise ConfigurationError(f"Workspace {name} is missing write_root")
        resolved_read = Path(read_root).expanduser().resolve(strict=False)
        resolved_write = Path(write_root).expanduser().resolve(strict=False)
        if not any(_within(resolved_read, root) for root in read_bounds):
            raise ConfigurationError(f"Workspace {name} read_root is outside paths.read_roots: {resolved_read}")
        if not any(_within(resolved_write, root) for root in write_bounds):
            raise ConfigurationError(f"Workspace {name} write_root is outside paths.write_roots: {resolved_write}")

    executors = config.get("executors", {})
    if not isinstance(executors, dict): raise ConfigurationError("executors configuration must be a mapping")
    gpu = executors.get("gpu", {})
    if gpu and not isinstance(gpu, dict): raise ConfigurationError("executors.gpu must be a mapping")
    if gpu.get("enabled"):
        required = ("host", "port", "username", "python", "config_dir")
        missing = [name for name in required if not gpu.get(name)]
        if missing: raise ConfigurationError(f"Enabled GPU executor is missing fixed endpoint fields: {', '.join(missing)}")

def runtime_dir(config: dict[str, Any]) -> Path:
    if value := config.get("geomcp", {}).get("runtime_dir"):
        return Path(value).expanduser().resolve(strict=False)
    for root in config["paths"]["write_roots"]:
        path = Path(root).expanduser().resolve(strict=False)
        if path.name == "runtime": return path
    return Path(config["_meta"]["project_root"]) / "runtime"

def outputs_dir(config: dict[str, Any]) -> Path:
    if value := config.get("geomcp", {}).get("outputs_dir"):
        return Path(value).expanduser().resolve(strict=False)
    for root in config["paths"]["write_roots"]:
        path = Path(root).expanduser().resolve(strict=False)
        if path.name == "outputs": return path
    return Path(config["_meta"]["project_root"]) / "outputs"
