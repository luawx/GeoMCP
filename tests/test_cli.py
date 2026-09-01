from pathlib import Path

from geomcp.cli.main import main


def write_config(config_dir: Path, root: Path):
    out = root / "out"
    out.mkdir(parents=True)
    config_dir.mkdir()
    files = {
        "geomcp.yaml": "name: GeoMCP\n",
        "paths.yaml": f"read_roots: [{root}]\nwrite_roots: [{out}]\n",
        "permissions.yaml": (
            "default_policy: deny\n"
            "allowed_capabilities: [filesystem.inspect, filesystem.read, filesystem.write, system.status]\n"
            "denied_capabilities: [delete]\n"
        ),
        "executors.yaml": "default_executor: cpu\n",
        "rag.yaml": "enabled: false\n",
        "workspaces.yaml": f"workspaces:\n  test:\n    read_root: {root}\n    write_root: {out}\n",
    }
    for name, text in files.items():
        (config_dir / name).write_text(text, encoding="utf-8")


def test_cli_status_json(tmp_path: Path, capsys):
    root = tmp_path / "root"
    root.mkdir()
    config = tmp_path / "config"
    write_config(config, root)
    code = main(["--config-dir", str(config), "system", "status", "--json"])
    assert code == 0
    assert '"success": true' in capsys.readouterr().out


def test_cli_rejects_outside_path(tmp_path: Path, capsys):
    root = tmp_path / "root"
    root.mkdir()
    config = tmp_path / "config"
    write_config(config, root)
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    code = main(["--config-dir", str(config), "filesystem", "inspect", str(outside), "--json"])
    assert code != 0
    assert '"success": false' in capsys.readouterr().out
