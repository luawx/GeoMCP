import csv
import hashlib
import json
from pathlib import Path
import pytest

pytest.importorskip("h5py")
pytest.importorskip("obspy")


def test_picking_core_available():
    from geomcp.scientific import picking
    assert callable(getattr(picking, 'prepare_inputs', None))


def fixture_inputs(tmp_path):
    import h5py
    import numpy as np
    path = tmp_path / 'data.h5'
    data = np.zeros((2, 1000))
    data[:, 300:330] = 5
    with h5py.File(path, 'w') as f:
        f['data'] = data
    receivers = tmp_path / 'receivers.csv'
    receivers.write_text('receiver_id,data_kind,network,station,location,channel_id,longitude_deg,latitude_deg,elevation_m,valid_from,valid_to\nr0,das,,,,0,110,30,0,2026-01-01T00:00:00Z,2027-01-01T00:00:00Z\nr1,das,,,,1,110.001,30,0,2026-01-01T00:00:00Z,2027-01-01T00:00:00Z\n')
    geo = tmp_path / 'geometry.json'
    geo.write_text(json.dumps(dict(schema_version='1.0', geometry_id='g', crs='EPSG:4326', axis_order='longitude,latitude', vertical_datum='WGS84', receivers_ref='receivers.csv',receivers_sha256=hashlib.sha256(receivers.read_bytes()).hexdigest())))
    manifest = tmp_path / 'waveforms.json'
    manifest.write_text(json.dumps(dict(schema_version='1.0',manifest_id='m',geometry_id='g',waveforms=[dict(waveform_id='w',data_kind='das',format='hdf5',files=[dict(path='data.h5',sha256=hashlib.sha256(path.read_bytes()).hexdigest())],start_time='2026-11-06T00:00:00Z',end_time='2026-11-06T00:00:10Z',sampling_rate_hz=100,sample_count=1000,quantity='strain_rate',unit='1/s',receiver_ids=['r0','r1'],components=[],geometry_id='g',gaps=[],bad_receivers=[],format_options=dict(dataset='data',axis_order='channel,time',channel_ids=['0','1']))])))
    return manifest,geo


def test_inputs_and_stalta_execute(tmp_path):
    from geomcp.scientific import picking
    manifest, geo = fixture_inputs(tmp_path)
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=5000,max_picks=100,max_output_bytes=1000000)
    inputs=picking.prepare_inputs(manifest,geo,Path,limits)
    resolved=picking.resolve_parameters({'parameters':{'algorithm':{'sta_s':0.1,'lta_s':1.,'threshold_on':3.,'threshold_off':1.5,'min_trigger_s':0.,'max_trigger_s':3.}}}, {}, 'stalta', limits)
    result=picking.execute(dict(run_id='test',inputs=inputs,parameters=resolved['effective'],backend_id='stalta',model=None,limits=limits),tmp_path/'out',Path)
    assert result['summary']['pick_count']==2
    rows=list(csv.DictReader((tmp_path/'out/artifacts/picks.csv').open()))
    assert all(r['phase']=='unknown' and r['score_type']=='stalta_ratio' for r in rows)
    assert rows[0]['time']=='2026-11-06T00:00:03.000000000Z'
    assert (tmp_path/'out/manifest.json').is_file()


def test_hash_and_unknown_params_rejected(tmp_path):
    from geomcp.scientific import picking
    manifest,geo=fixture_inputs(tmp_path)
    (tmp_path/'data.h5').write_bytes(b'corrupt')
    with pytest.raises(Exception,match='checksum|SHA|hash'):
        picking.prepare_inputs(manifest,geo,Path,{'max_input_bytes':1000000,'max_receivers':10})
    with pytest.raises(Exception,match='Unknown|unknown'):
        picking.resolve_parameters({'parameters':{}},{'algorithm':{'command':'bad'}},'stalta',{})


def test_unknown_phase_not_locatable():
    from geomcp.scientific import picking
    used,excluded=picking.location_picks([{'phase':'unknown'},{'phase':'P'}])
    assert used==[{'phase':'P'}] and excluded==1

def test_station_mseed_stalta_three_component_manifest(tmp_path):
    import numpy as np
    from obspy import Trace, UTCDateTime
    from geomcp.scientific import picking
    manifest, geo=fixture_inputs(tmp_path)
    obj=json.loads(manifest.read_text())
    w=obj['waveforms'][0]
    w.update(data_kind='station',format='mseed',receiver_ids=['r0'],components=['E','N','Z'],files=[])
    for component in w['components']:
        x=np.zeros(1000,dtype=np.float64); x[300:330]=5
        tr=Trace(x,header=dict(network='XX',station='AAA',location='',channel='HH'+component,starttime=UTCDateTime(w['start_time']),sampling_rate=100))
        path=tmp_path/(component+'.mseed'); tr.write(str(path),format='MSEED')
        w['files'].append(dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),receiver_id='r0',component=component,network='XX',station='AAA',location='',channel='HH'+component))
    manifest.write_text(json.dumps(obj))
    receivers=tmp_path/'receivers.csv'
    receivers.write_text('receiver_id,data_kind,network,station,location,channel_id,longitude_deg,latitude_deg,elevation_m,valid_from,valid_to\nr0,station,XX,AAA,,,110,30,0,2026-01-01T00:00:00Z,2027-01-01T00:00:00Z\n')
    g=json.loads(geo.read_text());g['receivers_sha256']=hashlib.sha256(receivers.read_bytes()).hexdigest();geo.write_text(json.dumps(g))
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=5000,max_picks=100,max_output_bytes=1000000)
    inputs=picking.prepare_inputs(manifest,geo,Path,limits)
    params=picking.resolve_parameters({'parameters':{'algorithm':{'sta_s':.1,'lta_s':1.,'max_trigger_s':3.}}},{},'stalta',limits)
    result=picking.execute(dict(run_id='station',inputs=inputs,parameters=params['effective'],backend_id='stalta',model=None,limits=limits),tmp_path/'out',Path)
    assert result['summary']['pick_count']==1


def test_hdf5_external_parent_rejected(tmp_path):
    import h5py
    from geomcp.scientific import picking
    manifest,geo=fixture_inputs(tmp_path)
    with h5py.File(tmp_path/'outside.h5','w') as f:
        f.create_group('group').create_dataset('data',data=[[0]*1000,[0]*1000])
    with h5py.File(tmp_path/'external.h5','w') as f:
        f['escape']=h5py.ExternalLink('outside.h5','/group')
    obj=json.loads(manifest.read_text());w=obj['waveforms'][0]
    w['files'][0]={'path':'external.h5','sha256':hashlib.sha256((tmp_path/'external.h5').read_bytes()).hexdigest()}
    w['format_options']['dataset']='escape/data';manifest.write_text(json.dumps(obj))
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=5000,max_picks=100,max_output_bytes=1000000)
    inputs=picking.prepare_inputs(manifest,geo,Path,limits)
    params=picking.resolve_parameters({'parameters':{}},{},'stalta',limits)
    with pytest.raises(Exception,match='local hard link|external'):
        picking.execute(dict(run_id='external',inputs=inputs,parameters=params['effective'],backend_id='stalta',model=None,limits=limits),tmp_path/'out',Path)

def test_deep_gap_split_and_spatial_chunks(tmp_path, monkeypatch):
    import h5py
    from geomcp.scientific import picking
    from geomcp.scientific.picking import backends
    manifest,geo=fixture_inputs(tmp_path)
    with h5py.File(tmp_path/'data.h5','r+') as f:
        f['data'][:,500:510]=float('nan')
    obj=json.loads(manifest.read_text()); obj['waveforms'][0]['files'][0]['sha256']=hashlib.sha256((tmp_path/'data.h5').read_bytes()).hexdigest(); manifest.write_text(json.dumps(obj))
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=10000,max_picks=100,max_output_bytes=1000000)
    inputs=picking.prepare_inputs(manifest,geo,Path,limits)
    params=picking.resolve_parameters({'parameters':{'chunking':{'core_channels':1,'context_channels':0}}},{},'phasenet_das',limits)
    seen=[]
    def inference(backend,data,rate,parameters,model,context):
        import numpy as np
        assert np.isfinite(data).all()
        seen.append(data.shape)
        return [dict(receiver_index=0,phase='P',sample_index=0,score=.9,score_type='model_score',quality_flags=[])]
    monkeypatch.setattr(backends,'run_backend',inference)
    result=picking.execute(dict(run_id='deep',inputs=inputs,parameters=params['effective'],backend_id='phasenet_das',model={'quantity':'strain_rate','unit':'1/s','sampling_rate_hz':100},limits=limits),tmp_path/'out',Path)
    assert len(seen)==4
    assert result['summary']['pick_count']==4

def test_execution_uses_verified_snapshot(tmp_path, monkeypatch):
    import h5py
    from geomcp.scientific import picking
    from geomcp.scientific.picking import backends
    manifest,geo=fixture_inputs(tmp_path)
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=5000,max_picks=100,max_output_bytes=1000000)
    inputs=picking.prepare_inputs(manifest,geo,Path,limits)
    params=picking.resolve_parameters({'parameters':{'algorithm':{'sta_s':.1,'lta_s':1.,'max_trigger_s':3.}}},{},'stalta',limits)
    original=backends.run_backend
    called=[]
    def mutate(*args,**kwargs):
        with h5py.File(tmp_path/'data.h5','r+') as f: f['data'][:]=0
        called.append(1)
        return original(*args,**kwargs)
    monkeypatch.setattr(backends,'run_backend',mutate)
    result=picking.execute(dict(run_id='snapshot',inputs=inputs,parameters=params['effective'],backend_id='stalta',model=None,limits=limits),tmp_path/'out',Path)
    assert len(called)==2 and result['summary']['pick_count']==2

def test_stalta_bounded_read_of_long_trace(tmp_path):
    from geomcp.scientific import picking
    manifest,geo=fixture_inputs(tmp_path)
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=120,max_picks=100,max_output_bytes=1000000)
    inputs=picking.prepare_inputs(manifest,geo,Path,limits)
    params=picking.resolve_parameters({'parameters':{'chunking':{'core_duration_s':1},'algorithm':{'sta_s':.1,'lta_s':1.,'max_trigger_s':3.}}},{},'stalta',limits)
    result=picking.execute(dict(run_id='stream',inputs=inputs,parameters=params['effective'],backend_id='stalta',model=None,limits=limits),tmp_path/'out',Path)
    assert result['summary']['pick_count']==2

def test_import_table_and_geometry_checksums(tmp_path):
    from geomcp.scientific import picking
    manifest,geo=fixture_inputs(tmp_path)
    source=tmp_path/'external.csv'
    source.write_text('pick_id,waveform_id,receiver_id,phase,time,score,score_type,time_uncertainty_s\na,w,r0,unknown,2026-11-06T00:00:03Z,4.2,stalta_ratio,\n')
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=5000,max_picks=100,max_output_bytes=1000000)
    result=picking.import_picks(source,geo,tmp_path/'import',Path,limits)
    assert result['summary']['phase_counts']['unknown']==1
    geometry=json.loads((tmp_path/'import/artifacts/geometry.json').read_text())
    assert geometry['receivers_sha256']==hashlib.sha256((tmp_path/'import/artifacts/receivers.csv').read_bytes()).hexdigest()
    source.write_text(source.read_text().replace('4.2','NaN'))
    with pytest.raises(Exception,match='finite'):
        picking.import_picks(source,geo,tmp_path/'invalid',Path,limits)

def test_station_gap_on_unselected_component_preserves_trigger(tmp_path):
    # Reuse the real miniSEED fixture test's input construction through a small monkeypatch.
    import numpy as np
    from geomcp.scientific.picking.pipeline import _read_trace
    from obspy import Trace,UTCDateTime
    path=tmp_path/'z.mseed';data=np.ones(100)
    Trace(data,header=dict(network='XX',station='S',location='',channel='HHZ',sampling_rate=10,starttime=UTCDateTime('2026-01-01'))).write(str(path),format='MSEED')
    w=dict(data_kind='station',components=['E','N','Z'],receiver_ids=['r'],files=[dict(path=str(path),receiver_id='r',component='Z',network='XX',station='S',location='',channel='HHZ')],sampling_rate_hz=10,start_time='2026-01-01T00:00:00Z',gaps=[dict(receiver_id='r',component='E',sample_start=10,sample_stop=20)])
    result=_read_trace(w,'r',0,100,{'_backend':'stalta','algorithm':{'station_component':'Z'}},Path,1000)
    assert np.isfinite(result).all()


def test_deep_short_segments_not_counted_processed(tmp_path,monkeypatch):
    from geomcp.scientific import picking
    from geomcp.scientific.picking import backends
    manifest,geo=fixture_inputs(tmp_path)
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=5000,max_picks=100,max_output_bytes=1000000)
    inputs=picking.prepare_inputs(manifest,geo,Path,limits)
    params=picking.resolve_parameters({'parameters':{}},{},'phasenet_das',limits)
    monkeypatch.setattr(backends,'run_backend',lambda *args: pytest.fail('No valid model segment'))
    result=picking.execute(dict(run_id='short',inputs=inputs,parameters=params['effective'],backend_id='phasenet_das',model={'quantity':'strain_rate','unit':'1/s','sampling_rate_hz':100,'min_samples':2000},limits=limits),tmp_path/'out',Path)
    assert result['summary']['processed_samples']==0
    assert result['summary']['quality_status']=='no_valid_data'

def test_import_uses_verified_snapshot(tmp_path,monkeypatch):
    from geomcp.scientific import picking
    from geomcp.scientific.picking import contracts
    _,geo=fixture_inputs(tmp_path)
    source=tmp_path/'external.csv';source.write_text('pick_id,waveform_id,receiver_id,phase,time\na,w,r0,P,2026-11-06T00:00:03Z\n')
    original=contracts.validate_geometry
    def replace_csv(*args,**kwargs):
        result=original(*args,**kwargs)
        source.write_text(source.read_text().replace('2026-11-06','2030-11-06'))
        return result
    monkeypatch.setattr(contracts,'validate_geometry',replace_csv)
    limits=dict(max_input_bytes=1000000,max_samples=10000,max_receivers=10,max_block_points=5000,max_picks=100,max_output_bytes=1000000)
    result=picking.import_picks(source,geo,tmp_path/'import',Path,limits)
    assert result['summary']['pick_count']==1

def test_das_declared_spatial_segments_are_not_convolved_together():
    from geomcp.scientific.picking.pipeline import _spatial_groups
    w={'receiver_ids':['a','b'],'format_options':{'spatial_segments':[[0,1],[1,2]]}}
    assert _spatial_groups(w,['a','b'],64,4)==[(['a'],['a']),(['b'],['b'])]
