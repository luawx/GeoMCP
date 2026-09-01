from pathlib import Path

from geomcp.api.filesystem import inspect
from geomcp.api.system import status
from geomcp.cli.main import main
from geomcp.mcp.registry import build_registry


def test_python_api_returns_structured_result(config_dir):
    root = Path(config_dir)
    result = status(root)
    assert result.success is True
    assert result.data["steps_completed"] == [1, 2, 3, 4, 5]


def test_filesystem_api_enforces_sandbox(config_dir):
    result = inspect("/etc/passwd", config_dir)
    assert result.success is False
    assert result.error_code in {"PERMISSION_DENIED", "INVALID_PATH"}


def test_cli_config_validate(config_dir, capsys):
    code = main(["--config-dir", str(config_dir), "--json", "config", "validate"])
    assert code == 0
    assert '"valid": true' in capsys.readouterr().out


def test_registry_is_explicit_and_small():
    registry = build_registry()
    assert [item.name for item in registry] == ["system.status", "filesystem.inspect"]
    for item in registry:
        assert item.input_schema["type"] == "object"
        assert item.output_schema["type"] == "object"
