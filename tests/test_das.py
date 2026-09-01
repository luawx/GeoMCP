from pathlib import Path
import numpy as np
from geomcp.api import das
from geomcp.cli.main import main
from geomcp.scientific import das as core

class FakeSection:
    def __init__(self, data, *, start_channel=10):
        self.data = np.array(data, dtype=float)
        self.fs = 100.0
        self.dx = 2.0
        self.start_channel = start_channel
        self.start_time = None
        self.gauge_length = 5.0
        self.data_type = "strain rate"
        self.band = None

    @property
    def shape(self):
        return self.data.shape

    @property
    def nch(self):
        return self.data.shape[0]

    @property
    def nt(self):
        return self.data.shape[1]

    @property
    def end_channel(self):
        return self.start_channel + self.nch

    @property
    def end_time(self):
        return None

    def bandpass(self, a, b):
        self.band = (a, b)
        self.data = self.data * 2

    def plot(self, savefig, dpi=150):
        Path(savefig).write_bytes(b"png")

def make_fake_read(calls):
    def fake_read(path, headonly=False, chmin=None, chmax=None, spmin=None, spmax=None):
        calls.append(
            {
                "headonly": headonly,
                "chmin": chmin,
                "chmax": chmax,
                "spmin": spmin,
                "spmax": spmax,
            }
        )
        data = np.arange(40, dtype=float).reshape(4, 10)
        start_channel = 10
        if chmin is not None or chmax is not None:
            start = 0 if chmin is None else max(0, chmin - 10)
            stop = 4 if chmax is None else min(4, chmax - 10)
            data = data[start:stop]
            start_channel = 10 + start
        if spmin is not None or spmax is not None:
            start = 0 if spmin is None else spmin
            stop = data.shape[1] if spmax is None else spmax
            data = data[:, start:stop]
        if headonly:
            data = np.zeros((4, 10), dtype=float)
            start_channel = 10
        return FakeSection(data, start_channel=start_channel)
    return fake_read

def test_das_inspect_window_rms_bandpass_plot(config_factory, monkeypatch):
    config_dir, root, _, _ = config_factory()
    sample = root / "sample.h5"
    sample.write_bytes(b"fake")
    calls = []
    monkeypatch.setattr(core, "_daspy_read", lambda: make_fake_read(calls))

    meta = das.inspect(sample, config_dir=config_dir)
    assert meta.success
    assert meta.data["sampling_rate_hz"] == 100.0
    assert main(["--config-dir", str(config_dir), "das", "inspect", str(sample), "--json"]) == 0

    window = das.read_window(
        sample,
        channel_start=10,
        channel_stop=12,
        sample_start=2,
        sample_stop=5,
        config_dir=config_dir,
    )
    assert window.success
    assert len(window.data["data"]) == 2
    assert len(window.data["data"][0]) == 3
    bounded = [c for c in calls if not c["headonly"]][-1]
    assert bounded == {
        "headonly": False,
        "chmin": 10,
        "chmax": 12,
        "spmin": 2,
        "spmax": 5,
    }

    rr = das.rms(
        sample,
        channel_start=10,
        channel_stop=12,
        sample_start=0,
        sample_stop=4,
        config_dir=config_dir,
    )
    assert rr.success
    assert len(rr.data["rms_per_channel"]) == 2

    bp = das.bandpass(
        sample,
        freqmin=1,
        freqmax=20,
        channel_start=10,
        channel_stop=12,
        sample_start=0,
        sample_stop=4,
        config_dir=config_dir,
    )
    assert bp.success
    assert Path(bp.data["output_path"]).is_file()

    pl = das.plot(
        sample,
        channel_start=10,
        channel_stop=12,
        sample_start=0,
        sample_stop=4,
        config_dir=config_dir,
    )
    assert pl.success
    assert Path(pl.data["output_path"]).is_file()

def test_das_rejects_nyquist_and_large_window(config_factory, monkeypatch):
    config_dir, root, _, _ = config_factory()
    sample = root / "sample.h5"
    sample.write_bytes(b"fake")
    calls = []
    monkeypatch.setattr(core, "_daspy_read", lambda: make_fake_read(calls))

    bad = das.bandpass(
        sample,
        freqmin=1,
        freqmax=60,
        channel_start=10,
        channel_stop=12,
        sample_start=0,
        sample_stop=4,
        config_dir=config_dir,
    )
    assert not bad.success

    too_big = das.read_window(
        sample,
        channel_start=10,
        channel_stop=200,
        sample_start=0,
        sample_stop=10,
        config_dir=config_dir,
    )
    assert not too_big.success


def test_das_workspace_relative_input_and_output(config_factory, monkeypatch):
    config_dir, root, _, outputs = config_factory()
    sample = root / "raw" / "sample.h5"
    sample.parent.mkdir()
    sample.write_bytes(b"fake")
    calls = []
    monkeypatch.setattr(core, "_daspy_read", lambda: make_fake_read(calls))

    meta = das.inspect("raw/sample.h5", workspace="test", config_dir=config_dir)
    assert meta.success
    assert meta.data["path"] == str(sample.resolve())

    bp = das.bandpass(
        "raw/sample.h5",
        workspace="test",
        freqmin=1,
        freqmax=20,
        channel_start=10,
        channel_stop=12,
        sample_start=0,
        sample_stop=4,
        output_path="processed/event001/filter.npy",
        config_dir=config_dir,
    )
    assert bp.success
    assert Path(bp.data["output_path"]) == (outputs / "processed" / "event001" / "filter.npy").resolve()
    assert Path(bp.data["output_path"]).is_file()

    rejected = das.inspect(str(sample), workspace="test", config_dir=config_dir)
    assert not rejected.success
    assert rejected.error_code == "INVALIDPATHERROR"
