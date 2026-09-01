from pathlib import Path

import pytest

from geomcp.config import GeoMCPConfig
from geomcp.exceptions import InvalidPathError, PermissionDenied
from geomcp.services.paths import PathSandbox


def test_allows_read_inside_root(config_dir):
    config = GeoMCPConfig.load(config_dir)
    root = Path(config.section("paths")["read_roots"][0])
    target = root / "sample.dat"
    target.write_text("x", encoding="utf-8")
    assert PathSandbox(config).resolve_for_read(target) == target.resolve()


def test_rejects_outside_root(config_dir, tmp_path):
    config = GeoMCPConfig.load(config_dir)
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(PermissionDenied):
        PathSandbox(config).resolve_for_read(outside)


def test_rejects_relative_path(config_dir):
    with pytest.raises(InvalidPathError):
        PathSandbox(GeoMCPConfig.load(config_dir)).resolve_for_read("../escape")


def test_rejects_write_to_raw_data(config_dir):
    config = GeoMCPConfig.load(config_dir)
    raw = Path(config.section("paths")["read_roots"][0]) / "raw.dat"
    with pytest.raises(PermissionDenied):
        PathSandbox(config).resolve_for_write(raw)


def test_rejects_symlink_escape(config_dir, tmp_path):
    config = GeoMCPConfig.load(config_dir)
    read_root = Path(config.section("paths")["read_roots"][0])
    outside = tmp_path.parent / "outside-dir"
    outside.mkdir(exist_ok=True)
    link = read_root / "escape-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(PermissionDenied):
        PathSandbox(config).resolve_for_read(link / "secret.dat")
