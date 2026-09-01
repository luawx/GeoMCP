"""DASPy-backed scientific core for bounded DAS operations."""
from __future__ import annotations
from datetime import timedelta
from pathlib import Path
from typing import Any
from geomcp.exceptions import ScientificToolError

def _daspy_read():
    try:
        from daspy import read
    except ImportError as exc:
        raise ScientificToolError('DAS support is not installed. Install GeoMCP with the "das" extra.') from exc
    return read

def _numpy():
    try: import numpy as np
    except ImportError as exc: raise ScientificToolError('NumPy is required for DAS processing. Install GeoMCP with the "das" extra.') from exc
    return np

def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)): return value
    return str(value)

def section_metadata(sec: Any, path: str | Path) -> dict[str, Any]:
    shape = tuple(int(x) for x in getattr(sec, "shape", getattr(getattr(sec, "data", None), "shape", ())))
    nch = int(getattr(sec, "nch", shape[0] if len(shape) >= 1 else 0))
    nt = int(getattr(sec, "nt", shape[1] if len(shape) >= 2 else 0))
    return {
        "path": str(path), "shape": list(shape), "channels": nch, "samples": nt,
        "sampling_rate_hz": _safe_value(getattr(sec, "fs", None)), "channel_spacing_m": _safe_value(getattr(sec, "dx", None)),
        "start_channel": _safe_value(getattr(sec, "start_channel", None)), "end_channel": _safe_value(getattr(sec, "end_channel", None)),
        "start_time": _safe_value(getattr(sec, "start_time", None)), "end_time": _safe_value(getattr(sec, "end_time", None)),
        "gauge_length_m": _safe_value(getattr(sec, "gauge_length", None)), "data_type": _safe_value(getattr(sec, "data_type", None)),
    }

def inspect(path: str | Path) -> dict[str, Any]:
    sec = _daspy_read()(str(path), headonly=True)
    return section_metadata(sec, path)

def _validate_window(meta: dict[str, Any], *, channel_start: int | None, channel_stop: int | None, sample_start: int, sample_stop: int | None, max_points: int) -> tuple[int | None, int | None, int, int]:
    if sample_start < 0: raise ScientificToolError("sample_start must be >= 0")
    total_samples = int(meta.get("samples") or 0); total_channels = int(meta.get("channels") or 0)
    stop = total_samples if sample_stop is None else int(sample_stop)
    if stop <= sample_start: raise ScientificToolError("sample_stop must be greater than sample_start")
    if total_samples and stop > total_samples: raise ScientificToolError(f"sample_stop exceeds available samples ({total_samples})")
    c1 = channel_start; c2 = channel_stop
    if c1 is not None and c2 is not None and c2 <= c1: raise ScientificToolError("channel_stop must be greater than channel_start")
    selected_channels = (c2 - c1) if c1 is not None and c2 is not None else total_channels
    if selected_channels <= 0: raise ScientificToolError("Unable to determine a non-empty channel window")
    points = selected_channels * (stop - sample_start)
    if points > max_points: raise ScientificToolError(f"Requested DAS window has {points} points; limit is {max_points}. Narrow channels or samples.")
    return c1, c2, sample_start, stop

def _read_bounded(path: str | Path, *, channel_start: int | None=None, channel_stop: int | None=None, sample_start: int=0, sample_stop: int | None=None, max_points: int=200_000):
    meta = inspect(path)
    c1, c2, s1, s2 = _validate_window(meta, channel_start=channel_start, channel_stop=channel_stop, sample_start=sample_start, sample_stop=sample_stop, max_points=max_points)
    kwargs = {}
    if c1 is not None: kwargs["ch1"] = int(c1)
    if c2 is not None: kwargs["ch2"] = int(c2)
    sec = _daspy_read()(str(path), **kwargs)
    data = getattr(sec, "data", None)
    if data is None: raise ScientificToolError("DASPy returned a section without data")
    sec.data = data[:, s1:s2]
    fs = getattr(sec, "fs", None)
    start_time = getattr(sec, "start_time", None)
    if s1 and fs and start_time is not None:
        try: sec.start_time = start_time + timedelta(seconds=s1 / float(fs))
        except Exception: pass
    return sec, section_metadata(sec, path)

def read_window(path: str | Path, **kwargs) -> dict[str, Any]:
    sec, meta = _read_bounded(path, **kwargs); np = _numpy(); arr = np.asarray(sec.data)
    return {"metadata": meta, "data": arr.tolist()}

def bandpass(path: str | Path, *, freqmin: float, freqmax: float, output_path: str | Path, **kwargs) -> dict[str, Any]:
    meta = inspect(path); fs = meta.get("sampling_rate_hz")
    if fs is None: raise ScientificToolError("Sampling rate is missing; cannot validate bandpass")
    fs = float(fs)
    if not (0 < float(freqmin) < float(freqmax) < fs / 2): raise ScientificToolError(f"Bandpass must satisfy 0 < freqmin < freqmax < Nyquist ({fs/2:g} Hz)")
    sec, window_meta = _read_bounded(path, **kwargs); sec.bandpass(float(freqmin), float(freqmax))
    np = _numpy(); output = Path(output_path); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream: np.save(stream, np.asarray(sec.data))
    return {"output_path": str(output), "metadata": window_meta, "freqmin_hz": float(freqmin), "freqmax_hz": float(freqmax)}

def rms(path: str | Path, **kwargs) -> dict[str, Any]:
    sec, meta = _read_bounded(path, **kwargs); np = _numpy(); arr = np.asarray(sec.data, dtype=float)
    values = np.sqrt(np.mean(np.square(arr), axis=1))
    return {"metadata": meta, "rms_per_channel": values.tolist()}

def plot(path: str | Path, *, output_path: str | Path, dpi: int=150, **kwargs) -> dict[str, Any]:
    if dpi < 50 or dpi > 600: raise ScientificToolError("dpi must be between 50 and 600")
    sec, meta = _read_bounded(path, **kwargs)
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
    except ImportError as exc: raise ScientificToolError('Matplotlib is required for DAS plotting. Install GeoMCP with the "das" extra.') from exc
    output = Path(output_path); output.parent.mkdir(parents=True, exist_ok=True)
    sec.plot(savefig=str(output), dpi=int(dpi))
    return {"output_path": str(output), "metadata": meta, "dpi": int(dpi)}
