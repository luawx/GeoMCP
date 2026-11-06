"""Fixed, offline picking adapters. Scores retain native semantics."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np
if __name__ != '__main__':
    from geomcp.exceptions import ScientificToolError


def describe_backends():
    return [dict(backend_id=k, adapter_version='1', data_kinds=d, phases=p, score_type=s,
                 scientific_acceptance='not_benchmarked', requires_model=k!='stalta')
            for k,d,p,s in [('stalta',['station','das'],['unknown'],'stalta_ratio'),
                            ('phasenet',['station'],['P','S'],'model_score'),
                            ('phasenet_das',['das'],['P','S'],'model_score')]]


def _candidate(receiver, phase, index, score, score_type):
    return dict(receiver_index=int(receiver),phase=phase,sample_index=int(index),score=float(score),
                score_type=score_type,time_uncertainty_s=None,quality_flags=[])


def _samples(seconds, rate):
    from decimal import Decimal, ROUND_HALF_UP
    return int((Decimal(str(seconds))*Decimal(str(rate))).to_integral_value(rounding=ROUND_HALF_UP))


def _stalta(data, rate, parameters, context):
    a = parameters['algorithm']
    nsta, nlta = _samples(a['sta_s'],rate), _samples(a['lta_s'],rate)
    if not 1 <= nsta < nlta:
        raise ScientificToolError('STA/LTA windows require 1 <= nsta < nlta')
    on, off = a['threshold_on'], a['threshold_off']
    if not on > off > 0:
        raise ScientificToolError('STA/LTA thresholds require on > off > 0')
    if context.get('data_kind') == 'station':
        components = context.get('components', [])
        if a.get('station_component') not in components:
            raise ScientificToolError('STA/LTA station_component requires explicit component mapping')
        rows = [(0, data[components.index(a['station_component'])])]
    else:
        rows = enumerate(data)
    output = []
    block = int(context.get('block_size',data.shape[1]))
    if block <= 0:
        raise ScientificToolError('block_size must be positive')
    state = context.get('state', {})
    diagnostics = context.get('diagnostics', [])
    offset = int(context.get('offset', 0))
    if state.get('_next_offset', offset) != offset:
        raise ScientificToolError('Non-contiguous STA/LTA stream offset')
    def reject(receiver, start, end, reason):
        diagnostics.append(dict(receiver_index=receiver,sample_index=start,end_sample_index=end,reason_code=reason))
    for receiver, row in rows:
        sta, lta, age, start, peak = state.get(receiver,(0., np.finfo(float).tiny, 0, None, 0.))
        for chunk_offset in range(0,len(row),block):
            for local in range(chunk_offset,min(chunk_offset+block,len(row))):
                index = offset + local
                value = row[local]
                if not np.isfinite(value):
                    if start is not None:
                        reject(receiver,start,index,'gap_trigger')
                    sta, lta, age, start, peak = 0., np.finfo(float).tiny, 0, None, 0.
                    continue
                if age == 0:
                    age = 1
                    continue
                square = float(value)*float(value)
                if not np.isfinite(square):
                    raise ScientificToolError('STA/LTA non-finite squared amplitude')
                sta = (1.-1./nsta)*sta + square/nsta
                lta = (1.-1./nlta)*lta + square/nlta
                ratio = sta/lta if age >= nlta and lta>0 else 0.
                if not np.isfinite(sta) or not np.isfinite(lta) or not np.isfinite(ratio):
                    raise ScientificToolError('STA/LTA non-finite recurrence')
                age += 1
                if start is None and ratio > on:
                    start, peak = index, ratio
                elif start is not None:
                    peak = max(peak,ratio)
                    if ratio <= off:
                        duration = (index-start)/rate
                        if a['min_trigger_s'] <= duration <= a['max_trigger_s']:
                            output.append(_candidate(receiver,'unknown',start,peak,'stalta_ratio'))
                        else:
                            reject(receiver,start,index,'short_trigger' if duration<a['min_trigger_s'] else 'long_trigger')
                        start, peak = None, 0.
        if context.get('final', 'state' not in context) and start is not None:
            reject(receiver,start,offset+len(row),'unclosed_trigger')
            start,peak=None,0.
        state[receiver]=(sta,lta,age,start,peak)
    state['_next_offset'] = offset + data.shape[1]
    return output


def run_backend(backend_id, data, sampling_rate, parameters, model, context):
    if backend_id not in {x['backend_id'] for x in describe_backends()}:
        raise ScientificToolError('Unknown picking backend')
    data = np.asarray(data,dtype=np.float64)
    if data.ndim != 2 or not data.size or not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ScientificToolError('Invalid waveform shape or sampling rate')
    if backend_id == 'stalta':
        return _stalta(data,sampling_rate,parameters,context)
    if not model:
        raise ScientificToolError('Registered model is required')
    for key in ('python','source_dir','weights','sha256','sampling_rate_hz'):
        if key not in model:
            raise ScientificToolError(f'Registered model requires {key}')
    if sampling_rate != model['sampling_rate_hz']:
        raise ScientificToolError('Sampling rate incompatible with model')
    if not np.isfinite(data).all():
        raise ScientificToolError('Deep models require finite continuous input')
    if backend_id == 'phasenet' and (data.shape[0] != 3 or context.get('components') != model.get('components')):
        raise ScientificToolError('PhaseNet requires registered three component order')
    if not model['sha256']:
        raise ScientificToolError('Model weight checksums required')
    for path, digest in model['sha256'].items():
        p = Path(path)
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ScientificToolError('Model weight checksum mismatch')
    if not Path(model['python']).is_file() or not Path(model['source_dir']).is_dir():
        raise ScientificToolError('Registered model environment/source missing')
    weights = Path(model['weights']).resolve()
    weight_files = [weights] if weights.is_file() else list(weights.parent.glob(weights.name+'.*'))
    verified = {Path(p).resolve() for p in model['sha256']}
    if not weight_files or not set(weight_files) <= verified:
        raise ScientificToolError('All model weight files require checksums')
    provenance_file = Path(model['source_dir'])/'PROVENANCE.json'
    try:
        expected_provenance = {'phasenet': 'd103df389738e752c480f9f9d01560e84c61fe53dd77f8ddb2d6121fd0703f2d', 'phasenet_das': '865b4c2d77e2d4c6fbb0e0383f9b1dbdd0304d7b1b58e8c60306a8029a092c20'}
        if hashlib.sha256(provenance_file.read_bytes()).hexdigest() != expected_provenance[backend_id]:
            raise ValueError('Unregistered source manifest')
        provenance = json.loads(provenance_file.read_text())
        expected_commit = {'phasenet':'62005c6195638f88d077f8870ea895971062715a',
                           'phasenet_das':'7dd24edd275b914115c0c6bdf2c329517f61efc8'}[backend_id]
        if provenance['commit'] != expected_commit:
            raise ValueError('Unregistered source version')
        for rel, digest in provenance['files_sha256'].items():
            source = (Path(model['source_dir'])/rel).resolve()
            if not source.is_relative_to(Path(model['source_dir']).resolve()) or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                raise ValueError('Source checksum mismatch')
    except (OSError, ValueError, KeyError) as exc:
        raise ScientificToolError('Pinned source provenance verification failed') from exc
    root = context.get('output_dir')
    with tempfile.TemporaryDirectory(prefix='picker-',dir=root) as temp:
        work = Path(temp)
        np.save(work/'input.npy',data,allow_pickle=False)
        request = dict(backend_id=backend_id,model=model,device=context.get('device','cpu'),algorithm=parameters['algorithm'])
        (work/'request.json').write_text(json.dumps(request),encoding='utf-8')
        try:
            with (work/'stdout.log').open('wb') as stdout, (work/'stderr.log').open('wb') as stderr:
                completed = subprocess.run([str(model['python']),str(Path(__file__).resolve()),str(work)],
                                          stdout=stdout,stderr=stderr,timeout=context.get('timeout_s',3600),shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ScientificToolError(f'Model execution failed: {type(exc).__name__}') from exc
        if completed.returncode:
            with (work/'stderr.log').open('rb') as log:
                log.seek(0,2)
                log.seek(max(0,log.tell()-2000))
                tail=log.read(2000).decode('utf-8',errors='replace')
            raise ScientificToolError('Model execution failed: '+tail)
        try:
            probabilities = np.load(work/'probabilities.npy',allow_pickle=False)
        except (OSError,ValueError) as exc:
            raise ScientificToolError('Missing or corrupt model output') from exc
        expected = (1 if backend_id == 'phasenet' else data.shape[0], 3, data.shape[1])
        if probabilities.shape != expected or not np.isfinite(probabilities).all() or np.any((probabilities<0)|(probabilities>1)):
            raise ScientificToolError('Invalid model score tensor')
        if context.get('save_native', True) and root is not None:
            native = Path(root)
            validated=work/'validated.npy'
            np.save(validated,probabilities,allow_pickle=False)
            total=validated.stat().st_size+sum(min((work/name).stat().st_size,1024*1024) for name in ('stdout.log','stderr.log'))
            if total>context.get('max_native_bytes',float('inf')):
                raise ScientificToolError('Native model output exceeds max_native_bytes')
            validated.replace(native/'probabilities.npy')
            for name in ('stdout.log','stderr.log'):
                _save_log_tail(work/name,native/name)
    from scipy.signal import find_peaks
    picks=[]
    a=parameters['algorithm']
    for receiver, scores in enumerate(probabilities):
        for phase, channel in [('P',1),('S',2)]:
            indices,_=find_peaks(scores[channel],height=a[phase.lower()+'_threshold'],distance=max(1,_samples(a['min_peak_distance_s'],sampling_rate)))
            picks.extend(_candidate(receiver,phase,i,scores[channel,i],'model_score') for i in indices)
    return picks


def _save_log_tail(source, target, limit=1024*1024):
    """Persist bounded diagnostics without loading full subprocess logs."""
    marker=b'[truncated; last bytes follow]\n'
    size=source.stat().st_size
    with source.open('rb') as stream, target.open('wb') as output:
        if size>limit:
            output.write(marker)
            stream.seek(size-(limit-len(marker)))
        while True:
            chunk=stream.read(65536)
            if not chunk:
                break
            output.write(chunk)


def _isolated_main(work):
    import os
    work=Path(work)
    request=json.loads((work/'request.json').read_text(encoding='utf-8'))
    model=request['model']
    sys.path.insert(0,model['source_dir'])
    data=np.load(work/'input.npy',allow_pickle=False)
    device=request['device']
    if device == 'cpu':
        os.environ['CUDA_VISIBLE_DEVICES']='-1'
    if request['backend_id']=='phasenet':
        import tensorflow as tf
        from phasenet.model import ModelConfig, UNet
        if device != 'cpu' and not tf.config.list_physical_devices('GPU'):
            raise RuntimeError('Requested GPU unavailable')
        config=ModelConfig(X_shape=[data.shape[1],1,3],Y_shape=[data.shape[1],1,3])
        network=UNet(config=config,mode='pred')
        saver=tf.compat.v1.train.Saver()
        with tf.compat.v1.Session() as session:
            saver.restore(session,model['weights'])
            from phasenet.data_reader import normalize
            x=normalize(data.T[:,None,:].copy())[None,:,:,:].astype('float32')
            scores=session.run(network.preds,feed_dict={network.X:x,network.drop_rate:0.,network.is_training:False})
        result=scores[0,:,0,:].T[None,:,:]
    else:
        import torch
        from eqnet.models.phasenet_das import build_model
        if device != 'cpu' and not torch.cuda.is_available():
            raise RuntimeError('Requested GPU unavailable')
        network=build_model(**model.get('model_kwargs',{})).to(device)
        state=torch.load(model['weights'],map_location=device,weights_only=True)
        network.load_state_dict(state.get('model',state))
        network.eval()
        with torch.inference_mode():
            x=torch.as_tensor(data.T[None,None,:,:],dtype=torch.float32,device=device)
            nt,nx=x.shape[-2:]
            x=torch.nn.functional.pad(x,(0,(-nx)%1024,0,max(2048,((nt+1023)//1024)*1024)-nt))
            result=network({'data':x})['phase'].softmax(dim=1)[0,:,:nt,:nx].permute(2,0,1).cpu().numpy()
    np.save(work/'probabilities.npy',result,allow_pickle=False)

if __name__=='__main__':
    _isolated_main(sys.argv[1])
