from __future__ import annotations
import uuid
from pathlib import Path
from geomcp.config import load_config, outputs_dir
from geomcp.scientific import das as core
from geomcp.services.permissions import PathPolicy
from geomcp.services.workspaces import WorkspaceManager

class DASService:
    def __init__(self, *, config_dir: str | Path | None=None):
        self.config=load_config(config_dir); self.policy=PathPolicy.from_config(self.config)
        self.workspaces=WorkspaceManager(self.config, policy=self.policy)
        das_cfg=self.config.get("geomcp", {}).get("das", {}) or {}
        self.max_points=int(das_cfg.get("max_points", 200_000))

    def _input(self, path, workspace: str | None=None):
        if workspace is not None:
            return self.workspaces.resolve_read(workspace, path)
        return self.policy.validate_read(path)

    def _output(self, output_path: str | Path | None, suffix: str, workspace: str | None=None) -> Path:
        if workspace is not None:
            candidate=Path(output_path) if output_path is not None else Path("das") / f"{uuid.uuid4().hex}{suffix}"
            if candidate.suffix.lower() != suffix:
                candidate=candidate.with_suffix(suffix)
            return self.workspaces.resolve_write(workspace, candidate)
        if output_path is None:
            base=outputs_dir(self.config) / "das"; candidate=base / f"{uuid.uuid4().hex}{suffix}"
        else:
            candidate=Path(output_path)
            if candidate.suffix.lower() != suffix:
                candidate=candidate.with_suffix(suffix)
        return self.policy.validate_write(candidate)

    def inspect(self, path, *, workspace: str | None=None):
        self.policy.assert_capability_allowed("das.inspect"); return core.inspect(self._input(path, workspace))

    def read_window(self, path, *, channel_start=None, channel_stop=None, sample_start=0, sample_stop=None, workspace: str | None=None):
        self.policy.assert_capability_allowed("das.read")
        return core.read_window(self._input(path, workspace), channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=self.max_points)

    def bandpass(self, path, *, freqmin, freqmax, channel_start=None, channel_stop=None, sample_start=0, sample_stop=None, output_path=None, workspace: str | None=None):
        self.policy.assert_capability_allowed("das.process"); out=self._output(output_path, ".npy", workspace)
        return core.bandpass(self._input(path, workspace), freqmin=freqmin, freqmax=freqmax, output_path=out, channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=self.max_points)

    def rms(self, path, *, channel_start=None, channel_stop=None, sample_start=0, sample_stop=None, workspace: str | None=None):
        self.policy.assert_capability_allowed("das.process")
        return core.rms(self._input(path, workspace), channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=self.max_points)

    def plot(self, path, *, channel_start=None, channel_stop=None, sample_start=0, sample_stop=None, output_path=None, dpi=150, workspace: str | None=None):
        self.policy.assert_capability_allowed("das.plot"); out=self._output(output_path, ".png", workspace)
        return core.plot(self._input(path, workspace), output_path=out, dpi=dpi, channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=self.max_points)
