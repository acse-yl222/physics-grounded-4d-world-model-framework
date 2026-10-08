"""City-independent access to retained fields, protocol views and solver entrypoints.

`python -m common.city audit` compares both cities without hiding missing capabilities.
`python -m common.city import-fields SCENE` exposes preserved fields without
resampling them or claiming their historical solvers have been reproduced.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo
import numpy as np
from .contract import validate
from .catalog import view as check_view
from .export import copy_asset, digest, write
from .runs import refresh_catalog
from .storage import Storage, scene_id

SCENES = ('south_ken', 'white_city')
MODULES = ('geometry', 'wind', 'temperature', 'solar', 'pollution', 'flood', 'traffic', 'diurnal', 'transport')
LEGACY_KEYS = {'wind': 'wind', 'temperature': 'temp', 'pollution': 'poll', 'flood': 'flood'}


def sources(storage, scene):
    scene = scene_id(scene)
    base = storage.run(scene, 'legacy_web')
    return base, json.loads((base/'scene.json').read_text()), json.loads((base/'physics/manifest.json').read_text())


def field_spec(storage, scene, module, date='20260621'):
    base, old, meta = sources(storage, scene)
    if module == 'solar':
        layer = old['layers']['solar']; filename = layer['dates'][date]['ghi']
    else:
        layer = old['layers'][LEGACY_KEYS[module]]; filename = layer['file']
    info = meta['arrays'][filename]
    path = base/'physics'/filename
    data = np.load(path, mmap_mode='r', allow_pickle=False)
    if list(data.shape) != info['shape']:
        raise ValueError(f'{module}: array and recorded shape disagree')
    epoch = None
    if 'time_utc' in info:
        utc = [datetime.fromisoformat(t.replace('Z', '+00:00')) for t in info['time_utc']]
        epoch = utc[0].isoformat(); samples = [(t-utc[0]).total_seconds() for t in utc]
    elif 'time_s' in info:
        samples = info['time_s']
    elif module == 'solar' and 'time_local' in info:
        day = datetime.strptime(date, '%Y%m%d').date().isoformat()
        utc = [datetime.fromisoformat(day+'T'+t).replace(tzinfo=ZoneInfo('Europe/London')).astimezone(timezone.utc) for t in info['time_local']]
        epoch = utc[0].isoformat(); samples = [(t-utc[0]).total_seconds() for t in utc]
    else:
        raise ValueError(f'{module}: missing recorded time axis')
    if len(samples) != len(data) or not np.isfinite(samples).all() or np.any(np.diff(samples) <= 0):
        raise ValueError(f'{module}: invalid recorded timestamps')
    heights = info.get('layer_m')
    # Legacy y is sometimes a display lift, not the physical sample height.
    z = float(np.mean(heights)) if heights else {'south_ken': {'temperature': 14., 'pollution': 14., 'wind': 10.},
                                               'white_city': {'temperature': 12., 'pollution': 12., 'wind': 12.}}[scene].get(module, 0.)
    cell = info.get('cell_m', layer['cell_m'])
    return {'path': path, 'info': info, 'samples': samples, 'epoch': epoch,
            'cell_m': cell, 'z_m': z, 'shape': list(data.shape), 'dtype': data.dtype.str,
            'origin_xy': [old['grid']['x0'], -old['grid']['z_south']]}


def field_layer(spec, module, asset):
    vector = module == 'wind'
    name, unit = {'wind': ('velocity', 'm/s'), 'temperature': ('temperature', 'degC'),
                  'solar': ('irradiance', 'W/m2'), 'pollution': ('normalized_tracer', '1'),
                  'flood': ('water_depth', 'm')}[module]
    kind = 'vector_field' if vector else 'scalar_field'
    return {'id': module, 'kind': kind, 'format': 'npy', 'asset': asset, 'sampling': 'linear',
            'field': {'name': name, 'unit': unit},
            'encoding': {'coordinate_frame': 'ENU', 'dtype': spec['dtype'], 'shape': spec['shape'],
                         'axes': 'TCYX' if vector else 'TYX', 'origin_m': [*spec['origin_xy'], spec['z_m']],
                         'spacing_m': [spec['cell_m']]*2, 'sample_location': 'cell_center',
                         'byte_order': 'little', 'compression': 'none'},
            'display': {'widget': kind, 'capabilities': ['pick', 'legend', 'opacity']}}


def register_view(storage, scene, name, runs, layers, title):
    document = {'schema_version': '1.1.0', 'scene_id': scene, 'title': title, 'time_alignment': 'relative',
                'runs': runs, 'layers': layers}
    path = storage.metadata(scene)/'views'/f'{name}.json'
    with path.open('x') as handle: json.dump(document, handle, indent=2)
    try: check_view(storage, scene, name)
    except Exception:
        path.unlink(); raise
    refresh_catalog(storage)
    return path


def import_fields(storage, scene):
    base, old, meta = sources(storage, scene)
    project = json.loads((storage.metadata(scene)/'project.json').read_text())
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    created = {}
    requested = [(m, None) for m in LEGACY_KEYS] + [('solar', d) for d in old['layers']['solar']['dates']]
    specs = [field_spec(storage, scene, module, date) for module, date in requested]
    for (module, date), spec in zip(requested, specs):
        key = module + ('_'+date if date else '')
        rid = 'city_'+key+'_'+stamp
        out = storage.run(scene, rid); out.mkdir(parents=True, exist_ok=False)
        copy_asset(spec['path'], out/'field.npy')
        # Retain original metadata and adapter evidence, not a fictional solver identity.
        copy_asset(base/'physics/manifest.json', out/'legacy_fields.json')
        copy_asset(base/'scene.json', out/'legacy_scene.json')
        layer = field_layer(spec, module, 'field.npy')
        values = np.load(out/'field.npy', mmap_mode='r')
        invalid = np.zeros(values.shape[-2:], dtype=bool)
        for frame in values:
            bad = ~np.isfinite(frame)
            invalid |= np.any(bad, axis=0) if bad.ndim == 3 else bad
        artifacts = [{'id': x, 'asset': x, 'sha256': digest(out/x), 'media_type': 'application/json'} for x in ('legacy_fields.json', 'legacy_scene.json')]
        if invalid.any():
            np.save(out/'invalid.npy', invalid.astype('u1'))
            layer['encoding'].update(mask_asset='invalid.npy', mask_dtype='|u1', mask_semantics='invalid_nonzero')
        clock = {'unit': 's', 'samples': spec['samples']}
        if spec['epoch']: clock['epoch'] = spec['epoch']
        manifest = {'schema_version': '1.1.0', 'scene_id': scene, 'simulation': module, 'run_id': rid,
                    'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
                    'provenance': {'code_revision': 'legacy-unrecorded', 'dirty': False,
                                   'parameters': {'imported': True, 'operation': 'Preserved full array; no solver recomputation',
                                                  'original_metadata': spec['info'], 'time_source': 'physics/manifest.json',
                                                  'invalid_cells': int(invalid.sum()),
                                                  'limitations': old.get('limits', []) + ['Legacy field resolution, forcing and timestamps differ between cities; not a controlled cross-city comparison.']},
                                   'inputs': [{'id': 'array', 'sha256': digest(spec['path'])}, {'id': 'metadata', 'sha256': digest(base/'physics/manifest.json')}]},
                    'spatial': project['spatial'], 'time': clock, 'layers': [layer], 'artifacts': artifacts}
        write(out/'manifest.json', manifest); validate(out/'manifest.json')
        view_name = 'city_'+key+'_'+stamp.lower()
        register_view(storage, scene, view_name, ['legacy_web', rid],
                      [{'run_id': 'legacy_web', 'layer_id': 'geometry', 'visible': True}, {'run_id': rid, 'layer_id': module, 'visible': True}],
                      f'{module} · {date or "recorded simulation"}')
        created[key] = {'run_id': rid, 'view_id': view_name}
    write(storage.metadata(scene)/'configs/city_fields.json', created)
    return created


def sample_field(storage, scene, module, x, y, time_s, date='20260621'):
    """Recorded-time query with explicit nearest-cell and linear-time semantics."""
    spec = field_spec(storage, scene, module, date)
    if not np.isfinite([x, y, time_s]).all(): raise ValueError('Query must be finite')
    col = int(np.floor((x-spec['origin_xy'][0])/spec['cell_m']))
    row = int(np.floor((y-spec['origin_xy'][1])/spec['cell_m']))
    if not (0 <= row < spec['shape'][-2] and 0 <= col < spec['shape'][-1]):
        raise ValueError('Query outside recorded grid')
    times = np.asarray(spec['samples'])
    if not times[0] <= time_s <= times[-1]: raise ValueError('Query outside recorded time; no extrapolation')
    high = min(int(np.searchsorted(times, time_s)), len(times)-1); low = max(0, high-1)
    fraction = (time_s-times[low])/(times[high]-times[low]) if high != low else 0.
    data = np.load(spec['path'], mmap_mode='r')
    a, b = np.asarray(data[low, ..., row, col], float), np.asarray(data[high, ..., row, col], float)
    value = a*(1-fraction)+b*fraction
    return {'scene_id': scene, 'module': module, 'valid': bool(np.isfinite(value).all()),
            'value': value.tolist() if np.isfinite(value).all() else None,
            'row': row, 'col': col, 'sample_height_m': spec['z_m'], 'time_s': time_s,
            'source_times_s': [float(times[low]), float(times[high])], 'epoch': spec['epoch'],
            'sampling': 'containing spatial cell; linear temporal interpolation'}


def audit(storage):
    result = {'excluded': ['uav', 'bird'], 'scenes': {}}
    for scene in SCENES:
        base, old, meta = sources(storage, scene)
        registered = json.loads((storage.metadata(scene)/'configs/city_fields.json').read_text()) if (storage.metadata(scene)/'configs/city_fields.json').exists() else {}
        modules = {}
        for module in MODULES:
            key = LEGACY_KEYS.get(module, module)
            modules[module] = {'legacy_available': module == 'geometry' or key in old.get('layers', {}) or key in old,
                               'registered_views': [v['view_id'] for k, v in registered.items() if k == module or k.startswith(module+'_')]}
        modules['geometry']['registered_views']=['default']
        for module, filename in [('traffic','traffic_result.json'),('diurnal','diurnal_result.json'),('transport','transport_snapshot.json')]:
            path=storage.metadata(scene)/'configs'/filename
            if path.exists():
                selected=json.loads(path.read_text())
                if (storage.run(scene,selected['run_id'])/'manifest.json').is_file():
                    modules[module]['registered_views']=[selected['view_id']]
                    modules[module]['run_id']=selected['run_id']
                    if 'failed_requests' in selected:modules[module]['missing_requests']=selected['failed_requests']
        for module in MODULES:
            checked=[]
            for view_id in modules[module]['registered_views']:
                try:
                    check_view(storage,scene,view_id,check_assets=False)
                    checked.append(view_id)
                except (OSError,ValueError):pass
            modules[module]['registered_views']=checked
            modules[module]['available']=bool(checked)
        modules['traffic']['rerunnable'] = (storage.metadata(scene)/'configs/traffic.json').exists() and (storage.assets(scene,'input')/'traffic/osm_20260930/map.osm.xml').exists()
        observations=storage.metadata(scene)/'configs/traffic_observations.json'
        if observations.exists():
            obs=json.loads(observations.read_text())
            modules['traffic']['observed_counts']={k:obs[k] for k in ('rows','count_points','latest_year')}
        modules['traffic']['calibration_status']='synthetic_uncalibrated'
        modules['pipeline'] = {'configured': (storage.metadata(scene)/'configs/pipeline.json').exists()}
        modules['planning'] = {'configured': (storage.metadata(scene)/'configs/planning_city_task.json').exists(),
                               'shared_rsi_runner':True}
        result['scenes'][scene] = modules
    result['module_parity']=all(result['scenes'][s][m]['available'] for s in SCENES for m in MODULES)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('audit')
    q = sub.add_parser('import-fields'); q.add_argument('scene', choices=SCENES)
    q = sub.add_parser('sample'); q.add_argument('scene', choices=SCENES); q.add_argument('module', choices=[*LEGACY_KEYS, 'solar'])
    q.add_argument('--x', type=float, required=True); q.add_argument('--y', type=float, required=True); q.add_argument('--time', type=float, required=True); q.add_argument('--date', default='20260621')
    a = p.parse_args(); storage = Storage.load()
    if a.action == 'audit': result = audit(storage)
    elif a.action == 'import-fields': result = import_fields(storage, a.scene)
    else: result = sample_field(storage, a.scene, a.module, a.x, a.y, a.time, a.date)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__': main()
