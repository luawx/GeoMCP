from pathlib import Path

from geomcp import __version__
from geomcp.config import load_config


def test_version_is_available():
    assert __version__ == "0.1.0a1"


def test_load_config_from_fixture(tmp_path: Path):
    files = {
        "geomcp.yaml": "name: GeoMCP\n",
        "paths.yaml": "read_roots: [/tmp]\nwrite_roots: [/tmp/out]\n",
        "permissions.yaml": "denied_capabilities: [delete]\n",
        "executors.yaml": "default_executor: cpu\n",
        "rag.yaml": "enabled: false\n",
        "workspaces.yaml": "workspaces:\n  test:\n    read_root: /tmp\n    write_root: /tmp/out\n",
    }
    for name, body in files.items():
        (tmp_path / name).write_text(body, encoding="utf-8")
    config = load_config(tmp_path)
    assert config["geomcp"]["name"] == "GeoMCP"


def test_legacy_config_without_workspaces_still_loads(tmp_path: Path):
    files = {
        "geomcp.yaml": "name: GeoMCP\n",
        "paths.yaml": "read_roots: [/tmp]\nwrite_roots: [/tmp/out]\n",
        "permissions.yaml": "denied_capabilities: [delete]\n",
        "executors.yaml": "default_executor: cpu\n",
        "rag.yaml": "enabled: false\n",
    }
    for name, body in files.items():
        (tmp_path / name).write_text(body, encoding="utf-8")
    config = load_config(tmp_path)
    assert config["workspaces"] == {}
