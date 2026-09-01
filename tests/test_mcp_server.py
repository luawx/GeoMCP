import asyncio
from pathlib import Path
from mcp import Client
from geomcp.mcp.server import create_server

def write_config(config_dir: Path, root: Path) -> None:
    out = root / "out"
    runtime = out / "runtime"
    out.mkdir(parents=True)
    runtime.mkdir()
    config_dir.mkdir()
    files = {
        "geomcp.yaml": (
            f"name: GeoMCP\ncontrol_node: '1012'\ngpu_node: '1015'\n"
            f"runtime_dir: {runtime}\noutputs_dir: {out}\n"
        ),
        "paths.yaml": f"read_roots:\n  - {root}\nwrite_roots:\n  - {out}\n",
        "permissions.yaml": (
            "default_policy: deny\n"
            "allowed_capabilities: [filesystem.inspect, filesystem.read, filesystem.write, system.status, "
            "job.list, job.status, job.result, job.logs, job.cancel, job.submit_healthcheck, "
            "das.inspect, das.read, das.process, das.plot]\n"
            "denied_capabilities: [delete, recursive_delete, arbitrary_shell, arbitrary_ssh]\n"
        ),
        "executors.yaml": "default_executor: cpu\ncpu:\n  node: '1012'\n",
        "rag.yaml": "enabled: false\n",
    }
    for name, text in files.items():
        (config_dir / name).write_text(text, encoding="utf-8")

def test_mcp_server_lists_and_calls_registry_tools(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    sample = root / "sample.dat"
    sample.write_text("abc", encoding="utf-8")
    config_dir = tmp_path / "config"
    write_config(config_dir, root)

    async def exercise() -> None:
        async with Client(create_server(config_dir=config_dir), raise_exceptions=True) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools.tools] == [
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

            result = await client.call_tool("filesystem.inspect", {"path": str(sample)})
            assert result.is_error is False
            assert result.structured_content is not None
            assert result.structured_content["success"] is True
            assert result.structured_content["data"]["size_bytes"] == 3

    asyncio.run(exercise())
