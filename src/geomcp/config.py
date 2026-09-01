"""Central configuration loading and validation."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import yaml
from .exceptions import ConfigurationError

CONFIG_FILES = ("geomcp.yaml", "paths.yaml", "permissions.yaml", "executors.yaml", "rag.yaml")

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
