"""One-command scene runner: input/<scene>/config.json -> output/<scene>/ -> visualizer/scenes/<scene>/.

    python -m common.pipeline.run_scene white_city                # every stage listed in the config
    python -m common.pipeline.run_scene white_city --dry-run      # plan, grid size, rough cost, nothing runs
    python -m common.pipeline.run_scene white_city --stage wind   # one stage (its prerequisites must be done)
    python -m common.pipeline.run_scene white_city --force visualize

Stages, in order: geometry, wind, temperature, temperature3d, pollution, solar, flood, plot, verify, visualize.
Each stage is idempotent: a finished stage is skipped, an interrupted wind run resumes from its last
checkpoint, and every stage writes its log to cache/<scene>/pipeline/<run_id>/logs/<stage>.log. The existing scene scripts
are called unchanged through generated legacy configs in cache/<scene>/pipeline/<run_id>/configs/.
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, scene_input
import argparse
import copy
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
import os
import uuid
from common.storage import Storage, scene_id, identifier
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(repo_root()))
from common.pipeline.paths import ROOT, project_path
from urban_geometry.voxelization.glb_plan import read_glb_header, local_bounds, plan_grid

STAGES = ['geometry', 'wind', 'temperature', 'temperature3d', 'pollution', 'solar', 'flood', 'plot', 'verify', 'visualize']

DEFAULTS = {
    'scene': None,
    'source': 'scene.glb',
    'domain': {'cell_m': 2, 'crop_local_m': None, 'wind_layers': 64},
    'georeference': {'confirmed': False, 'latitude_deg': None, 'longitude_deg': None,
                     'north': 'local +y assumed north; local +x assumed east',
                     'terrain': 'GLB ground mesh, not surveyed elevation; uncovered cells at local zero',
                     'note': ''},
    'stages': STAGES,
    'wind': {'steps': 100, 'step_seconds': 50, 'coarse_factor': 4, 'min_free_gib': 2,
             'scaled_repo': '/home/yl222/workspace/SCALED-Tutorial',
             'temperature_checkpoint': str(scene_input('south_ken','models','temperature_one_step.pt'))},
    'thermal': {'ambient_c': 26.0, 'ground_c': 30.0, 'roof_c': 30.0,
                'surface_exchange_per_s': 0.001, 'diffusivity_m2_s': 1.0,
                'cfl_safety': 0.8, 'forcing_layers': 1,
                'temperature_steps': 5, 'temperature_overlap': [4, 8, 8],
                'temperature_step_seconds': 90.0, 'seed': 0},
    'temperature3d': {'frames': 20},
    'solar': {'dates': ['2026-06-21', '2026-12-21'], 'minutes': 10, 'canopy_transmittance': 0.3, 'albedo': 0.2},
    'flood': {'duration_seconds': 10800, 'frame_seconds': 300, 'dt_max_seconds': 0.3,
              'rain_mm_h_15min': [14.8, 29.6, 74.0, 44.4, 22.2, 14.8],
              'sewer_mm_h': 12, 'green_infiltration_mm_h': 20, 'manning_paved': 0.02, 'manning_green': 0.05},
    'visualize': {'layer': 1, 'title': None, 'description': None},
}

# White City reference run (2 m, 1792 x 1792 x 64 wind cells, RTX 5090) used for the rough cost estimate.
REF_CELLS = 1792 * 1792 * 64
REF = {'encode_s': 57, 'wind_s_per_step': 67, 'wind_mb_per_step': 63, 'pollution_s_per_step': 0.4,
       'pollution_mb_per_step': 9, 'temperature_s': 300, 'geometry_mb': 330, 'temperature3d_s': 600}


def merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        out[key] = merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else copy.deepcopy(value)
    return out


def load_config(target):
    """target: input/<scene> directory (config.json inside) or a config file path."""
    storage = Storage.load()
    candidate = storage.metadata(target) / 'configs/pipeline.json' if re.fullmatch(r'[a-z][a-z0-9_]*', str(target)) else None
    path = candidate if candidate is not None and candidate.is_file() else project_path(target)
    if path.is_dir():
        path = path / 'config.json'
    if not path.is_file():
        raise SystemExit(f'No config file at {path}')
    user = json.loads(path.read_text(encoding='utf-8'))
    cfg = merge(DEFAULTS, user)
    scene = cfg['scene'] or path.parent.name
    if not re.fullmatch(r'[a-z0-9_]+', scene):
        raise SystemExit(f'scene id must be lowercase letters, digits or underscores: {scene!r}')
    scene = scene_id(scene)
    cfg['scene'] = scene
    cell = cfg['domain']['cell_m']
    if cell not in (1, 2, 4, 8):
        raise SystemExit('domain.cell_m must be 1, 2, 4 or 8 (SCALED encoder tiles are 256 cells, wind depth 64 layers)')
    unknown = [s for s in cfg['stages'] if s not in STAGES]
    if unknown:
        raise SystemExit(f'Unknown stages {unknown}; valid: {STAGES}')
    p = {}
    p['config_path'] = path
    p['input'] = storage.assets(scene, 'input')
    p['source'] = ((storage.assets(scene, 'runs') / cfg['source'][5:]) if cfg['source'].startswith('runs/') else ((p['input'] / cfg['source']) if not Path(cfg['source']).is_absolute() else Path(cfg['source']))).resolve()
    run_id = identifier(os.environ.get('UWM_RUN_ID') or cfg.get('run_id') or 'preview', run=True)
    p['out'] = storage.scratch(scene, 'pipeline', run_id)
    p['run_id'] = run_id
    p['geometry'] = p['out'] / 'geometry' / f'voxel_{cell}m'
    p['physics'] = p['out'] / 'physics'
    p['run'] = p['physics'] / 'scaled_latent'
    p['temperature3d'] = p['physics'] / 'temperature3d_physical'
    p['configs'] = p['out'] / 'configs'
    p['logs'] = p['out'] / 'logs'
    p['status'] = p['out'] / 'pipeline_status.json'
    p['visualizer'] = ROOT / 'src/visualization/legacy'
    p['scene_web'] = p['out'] / 'export'
    return cfg, p


def rel(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def legacy_wind_config(cfg, p):
    w, cell = cfg['wind'], cfg['domain']['cell_m']
    thermal = dict(cfg['thermal'])
    thermal['fine_spacing_m'] = float(cell)
    thermal['factor'] = w['coarse_factor']
    thermal['wind_step_seconds'] = float(w['step_seconds'])
    return {'scene': cfg['scene'], 'geometry': rel(p['geometry']), 'output': rel(p['run']),
            'scaled_repo': w['scaled_repo'], 'temperature_checkpoint': w['temperature_checkpoint'],
            'cell_m': cell, 'wind_layers': cfg['domain']['wind_layers'], 'wind_steps': w['steps'],
            'step_seconds': w['step_seconds'], 'coarse_factor': w['coarse_factor'], 'min_free_gib': w['min_free_gib'],
            'thermal': thermal}


def legacy_surface_config(cfg, p):
    g = cfg['georeference']
    return {'scene': cfg['scene'], 'geometry': rel(p['geometry']), 'output': rel(p['physics']),
            'cell_m': cfg['domain']['cell_m'], 'coarse_factor': cfg['wind']['coarse_factor'],
            'experimental_assumptions_confirmed': bool(g['confirmed']),
            'assumptions': {'latitude_deg': g['latitude_deg'], 'longitude_deg': g['longitude_deg'],
                            'north': g['north'], 'terrain': g['terrain']},
            'solar': cfg['solar'], 'flood': cfg['flood'], 'confirmation_note': g.get('note', '')}


def write_legacy_configs(cfg, p):
    p['configs'].mkdir(parents=True, exist_ok=True)
    wind = p['configs'] / 'scaled_latent.json'
    surface = p['configs'] / 'surface_physics.json'
    wind.write_text(json.dumps(legacy_wind_config(cfg, p), indent=2))
    surface.write_text(json.dumps(legacy_surface_config(cfg, p), indent=2))
    return wind, surface


def sha256(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read_json(path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def georef_ok(cfg):
    g = cfg['georeference']
    return bool(g['confirmed']) and g['latitude_deg'] is not None and g['longitude_deg'] is not None


def status_of(stage, cfg, p, done):
    """Return (state, detail): state in done / ready / blocked."""
    cell, w = cfg['domain']['cell_m'], cfg['wind']
    coarse = cell * w['coarse_factor']
    run = p['run']
    if stage == 'geometry':
        meta = read_json(p['geometry'] / 'metadata.json')
        if meta is None:
            return 'ready', f'voxelise {p["source"].name} at {cell} m'
        if meta.get('spacing_xyz_m') != [cell] * 3:
            return 'blocked', 'existing geometry has a different cell size; use a new scene id'
        if meta.get('source_sha256') != sha256(p['source']):
            return 'blocked', 'existing geometry was built from a different GLB; use a new scene id or remove the geometry directory'
        return 'done', f'{meta["shape_zyx"]} cells (z, y, x)'
    if stage == 'wind':
        if 'geometry' not in done:
            return 'blocked', 'needs geometry'
        final = run / 'wind' / f'velocity_final_{cell}m_raw_czyx_float16.npy'
        last = run / 'wind' / f'wind{coarse}m_{w["steps"]:03d}.npz'
        if final.is_file() and last.is_file():
            return 'done', f'{w["steps"]} steps'
        resume = read_json(run / 'status.json')
        detail = f'{w["steps"]} steps of {w["step_seconds"]} s'
        if resume and resume.get('stage') == 'wind':
            detail += f' (resume after step {resume.get("completed_steps")})'
        return 'ready', detail
    if stage == 'temperature':
        if 'wind' not in done:
            return 'blocked', 'needs wind'
        spin = w['steps'] - math.ceil(450 / w['step_seconds'])
        if spin < 0:
            return 'blocked', f'needs at least {math.ceil(450 / w["step_seconds"])} wind steps for the 450 s spin-up window'
        status = read_json(run / 'status.json', {})
        if status.get('stage') == 'wind_temperature_complete':
            return 'done', f'{cfg["thermal"]["temperature_steps"]} controlled steps'
        return 'ready', 'controlled thermal transfer on the coarse grid'
    if stage == 'temperature3d':
        if 'wind' not in done:
            return 'blocked', 'needs wind'
        summary = read_json(p['temperature3d'] / 'summary.json', {})
        if summary.get('complete'):
            return 'done', f'{summary.get("frames")} frames at {summary.get("cell_m")} m'
        return 'ready', f'Yi Qi 3-D solver on the last {min(cfg["temperature3d"]["frames"], w["steps"])} wind frames'
    if stage == 'pollution':
        if 'wind' not in done:
            return 'blocked', 'needs wind'
        if read_json(run / 'pollution' / 'status.json', {}).get('complete'):
            return 'done', f'{w["steps"]} tracer frames'
        return 'ready', 'upwind tracer transport on the stored wind frames'
    if stage in ('solar', 'flood'):
        if 'geometry' not in done:
            return 'blocked', 'needs geometry'
        if not georef_ok(cfg):
            return 'blocked', 'georeference.confirmed must be true with latitude_deg/longitude_deg set'
        if read_json(p['physics'] / f'{stage}_experimental' / 'status.json', {}).get('complete'):
            return 'done', 'complete'
        return 'ready', 'fixed-operator surface model on the GLB ground'
    if stage == 'plot':
        if 'wind' not in done:
            return 'blocked', 'needs wind'
        figures = run / 'figures'
        wanted = ['wind_final.png', 'wind_convergence.png']
        if 'pollution' in done:
            wanted.append('pollution_final.png')
        if all((figures / f).is_file() for f in wanted):
            return 'done', ', '.join(wanted)
        return 'ready', 'overview figures'
    if stage == 'verify':
        for need in ('wind', 'temperature', 'pollution', 'plot'):
            if need not in done:
                return 'blocked', f'needs {need}'
        if read_json(run / 'verification.json', {}).get('all_pass'):
            return 'done', 'all_pass'
        return 'ready', 'file integrity and numerical sanity checks'
    if stage == 'visualize':
        if 'geometry' not in done:
            return 'blocked', 'needs geometry'
        if not (p['visualizer'] / 'serve.py').is_file():
            return 'blocked', 'visualizer/ (the web viewer repository) is missing'
        layers = sorted(s for s in ('wind', 'temperature3d', 'pollution', 'solar', 'flood') if s in done)
        manifest = read_json(p['scene_web'] / 'physics' / 'manifest.json', {})
        exported = sorted(s for s in manifest.get('exported_stages', []) if s != 'geometry')
        if exported == layers and (p['scene_web'] / 'physics' / 'web' / 'index.json').is_file():
            return 'done', 'layers: ' + (', '.join(layers) or 'geometry only')
        return 'ready', 'export layers: ' + (', '.join(layers) or 'geometry only')
    raise KeyError(stage)


def commands(stage, cfg, p, wind_cfg, surface_cfg):
    py = [sys.executable, '-u']
    if stage == 'geometry':
        cmd = py + [str(ROOT / 'src/urban_geometry/voxelization/prepare_glb.py'), '--cell', str(cfg['domain']['cell_m']),
                    '--source', str(p['source']), '--out', str(p['geometry']),
                    '--min-layers', str(cfg['domain']['wind_layers']), '--coarse-factor', str(cfg['wind']['coarse_factor'])]
        crop = cfg['domain']['crop_local_m']
        if crop is not None:
            cmd += ['--crop'] + [str(float(v)) for v in crop]
        return [cmd]
    if stage == 'wind':
        return [py + [str(ROOT / 'src/common/pipeline/scene_scaled_latent.py'), '--config', str(wind_cfg), '--stage', 'wind']]
    if stage == 'temperature':
        return [py + [str(ROOT / 'src/common/pipeline/scene_scaled_latent.py'), '--config', str(wind_cfg), '--stage', 'temperature']]
    if stage == 'temperature3d':
        return [py + [str(ROOT / 'src/common/pipeline/scene_temperature_physical.py'), '--config', str(wind_cfg),
                      '--out', str(p['temperature3d']), '--frames', str(cfg['temperature3d']['frames'])]]
    if stage == 'pollution':
        return [py + [str(ROOT / 'src/common/pipeline/scene_pollution.py'), '--config', str(wind_cfg)]]
    if stage in ('solar', 'flood'):
        return [py + [str(ROOT / 'src/common/pipeline/scene_surface_physics.py'), '--config', str(surface_cfg), '--stage', stage]]
    if stage == 'plot':
        return [py + [str(ROOT / 'src/common/pipeline/plot_scene.py'), '--config', str(wind_cfg)]]
    if stage == 'verify':
        return [py + [str(ROOT / 'src/common/pipeline/verify_scene_results.py'), '--config', str(wind_cfg)]]
    if stage == 'visualize':
        return [py + [str(ROOT / 'src/common/pipeline/export_scene_web.py'), '--config', str(p['config_path'])]]
    raise KeyError(stage)


def plan_domain(cfg, p):
    doc, _ = read_glb_header(p['source'])
    cell = cfg['domain']['cell_m']
    plan = plan_grid(local_bounds(doc), cell, cfg['domain']['crop_local_m'])
    cells = plan['nx'] * plan['ny'] * cfg['domain']['wind_layers']
    ratio = cells / REF_CELLS
    steps = cfg['wind']['steps']
    est = {'grid_xy_cells': [plan['nx'], plan['ny']], 'size_xy_m': [int(v) for v in plan['size_xy_m']],
           'origin_xy_m': [float(v) for v in plan['origin_xy']],
           'bounds_used_m': plan['bounds'][:, :2].tolist(),
           'wind_cells': cells, 'reference_ratio': round(ratio, 4),
           'wind_hours': round((REF['encode_s'] + steps * REF['wind_s_per_step']) * ratio / 3600, 2),
           'wind_gb': round(steps * REF['wind_mb_per_step'] * ratio / 1024, 2),
           'pollution_minutes': round(steps * REF['pollution_s_per_step'] * ratio / 60, 1),
           'pollution_gb': round(steps * REF['pollution_mb_per_step'] * ratio / 1024, 2),
           'geometry_gb': round(REF['geometry_mb'] * ratio / 1024, 2),
           'free_gb': round(shutil.disk_usage(ROOT).free / 1024 ** 3, 1),
           'draco': 'KHR_draco_mesh_compression' in doc.get('extensionsUsed', [])}
    return est


def save_status(p, record):
    p['out'].mkdir(parents=True, exist_ok=True)
    record['updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
    tmp = p['status'].with_suffix('.partial')
    tmp.write_text(json.dumps(record, indent=2))
    tmp.replace(p['status'])


def tail(path, n=25):
    try:
        lines = Path(path).read_text(errors='replace').splitlines()
    except OSError:
        return ''
    return '\n'.join(lines[-n:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', nargs='?', default='white_city', help='registered scene ID or a pipeline config file')
    ap.add_argument('--stage', action='append', choices=STAGES, help='run only these stages (repeatable); default: config "stages"')
    ap.add_argument('--force', action='append', default=[], choices=STAGES, help='re-run this stage even if it is done')
    ap.add_argument('--dry-run', action='store_true', help='print the plan and the commands; run nothing')
    ap.add_argument('--retain', action='store_true', help='retain the validated export and register a scene view')
    ap.add_argument('--run-id', help='reuse a trial ID to resume; otherwise create a new trial')
    args = ap.parse_args()
    os.environ['UWM_RUN_ID'] = args.run_id or ('preview' if args.dry_run else time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '_' + uuid.uuid4().hex[:8])

    cfg, p = load_config(args.target)
    requested = [s for s in STAGES if s in (args.stage or cfg['stages'])]
    if not p['source'].is_file():
        raise SystemExit(f'Source model not found: {p["source"]}')
    est = plan_domain(cfg, p)

    print(f'scene {cfg["scene"]}: {p["source"].name} -> {rel(p["out"])}')
    print(f'  grid {est["grid_xy_cells"][0]} x {est["grid_xy_cells"][1]} cells at {cfg["domain"]["cell_m"]} m '
          f'({est["size_xy_m"][0]} x {est["size_xy_m"][1]} m, origin {est["origin_xy_m"]}), '
          f'{cfg["domain"]["wind_layers"]} wind layers'
          + (f', crop {cfg["domain"]["crop_local_m"]}' if cfg['domain']['crop_local_m'] else ''))
    print(f'  rough cost (scaled from the White City 2 m run): wind ~{est["wind_hours"]} h and ~{est["wind_gb"]} GB '
          f'for {cfg["wind"]["steps"]} steps; pollution ~{est["pollution_minutes"]} min, ~{est["pollution_gb"]} GB; '
          f'geometry ~{est["geometry_gb"]} GB; free disk {est["free_gb"]} GB')

    record = read_json(p['status'], {}) or {}
    record.update({'scene': cfg['scene'], 'config': rel(p['config_path']), 'domain_plan': est,
                   'stages': record.get('stages', {})})
    if args.dry_run:
        wind_cfg = p['configs'] / 'scaled_latent.json'
        surface_cfg = p['configs'] / 'surface_physics.json'
    else:
        from common.provenance import snapshot_sources
        snapshot = p['out'] / 'source_snapshot.tar.gz'
        if not snapshot.exists():
            revision = snapshot_sources(ROOT, snapshot)
            (p['out'] / 'source_revision.txt').write_text(revision)
        wind_cfg, surface_cfg = write_legacy_configs(cfg, p)
        p['logs'].mkdir(parents=True, exist_ok=True)

    done = set()
    # Evaluate in order so downstream stages see upstream completion.
    for stage in STAGES:
        if status_of(stage, cfg, p, done)[0] == 'done':
            done.add(stage)

    print('\nstage          status   detail')
    for stage in STAGES:
        state, detail = status_of(stage, cfg, p, done)
        wanted = stage in requested
        if state == 'done' and stage in args.force:
            state = 'ready'; detail = 'forced: ' + detail
        mark = state if wanted else ('done' if state == 'done' else 'not requested')
        print(f'  {stage:13s} {mark:8s} {detail}')
        if args.dry_run and wanted and state in ('ready',):
            for cmd in commands(stage, cfg, p, wind_cfg, surface_cfg):
                print('      $ ' + ' '.join(str(c) if ' ' not in str(c) else repr(str(c)) for c in cmd))
    if args.dry_run:
        print('\ndry run: nothing executed')
        return

    failed = None
    for stage in requested:
        state, detail = status_of(stage, cfg, p, done)
        if state == 'done' and stage not in args.force:
            record['stages'][stage] = {'status': 'done', 'detail': detail}
            continue
        if state == 'blocked':
            record['stages'][stage] = {'status': 'skipped', 'detail': detail}
            print(f'[{stage}] skipped: {detail}', flush=True)
            save_status(p, record)
            continue
        if stage == 'verify':
            workflow = p['run'] / 'workflow_status.json'
            workflow.write_text(json.dumps({'complete': True, 'completed': sorted(done),
                                            'pending': {s: status_of(s, cfg, p, done)[1] for s in STAGES if s not in done and s != 'verify'}}, indent=2))
        log = p['logs'] / f'{stage}.log'
        started = time.time()
        record['stages'][stage] = {'status': 'running', 'detail': detail, 'log': rel(log), 'started': time.strftime('%Y-%m-%d %H:%M:%S')}
        save_status(p, record)
        print(f'[{stage}] {detail}; log {rel(log)}', flush=True)
        code = 0
        with log.open('a') as handle:
            for cmd in commands(stage, cfg, p, wind_cfg, surface_cfg):
                handle.write(f'\n# {time.strftime("%Y-%m-%d %H:%M:%S")} $ {" ".join(map(str, cmd))}\n'); handle.flush()
                code = subprocess.run(cmd, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT).returncode
                if code:
                    break
        elapsed = time.time() - started
        if code:
            record['stages'][stage] = {'status': 'failed', 'returncode': code, 'seconds': round(elapsed), 'log': rel(log)}
            save_status(p, record)
            print(f'[{stage}] FAILED (exit {code}) after {elapsed:.0f} s; last log lines:\n{tail(log)}', flush=True)
            failed = stage
            break
        state, detail = status_of(stage, cfg, p, done | {stage})
        if state != 'done':
            record['stages'][stage] = {'status': 'failed', 'detail': f'finished without completion marker: {detail}', 'log': rel(log)}
            save_status(p, record)
            print(f'[{stage}] FAILED: finished but no completion marker ({detail}); see {rel(log)}', flush=True)
            failed = stage
            break
        done.add(stage)
        record['stages'][stage] = {'status': 'done', 'detail': detail, 'seconds': round(elapsed), 'log': rel(log)}
        save_status(p, record)
        print(f'[{stage}] done in {elapsed:.0f} s: {detail}', flush=True)

    record['complete'] = failed is None and all(record['stages'].get(s, {}).get('status') == 'done' for s in requested)
    save_status(p, record)
    if failed:
        raise SystemExit(1)
    skipped = [s for s in requested if record['stages'].get(s, {}).get('status') == 'skipped']
    print('\nrequested stages finished' + (f'; skipped: {", ".join(skipped)}' if skipped else ''))
    if record['complete'] and 'visualize' in done:
        from common.export import package_export
        from common.runs import promote_bundle
        bundle = package_export(Storage.load(), p['scene_web'], cfg, p['run_id'], source_snapshot=p['out']/'source_snapshot.tar.gz', code_revision=(p['out']/'source_revision.txt').read_text().strip())
        print(f'Validated protocol bundle: {bundle}')
        if args.retain:
            print(f'Retained view: {promote_bundle(Storage.load(), bundle)}')
        print(f'view: python visualizer/serve.py  ->  http://localhost:8787/viewer/3d/?scene={cfg["scene"]}')


if __name__ == '__main__':
    main()
