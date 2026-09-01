from pathlib import Path

import pytest

from geomcp.api import system, workspace
from geomcp.cli.main import main
from geomcp.exceptions import InvalidPathError, PermissionDenied
from geomcp.services.workspaces import WorkspaceManager


def test_workspace_list_and_relative_resolution(config_factory):
    config_dir, root, _, outputs = config_factory()
    sample = root / "raw" / "sample.h5"
    sample.parent.mkdir()
    sample.write_bytes(b"fake")

    result = workspace.list_workspaces(config_dir=config_dir)
    assert result.success
    assert result.data == [
        {
            "name": "test",
            "description": "Test workspace",
            "read_root": str(root.resolve()),
            "write_root": str(outputs.resolve()),
        }
    ]

    manager = WorkspaceManager()
    manager = WorkspaceManager.__new__(WorkspaceManager)
    from geomcp.config import load_config
    from geomcp.services.permissions import PathPolicy
    config = load_config(config_dir)
    manager = WorkspaceManager(config, policy=PathPolicy.from_config(config))

    assert manager.resolve_read("test", "raw/sample.h5") == sample.resolve()
    assert manager.resolve_write("test", "processed/result.npy") == (outputs / "processed" / "result.npy").resolve()


def test_workspace_rejects_absolute_traversal_and_unknown(config_factory):
    config_dir, root, _, _ = config_factory()
    sample = root / "sample.h5"
    sample.write_bytes(b"fake")

    from geomcp.config import load_config
    from geomcp.services.permissions import PathPolicy
    config = load_config(config_dir)
    manager = WorkspaceManager(config, policy=PathPolicy.from_config(config))

    with pytest.raises(InvalidPathError):
        manager.resolve_read("test", sample)
    with pytest.raises(PermissionDenied):
        manager.resolve_write("test", "../escape.npy")
    with pytest.raises(InvalidPathError):
        manager.resolve_read("missing", "sample.h5")


def test_workspace_config_cannot_expand_global_write_boundary(config_factory, tmp_path):
    config_dir, root, _, _ = config_factory()
    outside = tmp_path / "outside"
    outside.mkdir()
    (config_dir / "workspaces.yaml").write_text(
        f"workspaces:\n"
        f"  bad:\n"
        f"    read_root: {root}\n"
        f"    write_root: {outside}\n",
        encoding="utf-8",
    )
    result = system.validate(config_dir)
    assert not result.success
    assert "outside paths.write_roots" in result.error_message


def test_workspace_cli_list(config_factory):
    config_dir, _, _, _ = config_factory()
    assert main(["--config-dir", str(config_dir), "workspace", "list", "--json"]) == 0
