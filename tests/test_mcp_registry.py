from geomcp.mcp.registry import build_registry


def test_registry_contains_only_initial_safe_tools():
    registry = build_registry()
    names = [tool.name for tool in registry.list()]
    assert names == ["system.status", "filesystem.inspect"]
    assert all("shell" not in name for name in names)
    assert all("delete" not in name for name in names)
    assert all("ssh" not in name for name in names)
