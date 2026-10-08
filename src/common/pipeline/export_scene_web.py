"""Export a finished scene into the web viewer: visualizer/scenes/<scene>/{models,physics,scene.json}.

    python src/common/pipeline/export_scene_web.py --config input/<scene>/config.json

Generic version of visualizer/scenes/white_city/tools/export_from_run.py: reads whatever stages of
output/<scene>/ are complete (wind, 3-D physical temperature, pollution, solar, flood), writes one float16
viewer array per layer (row 0 = south = local -y, col 0 = west = local -x), manifest.json, a scene.json built
from the geometry metadata, registers the scene in visualizer/scenes/index.json and pre-renders the PNG
frames with visualizer/scenes/tools/export_web_frames.py. The city model is the input GLB itself
(hard-linked; the viewer decodes Draco and plain glTF).
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

if __package__ in (None, ''):
    sys.path.insert(0, str(repo_root()))
from common.pipeline.paths import ROOT
from urban_geometry.voxelization.glb_plan import read_glb_header
from common.pipeline.run_scene import load_config, read_json, rel


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True)
    ap.add_argument('--no-frames', action='store_true', help='skip the PNG frame pre-render')
    args = ap.parse_args()
    cfg, p = load_config(args.config)
    scene, cell = cfg['scene'], cfg['domain']['cell_m']
    coarse = cell * cfg['wind']['coarse_factor']
    LZ = int(cfg['visualize']['layer'])
    zlo, zhi = LZ * coarse, (LZ + 1) * coarse
    G, RUN, PHYS = p['geometry'], p['run'], p['physics']
    web = p['scene_web']
    out = web / 'physics'
    (web / 'models').mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((G / 'metadata.json').read_text())
    nz, ny, nx = meta['shape_zyx']
    ox, oy, _ = meta['source_region_origin_xyz_m']
    step_s = float(cfg['wind']['step_seconds'])

    # ---- city model: keep a hand-packed model from an earlier export, else hard-link the input GLB
    existing = read_json(web / 'scene.json') or {}
    kept_model = existing.get('model') if existing.get('model') and (web / existing['model'].get('url', '')).is_file() else None
    doc, _ = read_glb_header(p['source'])
    compression = 'draco' if 'KHR_draco_mesh_compression' in doc.get('extensionsUsed', []) else 'none'
    model = web / 'models' / f'{scene}.glb'
    if kept_model is None and not (model.exists() and model.stat().st_size == p['source'].stat().st_size):
        if model.exists() or model.is_symlink():
            model.unlink()
        try:
            os.link(p['source'], model)
        except OSError:
            shutil.copy2(p['source'], model)

    man = {'run': scene, 'generated': time.strftime('%Y-%m-%dT%H:%M'), 'source_run': str(p['out']),
           'cell_m': cell, 'coarse_cell_m': coarse, 'local_origin_xy_m': [ox, oy], 'gltf_to_local_xyz': '(x, -z, y)',
           'orientation': 'row 0 = south (local -y), col 0 = west (local -x); north assumed = local +y unless georeferenced',
           'wind_step_seconds': step_s, 'arrays': {}, 'limits': [], 'exported_stages': []}

    def save(relpath, arr, **info):
        path = out / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, arr)
        man['arrays'][relpath] = {'shape': list(arr.shape), 'dtype': str(arr.dtype), **info}
        print(f'{relpath:50s} {str(arr.dtype):8s} {arr.shape} {path.stat().st_size / 1e6:7.1f} MB', flush=True)

    # ---- geometry masks
    foot = np.load(G / f'footprint_{cell}m_yx.npy')
    height = np.load(G / 'height_m.npy')
    save(f'masks/building_footprint_{cell}m_yx.npy', foot.astype(bool), meaning=f'True = building column ({cell} m cells)')
    save(f'masks/roof_height_m_{cell}m_yx.npy', height.astype(np.float16), meaning=f'max roof height per {cell} m cell, metres')
    save(f'masks/building_footprint_{coarse}m_yx.npy', np.load(G / f'footprint_{coarse}m_yx.npy').astype(bool), meaning=f'True = building ({coarse} m cells)')
    for k in ('grass', 'asphalt', 'paving', 'canopy'):
        src = G / f'{k}_{coarse}m_yx.npy'
        if src.exists():
            save(f'masks/{k}_{coarse}m_yx.npy', np.load(src).astype(bool), meaning=f'{k} ({coarse} m cells, from the GLB materials)')
    solid_coarse = RUN / 'temperature' / f'solid_{coarse}m_zyx.npy'
    if solid_coarse.exists():
        solid = np.load(solid_coarse).astype(bool)
    else:
        layers = cfg['domain']['wind_layers']
        fine = np.load(G / 'solid.npy', mmap_mode='r')[:layers]
        f = cfg['wind']['coarse_factor']
        solid = np.asarray(fine).reshape(layers // f, f, ny // f, f, nx // f, f).max(axis=(1, 3, 5))
    save(f'masks/solid_{coarse}m_zyx.npy', solid, meaning=f'True = building, {solid.shape[0]} layers x {coarse} m')
    man['exported_stages'].append('geometry')

    layers_json = {}
    phase_order = []
    timeline = None

    # ---- wind
    wind_files = sorted(glob.glob(str(RUN / 'wind' / f'wind{coarse}m_*.npz')))[1:]
    wind_done = read_json(p['status'], {}).get('stages', {}).get('wind', {}).get('status') == 'done' or \
        (RUN / 'wind' / f'velocity_final_{cell}m_raw_czyx_float16.npy').is_file()
    if wind_done and wind_files:
        uvw = np.empty((len(wind_files), 3, ny // cfg['wind']['coarse_factor'], nx // cfg['wind']['coarse_factor']), np.float16)
        for i, f in enumerate(wind_files):
            with np.load(f) as d:
                uvw[i] = d['uvw'][:, LZ]
        name = f'wind/uvw_{coarse}m_z{zlo}-{zhi}m_tcyx.npy'
        save(name, uvw, components='u local +x, v local +y, w up (m/s)', time_s=[step_s * (i + 1) for i in range(len(wind_files))],
             layer_m=[zlo, zhi],
             note='SCALED latent surrogate, block mean of the fine field, solid cells zero')
        timeline = {'step_s': step_s, 'steps': len(wind_files)}
        layers_json['wind'] = {'file': name, 'cell_m': coarse, 'frames': len(wind_files), 't0_s': step_s, 'step_s': step_s,
                               'range': [0, 1.8], 'web_range': [-2.5, 2.5], 'y': zlo + coarse / 2,
                               'label': f'Wind speed · {zlo}–{zhi} m', 'legend': ['0', '|V| m/s', '1.8'],
                               'title': f'Wind speed · {zlo}–{zhi} m (SCALED, {coarse} m frames)'}
        phase_order.append('wind')
        man['exported_stages'].append('wind')
        man['limits'].append('Wind: SCALED surrogate transfer, no CFD or measured validation.')

    # ---- temperature: 3-D physical solver
    T = p['temperature3d']
    tcfg = read_json(T / 'run_config.json')
    if read_json(T / 'summary.json', {}).get('complete') and tcfg:
        tz = np.load(T / 'temperature_c_tzyx.npy', mmap_mode='r')
        name = f'temperature/temperature_{coarse}m_z{zlo}-{zhi}m_tyx.npy'
        frames = tz.shape[0]
        dt = tcfg['duration_seconds'] / max(frames - 1, 1)
        save(name, np.asarray(tz[:, LZ]).astype(np.float16), time_s=[dt * i for i in range(frames)], units='C',
             layer_m=[zlo, zhi],
             ambient_c=tcfg['ambient_c'], surface_c=tcfg['surface_c'],
             note='Yi Qi 3-D finite-difference solver driven by the last wind frames; controlled thermal scenario')
        man['temperature3d_physical'] = {k: tcfg[k] for k in ('ambient_c', 'surface_c', 'cell_m', 'duration_seconds', 'limitations') if k in tcfg}
        lo, hi = float(tcfg['ambient_c']), float(tcfg['surface_c'])
        layers_json['temp'] = {'file': name, 'cell_m': coarse, 'frames': frames, 't0_s': 0, 'step_s': dt,
                               'range': [lo, hi], 'web_range': [lo - 1, hi + 1], 'y': 0.6,
                               'iso': {'from': lo, 'step': 0.25, 'n': int((hi - lo) / 0.25) + 1}, 'iso_label': 'Isotherms (every 0.25 °C)',
                               'label': f'Temperature · 3-D physical model, {zlo}–{zhi} m', 'legend': [f'{lo:g}', '°C', f'{hi:g}'],
                               'title': f'Temperature · 3-D physical solver ({zlo}–{zhi} m)'}
        phase_order.append('temp')
        man['exported_stages'].append('temperature3d')
        man['limits'].append(f'Temperature: controlled scenario ({lo:g} °C air, {hi:g} °C surfaces), not measured.')

    # ---- pollution
    poll_files = sorted(glob.glob(str(RUN / 'pollution' / 'concentration_*.npz')))
    if read_json(RUN / 'pollution' / 'status.json', {}).get('complete') and poll_files:
        conc = np.empty((len(poll_files), ny // cfg['wind']['coarse_factor'], nx // cfg['wind']['coarse_factor']), np.float16)
        for i, f in enumerate(poll_files):
            with np.load(f) as d:
                conc[i] = d['concentration'][LZ]
        name = f'pollution/concentration_{coarse}m_z{zlo}-{zhi}m_tyx.npy'
        save(name, conc, time_s=[step_s * (i + 1) for i in range(len(poll_files))],
             note='upwind transport of an assumed line source, driven by the wind frames; arbitrary units')
        layers_json['poll'] = {'file': name, 'cell_m': coarse, 'frames': len(poll_files), 't0_s': step_s, 'step_s': step_s, 'y': zlo + coarse / 2 + 2,
                               'label': f'Pollution · {zlo}–{zhi} m tracer layer (assumed line source)',
                               'legend': ['0.1', 'concentration (log)', '1000'],
                               'title': f'Pollution · {zlo}–{zhi} m tracer concentration (assumed upstream line source)'}
        phase_order.append('poll')
        man['exported_stages'].append('pollution')
        man['limits'].append('Pollution: assumed upstream line source, not measured concentrations.')

    # ---- sunlight
    S = PHYS / 'solar_experimental'
    srun = read_json(S / 'run_config.json')
    if read_json(S / 'status.json', {}).get('complete') and srun:
        scfg = srun['config']
        man['solar'] = {'assumptions': scfg['assumptions'], 'dates': scfg['solar']['dates'], 'minutes': scfg['solar']['minutes']}
        dates = {}
        for date in scfg['solar']['dates']:
            d = S / date
            tag = date.replace('-', '')
            frames = json.loads((d / 'frames.json').read_text())
            info = dict(time_local=[f['local_time'][11:16] for f in frames], time_utc=[f['utc'] for f in frames],
                        altitude_deg=[round(f['altitude_deg'], 2) for f in frames], azimuth_deg=[round(f['azimuth_deg'], 2) for f in frames])
            ghi_name = f'solar/ghi_{coarse}m_{tag}_tyx.npy'
            ghi_src = d / f'ghi_{coarse}m_tyx.npy'
            if not ghi_src.exists():
                ghi_src = d / 'ghi_8m_tyx.npy'  # name used by runs before 2026-09-17 regardless of cell size
            save(ghi_name, np.load(ghi_src).astype(np.float16), units='W/m2', **info)
            packed = np.stack([np.load(f) for f in sorted(glob.glob(str(d / 'shadow_*_packed.npy')))])
            shadow_name = f'solar/shadow_{cell}m_{tag}_packed_tyx.npy'
            save(shadow_name, packed.astype(np.uint8), packed_bits=f'axis 1 (columns), np.unpackbits -> {nx} columns', meaning='1 = shaded', **info)
            daily = d / 'daily_irradiation_kwh_m2.npy'
            if daily.exists():
                save(f'solar/daily_irradiation_kwh_m2_{tag}_yx.npy', np.load(daily).astype(np.float16), units='kWh/m2/day')
            label = time.strftime('%d %B', time.strptime(date, '%Y-%m-%d')).lstrip('0')
            dates[tag] = {'label': label, 'ghi': ghi_name, 'shadow': shadow_name}
        svf = S / 'sky_view_factor.npy'
        if svf.exists():
            save(f'solar/sky_view_factor_{cell}m_yx.npy', np.load(svf).astype(np.float16))
        rate = max(1, round(120 / scfg['solar']['minutes']))
        layers_json['solar'] = {'cell_m': coarse, 'shadow_cell_m': cell, 'shadow_packed': True, 'ghi_rate': rate, 'shadow_rate': rate, 'dates': dates,
                                'label': 'Sunlight · clear-sky shadows and irradiance',
                                'title': 'Sunlight · clear-sky shadows and irradiance (north = local +y as configured)',
                                'ghi_label': f'Irradiance · {coarse} m, every {scfg["solar"]["minutes"]} min',
                                'shadow_label': f'Shadows · {cell} m, every {scfg["solar"]["minutes"]} min'}
        phase_order.append('solar')
        man['exported_stages'].append('solar')
        man['limits'].append('Sunlight: assumed latitude %.4f / longitude %.4f and north = local +y.' % (scfg['assumptions']['latitude_deg'], scfg['assumptions']['longitude_deg']))

    # ---- flood
    F = PHYS / 'flood_experimental'
    frun = read_json(F / 'run_config.json')
    if read_json(F / 'status.json', {}).get('complete') and frun:
        fcfg = frun['config']
        series = json.loads((F / 'series.json').read_text())
        files = sorted(glob.glob(str(F / 'depth_*.npz')))
        depth = np.empty((len(files), ny, nx), np.float16)
        for i, f in enumerate(files):
            with np.load(f) as d:
                depth[i] = d['depth_m']
        rain15 = fcfg['flood']['rain_mm_h_15min']
        time_s = [round(s['time_seconds']) for s in series][:len(files)]
        rain = [rain15[int(t // 900)] if t // 900 < len(rain15) else 0.0 for t in time_s]
        name = f'flood/depth_{cell}m_tyx.npy'
        save(name, depth, units='m', time_s=time_s, rain_mm_h=rain, max_depth_m=[round(s['max_depth_m'], 3) for s in series][:len(files)],
             note='semi-implicit shallow-water solver on the GLB ground mesh (not surveyed terrain); design storm %s mm/h per 15 min, sewer %s mm/h' % (rain15, fcfg['flood']['sewer_mm_h']))
        max_name = f'flood/max_depth_{cell}m_yx.npy'
        save(max_name, np.load(F / 'max_depth_m.npy').astype(np.float32), units='m', meaning='maximum depth over the event')
        man['flood'] = {'assumptions': fcfg['assumptions'], **fcfg['flood']}
        hours = fcfg['flood']['duration_seconds'] / 3600
        layers_json['flood'] = {'file': name, 'max': max_name, 'cell_m': cell, 'frames': len(files), 'own_clock': True, 'rate': 4,
                                'range': [0.02, 0.25], 'web_range': [0, 2.5], 'y': 0.8,
                                'label': f'Flooding · surface water depth ({hours:g} h storm)', 'legend': ['0.02', 'depth m', '≥ 0.25'],
                                'title': f'Flooding · surface water depth ({hours:g} h storm, {cell} m shallow-water model on the GLB ground)'}
        phase_order.append('flood')
        man['exported_stages'].append('flood')
        man['limits'].append('Flooding: the GLB ground mesh stands in for terrain; no surveyed elevation.')

    (out / 'manifest.json').write_text(json.dumps(man, indent=1))
    print('wrote', rel(out / 'manifest.json'))

    # ---- scene.json: camera focus on the tallest cluster, grid from the geometry metadata
    tall = height >= max(0.6 * float(height.max()), 1.0)
    ys, xs = np.nonzero(tall)
    if len(xs):
        x0, x1 = ox + xs.min() * cell, ox + (xs.max() + 1) * cell
        y0, y1 = oy + ys.min() * cell, oy + (ys.max() + 1) * cell
    else:
        x0, x1 = ox + nx * cell * 0.4, ox + nx * cell * 0.6
        y0, y1 = oy + ny * cell * 0.4, oy + ny * cell * 0.6
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = min(max((x1 - x0) / 2, (y1 - y0) / 2, 120), 400)
    x0, x1, y0, y1 = cx - half, cx + half, cy - half, cy + half
    title = cfg['visualize']['title'] or scene.replace('_', ' ').title()
    description = cfg['visualize']['description'] or (
        f'{nx * cell} × {ny * cell} m scene at {cell} m from {p["source"].name}: ' + ', '.join(man['exported_stages'][1:] or ['geometry only']) + '.')
    scene_json = {
        'id': scene, 'title': title, 'description': description,
        'grid': {'cell_m': cell, 'cols': nx, 'rows': ny, 'x0': ox, 'z_south': -oy, 'origin_label': 'Local',
                 'domain_origin_xy_m': [ox, oy], 'size_note': f'{nx * cell} × {ny * cell} m'},
        'model': kept_model or {'url': f'models/{scene}.glb', 'bytes': model.stat().st_size, 'compression': compression},
        'lite': {'footprint': f'masks/building_footprint_{cell}m_yx.npy', 'roof': f'masks/roof_height_m_{cell}m_yx.npy', 'cell_m': cell},
        'masks': {'footprint': {str(cell): f'masks/building_footprint_{cell}m_yx.npy', str(coarse): f'masks/building_footprint_{coarse}m_yx.npy'},
                  'solid_wind': {'file': f'masks/solid_{coarse}m_zyx.npy', 'layer': LZ}},
        'focus': {'box': [[float(x0), float(-y1)], [float(x1), float(-y0)]], 'orbit_m': float(2 * half + 300), 'label': 'Tallest buildings',
                  'note': 'model X = local x, model Z = -local y; box around the tallest 40 % of roof heights'},
        'timeline': timeline or {'step_s': step_s, 'steps': cfg['wind']['steps']},
        'phase_order': phase_order,
        'layers': layers_json,
        'limits': man['limits'] + ['Not georeferenced unless a fitted georef.json is supplied; north assumed local +y.'],
    }
    if existing:
        # keep hand-made additions (transport, traffic, georeference, model recolour) from a previous export
        for key in ('transport', 'traffic', 'georeference', 'replay'):
            if key in existing:
                scene_json[key] = existing[key]
        for key in ('recolor', 'lift', 'parts_manifest'):
            if key in existing.get('model', {}) and key not in scene_json['model']:
                scene_json['model'][key] = existing['model'][key]
        if existing.get('title') and not cfg['visualize']['title']:
            scene_json['title'] = existing['title']
        if existing.get('description') and not cfg['visualize']['description']:
            scene_json['description'] = existing['description']
        if existing.get('focus'):
            scene_json['focus'] = existing['focus']
        if existing.get('limits'):
            scene_json['limits'] = existing['limits']   # hand-written limits (e.g. a fitted georeference note) win
        if existing.get('phase_order') and set(existing['phase_order']) == set(phase_order):
            scene_json['phase_order'] = existing['phase_order']
    (web / 'scene.json').write_text(json.dumps(scene_json, indent=2, ensure_ascii=False))
    print('wrote', rel(web / 'scene.json'))

    index_path = p['out'] / 'export_index.json'
    index = read_json(index_path, {'default': scene, 'scenes': []})
    previous = next((s for s in index['scenes'] if s['id'] == scene), {})
    entry = {'id': scene, 'title': scene_json['title'], 'short': previous.get('short') or scene_json['title'].split('·')[0].strip()}
    if any(s['id'] == scene for s in index['scenes']):
        index['scenes'] = [entry if s['id'] == scene else s for s in index['scenes']]
    else:
        index['scenes'].append(entry)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False))
    print('registered in', rel(index_path))

    if not args.no_frames and phase_order:
        cmd = [sys.executable, str(ROOT / 'src/visualization/adapters/legacy/shared/export_web_frames.py'), str(web)]
        print('$ ' + ' '.join(cmd), flush=True)
        subprocess.run(cmd, cwd=p['visualizer'], check=True)
    elif not phase_order:
        (out / 'web').mkdir(exist_ok=True)
        (out / 'web' / 'index.json').write_text(json.dumps({'layers': {}}))
    print(f'open: python visualizer/serve.py  ->  http://localhost:8787/viewer/3d/?scene={scene}')


if __name__ == '__main__':
    main()
