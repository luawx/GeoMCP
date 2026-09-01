"""GeoMCP MCP stdio server.

The MCP SDK is intentionally an optional dependency. Core/API/CLI remain usable
without it, which simplifies offline deployments that do not need an agent.
"""

from __future__ import annotations

import argparse
import os
from typing import Sequence

from geomcp.api import filesystem as filesystem_api
from geomcp.api import system as system_api


def create_server():
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError('MCP support is not installed. Install GeoMCP with the "mcp" extra.') from exc

    server = MCPServer(
        "GeoMCP",
        instructions=(
            "Use GeoMCP only for registered research tools. Paths are checked server-side. "
            "No arbitrary shell, arbitrary SSH, or delete capability is exposed."
        ),
    )

    @server.tool(name="system.status", description="Return GeoMCP status and configuration health.")
    def system_status(config_dir: str | None = None) -> dict:
        return system_api.status(config_dir).to_dict()

    @server.tool(
        name="filesystem.inspect",
        description="Inspect an allowed server path. Requests outside configured read roots are denied.",
    )
    def filesystem_inspect(path: str, config_dir: str | None = None) -> dict:
        return filesystem_api.inspect(path, config_dir=config_dir).to_dict()

    return server


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geomcp-mcp")
    parser.add_argument("--config-dir", default=None)
    args = parser.parse_args(argv)
    if args.config_dir:
        os.environ["GEOMCP_CONFIG_DIR"] = args.config_dir
    create_server().run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
