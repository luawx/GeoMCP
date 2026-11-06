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
    _register_picking(r, fixed_config, common)
    return r

def _register_picking(registry, config_dir, output_schema):
    """Keep the public picking boundary bounded, strict and server configured."""
    import json
    import math
    from geomcp.api import picking
    from geomcp.models import fail

    def obj(properties):
        return {"type": "object", "properties": properties, "additionalProperties": False}

    string = {"type": "string", "minLength": 1}
    nullable = {"type": ["string", "null"]}
    number = {"type": "number"}
    positive = {"type": "number", "exclusiveMinimum": 0}
    nonnegative = {"type": "number", "minimum": 0}
    integer = {"type": "integer", "minimum": 1}
    overrides = obj({
        "selection": obj({"start_time": nullable, "end_time": nullable,
            "receiver_ids": {"type": ["array", "null"], "items": string, "minItems": 1}}),
        "preprocessing": obj({"gap_policy": {"enum": ["split"]},
            "detrend": {"enum": ["none", "constant", "linear"]},
            "bandpass_hz": {"type": ["array", "null"], "items": positive, "minItems": 2, "maxItems": 2},
            "target_sampling_rate_hz": {"type": ["number", "null"], "exclusiveMinimum": 0}}),
        "chunking": obj({"core_duration_s": positive, "context_before_s": nonnegative,
            "context_after_s": nonnegative, "core_channels": integer,
            "context_channels": {"type": "integer", "minimum": 0}}),
        "postprocessing": obj({"dedup_window_s": nonnegative}),
        "output": obj({"save_native": {"type": "boolean"}}),
        "algorithm": obj({"p_threshold": {"type": "number", "minimum": 0, "maximum": 1},
            "s_threshold": {"type": "number", "minimum": 0, "maximum": 1},
            "min_peak_distance_s": positive, "batch_size": integer,
            "method": {"enum": ["recursive_sta_lta"]}, "sta_s": positive, "lta_s": positive,
            "threshold_on": positive, "threshold_off": positive, "min_trigger_s": nonnegative,
            "max_trigger_s": positive, "station_component": string}),
    })
    preview = {"type": "integer", "minimum": 0, "maximum": 100, "default": 20}
    workspace = {"workspace": nullable}
    # Canonical-column -> input-column mapping; only known canonical columns are accepted.
    mapping = obj({
        "columns": obj({name: string for name in (
            "pick_id", "waveform_id", "receiver_id", "phase", "time", "score", "score_type",
            "time_uncertainty_s", "backend_id", "model_id", "quality_flags")}),
        "phase_map": {"type": "object", "additionalProperties": {"type": "string", "enum": ["P", "S", "unknown"]}},
        "missing_phase": {"enum": ["unknown"]}, "score_type": string, "waveform_id": string,
    })
    definitions = {
        "backends": ({}, [], picking.backends),
        "presets": ({"backend_id": nullable}, [], picking.presets),
        "inspect": ({"waveform_manifest_ref": string, "geometry_ref": nullable,
            "preview_limit": preview, **workspace}, ["waveform_manifest_ref"], picking.inspect),
        "prepare": ({"waveform_manifest_ref": string, "geometry_ref": string,
            "preset_id": string, "preset_version": string, "overrides": overrides,
            "output_path": nullable, **workspace},
            ["waveform_manifest_ref", "geometry_ref", "preset_id", "preset_version"], picking.prepare),
        "validate": ({"prepared_ref": string, **workspace}, ["prepared_ref"], picking.validate),
        "run": ({"prepared_ref": string, **workspace}, ["prepared_ref"], picking.run),
        "result": ({"job_id": string, "preview_limit": preview}, ["job_id"], picking.result),
        "import": ({"input_ref": string, "geometry_ref": string,
            "format": {"type": "string", "enum": ["external_csv"], "default": "external_csv"},
            "mapping": mapping, "output_path": nullable, **workspace},
            ["input_ref", "geometry_ref"], picking.import_picks),
    }

    def check(value, schema, path="request"):
        types = schema.get("type")
        if types:
            types = types if isinstance(types, list) else [types]
            valid = {"object": isinstance(value, dict), "array": isinstance(value, list),
                "string": isinstance(value, str), "null": value is None,
                "boolean": isinstance(value, bool), "integer": type(value) is int,
                "number": type(value) in (int, float) and math.isfinite(value)}
            if not any(valid[t] for t in types):
                raise ValueError(f"{path}: invalid type")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path}: unsupported value")
        if isinstance(value, dict):
            properties = schema.get("properties", {})
            if schema.get("additionalProperties") is False and set(value) - set(properties):
                raise ValueError(f"{path}: unknown fields {sorted(set(value) - set(properties))}")
            if set(schema.get("required", [])) - set(value):
                raise ValueError(f"{path}: missing required fields")
            for key, item in value.items():
                check(item, properties.get(key, schema.get("additionalProperties", {})), path + "." + key)
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
                raise ValueError(f"{path}: invalid array length")
            for item in value:
                check(item, schema.get("items", {}), path)
        if isinstance(value, str) and len(value) < schema.get("minLength", 0):
            raise ValueError(f"{path}: empty string")
        if type(value) in (int, float):
            if not math.isfinite(value):
                raise ValueError(f"{path}: non-finite number")
            for bound, test in (("minimum", lambda a,b:a<b), ("maximum", lambda a,b:a>b),
                                ("exclusiveMinimum", lambda a,b:a<=b)):
                if bound in schema and test(value, schema[bound]):
                    raise ValueError(f"{path}: outside allowed range")

    def make_handler(function, schema):
        def handler(**kwargs):
            try:
                check(kwargs, schema)
            except ValueError as exc:
                return fail("INVALID_ARGUMENT", str(exc)[:2000]).to_dict()
            result = function(config_dir=config_dir, **kwargs).to_dict()
            if len(json.dumps(result, ensure_ascii=False, default=str).encode("utf-8")) > 65536:
                return fail("RESPONSE_TOO_LARGE", "Picking response exceeds 64 KiB; use artifact references.").to_dict()
            return result
        return handler

    for name, (properties, required, function) in definitions.items():
        schema = obj(properties)
        schema["required"] = required
        registry.register(ToolDefinition("picking." + name,
            "Controlled picking " + name + "; no model downloads or caller-selected execution configuration.",
            schema, output_schema, make_handler(function, schema)))
