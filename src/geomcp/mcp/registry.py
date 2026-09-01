"""Explicit MCP tool registry independent of transport implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from geomcp.api import filesystem as filesystem_api
from geomcp.api import system as system_api

ToolHandler = Callable[..., dict[str, Any]]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        return self._tools[name]

    def list(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())


def _system_status(config_dir: str | None = None) -> dict[str, Any]:
    return system_api.status(config_dir).to_dict()


def _filesystem_inspect(path: str, config_dir: str | None = None) -> dict[str, Any]:
    return filesystem_api.inspect(path, config_dir=config_dir).to_dict()


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    common_output = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "data": {},
            "error_code": {"type": ["string", "null"]},
            "error_message": {"type": ["string", "null"]},
            "metadata": {"type": "object"},
        },
        "required": ["success", "data", "error_code", "error_message", "metadata"],
    }
    registry.register(
        ToolDefinition(
            name="system.status",
            description="Return GeoMCP server status and configuration health.",
            input_schema={
                "type": "object",
                "properties": {"config_dir": {"type": ["string", "null"]}},
            },
            output_schema=common_output,
            handler=_system_status,
        )
    )
    registry.register(
        ToolDefinition(
            name="filesystem.inspect",
            description="Inspect metadata for a path after server-side path permission checks.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "config_dir": {"type": ["string", "null"]},
                },
                "required": ["path"],
            },
            output_schema=common_output,
            handler=_filesystem_inspect,
        )
    )
    return registry
