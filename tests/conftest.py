from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    read_root = tmp_path / "data"
    project_root = read_root / "GeoMCP"
    for path in (
        read_root,
        project_root / "outputs",
        project_root / "runtime",
        project_root / "knowledge",
    ):
        path.mkdir(parents=True, exist_ok=True)

    files = {
        "geomcp.yaml": {
            "project": {
                "name": "GeoMCP-Test",
                "control_node": "1012",
                "gpu_node": "1015",
            }
        },
        "paths.yaml": {
            "read_roots": [str(read_root)],
            "write_roots": [
                str(project_root / "outputs"),
                str(project_root / "runtime"),
                str(project_root / "knowledge"),
            ],
        },
        "permissions.yaml": {
            "capabilities": {
                "inspect": True,
                "write": True,
                "delete": False,
                "recursive_delete": False,
                "arbitrary_shell": False,
                "arbitrary_ssh": False,
            }
        },
        "executors.yaml": {"executors": {"cpu": {"enabled": False}, "gpu": {"enabled": False}}},
        "rag.yaml": {"rag": {"enabled": False}},
    }
    for name, content in files.items():
        (tmp_path / name).write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
    return tmp_path
