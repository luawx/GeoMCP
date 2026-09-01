from geomcp.mcp.registry import build_registry

def test_registry_contains_step_06_10_safe_tools():
    registry = build_registry()
    names = [tool.name for tool in registry.list()]
    assert names == [
        "system.status",
        "filesystem.inspect",
        "job.list",
        "job.status",
        "job.result",
        "job.cancel",
        "das.inspect",
        "das.read_window",
        "das.bandpass",
        "das.rms",
        "das.plot",
    ]
    assert all("shell" not in name for name in names)
    assert all("delete" not in name for name in names)
    assert all("ssh" not in name for name in names)
