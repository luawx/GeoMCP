from __future__ import annotations
import uuid
from pathlib import Path
from geomcp.config import load_config, outputs_dir
from geomcp.scientific import das as core
from geomcp.services.permissions import PathPolicy

class DASService:
    def __init__(self, *, config_dir: str | Path | None=None):
        self.config=load_config(config_dir); self.policy=PathPolicy.from_config(self.config)
        das_cfg=self.config.get("geomcp", {}).get("das", {}) or {}
        self.max_points=int(das_cfg.get("max_points", 200_000))
    def _input(self, path): return self.policy.validate_read(path)
    def _output(self, output_path: str | Path | None, suffix: str) -> Path:
        if output_path is None:
            base=outputs_dir(self.config) / "das"; candidate=base / f"{uuid.uuid4().hex}{suffix}"
        else:
            candidate=Path(output_path)
            if candidate.suffix.lower() != suffix:
                candidate=candidate.with_suffix(suffix)
        return self.policy.validate_write(candidate)
    def inspect(self, path):
        self.policy.assert_capability_allowed("das.inspect"); return core.inspect(self._input(path))
    def read_window(self, path, *, channel_start=None, channel_stop=None, sample_start=0, sample_stop=None):
        self.policy.assert_capability_allowed("das.read")
        return core.read_window(self._input(path), channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=self.max_points)
    def bandpass(self, path, *, freqmin, freqmax, channel_start=None, channel_stop=None, sample_start=0, sample_stop=None, output_path=None):
        self.policy.assert_capability_allowed("das.process"); out=self._output(output_path, ".npy")
        return core.bandpass(self._input(path), freqmin=freqmin, freqmax=freqmax, output_path=out, channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=self.max_points)
    def rms(self, path, *, channel_start=None, channel_stop=None, sample_start=0, sample_stop=None):
        self.policy.assert_capability_allowed("das.process")
        return core.rms(self._input(path), channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=self.max_points)
    def plot(self, path, *, channel_start=None, channel_stop=None, sample_start=0, sample_stop=None, output_path=None, dpi=150):
        self.policy.assert_capability_allowed("das.plot"); out=self._output(output_path, ".png")
        return core.plot(self._input(path), output_path=out, dpi=dpi, channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=self.max_points)
