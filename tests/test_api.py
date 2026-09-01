from pathlib import Path
from geomcp.api import jobs
from geomcp.api.filesystem import inspect
from geomcp.api.system import status

def write_config(config_dir: Path, root: Path):
    out = root / "out"
    out.mkdir(parents=True)
    values = {
        "geomcp.yaml": "name: GeoMCP\ncontrol_node: '1012'\ngpu_node: '1015'\n",
        "paths.yaml": f"read_roots:\n  - {root}\nwrite_roots:\n  - {out}\n",
        "permissions.yaml": (
            "default_policy: deny\n"
            "allowed_capabilities: [filesystem.inspect, filesystem.read, filesystem.write, system.status]\n"
            "denied_capabilities: [delete, arbitrary_shell, arbitrary_ssh]\n"
        ),
        "executors.yaml": "default_executor: cpu\n",
        "rag.yaml": "enabled: false\n",
    }
    config_dir.mkdir()
    for name, text in values.items():
        (config_dir / name).write_text(text, encoding="utf-8")

def test_status_and_filesystem_api(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    config_dir = tmp_path / "config"
    write_config(config_dir, root)
    file = root / "x.txt"
    file.write_text("abc", encoding="utf-8")
    assert status(config_dir).success is True
    result = inspect(file, config_dir=config_dir)
    assert result.success is True
    assert result.data["size_bytes"] == 3

def test_filesystem_api_rejects_outside_path(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    config_dir = tmp_path / "config"
    write_config(config_dir, root)
    outside = tmp_path / "outside.txt"
    outside.write_text("no", encoding="utf-8")
    result = inspect(outside, config_dir=config_dir)
    assert result.success is False
    assert result.error_code == "PERMISSIONDENIED"

def test_jobs_api_available_after_step_06():
    assert set(jobs.__all__) == {
        "list_jobs",
        "status",
        "result",
        "logs",
        "cancel",
        "submit_healthcheck",
    }
