"""Traffic-source / morphology screening with existing CPU MAC and conservative tracer.

Run with an environment providing torch/scipy/numpy/jsonschema/matplotlib.
All field runs are deterministic; no scripted decision policy is an LLM agent.
"""
import argparse
from datetime import datetime, timezone
import itertools
import importlib.metadata
import json
from pathlib import Path
import time
import sys
import uuid

import numpy as np

from common.storage import Storage
from .problem import digest, write_json


def aggregate(array, factor, mode='mean'):
    if any(n % factor for n in array.shape[-2:]):
        raise ValueError('Non-divisible raster')
    shape = array.shape[:-2] + (array.shape[-2]//factor, factor, array.shape[-1]//factor, factor)
    values = array.reshape(shape)
    if mode == 'max':
        return values.max(axis=(-3, -1))
    if mode == 'sum':
        return values.sum(axis=(-3, -1))
    return values.mean(axis=(-3, -1))


def prepare_inputs(storage, cfg):
    legacy = storage.run('south_ken', 'legacy_web')
    meta_path = legacy/'scene.json'
    grid = json.loads(meta_path.read_text())['grid']
    if grid['cell_m'] != 4:
        raise ValueError('Expected preserved 4 m raster')
    x0, y0 = grid['x0'], -grid['z_south']
    xmin, ymin, xmax, ymax = cfg['bounds_enu_m']
    offsets = [(xmin-x0)/4, (ymin-y0)/4, (xmax-x0)/4, (ymax-y0)/4]
    if any(x != int(x) for x in offsets):
        raise ValueError('Crop not aligned with declared source grid')
    c0, r0, c1, r1 = map(int, offsets)
    roof_path = legacy/'physics/masks/roof_height_m_yx.npy'
    foot_path = legacy/'physics/masks/building_footprint_yx.npy'
    roof = np.asarray(np.load(roof_path, mmap_mode='r')[r0:r1, c0:c1], dtype=float)
    foot = np.asarray(np.load(foot_path, mmap_mode='r')[r0:r1, c0:c1], dtype=bool)
    roof = np.where(foot, np.maximum(roof, 8), 0)
    # Freeze source/receptor support to the primary coarse grid for refinements.
    blocked = np.repeat(np.repeat(aggregate(foot, 2, 'max'), 2, axis=0), 2, axis=1)
    replay = storage.run('south_ken', 'legacy_agents')/'data/traffic/replay'
    index_path, raw_path = replay/'frames_index.json', replay/'traffic_flow.f32'
    index = json.loads(index_path.read_text())
    samples = np.array([f['t_s'] for f in index], dtype=float)
    if np.any(np.diff(samples) <= 0) or samples[0] != 1 or samples[-1] != 300:
        raise ValueError('Unexpected recorded traffic interval; inspect explicitly')
    raw = np.fromfile(raw_path, dtype='<f4').reshape(-1, 5)
    occupancy = np.zeros(roof.shape)
    within_count = blocked_count = total_count = 0.
    unique = set()
    for frame, dt in zip(index[:-1], np.diff(samples)):
        start = frame['offset_bytes']//20
        rows = raw[start:start+frame['count']]
        if len(rows) != frame['count']:
            raise ValueError('Truncated frame')
        xy = rows[:, 1:3].astype(float)-[2912.594719173, 1704.705026026]
        cc = np.floor((xy[:, 0]-xmin)/4).astype(int)
        rr = np.floor((xy[:, 1]-ymin)/4).astype(int)
        inside = (cc >= 0) & (rr >= 0) & (cc < roof.shape[1]) & (rr < roof.shape[0])
        total_count += len(rows)*dt
        within_count += int(inside.sum())*dt
        cc, rr = cc[inside], rr[inside]
        valid = ~blocked[rr, cc]
        blocked_count += int((~valid).sum())*dt
        unique.update(rows[inside][valid, 0].astype(int).tolist())
        np.add.at(occupancy, (rr[valid], cc[valid]), dt)
    if occupancy.sum() == 0:
        raise ValueError('No unblocked recorded sources')
    ny, nx = roof.shape
    if (ny, nx) != (64, 64):
        raise ValueError('v0.1 idealized fixture requires the declared 256 m square crop')
    yy, xx = np.indices(roof.shape)
    sectors = (xx >= nx//2).astype(int) + 2*(yy >= ny//2).astype(int)
    source = np.stack([np.where(sectors == i, occupancy, 0) for i in range(4)])
    source *= cfg['total_source_au_s']/source.sum()
    # Explicit idealized blocks and two crossing roads, with unequal source shares.
    ideal_roof = np.zeros_like(roof)
    for ys, ye, xs, xe, height in [(8,24,8,24,24), (8,24,40,56,16),
                                   (40,56,8,24,32), (40,56,40,56,24)]:
        ideal_roof[ys:ye, xs:xe] = height
    ideal_blocked = ideal_roof > 0
    ideal_road = ((np.abs(xx-nx/2) < 2) | (np.abs(yy-ny/2) < 2)) & ~ideal_blocked
    ideal_source = np.stack([(ideal_road & (sectors == i)).astype(float) for i in range(4)])
    for i, share in enumerate([.1, .4, .2, .3]):
        ideal_source[i] *= cfg['total_source_au_s']*share/ideal_source[i].sum()
    provenance = [{'id': name, 'source_path': str(path), 'sha256': digest(path)} for name, path in
                  [('roof_height', roof_path), ('footprint', foot_path), ('scene_grid', meta_path),
                   ('traffic_index', index_path), ('traffic_records', raw_path)]]
    audit = {'recorded_interval_s': [float(samples[0]), float(samples[-1])],
             'integrated_interval_s': [1, 300], 'duration_s': float(samples[-1]-samples[0]),
             'method': 'Left-held recorded occupancy on observed intervals only; final frame not extrapolated.',
             'source_xy_to_enu_translation_m': [-2912.594719173, -1704.705026026],
             'all_recorded_vehicle_seconds': total_count, 'crop_vehicle_seconds': within_count,
             'excluded_solid_vehicle_seconds': blocked_count,
             'excluded_solid_fraction_of_crop': blocked_count/within_count,
             'accepted_unique_vehicle_ids': len(unique),
             'source_sector_fractions': (source.sum(axis=(1,2))/source.sum()).tolist(),
             'limitations': 'Recorded SUMO output, not field measurements. Uniform per-vehicle emission proxy; no speed/type/chemistry calibration.'}
    return {'south_ken_roof4': roof, 'south_ken_source4': source, 'south_ken_blocked4': blocked,
            'idealized_roof4': ideal_roof, 'idealized_source4': ideal_source,
            'idealized_blocked4': ideal_blocked}, provenance, audit


def domain(inputs, case, cfg, cell, height_factor):
    factor = cell//4
    if cell not in (4, 8):
        raise ValueError('Supported cells are 4 or 8 m')
    roof = aggregate(inputs[f'{case}_roof4'], factor, 'max')*height_factor
    blocked = aggregate(inputs[f'{case}_blocked4'], factor, 'max')
    nz = int(cfg['height_m']/cell)
    if np.max(roof) >= cfg['height_m']-2*cell:
        raise ValueError('Insufficient top clearance')
    zz = (np.arange(nz)+.5)*cell
    fluid = zz[:, None, None] >= roof[None, :, :]
    source2 = aggregate(inputs[f'{case}_source4'], factor, 'sum')
    source = np.zeros((4, *fluid.shape))
    layers = (zz >= cfg['source_layer_m'][0]) & (zz < cfg['source_layer_m'][1])
    source[:, layers] = source2[:, None]/layers.sum()
    if np.any(source[:, ~fluid] != 0):
        raise ValueError('Frozen source support intersects changed solid geometry')
    receptor = ~blocked
    b = int(cfg['receptor_boundary_buffer_m']/cell)
    receptor[:b] = False; receptor[-b:] = False
    receptor[:, :b] = False; receptor[:, -b:] = False
    return fluid, source, receptor, roof


def compute_wind(fluid, cell, cfg, duration):
    import torch
    from urban_flow.solvers.mac_torch import MAC
    torch.set_num_threads(cfg['torch_threads'])
    f = torch.as_tensor(fluid.copy(), dtype=torch.bool)
    inlet = torch.full(f.shape[:2], cfg['inlet_speed_m_s'], dtype=torch.float32)*f[:, :, 0]
    model = MAC(f, cell, inlet, open_top=True)
    model.vel[0].fill_(cfg['inlet_speed_m_s'])
    for c in range(3):
        model.vel[c] *= model.opened(c)
    records = []
    started = time.perf_counter()
    with torch.inference_mode():
        check = model.project(rtol=cfg['pressure_rtol'], maxiter=200)
        t = 0.; step = 0; next_record = 0.; previous = [v.clone() for v in model.vel]
        while t < duration-1e-9:
            dt = min(cfg['flow_dt_max_s'], cfg['flow_cfl']*cell/max(model.maxsum(), .01), duration-t)
            model.advect(dt)
            check = model.project(rtol=cfg['pressure_rtol'], maxiter=200)
            t += dt; step += 1
            if t >= next_record or t >= duration-1e-9:
                change = sum(float(torch.sum((a-b)**2)) for a,b in zip(model.vel, previous))**.5
                norm = sum(float(torch.sum(a*a)) for a in model.vel)**.5
                records.append({'time_s': t, 'step': step, 'relative_velocity_change_since_record': change/max(norm, 1e-12), **check})
                previous = [v.clone() for v in model.vel]
                next_record = t+20
    faces = [v.numpy().astype(float) for v in model.vel]
    return faces, inlet.numpy().astype(float), {'records': records, 'wall_seconds': time.perf_counter()-started,
            'flow_model': 'Existing inviscid upwind MAC; finite-duration snapshot, no turbulence closure.',
            'stationarity_established': False, 'duration_s': duration}


def solve_case(inputs, cfg, case, height_factor, rotation, cell, duration, diffusivity, out, label):
    from urban_flow.physics.conservative_tracer import SteadyTracer
    fluid, sources, receptor, roof = domain(inputs, case, cfg, cell, height_factor)
    rotated_fluid = np.rot90(fluid, rotation, axes=(1,2)).copy()
    rotated_sources = np.rot90(sources, rotation, axes=(2,3)).copy()
    start = time.perf_counter()
    faces, inlet, flow_report = compute_wind(rotated_fluid, cell, cfg, duration)
    solver = SteadyTracer(rotated_fluid, faces, inlet, cell, diffusivity, open_top=True)
    responses, diagnostics = [], []
    for source in rotated_sources:
        field, check = solver.solve(source)
        responses.append(np.rot90(field, -rotation, axes=(1,2)))
        diagnostics.append(check)
    total, direct_check = solver.solve(rotated_sources.sum(axis=0))
    total = np.rot90(total, -rotation, axes=(1,2))
    responses = np.stack(responses)
    superposition_error = float(np.max(np.abs(total-responses.sum(axis=0)))/max(float(total.max()), 1e-30))
    if superposition_error > 1e-6:
        raise RuntimeError('Linear superposition verification failed')
    z = (np.arange(fluid.shape[0])+.5)*cell
    slab = (z >= cfg['receptor_layer_m'][0]) & (z < cfg['receptor_layer_m'][1])
    fields = responses[:, slab].mean(axis=1)
    if not fluid[slab][:, receptor].all():
        raise ValueError('Fixed receptors overlap solid')
    plans = [list(p) for n in range(cfg['max_intervention_sectors']+1) for p in itertools.combinations(range(4), n)]
    metrics = []
    base = fields.sum(axis=0)
    weights = sources.sum(axis=(1,2,3))
    baseline_mean = float(base[receptor].mean())
    for plan in plans:
        combined = base-cfg['source_reduction_fraction']*fields[plan].sum(axis=0) if plan else base
        values = combined[receptor]
        metrics.append({'plan': plan, 'mean': float(values.mean()), 'p95': float(np.quantile(values, .95)),
                        'maximum': float(values.max()), 'mean_reduction_fraction': float(1-values.mean()/baseline_mean),
                        'emission_reduction_fraction': float(cfg['source_reduction_fraction']*weights[plan].sum()/weights.sum())})
    ny,nx = receptor.shape
    yy,xx = np.indices(receptor.shape); sectors = (xx>=nx//2).astype(int)+2*(yy>=ny//2).astype(int)
    local = [float(base[receptor & (sectors==i)].mean()) if (receptor & (sectors==i)).any() else 0 for i in range(4)]
    path = out/'cases'/label; path.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(path/'fields.npz', responses=responses, source_mass_au_s=sources,
                        receptor_mask=receptor, roof_m=roof,
                        solver_faces=np.stack(faces), solver_inlet=inlet, solver_fluid=rotated_fluid)
    report = {'id':label, 'case':case, 'height_factor':height_factor, 'rotation':rotation,'cell_m':cell,
              'duration_s':duration, 'diffusivity_m2_s':diffusivity, 'shape_zyx':list(fluid.shape),
              'source_sector_au_s':weights.tolist(), 'baseline_mean':baseline_mean,
              'local_sector_means':local, 'plans':metrics, 'flow':flow_report,
              'transport_checks':diagnostics, 'total_source_check':direct_check,
              'superposition_relative_error':superposition_error, 'wall_seconds':time.perf_counter()-start}
    write_json(path/'result.json',report)
    print(json.dumps({'finished':label,'seconds':report['wall_seconds'],'mean':baseline_mean,
                      'divergence':flow_report['records'][-1]['divergence_rms']}),flush=True)
    return report


def run(config, only_smoke=False):
    storage = Storage.load()
    cfg = json.loads(Path(config).read_text())
    if cfg['version'] != 'traffic-morphology-screening-0.1' or cfg['device'] != 'cpu':
        raise ValueError('Unsupported configuration')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_id = f'traffic_morphology_{stamp}_{uuid.uuid4().hex[:6]}'
    out = storage.scratch('south_ken','urban_planning',run_id)
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'status.json',{'status':'preparing','run_id':run_id})
    try:
        inputs,provenance,audit = prepare_inputs(storage,cfg)
    except Exception as exc:
        write_json(out/'status.json',{'status':'failed_preparation','run_id':run_id,'error':repr(exc)})
        raise
    np.savez_compressed(out/'inputs.npz',**inputs)
    write_json(out/'config.json',cfg); write_json(out/'input_provenance.json',provenance)
    write_json(out/'traffic_audit.json',audit)
    from common.provenance import snapshot_sources
    revision = snapshot_sources(storage.root, out/'source_snapshot.tar.gz')
    write_json(out/'environment.json', {'python':sys.version,'code_revision':revision,
               'packages':{k:importlib.metadata.version(k) for k in ['numpy','scipy','torch','matplotlib','jsonschema']},
               'solver_sha256':digest(storage.root/'src/urban_flow/solvers/mac_torch.py'),
               'tracer_sha256':digest(storage.root/'src/urban_flow/physics/conservative_tracer.py'),
               'runner_sha256':digest(Path(__file__)), 'device':'cpu','threads':cfg['torch_threads']})
    write_json(out/'status.json',{'status':'running','run_id':run_id})
    print(json.dumps({'run_directory':str(out),'traffic_audit':audit}),flush=True)
    results=[]
    try:
        for case in ['idealized','south_ken']:
            for height in cfg['height_factors']:
                for rotation in cfg['wind_rotations_quarter_turns']:
                    label=f'{case}_h{height:g}_r{rotation}_dx{cfg["cell_m"]}'
                    results.append(solve_case(inputs,cfg,case,height,rotation,cfg['cell_m'],
                                             cfg['flow_duration_s'],cfg['scalar_diffusivity_m2_s'],out,label))
                    write_json(out/'results.json',results)
                    if only_smoke:
                        write_json(out/'status.json',{'status':'smoke_complete','run_id':run_id})
                        return out
        for cell,duration,k,name in [(4,120,1,'fine4'),(8,240,1,'long240'),(8,120,.5,'diff05'),(8,120,2,'diff2')]:
            results.append(solve_case(inputs,cfg,'south_ken',1.,0,cell,duration,k,out,f'sensitivity_{name}'))
            write_json(out/'results.json',results)
        write_json(out/'status.json',{'status':'complete','run_id':run_id,'case_count':len(results)})
    except Exception as exc:
        write_json(out/'status.json',{'status':'failed','run_id':run_id,'error':repr(exc),'completed':len(results)})
        raise
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True);parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    print(run(args.config,args.smoke),flush=True)


if __name__=='__main__':
    main()
