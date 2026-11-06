import numpy as np
import pytest
from geomcp.scientific.picking.backends import run_backend, describe_backends
from geomcp.exceptions import ScientificToolError

P = {'algorithm': {'sta_s': 1., 'lta_s': 4., 'threshold_on': 2., 'threshold_off': 1.1, 'min_trigger_s': 0., 'max_trigger_s': 100., 'station_component': 'Z'}}

def test_describe():
    assert {x['backend_id'] for x in describe_backends()} == {'stalta', 'phasenet', 'phasenet_das'}

def test_stalta_boundary_and_gap():
    x = np.r_[np.ones(20), np.ones(3)*10, np.ones(30)][None,:]
    a = run_backend('stalta', x, 1., P, None, {'data_kind':'station','components':['Z']})
    b = run_backend('stalta', x, 1., P, None, {'data_kind':'station','components':['Z'],'block_size':7})
    assert a == b
    assert len(a) == 1
    assert a[0]['sample_index'] == 20
    assert a[0]['phase'] == 'unknown'
    assert a[0]['score'] == pytest.approx(100 / (25 + .75 * (1 - .75**19)))
    y = np.r_[np.ones(20), np.nan, 10., 10., 10.][None,:]
    assert run_backend('stalta', y, 1., P, None, {'data_kind':'station','components':['Z']}) == []

@pytest.mark.parametrize('backend', ['phasenet','phasenet_das'])
def test_model_required(backend):
    with pytest.raises(ScientificToolError, match='model'):
        run_backend(backend,np.ones((3,40)),100.,{},None,{'data_kind':'station'})

def test_rejects_unclosed_and_duration():
    x=np.r_[np.ones(20),np.ones(30)*10][None,:]
    a={**P,'algorithm':{**P['algorithm'],'max_trigger_s':.5}}
    assert run_backend('stalta',x,1.,a,None,{'data_kind':'station','components':['Z']}) == []
    assert run_backend('stalta',np.r_[np.ones(20),100.][None,:],1.,P,None,{'data_kind':'station','components':['Z']}) == []

def test_deep_rejects_checksum_and_sampling(tmp_path):
    model={'python':__import__('sys').executable,'source_dir':str(tmp_path),'weights':str(tmp_path/'missing'),'sha256':{'missing':'a'*64},'sampling_rate_hz':100.,'components':['E','N','Z']}
    with pytest.raises(ScientificToolError,match='checksum'):
        run_backend('phasenet',np.ones((3,40)),100.,{},model,{'components':['E','N','Z']})
    with pytest.raises(ScientificToolError,match='Sampling rate'):
        run_backend('phasenet',np.ones((3,40)),50.,{},model,{})

def test_vendored_source_provenance():
    import hashlib,json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'third_party'
    for name in ('phasenet','eqnet','obspy'):
        source=root/name
        provenance=json.loads((source/'PROVENANCE.json').read_text())
        assert len(provenance['commit']) == 40
        assert provenance['files_sha256']
        for rel,digest in provenance['files_sha256'].items():
            assert hashlib.sha256((source/rel).read_bytes()).hexdigest() == digest
        assert not list(source.rglob('.git'))
    assert (root/'eqnet/eqnet/data/__init__.py').is_file()

def test_streaming_calls_equal_whole_and_report_gap():
    x=np.r_[np.ones(20),np.ones(3)*10,np.ones(30)][None,:]
    base={'data_kind':'station','components':['Z']}
    full=run_backend('stalta',x,1.,P,None,base)
    state={};diagnostics=[]; streamed=[]
    for i in range(0,x.shape[1],7):
        streamed+=run_backend('stalta',x[:,i:i+7],1.,P,None,dict(base,state=state,offset=i,final=i+7>=x.shape[1],diagnostics=diagnostics))
    assert streamed == full
    diagnostics=[]
    run_backend('stalta',np.r_[np.ones(20),100.,np.nan][None,:],1.,P,None,dict(base,diagnostics=diagnostics))
    assert diagnostics[0]['reason_code']=='gap_trigger'

def test_stream_gap_resets_and_rejects_unclosed():
    context={'data_kind':'station','components':['Z'],'state':{},'diagnostics':[],'offset':0,'final':False}
    first=np.r_[np.ones(20),100.][None,:]
    assert run_backend('stalta',first,1.,P,None,context)==[]
    context.update(offset=21,final=True)
    assert run_backend('stalta',np.array([[np.nan,100.,100.,100.]]),1.,P,None,context)==[]
    assert [d['reason_code'] for d in context['diagnostics']]==['gap_trigger']
    with pytest.raises(ScientificToolError,match='offset'):
        run_backend('stalta',np.ones((1,2)),1.,P,None,context)
@pytest.mark.parametrize('save_native',[True,False])
def test_native_outputs_engineering_fixture(tmp_path,monkeypatch,save_native):
    # Simulated wrapper output tests plumbing only, never real-model inference.
    import hashlib,sys
    from pathlib import Path
    from types import SimpleNamespace
    from geomcp.scientific.picking import backends
    weight=tmp_path/'fixture.pth';weight.write_bytes(b'engineering fixture')
    source=Path(__file__).resolve().parents[1]/'third_party/phasenet'
    model=dict(python=sys.executable,source_dir=str(source),weights=str(weight),sha256={str(weight):hashlib.sha256(weight.read_bytes()).hexdigest()},sampling_rate_hz=100.,components=['E','N','Z'])
    def fake_run(args,**kwargs):
        work=Path(args[-1])
        scores=np.zeros((1,3,40));scores[0,1,20]=.9
        np.save(work/'probabilities.npy',scores)
        kwargs['stdout'].write(b'x'*(1024*1024+20))
        kwargs['stderr'].write(b'fixture stderr')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(backends.subprocess,'run',fake_run)
    output=tmp_path/'native';output.mkdir()
    result=run_backend('phasenet',np.ones((3,40)),100.,{'algorithm':{'p_threshold':.5,'s_threshold':.5,'min_peak_distance_s':.01}},model,{'components':['E','N','Z'],'output_dir':str(output),'save_native':save_native})
    assert result[0]['sample_index']==20
    if save_native:
        assert np.load(output/'probabilities.npy').shape==(1,3,40)
        assert (output/'stderr.log').read_bytes()==b'fixture stderr'
        assert (output/'stdout.log').stat().st_size<=1024*1024
        assert (output/'stdout.log').read_bytes().startswith(b'[truncated')
    else:
        assert list(output.iterdir())==[]

def test_stalta_rejects_numeric_overflow():
    with pytest.raises(ScientificToolError,match='non-finite'):
        run_backend('stalta',np.ones((1,20))*1e308,1.,P,None,{'data_kind':'station','components':['Z']})
