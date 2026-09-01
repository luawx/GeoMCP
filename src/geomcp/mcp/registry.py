"""Explicit MCP tool registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from geomcp.api.filesystem import inspect as filesystem_inspect
from geomcp.api.system import status as system_status


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[..., Any]


def _system_status() -> dict[str, Any]:
    return system_status().to_dict()


def _filesystem_inspect(path: str) -> dict[str, Any]:
    return filesystem_inspect(path).to_dict()


def build_registry() -> tuple[ToolSpec, ...]:
    result_schema = {
        "type": "object",
        "required": ["success", "data", "error_code", "error_message", "metadata"],
    }
    return (
        ToolSpec(
            name="system.status",
            description="Return GeoMCP status and configuration location.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            output_schema=result_schema,
            handler=_system_status,
        ),
        ToolSpec(
            name="filesystem.inspect",
            description="Inspect metadata for one path after server-side sandbox validation.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
            output_schema=result_schema,
            handler=_filesystem_inspect,
        ),
    )
