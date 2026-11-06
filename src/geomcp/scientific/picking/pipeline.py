"""Bounded waveform execution and atomic publication of normalized pick artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import copy
import shutil
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .contracts import SCHEMA, epoch, error, finite, read_json, sha256, timestamp

PICK_FIELDS = ['pick_id','waveform_id','receiver_id','phase','time','score','score_type','time_uncertainty_s','backend_id','model_id','quality_flags']
SOURCE_FIELDS = ['source_id','pick_id','waveform_id','receiver_id','component','block_id','source_sample_index','processed_sample_index','source_reference_time','source_sampling_rate_hz','raw_time','time_transform_id','disposition']
REJECT_FIELDS = ['source_id','waveform_id','receiver_id','reason_code','detail','retained_pick_id']
COVERAGE_FIELDS = ['receiver_id','waveform_id','requested_samples','valid_samples','processed_samples','excluded_samples','reason']


def write_json(path, value):
    path=Path(path)
    temporary=path.with_suffix(path.suffix+'.incomplete')
    temporary.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
    os.replace(temporary,path)


def write_csv(path, fields, rows):
    with Path(path).open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False,allow_nan=False) if isinstance(v,(list,dict)) else v for k,v in row.items() if k in fields})


def _dependencies():
    try:
        import numpy as np
    except ImportError as exc:
        from geomcp.exceptions import ScientificToolError
        raise ScientificToolError('Install the picking extra for waveform processing') from exc
    return np


def _samples(seconds, rate):
    return int((Decimal(str(seconds))*Decimal(str(rate))).to_integral_value(rounding=ROUND_HALF_UP))


def _spatial_groups(waveform, selected, core_size, context_size):
    """Never collapse missing/bad/selection-excluded acquisition positions."""
    valid=set(selected)-set(waveform.get('bad_receivers',[]))
    runs=[];current=[]
    boundaries={seg[0] for seg in waveform.get('format_options',{}).get('spatial_segments',[])}
    for index,rid in enumerate(waveform['receiver_ids']):
        if index in boundaries and current:
            runs.append(current);current=[]
        if rid in valid:
            current.append(rid)
        elif current:
            runs.append(current);current=[]
    if current: runs.append(current)
    groups=[]
    for run in runs:
        for index in range(0,len(run),core_size):
            groups.append((run[index:index+core_size],run[max(0,index-context_size):index+core_size+context_size]))
    return groups


def _read_trace(w, rid, start, stop, parameters, validate_read, max_points):
    np=_dependencies()
    n=stop-start
    components=([parameters['algorithm']['station_component']] if parameters.get('_backend')=='stalta' and w['data_kind']=='station' else w.get('components',[]))
    if n*max(1,len(components))>max_points: error('Waveform block exceeds max_block_points; shorten core duration or continuous segment')
    if w['data_kind']=='das':
        try: import h5py
        except ImportError: error('HDF5 support requires picking extra')
        if len(w['files'])!=1: error('DAS record requires one HDF5 file')
        ref=w['files'][0]
        with h5py.File(validate_read(ref['path']),'r') as stream:
            opts=w['format_options']
            # External and virtual datasets can read arbitrary paths outside PathPolicy.
            group=stream
            segments=[part for part in opts['dataset'].split('/') if part]
            for part in segments:
                link=group.get(part,getlink=True)
                if not isinstance(link,h5py.HardLink): error('HDF5 dataset must be a local hard link; external links forbidden')
                group=group[part]
            dataset=stream[opts['dataset']]
            if dataset.is_virtual or dataset.external: error('HDF5 external/virtual datasets are not allowed')
            expected=(len(w['receiver_ids']),w['sample_count'])
            if opts['axis_order']=='time,channel': expected=expected[::-1]
            if dataset.shape!=expected: error('HDF5 shape does not match manifest')
            index=w['receiver_ids'].index(rid)
            data=np.asarray(dataset[index,start:stop] if opts['axis_order']=='channel,time' else dataset[start:stop,index],dtype=float)[None,:]
    else:
        try: from obspy import read,UTCDateTime
        except ImportError: error('miniSEED support requires picking extra')
        requested=components if parameters.get('_backend')!='stalta' else [parameters['algorithm']['station_component']]
        if parameters.get('_backend')!='stalta' and len(requested)!=3: error('PhaseNet requires three explicit components')
        series=[]
        for component in requested:
            refs=[f for f in w['files'] if f.get('receiver_id')==rid and f.get('component')==component]
            if len(refs)!=1: error(f'Missing or ambiguous component {component}')
            ref=refs[0]
            rate=w['sampling_rate_hz']
            t0=UTCDateTime(timestamp(w['start_time'],start,rate))
            t1=UTCDateTime(timestamp(w['start_time'],stop-1,rate))
            stream=read(str(validate_read(ref['path'])),starttime=t0,endtime=t1,format='MSEED')
            for key in ('network','station','location','channel'):
                if key not in ref: error(f'miniSEED file mapping missing {key}')
            stream=stream.select(network=ref['network'],station=ref['station'],location=ref['location'],channel=ref['channel'])
            if not stream: error('miniSEED trace selection is empty')
            stream.merge(method=0,fill_value=None)
            if len(stream)!=1: error('miniSEED selection must resolve to one trace')
            trace=stream[0]
            if abs(trace.stats.sampling_rate-rate)>1e-8 or abs(float(trace.stats.starttime-t0))>1e-7: error('miniSEED sample grid mismatch')
            arr=np.ma.filled(trace.data.astype(float),np.nan)
            if arr.size!=n: error('miniSEED sample_count mismatch')
            series.append(arr)
        data=np.stack(series)
    for gap in w.get('gaps',[]):
        if gap.get('receiver_id') not in (None,rid): continue
        lo=max(start,gap['sample_start'])-start
        hi=min(stop,gap['sample_stop'])-start
        if hi>lo:
            if gap.get('component') is not None and w['data_kind']=='station':
                if gap['component'] in components:
                    data[components.index(gap['component']),lo:hi]=np.nan
            else:
                data[:,lo:hi]=np.nan
    return data


def _preprocess(data, sampling_rate, parameters):
    np=_dependencies()
    pre=parameters['preprocessing']
    target=pre['target_sampling_rate_hz']
    if target is not None and target!=sampling_rate:
        # Mapping resampled sample indices requires explicit transform provenance.
        error('Resampling is not enabled in this release; supply a separately versioned resampled input')
    valid=np.all(np.isfinite(data),axis=0)
    padded=np.r_[False,valid,False].astype(int)
    changes=np.diff(padded)
    for start,stop in zip(np.where(changes==1)[0],np.where(changes==-1)[0]):
        piece=data[:,start:stop]
        if pre['detrend']!='none':
            from scipy.signal import detrend
            piece=detrend(piece,axis=-1,type=pre['detrend'])
        band=pre['bandpass_hz']
        if band is not None:
            from scipy.signal import butter,sosfiltfilt
            if band[1]>=sampling_rate/2: error('Bandpass exceeds Nyquist')
            sos=butter(4,band,fs=sampling_rate,btype='bandpass',output='sos')
            try: piece=sosfiltfilt(sos,piece,axis=-1)
            except ValueError:
                data[:,start:stop]=np.nan
                continue
        data[:,start:stop]=piece
    return data,int(valid.sum())


def _deduplicate(candidates, window):
    candidates.sort(key=lambda r:(r['receiver_id'],r['phase'],r['backend_id'],epoch(r['time']),r['_source']['source_id']))
    kept=[];duplicates=[]
    i=0
    while i<len(candidates):
        first=candidates[i];group=[first];j=i+1
        key=(first['receiver_id'],first['phase'],first['backend_id'],first['model_id'])
        while j<len(candidates):
            item=candidates[j]
            if (item['receiver_id'],item['phase'],item['backend_id'],item['model_id'])!=key or epoch(item['time'])-epoch(first['time'])>Decimal(str(window)): break
            group.append(item);j+=1
        best=min(group,key=lambda r:(-(r['score'] if r['score'] is not None else -math.inf),epoch(r['time']),r['_source']['source_id']))
        kept.append(best)
        duplicates.extend((row,best) for row in group if row is not best)
        i=j
    return kept,duplicates


def _stream_stalta_trace(w, rid, start, stop, parameters, validate_read, max_points):
    from .backends import run_backend
    np=_dependencies()
    pre=parameters['preprocessing']
    special=pre['detrend']!='none' or pre['bandpass_hz'] is not None or pre['target_sampling_rate_hz'] is not None
    if special and stop-start>max_points:
        error('Continuous detrend/filter preprocessing exceeds working-set limit; supply a separately preprocessed input')
    width=(stop-start) if special else min(max_points,max(1,_samples(parameters['chunking']['core_duration_s'],w['sampling_rate_hz'])))
    state={};diagnostics=[];result=[];valid=0;processed=0;age=0
    warmup=_samples(parameters['algorithm']['lta_s'],w['sampling_rate_hz'])
    for lo in range(start,stop,width):
        hi=min(stop,lo+width)
        data=_read_trace(w,rid,lo,hi,dict(parameters,_backend='stalta'),validate_read,max_points)
        data,_=_preprocess(data,w['sampling_rate_hz'],parameters)
        for ok in np.all(np.isfinite(data),axis=0):
            if ok:
                valid+=1
                if age>=warmup: processed+=1
                age+=1
            else: age=0
        context={'data_kind':w['data_kind'],'components':[parameters['algorithm']['station_component']] if w['data_kind']=='station' else [],'state':state,'offset':lo-start,'final':hi==stop,'diagnostics':diagnostics}
        result.extend(run_backend('stalta',data,w['sampling_rate_hz'],parameters,None,context))
    return result,valid,processed,diagnostics


def _publish(prepared, output_dir, candidates, rejected, coverage, native_files=None):
    output_dir=Path(output_dir)
    artifacts=output_dir/'artifacts'
    artifacts.mkdir(parents=True,exist_ok=True)
    run_id=prepared['run_id']
    parameters=prepared.get('effective_parameters') or prepared.get('parameters',{})
    if 'effective' in parameters: parameters=parameters['effective']
    kept,duplicates=_deduplicate(candidates,parameters.get('postprocessing',{}).get('dedup_window_s',0))
    sources=[]
    for row in kept:
        identity=f"{run_id}:{row['_source']['source_id']}"
        row['pick_id']='pick-'+hashlib.sha256(identity.encode()).hexdigest()[:32]
        row['_source'].update(pick_id=row['pick_id'],disposition='retained')
        sources.append(row['_source'])
    for row,best in duplicates:
        row['_source'].update(pick_id=best['pick_id'],disposition='duplicate')
        sources.append(row['_source'])
        rejected.append(dict(source_id=row['_source']['source_id'],waveform_id=row['waveform_id'],receiver_id=row['receiver_id'],reason_code='duplicate',detail='dedup_window',retained_pick_id=best['pick_id']))
    kept.sort(key=lambda r:(epoch(r['time']),r['receiver_id'],r['phase'],r['pick_id']))
    if len(kept)>prepared['limits'].get('max_picks',100000): error('Pick count limit exceeded')
    write_csv(artifacts/'picks.csv',PICK_FIELDS,kept)
    write_csv(artifacts/'pick_sources.csv',SOURCE_FIELDS,sources)
    write_csv(artifacts/'rejected.csv',REJECT_FIELDS,rejected)
    write_csv(artifacts/'coverage.csv',COVERAGE_FIELDS,coverage)
    inputs=prepared['inputs']
    if inputs.get('receivers'):
        write_csv(artifacts/'receivers.csv',list(inputs['receivers'][0]),inputs['receivers'])
    write_json(artifacts/'geometry.json',dict(inputs['geometry'],receivers_ref='receivers.csv',receivers_sha256=sha256(artifacts/'receivers.csv')))
    phases={p:sum(r['phase']==p for r in kept) for p in ('P','S','unknown')}
    receiver_stats={}
    for row in kept:
        stats=receiver_stats.setdefault(row['receiver_id'],dict(receiver_id=row['receiver_id'],pick_count=0,P=0,S=0,unknown=0))
        stats['pick_count']+=1;stats[row['phase']]+=1
    write_csv(artifacts/'receiver_stats.csv',['receiver_id','pick_count','P','S','unknown'],list(receiver_stats.values()))
    requested=sum(r['requested_samples'] for r in coverage)
    processed=sum(r['processed_samples'] for r in coverage)
    summary={'pick_count':len(kept),'phase_counts':phases,'rejected_count':len(rejected),'duplicate_count':len(duplicates),'requested_samples':requested,'processed_samples':processed,'coverage':processed/requested if requested else None,'quality_status':'accepted' if processed or prepared.get('imported') else 'no_valid_data','warnings':[]}
    if phases['unknown']: summary['warnings'].append('Unknown phases require classification before P/S association or location')
    groups={}
    for row in kept:
        if row['score'] is not None: groups.setdefault(row['score_type'],[]).append(row['score'])
    summary['score_distributions']={key:{'count':len(vals),'min':min(vals),'max':max(vals),'mean':sum(vals)/len(vals)} for key,vals in groups.items()}
    write_json(output_dir/'parameters.json',{'effective':parameters,'sources':prepared.get('parameter_sources',{}),'preset':prepared.get('preset_id'),'preset_version':prepared.get('preset_version'),'overrides':prepared.get('overrides',{}),'model':prepared.get('model'),'execution_profile_fingerprint':prepared.get('configuration_fingerprint')})
    write_json(output_dir/'summary.json',summary)
    outputs=[]
    for path in sorted(output_dir.rglob('*')):
        if path.is_file() and path.name!='manifest.json': outputs.append({'path':str(path.relative_to(output_dir)).replace('\\','/'),'sha256':sha256(path),'bytes':path.stat().st_size})
    manifest={'schema_version':SCHEMA,'run_id':run_id,'module':'picking','status':'completed','job_id':prepared.get('job_id'),'backend_id':prepared.get('backend_id'),'adapter_version':'1','model_id':(prepared.get('model') or {}).get('model_id'),'inputs':inputs['references'],'parameters_ref':'parameters.json','geometry_id':inputs['geometry']['geometry_id'],'table_schemas':{'picks.csv':SCHEMA,'pick_sources.csv':SCHEMA,'rejected.csv':SCHEMA,'coverage.csv':SCHEMA,'receiver_stats.csv':SCHEMA},'time_format':'UTC ISO8601 Z, 9 fractional digits; not measurement precision','artifacts':outputs,'summary':summary,'imported':bool(prepared.get('imported'))}
    from importlib.metadata import version,PackageNotFoundError
    manifest['environment_versions']={}
    for package in ('geomcp','numpy','scipy','obspy','h5py'):
        try: manifest['environment_versions'][package]=version(package)
        except PackageNotFoundError: pass
    budget=prepared['limits'].get('max_output_bytes',64*1024*1024)
    if sum(row['bytes'] for row in outputs)+len(json.dumps(manifest).encode())>budget: error('Output byte limit exceeded')
    write_json(output_dir/'manifest.json',manifest)
    return {'summary':summary,'manifest_ref':str(output_dir/'manifest.json'),'artifacts':{'picks':str(artifacts/'picks.csv'),'sources':str(artifacts/'pick_sources.csv'),'coverage':str(artifacts/'coverage.csv')}}


def execute(prepared, output_dir, validate_read):
    from .backends import run_backend
    np=_dependencies()
    output_dir=Path(output_dir)
    if (output_dir/'manifest.json').exists(): error('Refusing to overwrite published result')
    (output_dir/'artifacts/native').mkdir(parents=True,exist_ok=True)
    inputs=copy.deepcopy(prepared['inputs'])
    # Hash the copies actually read by the algorithm, closing the check/reopen race.
    snapshot_dir=output_dir/'inputs';snapshot_dir.mkdir(exist_ok=True)
    staged={}
    for ref in inputs['references']:
        original=Path(validate_read(ref['path']))
        target=snapshot_dir/(ref['sha256']+original.suffix)
        shutil.copyfile(original,target)
        if sha256(target)!=ref['sha256']: error('Input checksum changed while snapshotting')
        staged[str(original)]=str(target)
    for w in inputs['waveforms']:
        for ref in w['files']:
            ref['path']=staged[str(Path(ref['path']))]
    original_validate_read=validate_read
    staged_paths={str(Path(path).resolve()) for path in staged.values()}
    def validate_read(path):
        # These service-owned copies have already passed source authorization and hash checks.
        resolved=Path(path).resolve()
        return resolved if str(resolved) in staged_paths else original_validate_read(path)
    prepared=dict(prepared,inputs=inputs)
    parameters=prepared.get('effective_parameters') or prepared['parameters']
    if 'effective' in parameters: parameters=parameters['effective']
    backend=prepared['backend_id'];model=prepared.get('model')
    if backend!='stalta' and not model: error('Deep-learning backend requires a registered model')
    candidates=[];rejected=[];coverage=[]
    wanted=parameters['selection']['receiver_ids']
    all_ids={rid for w in inputs['waveforms'] for rid in w['receiver_ids']}
    if wanted is not None and not set(wanted)<=all_ids: error('Selection references unknown receiver')
    for w in inputs['waveforms']:
        if backend=='phasenet' and w['data_kind']!='station': error('PhaseNet requires station input')
        if backend=='phasenet_das' and w['data_kind']!='das': error('PhaseNet-DAS requires DAS input')
        if model:
            for field in ('quantity','unit'):
                if model.get(field)!=w[field]: error(f'Model {field} incompatible with waveform')
            if model.get('sampling_rate_hz')!=w['sampling_rate_hz']: error('Model sampling rate mismatch')
            if backend=='phasenet' and model.get('components')!=w['components']: error('Model component order mismatch')
        rate=w['sampling_rate_hz'];n=w['sample_count']
        selection=parameters['selection']
        start=max(0,int(((epoch(selection['start_time'])-epoch(w['start_time']))*Decimal(str(rate))).to_integral_value(rounding='ROUND_CEILING'))) if selection['start_time'] else 0
        stop=min(n,int(((epoch(selection['end_time'])-epoch(w['start_time']))*Decimal(str(rate))).to_integral_value(rounding='ROUND_CEILING'))) if selection['end_time'] else n
        if start>=stop: continue
        rids=[r for r in w['receiver_ids'] if wanted is None or r in wanted]
        max_points=prepared['limits']['max_block_points']
        # STA/LTA keeps its recursion for the whole selected trace; refuse if its bounded working set does not fit.
        core=max(1,_samples(parameters['chunking']['core_duration_s'],rate))
        chunks=[(start,stop,start,stop)] if backend=='stalta' else [(s,min(s+core,stop),max(start,s-_samples(parameters['chunking']['context_before_s'],rate)),min(stop,s+core+_samples(parameters['chunking']['context_after_s'],rate))) for s in range(start,stop,core)]
        for cs,ce,rs,re in chunks:
            groups=_spatial_groups(w,rids,parameters['chunking']['core_channels'],parameters['chunking']['context_channels']) if backend=='phasenet_das' else [([rid],[rid]) for rid in rids]
            for core_rids,group in groups:
                if backend=='phasenet_das' and len(group)*(re-rs)>max_points: error('DAS spatial block exceeds max_block_points; select fewer channels or shorter windows')
                arrays=[];valid_counts=[];active=[];stream_result=[];stream_diagnostics=[];group_coverage=[]
                for rid in group:
                    requested=ce-cs
                    if rid in w.get('bad_receivers',[]):
                        rejected.append(dict(waveform_id=w['waveform_id'],receiver_id=rid,reason_code='bad_receiver',detail='Declared bad receiver'))
                        coverage.append(dict(receiver_id=rid,waveform_id=w['waveform_id'],requested_samples=requested,valid_samples=0,processed_samples=0,excluded_samples=requested,reason='bad_receiver'))
                        continue
                    params=dict(parameters,_backend=backend)
                    if backend=='stalta':
                        stream_result,valid_core,processed_core,stream_diagnostics=_stream_stalta_trace(w,rid,rs,re,parameters,validate_read,max_points)
                        data=None;valid=valid_core
                    else:
                        data=_read_trace(w,rid,rs,re,params,validate_read,max_points)
                        data,valid=_preprocess(data,rate,parameters)
                        valid_core=int(np.all(np.isfinite(data[:,cs-rs:ce-rs]),axis=0).sum())
                        processed_core=valid_core
                    arrays.append(data);active.append(rid);valid_counts.append(valid)
                    if rid in core_rids:
                        coverage_row=dict(receiver_id=rid,waveform_id=w['waveform_id'],requested_samples=requested,valid_samples=valid_core,processed_samples=processed_core if backend=='stalta' else 0,excluded_samples=requested-processed_core if backend=='stalta' else requested,reason='' if processed_core==requested else 'gap_warmup_or_short_segment')
                        coverage.append(coverage_row);group_coverage.append(coverage_row)
                if not active: continue
                data=np.concatenate(arrays,axis=0) if backend=='phasenet_das' else arrays[0]
                block=f"{w['waveform_id']}:{cs}:{active[0]}"
                native=output_dir/'artifacts/native'/hashlib.sha256(block.encode()).hexdigest()[:16]
                native.mkdir(parents=True,exist_ok=True)
                diagnostics=[]
                context={'data_kind':w['data_kind'],'output_dir':str(native),'device':prepared.get('device',prepared.get('execution_profile',{}).get('device','cpu')),'components':[parameters['algorithm']['station_component']] if backend=='stalta' and w['data_kind']=='station' else w.get('components',[]),'block_size':max(1,int(core)),'timeout_s':prepared.get('execution_profile',{}).get('timeout',3600),'diagnostics':diagnostics,'save_native':parameters['output']['save_native'],'max_native_bytes':prepared['limits']['max_output_bytes']}
                if backend=='stalta':
                    result=stream_result
                    diagnostics=stream_diagnostics
                else:
                    # Models see only common finite segments, never fabricated zeros at gaps.
                    mask=np.all(np.isfinite(data),axis=0)
                    edges=np.diff(np.r_[False,mask,False].astype(int))
                    result=[]
                    for seg_start,seg_stop in zip(np.where(edges==1)[0],np.where(edges==-1)[0]):
                        if seg_stop-seg_start<(model or {}).get('min_samples',1):
                            rejected.append(dict(waveform_id=w['waveform_id'],reason_code='short_model_segment',detail=f'{block}:{seg_start}:{seg_stop}'))
                            continue
                        subdir=native/f'{seg_start}-{seg_stop}';subdir.mkdir(exist_ok=True)
                        part=run_backend(backend,data[:,seg_start:seg_stop],rate,parameters,model,dict(context,output_dir=str(subdir)))
                        processed=max(0,min(ce,rs+int(seg_stop))-max(cs,rs+int(seg_start)))
                        for coverage_row in group_coverage:
                            coverage_row['processed_samples']+=processed
                            coverage_row['excluded_samples']-=processed
                            coverage_row['reason']='' if coverage_row['excluded_samples']==0 else 'gap_or_short_segment'
                        for item in part:
                            if not 0<=item['sample_index']<seg_stop-seg_start: error('Backend sample index outside continuous segment')
                            result.append(dict(item,sample_index=int(seg_start)+item['sample_index']))
                if parameters['output']['save_native']:
                    write_json(native/'candidates.json',result)
                for diagnostic in diagnostics:
                    rejected.append(dict(source_id=f"{block}:{diagnostic['sample_index']}",waveform_id=w['waveform_id'],receiver_id=active[diagnostic.get('receiver_index',0)],reason_code=diagnostic['reason_code'],detail=str(diagnostic)))
                for index,item in enumerate(result):
                    sample=item['sample_index'];finite(sample,'sample_index',0,True)
                    if sample>=re-rs: error('Backend sample index outside block')
                    if not cs<=rs+sample<ce: continue
                    receiver_index=item.get('receiver_index',0)
                    if not isinstance(receiver_index,int) or not 0<=receiver_index<len(active): error('Backend receiver index outside block')
                    rid=active[receiver_index]
                    if rid not in core_rids: continue
                    if backend!='stalta' and not np.all(np.isfinite(arrays[receiver_index if backend=='phasenet_das' else 0][:,sample])): error('Backend emitted pick in invalid data')
                    phase=item['phase']
                    if phase not in ('P','S','unknown'): error('Backend emitted invalid phase')
                    finite(item['score'],'score',0)
                    source_id=hashlib.sha256(f'{block}:{rid}:{phase}:{rs+sample}:{index}'.encode()).hexdigest()[:32]
                    source=dict(source_id=source_id,waveform_id=w['waveform_id'],receiver_id=rid,component=parameters['algorithm'].get('station_component') if backend=='stalta' and w['data_kind']=='station' else None,block_id=block,source_sample_index=rs+sample,processed_sample_index=sample,source_reference_time=w['start_time'],source_sampling_rate_hz=rate,raw_time=None,time_transform_id='identity')
                    flags=list(item.get('quality_flags',[]))
                    if backend!='stalta' and (sample<_samples(parameters['chunking']['context_before_s'],rate) or re-rs-sample<=_samples(parameters['chunking']['context_after_s'],rate)):
                        flags.append('boundary_context')
                    candidates.append(dict(waveform_id=w['waveform_id'],receiver_id=rid,phase=phase,time=timestamp(w['start_time'],rs+sample,rate),score=item['score'],score_type=item['score_type'],time_uncertainty_s=item.get('time_uncertainty_s'),backend_id=backend,model_id=(model or {}).get('model_id'),quality_flags=sorted(set(flags)),_source=source))
                    if len(candidates)>prepared['limits']['max_picks']: error('Candidate count limit exceeded')
    return _publish(prepared,output_dir,candidates,rejected,coverage)


def import_picks(input_path,geometry_path,output_dir,validate_read,limits,mapping=None,expected_references=None,job_id=None):
    import uuid
    from .contracts import validate_geometry
    path=Path(validate_read(input_path));geo_path=Path(validate_read(geometry_path))
    raw_geometry=read_json(geo_path,limits['max_input_bytes'])
    receivers_path=Path(validate_read(geo_path.parent/raw_geometry['receivers_ref']))
    if path.stat().st_size+geo_path.stat().st_size+receivers_path.stat().st_size>limits['max_input_bytes']: error('Import byte limit exceeded')
    references=expected_references or [{'path':str(p),'sha256':sha256(p)} for p in (path,geo_path,receivers_path)]
    expected={str(Path(ref['path']).resolve()):ref['sha256'] for ref in references}
    snapshot=Path(output_dir)/'inputs'
    if (Path(output_dir)/'manifest.json').exists(): error('Refusing to overwrite published import')
    snapshot.mkdir(parents=True,exist_ok=True)
    copied=[]
    for source,name in ((path,'external.csv'),(geo_path,'geometry.json'),(receivers_path,'receivers.csv')):
        target=snapshot/name
        shutil.copyfile(validate_read(source),target)
        if sha256(target)!=expected.get(str(source.resolve())): error('Import checksum changed while snapshotting')
        copied.append(target)
    path,geo_path,receivers_path=copied
    staged_geometry=read_json(geo_path,limits['max_input_bytes'])
    staged_geometry['receivers_ref']='receivers.csv'
    write_json(geo_path,staged_geometry)
    geometry,receivers,geometry_refs=validate_geometry(geo_path,lambda p: Path(p),limits)
    valid_ids={r['receiver_id'] for r in receivers}
    mapping=mapping or {}
    allowed={'columns','phase_map','missing_phase','score_type','waveform_id'}
    if set(mapping)-allowed: error('Unknown import mapping field')
    columns=mapping.get('columns',{})
    if set(columns)-set(PICK_FIELDS): error('Unknown mapped column')
    candidates=[];seen=set()
    with path.open(encoding='utf-8-sig',newline='') as f:
        for index,row in enumerate(csv.DictReader(f)):
            def value(key): return row.get(columns.get(key,key),'')
            rid=value('receiver_id');raw_phase=value('phase')
            if rid not in valid_ids: error('Dangling receiver_id in imported picks')
            phase=mapping.get('phase_map',{}).get(raw_phase,raw_phase)
            if not phase: phase=mapping.get('missing_phase')
            if phase not in ('P','S','unknown'): error('Invalid imported phase')
            time=value('time');instant=epoch(time)
            geo=[r for r in receivers if r['receiver_id']==rid and epoch(r['valid_from'])<=instant<epoch(r['valid_to'])]
            if len(geo)!=1: error('Imported time outside unique receiver validity')
            external=value('pick_id') or str(index)
            if external in seen: error('Duplicate imported pick_id')
            seen.add(external)
            score=float(value('score')) if value('score') else None
            score_type=value('score_type') or mapping.get('score_type') or None
            if score is not None: finite(score,'score')
            if (score is None)!=(score_type is None): error('Imported score and score_type must both be specified')
            uncertainty=float(value('time_uncertainty_s')) if value('time_uncertainty_s') else None
            if uncertainty is not None: finite(uncertainty,'time_uncertainty_s',0)
            flags=json.loads(value('quality_flags') or '[]')
            if not isinstance(flags,list) or any(not isinstance(x,str) for x in flags): error('Invalid quality_flags')
            wid=value('waveform_id') or mapping.get('waveform_id')
            if not wid: error('Imported waveform_id required')
            source=dict(source_id=external,waveform_id=wid,receiver_id=rid,raw_time=time,block_id='import',time_transform_id='identity')
            candidates.append(dict(waveform_id=wid,receiver_id=rid,phase=phase,time=timestamp(time),score=score,score_type=score_type,time_uncertainty_s=uncertainty,backend_id=value('backend_id') or 'external',model_id=value('model_id') or None,quality_flags=flags,_source=source))
            if len(candidates)>limits['max_picks']: error('Import pick limit exceeded')
    prepared={'run_id':Path(output_dir).name or uuid.uuid4().hex,'job_id':job_id,'inputs':{'geometry':geometry,'receivers':receivers,'references':references},'parameters':{},'backend_id':'external','limits':limits,'imported':True}
    return _publish(prepared,output_dir,candidates,[],[])
