from pathlib import Path
import numpy as np
from geomcp.api import das
from geomcp.cli.main import main
from geomcp.scientific import das as core

class FakeSection:
    def __init__(self, data):
        self.data=np.array(data,dtype=float); self.fs=100.0; self.dx=2.0; self.start_channel=10; self.start_time=None; self.gauge_length=5.0; self.data_type="strain rate"
        self.band=None
    @property
    def shape(self): return self.data.shape
    @property
    def nch(self): return self.data.shape[0]
    @property
    def nt(self): return self.data.shape[1]
    @property
    def end_channel(self): return self.start_channel+self.nch
    @property
    def end_time(self): return None
    def bandpass(self,a,b): self.band=(a,b); self.data=self.data*2
    def plot(self,savefig,dpi=150): Path(savefig).write_bytes(b"png")

def fake_read(path, headonly=False, ch1=None, ch2=None):
    data=np.arange(40,dtype=float).reshape(4,10)
    if ch1 is not None or ch2 is not None:
        start=0 if ch1 is None else max(0,ch1-10); stop=4 if ch2 is None else min(4,ch2-10); data=data[start:stop]
    if headonly: data=np.zeros_like(data)
    return FakeSection(data)

def test_das_inspect_window_rms_bandpass_plot(config_factory, monkeypatch):
    config_dir, root, _, _=config_factory(); sample=root/"sample.h5"; sample.write_bytes(b"fake")
    monkeypatch.setattr(core,"_daspy_read",lambda: fake_read)
    meta=das.inspect(sample,config_dir=config_dir); assert meta.success and meta.data["sampling_rate_hz"]==100.0
    assert main(["--config-dir",str(config_dir),"das","inspect",str(sample),"--json"])==0
    window=das.read_window(sample,channel_start=10,channel_stop=12,sample_start=2,sample_stop=5,config_dir=config_dir)
    assert window.success and len(window.data["data"])==2 and len(window.data["data"][0])==3
    rr=das.rms(sample,channel_start=10,channel_stop=12,sample_start=0,sample_stop=4,config_dir=config_dir); assert rr.success and len(rr.data["rms_per_channel"])==2
    bp=das.bandpass(sample,freqmin=1,freqmax=20,channel_start=10,channel_stop=12,sample_start=0,sample_stop=4,config_dir=config_dir); assert bp.success and Path(bp.data["output_path"]).is_file()
    pl=das.plot(sample,channel_start=10,channel_stop=12,sample_start=0,sample_stop=4,config_dir=config_dir); assert pl.success and Path(pl.data["output_path"]).is_file()

def test_das_rejects_nyquist_and_large_window(config_factory, monkeypatch):
    config_dir, root, _, _=config_factory(); sample=root/"sample.h5"; sample.write_bytes(b"fake"); monkeypatch.setattr(core,"_daspy_read",lambda: fake_read)
    bad=das.bandpass(sample,freqmin=1,freqmax=60,channel_start=10,channel_stop=12,sample_start=0,sample_stop=4,config_dir=config_dir)
    assert not bad.success
    too_big=das.read_window(sample,channel_start=10,channel_stop=200,sample_start=0,sample_stop=10,config_dir=config_dir)
    assert not too_big.success
