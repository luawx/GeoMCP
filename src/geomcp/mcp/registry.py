"""Explicit MCP tool registry independent of transport implementation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from geomcp.api import das as das_api, filesystem as filesystem_api, jobs as jobs_api, system as system_api

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
        if tool.name in self._tools: raise ValueError(f"Duplicate tool: {tool.name}")
        self._tools[tool.name] = tool
    def get(self, name: str) -> ToolDefinition: return self._tools[name]
    def list(self) -> tuple[ToolDefinition, ...]: return tuple(self._tools.values())

def _system_status(config_dir: str | None=None) -> dict[str, Any]: return system_api.status(config_dir).to_dict()
def _filesystem_inspect(path: str, config_dir: str | None=None) -> dict[str, Any]: return filesystem_api.inspect(path, config_dir=config_dir).to_dict()
def _job_list(limit: int=100, status: str | None=None, config_dir: str | None=None) -> dict[str, Any]: return jobs_api.list_jobs(limit=limit,status=status,config_dir=config_dir).to_dict()
def _job_status(job_id: str, config_dir: str | None=None) -> dict[str, Any]: return jobs_api.status(job_id,config_dir=config_dir).to_dict()
def _job_result(job_id: str, config_dir: str | None=None) -> dict[str, Any]: return jobs_api.result(job_id,config_dir=config_dir).to_dict()
def _job_cancel(job_id: str, config_dir: str | None=None) -> dict[str, Any]: return jobs_api.cancel(job_id,config_dir=config_dir).to_dict()
def _das_inspect(path: str, config_dir: str | None=None) -> dict[str, Any]: return das_api.inspect(path,config_dir=config_dir).to_dict()
def _das_read_window(path: str, channel_start: int | None=None, channel_stop: int | None=None, sample_start: int=0, sample_stop: int | None=None, config_dir: str | None=None) -> dict[str, Any]:
    return das_api.read_window(path,channel_start=channel_start,channel_stop=channel_stop,sample_start=sample_start,sample_stop=sample_stop,config_dir=config_dir).to_dict()
def _das_bandpass(path: str, freqmin: float, freqmax: float, channel_start: int | None=None, channel_stop: int | None=None, sample_start: int=0, sample_stop: int | None=None, output_path: str | None=None, config_dir: str | None=None) -> dict[str, Any]:
    return das_api.bandpass(path,freqmin=freqmin,freqmax=freqmax,channel_start=channel_start,channel_stop=channel_stop,sample_start=sample_start,sample_stop=sample_stop,output_path=output_path,config_dir=config_dir).to_dict()
def _das_rms(path: str, channel_start: int | None=None, channel_stop: int | None=None, sample_start: int=0, sample_stop: int | None=None, config_dir: str | None=None) -> dict[str, Any]:
    return das_api.rms(path,channel_start=channel_start,channel_stop=channel_stop,sample_start=sample_start,sample_stop=sample_stop,config_dir=config_dir).to_dict()
def _das_plot(path: str, channel_start: int | None=None, channel_stop: int | None=None, sample_start: int=0, sample_stop: int | None=None, output_path: str | None=None, dpi: int=150, config_dir: str | None=None) -> dict[str, Any]:
    return das_api.plot(path,channel_start=channel_start,channel_stop=channel_stop,sample_start=sample_start,sample_stop=sample_stop,output_path=output_path,dpi=dpi,config_dir=config_dir).to_dict()

def build_registry() -> ToolRegistry:
    r=ToolRegistry()
    common={"type":"object","properties":{"success":{"type":"boolean"},"data":{},"error_code":{"type":["string","null"]},"error_message":{"type":["string","null"]},"metadata":{"type":"object"}},"required":["success","data","error_code","error_message","metadata"]}
    def reg(name: str, desc: str, handler: ToolHandler, props: dict[str, Any] | None=None, required: list[str] | None=None) -> None:
        schema={"type":"object","properties":props or {}}
        if required: schema["required"]=required
        r.register(ToolDefinition(name,desc,schema,common,handler))
    reg("system.status","Return GeoMCP server status and configuration health.",_system_status,{"config_dir":{"type":["string","null"]}})
    reg("filesystem.inspect","Inspect metadata for a path after server-side path permission checks.",_filesystem_inspect,{"path":{"type":"string"},"config_dir":{"type":["string","null"]}},["path"])
    reg("job.list","List persisted GeoMCP jobs.",_job_list,{"limit":{"type":"integer"},"status":{"type":["string","null"]},"config_dir":{"type":["string","null"]}})
    reg("job.status","Return one job's lifecycle state.",_job_status,{"job_id":{"type":"string"},"config_dir":{"type":["string","null"]}},["job_id"])
    reg("job.result","Return one job's result or error.",_job_result,{"job_id":{"type":"string"},"config_dir":{"type":["string","null"]}},["job_id"])
    reg("job.cancel","Cancel a queued or running job without deleting data.",_job_cancel,{"job_id":{"type":"string"},"config_dir":{"type":["string","null"]}},["job_id"])
    window={"path":{"type":"string"},"channel_start":{"type":["integer","null"]},"channel_stop":{"type":["integer","null"]},"sample_start":{"type":"integer"},"sample_stop":{"type":["integer","null"]},"config_dir":{"type":["string","null"]}}
    reg("das.inspect","Inspect DAS metadata with DASPy after path checks.",_das_inspect,{"path":{"type":"string"},"config_dir":{"type":["string","null"]}},["path"])
    reg("das.read_window","Read a bounded DAS window; large reads are rejected.",_das_read_window,window,["path"])
    reg("das.bandpass","Band-pass a bounded DAS window after Nyquist validation and save to outputs.",_das_bandpass,{**window,"freqmin":{"type":"number"},"freqmax":{"type":"number"},"output_path":{"type":["string","null"]}},["path","freqmin","freqmax"])
    reg("das.rms","Compute per-channel RMS for a bounded DAS window.",_das_rms,window,["path"])
    reg("das.plot","Render a bounded DAS waveform window to an allowed output path.",_das_plot,{**window,"output_path":{"type":["string","null"]},"dpi":{"type":"integer"}},["path"])
    return r
