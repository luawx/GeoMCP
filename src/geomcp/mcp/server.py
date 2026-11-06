"""GeoMCP MCP stdio server.

The MCP SDK is intentionally an optional dependency. Core/API/CLI remain usable
without it, which simplifies offline deployments that do not need an agent.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
from typing import Sequence
from geomcp.mcp.registry import ToolRegistry, build_registry

def create_server(
    registry: ToolRegistry | None = None,
    *,
    config_dir: str | Path | None = None,
):
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:
        raise RuntimeError('MCP support is not installed. Install GeoMCP with the "mcp" extra.') from exc

    active_registry = registry or build_registry(config_dir=config_dir)

    class RegisteredServer(MCPServer):
        async def list_tools(self):
            from mcp.types import Tool
            tools = await super().list_tools()
            tools.extend(Tool(name=d.name, description=d.description,
                input_schema=d.input_schema, output_schema=d.output_schema)
                for d in active_registry.list() if d.name.startswith("picking."))
            return tools

        async def call_tool(self, name, arguments, context=None):
            if name.startswith("picking."):
                import json
                import anyio
                import functools
                from mcp.types import CallToolResult, TextContent
                payload = await anyio.to_thread.run_sync(
                    functools.partial(active_registry.get(name).handler, **arguments))
                return CallToolResult(content=[TextContent(type="text", text=json.dumps(payload))],
                    structured_content=payload, is_error=not payload["success"])
            return await super().call_tool(name, arguments, context)

    server = RegisteredServer(
        "GeoMCP",
        instructions=(
            "Use GeoMCP only for registered research tools. Paths and configuration are fixed server-side. "
            "No arbitrary shell, arbitrary SSH, delete capability, or caller-selected config directory is exposed."
        ),
    )

    for definition in active_registry.list():
        if definition.name.startswith("picking."):
            continue
        server.add_tool(
            definition.handler,
            name=definition.name,
            description=definition.description,
            structured_output=True,
        )
    return server

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geomcp-mcp")
    parser.add_argument("--config-dir", default=None)
    args = parser.parse_args(argv)
    if args.config_dir:
        os.environ["GEOMCP_CONFIG_DIR"] = args.config_dir
    create_server(config_dir=args.config_dir).run(transport="stdio")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
