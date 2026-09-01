from geomcp.mcp.registry import _compact_window, build_registry

def test_registry_contains_hardened_step_06_10_tools():
    registry = build_registry()
    names = [tool.name for tool in registry.list()]
    assert names == [
        "system.status",
        "filesystem.inspect",
        "job.list",
        "job.status",
        "job.result",
        "job.cancel",
        "job.submit_healthcheck",
        "das.inspect",
        "das.read_window",
        "das.bandpass",
        "das.rms",
        "das.plot",
    ]
    assert all("shell" not in name for name in names)
    assert all("delete" not in name for name in names)
    assert all("ssh" not in name for name in names)
    assert all("config_dir" not in tool.input_schema.get("properties", {}) for tool in registry.list())

def test_mcp_window_payload_is_compact():
    payload = {
        "success": True,
        "data": {
            "metadata": {"sampling_rate_hz": 100},
            "data": [[float(i + j) for j in range(20)] for i in range(5)],
        },
        "error_code": None,
        "error_message": None,
        "metadata": {},
    }
    compact = _compact_window(payload)
    assert "data" not in compact["data"]
    assert compact["data"]["shape"] == [5, 20]
    assert compact["data"]["point_count"] == 100
    assert compact["data"]["preview_shape"] == [3, 8]
    assert compact["data"]["truncated"] is True
