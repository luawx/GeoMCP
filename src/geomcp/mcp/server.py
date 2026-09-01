"""GeoMCP MCP stdio server."""

from __future__ import annotations

from mcp.server import MCPServer

from .registry import build_registry


def create_server() -> MCPServer:
    server = MCPServer("GeoMCP")
    specs = {spec.name: spec for spec in build_registry()}

    @server.tool(name="system.status", description=specs["system.status"].description)
    def system_status_tool() -> dict:
        return specs["system.status"].handler()

    @server.tool(name="filesystem.inspect", description=specs["filesystem.inspect"].description)
    def filesystem_inspect_tool(path: str) -> dict:
        return specs["filesystem.inspect"].handler(path=path)

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
