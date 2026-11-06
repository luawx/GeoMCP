from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from geomcp.exceptions import ScientificToolError

SCHEMA = '1.0'
DEFAULTS = {
    'selection': {'start_time': None, 'end_time': None, 'receiver_ids': None},
    'preprocessing': {'gap_policy': 'split', 'detrend': 'none', 'bandpass_hz': None, 'target_sampling_rate_hz': None},
    'chunking': {'core_duration_s': 120., 'context_before_s': 30., 'context_after_s': 10., 'core_channels': 64, 'context_channels': 0},
    'postprocessing': {'dedup_window_s': 0.},
    'output': {'save_native': True},
}
ALGORITHMS = {
    'stalta': {'method': 'recursive_sta_lta', 'sta_s': .5, 'lta_s': 5., 'threshold_on': 3., 'threshold_off': 1.5, 'min_trigger_s': .1, 'max_trigger_s': 10., 'station_component': 'Z'},
    'phasenet': {'p_threshold': .3, 's_threshold': .3, 'min_peak_distance_s': .5, 'batch_size': 1},
    'phasenet_das': {'p_threshold': .3, 's_threshold': .3, 'min_peak_distance_s': .5, 'batch_size': 1},
}


def error(message):
    raise ScientificToolError(message)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(path, limit=8*1024*1024):
    path = Path(path)
    if path.stat().st_size > limit:
        error('Metadata size limit exceeded')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: error(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda value: error(f'Non-finite JSON: {value}'))


def epoch(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        error('Time must be UTC ISO 8601 with Z')
    try:
        base, _, frac = value[:-1].partition('.')
        dt = datetime.strptime(base, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        if len(frac) > 9 or (frac and not frac.isdigit()): error('Invalid time precision')
        return Decimal(int(dt.timestamp())) + (Decimal('0.' + frac) if frac else 0)
    except ValueError as exc:
        raise ScientificToolError('Invalid UTC time') from exc


def timestamp(reference, index=0, rate=1):
    value = epoch(reference) + Decimal(str(index)) / Decimal(str(rate))
    ns = int((value * 10**9).to_integral_value(rounding=ROUND_HALF_UP))
    sec, nano = divmod(ns, 10**9)
    return datetime.fromtimestamp(sec, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + f'.{nano:09d}Z'


def finite(value, name, minimum=None, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        error(f'{name} must be finite numeric')
    if integer and not isinstance(value, int): error(f'{name} must be integer')
    if minimum is not None and value < minimum: error(f'{name} out of range')
    return value


def resolve_parameters(preset, overrides, backend_id, limits):
    if backend_id not in ALGORITHMS: error(f'Unknown backend: {backend_id}')
    effective = copy.deepcopy(DEFAULTS)
    effective['algorithm'] = copy.deepcopy(ALGORITHMS[backend_id])
    sources = {f'{group}.{key}': 'default' for group, fields in effective.items() for key in fields}
    for values, source in [(preset.get('parameters', {}), 'preset'), (overrides or {}, 'override')]:
        if not isinstance(values, dict): error('Parameters must be objects')
        for group, fields in values.items():
            if group not in effective or not isinstance(fields, dict): error(f'Unknown parameter group: {group}')
            for key, value in fields.items():
                if key not in effective[group]: error(f'Unknown parameter: {group}.{key}')
                effective[group][key] = copy.deepcopy(value)
                sources[f'{group}.{key}'] = source
    pre = effective['preprocessing']
    if pre['gap_policy'] != 'split' or pre['detrend'] not in ('none', 'constant', 'linear'): error('Unsupported preprocessing')
    if pre['target_sampling_rate_hz'] is not None:
        finite(pre['target_sampling_rate_hz'], 'target_sampling_rate_hz', .000001)
    if pre['bandpass_hz'] is not None:
        band = pre['bandpass_hz']
        if not isinstance(band, list) or len(band) != 2: error('bandpass_hz needs two frequencies')
        finite(band[0], 'low frequency', .000001); finite(band[1], 'high frequency', .000001)
        if band[0] >= band[1]: error('Invalid frequency order')
    select = effective['selection']
    for name in ('start_time', 'end_time'):
        if select[name] is not None: epoch(select[name])
    if select['start_time'] and select['end_time'] and epoch(select['start_time']) >= epoch(select['end_time']): error('Invalid selection time range')
    ids = select['receiver_ids']
    if ids is not None and (not isinstance(ids, list) or not ids or any(not isinstance(x,str) for x in ids) or len(ids) != len(set(ids))): error('Invalid receiver_ids')
    for key, value in effective['chunking'].items():
        finite(value, key, 1 if key in ('core_duration_s', 'core_channels') else 0, key.endswith('channels'))
    finite(effective['postprocessing']['dedup_window_s'], 'dedup_window_s', 0)
    if not isinstance(effective['output']['save_native'], bool): error('save_native must be boolean')
    a = effective['algorithm']
    if backend_id == 'stalta':
        if a['method'] != 'recursive_sta_lta': error('Unsupported STA/LTA method')
        for key in ('sta_s', 'lta_s', 'threshold_on', 'threshold_off', 'max_trigger_s'): finite(a[key], key, .000001)
        finite(a['min_trigger_s'], 'min_trigger_s', 0)
        if not (a['sta_s'] < a['lta_s'] and a['threshold_off'] < a['threshold_on'] and a['min_trigger_s'] < a['max_trigger_s']): error('Invalid STA/LTA windows/thresholds')
        if not isinstance(a['station_component'], str) or not a['station_component']: error('Invalid station_component')
    else:
        for key in ('p_threshold', 's_threshold'):
            finite(a[key], key, 0)
            if a[key] > 1: error('Phase threshold must be <=1')
        finite(a['min_peak_distance_s'], 'min_peak_distance_s', .000001)
        finite(a['batch_size'], 'batch_size', 1, True)
        if a['batch_size'] > limits.get('max_batch_size', 64): error('batch_size exceeds administrator limit')
    # A deployment can narrow every exposed numeric field without changing the public schema.
    for field, bounds in limits.get('parameter_ranges', {}).items():
        group, key = field.split('.')
        value = effective[group][key]
        if not bounds[0] <= value <= bounds[1]: error(f'{field} exceeds administrator range')
    allowed = preset.get('allowed_overrides')
    if allowed is not None:
        for group, fields in (overrides or {}).items():
            for key in fields:
                if f'{group}.{key}' not in allowed: error(f'Override not permitted: {group}.{key}')
    return {'effective': effective, 'sources': sources}


def prepare_inputs(waveform_manifest_path, geometry_path, validate_read, limits):
    max_bytes = limits.get('max_input_bytes', 64*1024*1024)
    references = []
    total_bytes = 0
    def checked(path, expected=None):
        nonlocal total_bytes
        path = Path(validate_read(Path(path)))
        if not path.is_file(): error(f'Missing input file: {path}')
        size = path.stat().st_size
        if size > max_bytes: error('Input byte limit exceeded')
        digest = sha256(path)
        if expected is not None and digest != expected: error(f'Input checksum mismatch: {path.name}')
        if str(path) not in [r['path'] for r in references]:
            total_bytes += size
            if total_bytes > max_bytes: error('Total input byte limit exceeded')
            references.append({'path': str(path), 'sha256': digest})
        return path
    manifest_path = checked(waveform_manifest_path)
    geometry_path = checked(geometry_path)
    manifest = read_json(manifest_path, max_bytes)
    geometry, receivers, geometry_refs = validate_geometry(geometry_path, validate_read, limits)
    if manifest.get('schema_version') != SCHEMA: error('Unsupported schema_version')
    if manifest.get('geometry_id') != geometry.get('geometry_id'): error('geometry_id mismatch')
    for ref in geometry_refs:
        checked(ref['path'], ref['sha256'])
    grouped = {}
    for row in receivers:
        grouped.setdefault(row['receiver_id'], []).append(row)
    waveforms=manifest.get('waveforms')
    if not isinstance(waveforms,list) or not waveforms: error('Empty waveform input')
    ids=set(); samples=0
    normalized=[]
    for source in waveforms:
        w=copy.deepcopy(source)
        wid=w.get('waveform_id')
        if not wid or wid in ids: error('Duplicate or missing waveform_id')
        ids.add(wid)
        kind=w.get('data_kind')
        if (kind,w.get('format')) not in [('das','hdf5'),('station','mseed')]: error('Unsupported waveform format')
        finite(w.get('sampling_rate_hz'),'sampling_rate_hz',.000001)
        finite(w.get('sample_count'),'sample_count',1,True)
        if not w.get('quantity') or not w.get('unit'): error('Physical quantity and unit required')
        if w.get('geometry_id')!=geometry['geometry_id']: error('Waveform geometry mismatch')
        start,end=epoch(w['start_time']),epoch(w['end_time'])
        expected=Decimal(w['sample_count'])/Decimal(str(w['sampling_rate_hz']))
        if abs(end-start-expected)>Decimal('0.000000001'): error('Waveform time/sample_count mismatch')
        rids=w.get('receiver_ids')
        if not isinstance(rids,list) or not rids or len(set(rids))!=len(rids): error('Invalid waveform receiver_ids')
        for rid in rids:
            if rid not in grouped: error('Dangling receiver_id')
            valid_rows=[r for r in grouped[rid] if epoch(r['valid_from'])<=start and epoch(r['valid_to'])>=end]
            if len(valid_rows)!=1: error('Waveform outside unique receiver validity interval')
            if valid_rows[0].get('data_kind') != kind: error('Receiver data_kind mismatch')
        if not isinstance(w.get('files'),list) or not w['files']: error('Waveform files required')
        for ref in w['files']:
            ref['path']=str(checked(manifest_path.parent / ref['path'], ref.get('sha256')))
        samples+=w['sample_count']*len(rids)*max(1,len(w.get('components',[])))
        if samples>limits.get('max_samples',100000000): error('Sample count limit exceeded')
        if kind=='das':
            opts=w.get('format_options',{})
            if not opts.get('dataset') or opts.get('axis_order') not in ('channel,time','time,channel'): error('Explicit HDF5 dataset/axis_order required')
            channels=opts.get('channel_ids')
            if not isinstance(channels,list) or len(channels)!=len(rids) or len(set(channels))!=len(channels): error('Invalid channel_ids')
            for rid,ch in zip(rids,channels):
                if str(grouped[rid][0].get('channel_id')) != str(ch): error('DAS channel geometry mapping mismatch')
            segments=opts.get('spatial_segments',[[0,len(rids)]])
            cursor=0
            if not isinstance(segments,list) or not segments: error('Invalid spatial_segments')
            for segment in segments:
                if not isinstance(segment,list) or len(segment)!=2 or any(isinstance(x,bool) or not isinstance(x,int) for x in segment) or segment[0]!=cursor or not cursor<segment[1]<=len(rids): error('spatial_segments must partition acquisition channel indices')
                cursor=segment[1]
            if cursor!=len(rids): error('spatial_segments must cover acquisition channels')
        for gap in w.get('gaps',[]):
            if not (isinstance(gap,dict) and isinstance(gap.get('sample_start'),int) and isinstance(gap.get('sample_stop'),int) and 0<=gap['sample_start']<gap['sample_stop']<=w['sample_count']): error('Invalid gap sample interval')
        if not set(w.get('bad_receivers',[]))<=set(rids): error('Unknown bad receiver')
        normalized.append(w)
    return {'schema_version':SCHEMA,'manifest':manifest,'geometry':geometry,'receivers':receivers,'waveforms':normalized,'references':references,'estimated_samples':samples,'input_bytes':total_bytes}


def inspect(path, validate_read, limits):
    path=Path(validate_read(path))
    obj=read_json(path,limits.get('max_input_bytes',8*1024*1024))
    return {'schema_version':obj.get('schema_version'),'kind':'waveform_manifest' if 'waveforms' in obj else 'artifact','waveform_count':len(obj.get('waveforms',[])),'manifest_id':obj.get('manifest_id'),'geometry_id':obj.get('geometry_id'),'status':obj.get('status')}


def location_picks(picks):
    accepted=[p for p in picks if p.get('phase') in ('P','S')]
    return accepted,len(picks)-len(accepted)


def validate_geometry(geometry_path, validate_read, limits):
    """Validate standalone geometry identically for imported and inferred picks."""
    path = Path(validate_read(Path(geometry_path)))
    budget = limits['max_input_bytes']
    geometry = read_json(path, budget)
    if geometry.get('schema_version') != SCHEMA or not isinstance(geometry.get('geometry_id'), str) or not geometry['geometry_id']:
        error('Invalid geometry schema or geometry_id')
    if geometry.get('crs') not in ('EPSG:4326', 'OGC:CRS84'):
        error('First release requires geographic WGS84 CRS')
    if geometry.get('axis_order') != 'longitude,latitude' or not isinstance(geometry.get('vertical_datum'), str) or not geometry['vertical_datum']:
        error('Geometry axis order and vertical datum required')
    ref = geometry.get('receivers_ref')
    if not isinstance(ref, str) or not ref:
        error('receivers_ref required')
    receivers_path = Path(validate_read(path.parent / ref))
    if path.stat().st_size + receivers_path.stat().st_size > budget:
        error('Geometry input byte limit exceeded')
    checksum = sha256(receivers_path)
    if geometry.get('receivers_sha256') != checksum:
        error('Geometry receiver checksum missing or mismatch')
    with receivers_path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'receiver_id', 'data_kind', 'network', 'station', 'location', 'channel_id', 'longitude_deg', 'latitude_deg', 'elevation_m', 'valid_from', 'valid_to'}
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            error('Geometry receiver CSV required columns missing')
        receivers = []
        for row in reader:
            if len(receivers) >= limits['max_receivers']:
                error('Receiver count limit exceeded')
            receivers.append(row)
    if not receivers:
        error('Empty receiver geometry')
    grouped = {}
    for row in receivers:
        rid = row['receiver_id']
        if not rid or row['data_kind'] not in ('station', 'das'):
            error('Invalid receiver identity or data_kind')
        if row['data_kind'] == 'station' and (not row['network'] or not row['station']):
            error('Station network and station required')
        if row['data_kind'] == 'das' and not row['channel_id']:
            error('DAS channel_id required')
        for field, low, high in [('longitude_deg', -180, 180), ('latitude_deg', -90, 90), ('elevation_m', -15000, 15000)]:
            try:
                value = float(row[field])
            except (TypeError, ValueError) as exc:
                raise ScientificToolError('Invalid receiver coordinate') from exc
            finite(value, field)
            if not low <= value <= high:
                error('Geometry coordinate out of bounds')
        start, end = epoch(row['valid_from']), epoch(row['valid_to'])
        if start >= end:
            error('Invalid receiver validity')
        for old in grouped.get(rid, []):
            if start < epoch(old['valid_to']) and end > epoch(old['valid_from']):
                error('Overlapping receiver validity')
        grouped.setdefault(rid, []).append(row)
    references = [{'path': str(path), 'sha256': sha256(path)}, {'path': str(receivers_path), 'sha256': checksum}]
    return geometry, receivers, references
