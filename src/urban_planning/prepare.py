"""Extract a compact, self-contained pilot from explicitly configured legacy data."""
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

import numpy as np

from common.storage import Storage, within
from .problem import digest, write_json


def prepare(config_path, storage=None):
    storage = storage or Storage.load()
    config_path = Path(config_path).resolve()
    cfg = json.loads(config_path.read_text())
    if cfg['schema_version'] != 'planning-pilot-0.1' or cfg['scene_id'] != 'south_ken':
        raise ValueError('This adapter supports the South Kensington pilot only')
    source_config = storage.root / 'sources.local.json'
    local = json.loads(source_config.read_text())
    source = within(Path(local['legacy_output']), cfg['legacy_relative_root'])
    terrain_meta = json.loads((source / 'flood/terrain/metadata.json').read_text())
    scene_path = storage.run('south_ken', 'legacy_web') / 'scene.json'
    scene = json.loads(scene_path.read_text())
    grid = scene['grid']
    shape = terrain_meta['grid_1m']['shape_yx']
    if grid['domain_origin_xy_m'] != terrain_meta['grid_1m']['domain_lower_xy_m']:
        raise ValueError('Legacy and scene domains disagree; do not infer a transform')
    if [grid['rows'] * grid['cell_m'], grid['cols'] * grid['cell_m']] != shape:
        raise ValueError('Grid extent mismatch')
    x0, y0 = grid['x0'], -grid['z_south']
    paths = {'footprint': source / 'flood/terrain/footprint_1m_yx.npy',
             'terrain': source / 'flood/terrain/dtm_1m_yx.npy'}
    footprint = np.load(paths['footprint'], mmap_mode='r')
    terrain = np.load(paths['terrain'], mmap_mode='r')
    if list(footprint.shape) != shape or terrain.shape != footprint.shape:
        raise ValueError('Source shapes differ from metadata')
    xmin, ymin, xmax, ymax = cfg['bounds_enu_m']
    col0, row0, col1, row1 = [int(v) for v in (xmin-x0, ymin-y0, xmax-x0, ymax-y0)]
    if not (0 <= col0 < col1 <= shape[1] and 0 <= row0 < row1 <= shape[0]):
        raise ValueError('Pilot window outside source domain')
    stride = cfg['receptor_spacing_m']
    if type(stride) is not int or stride < 1:
        raise ValueError('Receptor spacing must be a positive integer metre count')
    rr, cc = np.meshgrid(np.arange(row0, row1, stride), np.arange(col0, col1, stride), indexing='ij')
    rr, cc = rr.ravel(), cc.ravel()
    keep = ~footprint[rr, cc]
    rr, cc = rr[keep], cc[keep]
    receptors = np.column_stack((x0 + cc + .5, y0 + rr + .5, terrain[rr, cc]))
    if not len(receptors) or not np.isfinite(receptors).all():
        raise ValueError('No valid ground receptors')
    # Candidate generation uses terrain/obstacles only, never radiation scores.
    sites = []
    w, d = cfg['panel_width_m'], cfg['panel_depth_m']
    for y in np.arange(ymin + d, ymax - d, cfg['candidate_spacing_m']):
        for x in np.arange(xmin + w, xmax - w, cfg['candidate_spacing_m']):
            cols = slice(int(np.floor(x-w/2-x0)), int(np.ceil(x+w/2-x0)))
            rows = slice(int(np.floor(y-d/2-y0)), int(np.ceil(y+d/2-y0)))
            patch = terrain[rows, cols]
            if footprint[rows, cols].any() or not np.isfinite(patch).all() or np.ptp(patch) > cfg['max_site_relief_m']:
                continue
            sites.append({'x_m': float(x), 'y_m': float(y), 'z_m': float(patch.max() + cfg['panel_clearance_m']),
                          'width_m': w, 'depth_m': d, 'cost_units': 1})
    if len(sites) < cfg['candidate_count']:
        raise ValueError(f'Only {len(sites)} valid sites; requested {cfg["candidate_count"]}')
    chosen = np.linspace(0, len(sites)-1, cfg['candidate_count'], dtype=int)
    candidates = [dict(sites[int(i)], id=f'p{j:02d}') for j, i in enumerate(chosen)]
    arrays = {'receptors': receptors}
    records = []
    def record(path, role):
        records.append({'id': role, 'source_path': str(path), 'sha256': digest(path)})
    for key, path in paths.items():
        record(path, key)
    record(source / 'flood/terrain/metadata.json', 'terrain_metadata')
    record(scene_path, 'scene_metadata')
    record(config_path, 'pilot_configuration')
    frame_records = {}
    for season, date in cfg['dates'].items():
        folder = source / 'solar' / date
        frame_path = folder / 'frames.json'
        frames = json.loads(frame_path.read_text())
        hours = np.array([f['hour_utc'] for f in frames])
        if np.any(np.diff(hours) <= 0):
            raise ValueError('Source timestamps must be strictly increasing')
        record(frame_path, f'{season}_frames')
        selected = []
        for i, frame in enumerate(frames[:-1]):
            h = frame['hour_utc']
            if not (cfg['hours_utc'][0] <= h < cfg['hours_utc'][1]):
                continue
            dt = (frames[i+1]['hour_utc'] - h) * 3600
            if abs(dt - 600) > 1:
                raise ValueError('Expected recorded 10-minute intervals, no interpolation permitted')
            path = folder / 'shadow_1m_packed' / f'shadow_{frame["index"]:03d}.npy'
            packed = np.load(path, mmap_mode='r')
            if packed.shape != (shape[0], (shape[1]+7)//8):
                raise ValueError('Unexpected packed shadow layout')
            shade = ((packed[rr, cc//8] >> (7-cc%8)) & 1).astype(bool)
            direct = np.maximum(0, frame['dni_w_m2'] * np.sin(np.deg2rad(frame['altitude_deg']))) * (~shade)
            selected.append((frame, dt, direct))
            record(path, f'{season}_shadow_{frame["index"]}')
        if len(selected) < 4:
            raise ValueError('Insufficient recorded intervals')
        frame_records[season] = []
        for split, parity in (('development', 0), ('holdout', 1)):
            subset = selected[parity::2]
            prefix = f'{season}_{split}_'
            arrays[prefix+'direct_w_m2'] = np.stack([x[2] for x in subset])
            arrays[prefix+'duration_s'] = np.array([x[1] for x in subset])
            for key in ('altitude_deg', 'azimuth_deg', 'hour_utc'):
                arrays[prefix+key] = np.array([x[0][key] for x in subset])
            frame_records[season].append({'split': split, 'source_indices': [x[0]['index'] for x in subset]})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_id = f'planning_pilot_{stamp}_{uuid.uuid4().hex[:6]}'
    out = storage.scratch('south_ken', 'urban_planning', run_id)
    out.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(out / 'background.npz', **arrays)
    task = dict(cfg, candidates=candidates, receptor_count=len(receptors), run_id=run_id,
                source_frames=frame_records,
                coordinate_note='XY from retained scene grid; calculation Z is original DTM ODN. Display layers use z=0 planning plane.',
                objective='Maximize mean summer direct-ground-radiation reduction subject to winter-loss and budget constraints',
                split_note='Alternating recorded intervals on two clear-sky solstice dates. Temporal holdout is correlated, not unseen-weather validation.',
                source_solver_provenance='legacy-unrecorded; stored shadows and sun angles reused, original solar run not reproduced',
                physical_scope='Opaque horizontal panels; direct radiation only; fixed background buildings. No diffuse/reflected changes, heat, wind, people or structural model.')
    write_json(out / 'task.json', task)
    write_json(out / 'input_provenance.json', records)
    write_json(out / 'config.json', cfg)
    write_json(out / 'spatial.json', json.loads((storage.metadata('south_ken') / 'project.json').read_text())['spatial'])
    return out
