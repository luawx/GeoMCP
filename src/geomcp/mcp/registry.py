"""Explicit MCP tool registry independent of transport implementation."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from geomcp.api import das as das_api, filesystem as filesystem_api, jobs as jobs_api, system as system_api, workspace as workspace_api

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

def _compact_window(payload: dict[str, Any], *, preview_channels: int=3, preview_samples: int=8) -> dict[str, Any]:
    if not payload.get("success"):
        return payload
    data = payload.get("data")
    if not isinstance(data, dict):
        return payload
    rows = data.get("data")
    if not isinstance(rows, list):
        return payload
    channel_count = len(rows)
    sample_count = len(rows[0]) if rows and isinstance(rows[0], list) else 0
    preview = [
        row[:preview_samples] if isinstance(row, list) else row
        for row in rows[:preview_channels]
    ]
    payload["data"] = {
        "metadata": data.get("metadata", {}),
        "shape": [channel_count, sample_count],
        "point_count": sum(len(row) for row in rows if isinstance(row, list)),
        "preview": preview,
        "preview_shape": [
            min(channel_count, preview_channels),
            min(sample_count, preview_samples),
        ],
        "truncated": channel_count > preview_channels or sample_count > preview_samples,
    }
    return payload

def build_registry(config_dir: str | Path | None=None) -> ToolRegistry:
    fixed_config = str(Path(config_dir).expanduser().resolve()) if config_dir is not None else None
    r = ToolRegistry()
    common = {
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

    def reg(name: str, desc: str, handler: ToolHandler, props: dict[str, Any] | None=None, required: list[str] | None=None) -> None:
        schema = {"type": "object", "properties": props or {}}
        if required:
            schema["required"] = required
        r.register(ToolDefinition(name, desc, schema, common, handler))

    def system_status() -> dict[str, Any]:
        return system_api.status(fixed_config).to_dict()

    def filesystem_inspect(path: str) -> dict[str, Any]:
        return filesystem_api.inspect(path, config_dir=fixed_config).to_dict()

    def workspace_list() -> dict[str, Any]:
        return workspace_api.list_workspaces(config_dir=fixed_config).to_dict()

    def job_list(limit: int=100, status: str | None=None) -> dict[str, Any]:
        return jobs_api.list_jobs(limit=limit, status=status, config_dir=fixed_config).to_dict()

    def job_status(job_id: str) -> dict[str, Any]:
        return jobs_api.status(job_id, config_dir=fixed_config).to_dict()

    def job_result(job_id: str) -> dict[str, Any]:
        return jobs_api.result(job_id, config_dir=fixed_config).to_dict()

    def job_cancel(job_id: str) -> dict[str, Any]:
        return jobs_api.cancel(job_id, config_dir=fixed_config).to_dict()

    def job_submit_healthcheck(executor: str="cpu") -> dict[str, Any]:
        return jobs_api.submit_healthcheck(executor=executor, config_dir=fixed_config).to_dict()

    def das_inspect(path: str, workspace: str | None=None) -> dict[str, Any]:
        return das_api.inspect(path, workspace=workspace, config_dir=fixed_config).to_dict()

    def das_read_window(
        path: str,
        channel_start: int | None=None,
        channel_stop: int | None=None,
        sample_start: int=0,
        sample_stop: int | None=None,
        workspace: str | None=None,
    ) -> dict[str, Any]:
        result = das_api.read_window(
            path,
            channel_start=channel_start,
            channel_stop=channel_stop,
            sample_start=sample_start,
            sample_stop=sample_stop,
            workspace=workspace,
            config_dir=fixed_config,
        ).to_dict()
        return _compact_window(result)

    def das_bandpass(
        path: str,
        freqmin: float,
        freqmax: float,
        channel_start: int | None=None,
        channel_stop: int | None=None,
        sample_start: int=0,
        sample_stop: int | None=None,
        output_path: str | None=None,
        workspace: str | None=None,
    ) -> dict[str, Any]:
        return das_api.bandpass(
            path,
            freqmin=freqmin,
            freqmax=freqmax,
            channel_start=channel_start,
            channel_stop=channel_stop,
            sample_start=sample_start,
            sample_stop=sample_stop,
            output_path=output_path,
            workspace=workspace,
            config_dir=fixed_config,
        ).to_dict()

    def das_rms(
        path: str,
        channel_start: int | None=None,
        channel_stop: int | None=None,
        sample_start: int=0,
        sample_stop: int | None=None,
        workspace: str | None=None,
    ) -> dict[str, Any]:
        return das_api.rms(
            path,
            channel_start=channel_start,
            channel_stop=channel_stop,
            sample_start=sample_start,
            sample_stop=sample_stop,
            workspace=workspace,
            config_dir=fixed_config,
        ).to_dict()

    def das_plot(
        path: str,
        channel_start: int | None=None,
        channel_stop: int | None=None,
        sample_start: int=0,
        sample_stop: int | None=None,
        output_path: str | None=None,
        dpi: int=150,
        workspace: str | None=None,
    ) -> dict[str, Any]:
        return das_api.plot(
            path,
            channel_start=channel_start,
            channel_stop=channel_stop,
            sample_start=sample_start,
            sample_stop=sample_stop,
            output_path=output_path,
            dpi=dpi,
            workspace=workspace,
            config_dir=fixed_config,
        ).to_dict()

    reg("system.status", "Return GeoMCP server status and configuration health.", system_status)
    reg(
        "filesystem.inspect",
        "Inspect metadata for a path after server-side path permission checks.",
        filesystem_inspect,
        {"path": {"type": "string"}},
        ["path"],
    )
    reg(
        "workspace.list",
        "List configured Workspace/Data Regions that the Agent may use for workspace-relative input and output paths.",
        workspace_list,
    )
    reg(
        "job.list",
        "List persisted GeoMCP jobs.",
        job_list,
        {"limit": {"type": "integer"}, "status": {"type": ["string", "null"]}},
    )
    reg(
        "job.status",
        "Return one job's lifecycle state.",
        job_status,
        {"job_id": {"type": "string"}},
        ["job_id"],
    )
    reg(
        "job.result",
        "Return one job's result or error.",
        job_result,
        {"job_id": {"type": "string"}},
        ["job_id"],
    )
    reg(
        "job.cancel",
        "Cancel a queued or running job without deleting data.",
        job_cancel,
        {"job_id": {"type": "string"}},
        ["job_id"],
    )
    reg(
        "job.submit_healthcheck",
        "Submit only the built-in CPU or GPU healthcheck task. No arbitrary task, shell, SSH, host or command is accepted.",
        job_submit_healthcheck,
        {"executor": {"type": "string", "enum": ["cpu", "gpu"]}},
    )
    window = {
        "path": {"type": "string"},
        "workspace": {"type": ["string", "null"]},
        "channel_start": {"type": ["integer", "null"]},
        "channel_stop": {"type": ["integer", "null"]},
        "sample_start": {"type": "integer"},
        "sample_stop": {"type": ["integer", "null"]},
    }
    reg(
        "das.inspect",
        "Inspect DAS metadata after path checks. If workspace is set, path must be relative to that workspace read root.",
        das_inspect,
        {"path": {"type": "string"}, "workspace": {"type": ["string", "null"]}},
        ["path"],
    )
    reg(
        "das.read_window",
        "Read a bounded DAS window and return metadata plus a compact preview. Workspace paths are relative and sandboxed.",
        das_read_window,
        window,
        ["path"],
    )
    reg(
        "das.bandpass",
        "Band-pass a bounded DAS window. With workspace set, input/output paths are relative to its read/write roots.",
        das_bandpass,
        {
            **window,
            "freqmin": {"type": "number"},
            "freqmax": {"type": "number"},
            "output_path": {"type": ["string", "null"]},
        },
        ["path", "freqmin", "freqmax"],
    )
    reg("das.rms", "Compute per-channel RMS for a bounded DAS window.", das_rms, window, ["path"])
    reg(
        "das.plot",
        "Render a bounded DAS waveform window. With workspace set, output_path is relative to its write root.",
        das_plot,
        {
            **window,
            "output_path": {"type": ["string", "null"]},
            "dpi": {"type": "integer"},
        },
        ["path"],
    )
    return r
