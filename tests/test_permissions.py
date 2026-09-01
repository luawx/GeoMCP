from pathlib import Path

import pytest

from geomcp.exceptions import PermissionDenied
from geomcp.services.permissions import PathPolicy, inspect_path


def make_policy(read_root: Path, write_root: Path) -> PathPolicy:
    return PathPolicy(
        read_roots=(read_root.resolve(),),
        write_roots=(write_root.resolve(),),
        denied_capabilities=frozenset({"delete", "arbitrary_shell", "arbitrary_ssh"}),
    )


def test_read_inside_root_and_write_only_inside_write_root(tmp_path: Path):
    read_root = tmp_path / "research"
    write_root = read_root / "GeoMCP" / "outputs"
    write_root.mkdir(parents=True)
    raw = read_root / "raw.dat"
    raw.write_text("data", encoding="utf-8")
    policy = make_policy(read_root, write_root)

    assert policy.validate_read(raw) == raw.resolve()
    with pytest.raises(PermissionDenied):
        policy.validate_write(raw)
    assert policy.validate_write(write_root / "result.txt") == (write_root / "result.txt").resolve()


def test_parent_traversal_is_rejected(tmp_path: Path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    policy = make_policy(allowed, allowed)
    with pytest.raises(PermissionDenied):
        policy.validate_read(allowed / ".." / "outside.txt")


def test_symlink_escape_is_rejected(tmp_path: Path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    link = allowed / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink unavailable on this platform")
    policy = make_policy(allowed, allowed)
    with pytest.raises(PermissionDenied):
        policy.validate_read(link / "secret.txt")


def test_denied_capability_is_fail_closed(tmp_path: Path):
    policy = make_policy(tmp_path, tmp_path)
    with pytest.raises(PermissionDenied):
        policy.assert_capability_allowed("delete")


def test_inspect_returns_metadata(tmp_path: Path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    file = allowed / "a.txt"
    file.write_text("abc", encoding="utf-8")
    result = inspect_path(file, policy=make_policy(allowed, allowed))
    assert result["size_bytes"] == 3
    assert result["read_allowed"] is True
