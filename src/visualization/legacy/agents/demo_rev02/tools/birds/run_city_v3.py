"""revision_02 bird city run, v3 (CO, 2026-09-11) - fixes from Main CD's review applied in the WRAPPER only.

Akira's source (snapshot, hashes verified) is imported unchanged. This wrapper adds:
  * explicit day clock: day_length_s (default 86400) -> n_days = n_steps*dt/day_length_s, so the day
    speed is real time for ANY run length (short tests and the 3600 s run share the same clock);
    day_phase_start default 0.5 (noon);
  * site validation before the run: auto-generated roost/forage sites must lie inside the subdomain,
    on a free surface (no occupied voxel in the footprint above the surface) and >= --site-road-margin
    from every drivable lane centreline of the revision_02 road layer; invalid sites are replaced by
    the next valid candidate of Akira's own generator (world_generation='off' + explicit sites) and
    every replacement is recorded;
  * spawn validation after init_state: every bird must be inside the grid and >= --spawn-margin from
    any occupied voxel (Euclidean distance transform); invalid birds are resampled around the spawn
    point (same rng stream, altitude raised if needed) and recorded;
  * per-step occupancy checks on positions AND on ~1 m samples along each step segment, classified as
    roof_contact (bird within one z-cell of the column top while in FORAGE/DESCENT/ROOST) or
    penetration (deeper inside a column, or any state in flight);
  * correct sky_light export: day_fraction(state['time'], config) (scalar day light);
  * finiteness of EVERY exported channel per saved frame; checkpoints every --checkpoint steps;
  * wall time and peak RSS recorded.
Source findings kept as-is and recorded: W1 (world_gen reads config.scaled_grid_origin -> set equal to the
geometry origin), separation_mode not forwarded by integrator.step (effective baseline unchanged),
predator disabled.
"""
import argparse
import hashlib
import json
import os
import resource
import sys
import time
import numpy as np


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', required=True)
    ap.add_argument('--geometry', required=True)
    ap.add_argument('--road-layer', required=True, help='revision_02 city_roads_v2.json (world XYZ lane ribbons)')
    ap.add_argument('--out', required=True, help='output NPZ path')
    ap.add_argument('--n-birds', type=int, default=100)
    ap.add_argument('--n-steps', type=int, default=72000)
    ap.add_argument('--dt', type=float, default=0.05)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--spawn', default='700,-250,80', help='bird frame x,y,z')
    ap.add_argument('--save-every', type=int, default=5)
    ap.add_argument('--day-length-s', type=float, default=86400.0)
    ap.add_argument('--day-phase-start', type=float, default=0.5)
    ap.add_argument('--spawn-margin', type=float, default=6.0)
    ap.add_argument('--site-road-margin', type=float, default=6.0)
    ap.add_argument('--checkpoint', type=int, default=6000)
    ap.add_argument('--datum', type=float, default=0.0)
    ap.add_argument('--roost-near', default=None, help='world X,Z: use the valid roost candidate of the generator closest to this point (2026-09-12 addition)')
    ap.add_argument('--forage-near', default=None, help='world X,Z: use the closest valid forage candidates to this point')
    args = ap.parse_args()
    sys.path.insert(0, args.source)
    from sim.config import SimConfig
    from sim.integrator import init_state, step, _load_geometry
    from sim.environment import day_fraction
    from sim import world_gen
    from scipy.ndimage import distance_transform_edt
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree
    t0 = time.time()
    geo = np.load(args.geometry)
    G = geo['geometry']
    sp, spz = float(geo['grid_spacing']), float(geo['grid_spacing_z'])
    origin = np.array(geo['grid_origin'], dtype=float)
    nz, ny, nx = G.shape
    spawn = tuple(float(v) for v in args.spawn.split(','))
    n_days = args.n_steps * args.dt / args.day_length_s
    base_kwargs = dict(n_birds=args.n_birds, n_steps=args.n_steps, dt=args.dt, seed=args.seed, geometry_path=args.geometry,
                       wind_mode='none', spawn_point=spawn, save_every=args.save_every, n_days=n_days, day_phase_start=args.day_phase_start,
                       enable_predator=False, scaled_grid_origin=tuple(origin.tolist()))   # W1 workaround: same origin as the geometry

    # ---------------- geometry helpers
    col_top = np.zeros((ny, nx))                       # column top height (bird z) per (j,i)
    for k in range(nz):
        col_top[G[k]] = origin[2] + (k + 1) * spz
    free_dist = distance_transform_edt(~G, sampling=(spz, sp, sp))   # metres to nearest occupied voxel

    def cell(p):
        i = int((p[0] - origin[0]) / sp); j = int((p[1] - origin[1]) / sp); k = int((p[2] - origin[2]) / spz)
        return i, j, k

    def inside(i, j, k):
        return 0 <= i < nx and 0 <= j < ny and 0 <= k < nz

    def occupied_class(p, bstate):
        i, j, k = cell(p)
        if not inside(i, j, k):
            return 'outside_grid'
        if not G[k, j, i]:
            return None
        top = col_top[j, i]
        if p[2] >= top - spz and int(bstate) in (0, 3, 4):
            return 'roof_contact'
        return 'penetration'

    # ---------------- road layer for site validation (world -> bird frame: x = X, y = -Z)
    road = json.load(open(args.road_layer))
    lanes = [LineString([(p[0], -p[2]) for p in ln['world_xyz']]) for ln in road['lanes'] if len(ln['world_xyz']) >= 2]
    ltree = STRtree(lanes)

    def site_report(site, kind):
        c = np.array(site['center'], dtype=float); size = site.get('size', [8.0, 8.0])
        i, j, k = cell(c)
        rep = {'kind': kind, 'center': c.tolist(), 'size': list(size)}
        rep['inside_grid'] = bool(0 <= i < nx and 0 <= j < ny)
        if rep['inside_grid']:
            # footprint columns: everything above the surface must be free
            hw, hl = size[0] / 2, size[1] / 2
            i0, i1 = max(0, int((c[0] - hw - origin[0]) / sp)), min(nx - 1, int((c[0] + hw - origin[0]) / sp))
            j0, j1 = max(0, int((c[1] - hl - origin[1]) / sp)), min(ny - 1, int((c[1] + hl - origin[1]) / sp))
            tops = col_top[j0:j1 + 1, i0:i1 + 1]
            rep['surface_height_m'] = float(np.max(tops)); rep['surface_flat'] = bool(np.ptp(tops) <= spz + 1e-6)
            k_surface = int(round((rep['surface_height_m'] - origin[2]) / spz))
            above = G[k_surface:, j0:j1 + 1, i0:i1 + 1] if k_surface < nz else np.zeros((0,))
            rep['obstructed_above_surface'] = bool(above.any())
            rep['on_building_roof'] = rep['surface_height_m'] > origin[2] + 0.5 * spz
        pt = Point(c[0], c[1])
        near = ltree.query(pt.buffer(args.site_road_margin))
        d = min((lanes[q].distance(pt) for q in near), default=None)
        rep['nearest_drivable_lane_m'] = None if d is None else round(float(d), 2)
        rep['valid'] = rep['inside_grid'] and not rep.get('obstructed_above_surface', True) and (d is None or d >= args.site_road_margin) and rep.get('surface_flat', False)
        return rep

    # ---------------- pass 1: let Akira's generator place sites, then validate
    cfg0 = SimConfig(world_generation='naive', **base_kwargs)
    np.random.seed(cfg0.seed)
    _ = init_state(cfg0)
    auto_world = json.loads(json.dumps(cfg0.world, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)))
    reports = [site_report(s, 'roost') for s in auto_world['roosts']] + [site_report(s, 'forage') for s in auto_world['forage_sites']]
    for r in reports: print('  site check', json.dumps(r, default=str), flush=True)
    replaced = []
    user_selection = None
    if args.roost_near or args.forage_near:
        # user-chosen focus area: same candidate lists and the same validity rule, only the choice among candidates changes
        geo_data = _load_geometry(cfg0)
        col_h, ground_mask = world_gen._build_column_height_map(geo_data, geo_data['grid_origin'])
        roost_c = world_gen._find_roost_candidates(col_h, ground_mask, geo_data, geo_data['grid_origin'], cfg0.world_gen_min_roost_area)
        forage_c = world_gen._find_forage_candidates(col_h, ground_mask, geo_data, geo_data['grid_origin'], cfg0.world_gen_min_forage_area)
        def nearest_valid(cands, kind, n, world_xz):
            X, Z = (float(v) for v in world_xz.split(','))
            out = []
            for cnd in sorted(cands, key=lambda c: (c['center'][0] - X) ** 2 + (c['center'][1] + Z) ** 2):
                site = {k: v for k, v in cnd.items() if not k.startswith('_')}
                site.setdefault('forward', [1.0, 0.0, 0.0]); site.setdefault('normal', [0.0, 0.0, 1.0]); site.setdefault('quality', 1.0)
                if site_report(site, kind)['valid']:
                    out.append(site)
                if len(out) >= n:
                    break
            return out
        new_world = {'roosts': nearest_valid(roost_c, 'roost', cfg0.world_gen_n_roosts, args.roost_near) if args.roost_near else auto_world['roosts'],
                     'forage_sites': nearest_valid(forage_c, 'forage', cfg0.world_gen_n_forage, args.forage_near) if args.forage_near else auto_world['forage_sites'],
                     'roads': [], 'point_sources': []}
        user_selection = {'roost_near_world_xz': args.roost_near, 'forage_near_world_xz': args.forage_near, 'rule': 'closest valid candidates of the generator to the requested point'}
        base_kwargs_run = dict(base_kwargs, world_generation='off', world=new_world)
        for s_ in new_world['roosts'] + new_world['forage_sites']: print('  user-focus site', json.dumps(s_, default=str), flush=True)
    elif not all(r['valid'] for r in reports):
        # ask the generator's own candidate lists for the next valid ones (same heuristics, no model change)
        geo_data = _load_geometry(cfg0)
        col_h, ground_mask = world_gen._build_column_height_map(geo_data, geo_data['grid_origin'])   # 2026-09-12: the helper returns (heights, ground_mask); this branch had never run
        roost_c = world_gen._find_roost_candidates(col_h, ground_mask, geo_data, geo_data['grid_origin'], cfg0.world_gen_min_roost_area)
        forage_c = world_gen._find_forage_candidates(col_h, ground_mask, geo_data, geo_data['grid_origin'], cfg0.world_gen_min_forage_area)
        def pick(cands, kind, n):
            out = []
            for cnd in cands:
                site = {k: v for k, v in cnd.items() if not k.startswith('_')}
                site.setdefault('forward', [1.0, 0.0, 0.0]); site.setdefault('normal', [0.0, 0.0, 1.0]); site.setdefault('quality', 1.0)
                if site_report(site, kind)['valid']:
                    out.append(site)
                if len(out) >= n:
                    break
            return out
        new_world = {'roosts': pick(roost_c, 'roost', cfg0.world_gen_n_roosts), 'forage_sites': pick(forage_c, 'forage', cfg0.world_gen_n_forage), 'roads': [], 'point_sources': []}
        for r in reports:
            if not r['valid']:
                replaced.append(r)
        base_kwargs_run = dict(base_kwargs, world_generation='off', world=new_world)
    else:
        base_kwargs_run = dict(base_kwargs, world_generation='off', world=auto_world)   # identical sites, fixed explicitly
    config = SimConfig(**base_kwargs_run)
    np.random.seed(config.seed)
    state = init_state(config)
    final_world = json.loads(json.dumps(config.world, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)))
    final_site_reports = [site_report(s, 'roost') for s in final_world['roosts']] + [site_report(s, 'forage') for s in final_world['forage_sites']]

    # ---------------- spawn validation + resampling (wrapper action, recorded)
    def clearance(p):
        i, j, k = cell(p)
        return float(free_dist[k, j, i]) if inside(i, j, k) else -1.0
    rng = np.random.RandomState(config.seed + 1000)
    resampled = []
    for n in range(config.n_birds):
        tries = 0
        while clearance(state['pos'][n]) < args.spawn_margin and tries < 200:
            cand = np.array(spawn) + rng.randn(3) * config.init_flock_radius
            cand[2] = max(cand[2], spawn[2]) + 2.0 * (tries // 20)
            state['pos'][n] = cand; tries += 1
        if tries:
            resampled.append({'bird': n, 'tries': tries, 'new_pos': state['pos'][n].round(2).tolist(), 'clearance_m': round(clearance(state['pos'][n]), 2)})
    spawn_clear = [clearance(state['pos'][n]) for n in range(config.n_birds)]

    # ---------------- run
    frames = {k: [] for k in ('pos', 'vel', 'bank', 'bstate', 'energy', 'valence', 'arousal', 'time', 'sky_light')}
    cls_counts = {'roof_contact': 0, 'penetration': 0, 'outside_grid': 0}
    seg_counts = {'roof_contact': 0, 'penetration': 0, 'outside_grid': 0}
    per_bird = {}
    seg_samples = 0
    nonfinite = {k: 0 for k in ('pos', 'vel', 'bank', 'energy', 'valence', 'arousal', 'sky_light')}
    max_disp, max_disp_step = 0.0, None
    prev = state['pos'].copy()
    state_counts = []
    wall0 = time.time()

    def flush(tag):
        arrays = {k: np.array(v) for k, v in frames.items()}
        np.savez_compressed(args.out if tag == 'final' else args.out.replace('.npz', f'_{tag}.npz'), pos=arrays['pos'], vel=arrays['vel'], bank=arrays['bank'], bstate=arrays['bstate'],
                            energy=arrays['energy'], valence=arrays['valence'], arousal=arrays['arousal'], frame_times=arrays['time'], sky_light=arrays['sky_light'],
                            world=json.dumps(final_world), **{f'identity_{k}': np.asarray(v) for k, v in (state.get('identity') or {}).items()})

    def classify_vec(P, bst):
        # vectorised occupancy classification for an (N,3) array; returns array of codes 0 free,1 roof_contact,2 penetration,3 outside
        ii = ((P[:, 0] - origin[0]) / sp).astype(int); jj = ((P[:, 1] - origin[1]) / sp).astype(int); kk = ((P[:, 2] - origin[2]) / spz).astype(int)
        ins = (ii >= 0) & (ii < nx) & (jj >= 0) & (jj < ny) & (kk >= 0) & (kk < nz)
        code = np.where(ins, 0, 3)
        occ = np.zeros(len(P), dtype=bool); occ[ins] = G[kk[ins], jj[ins], ii[ins]]
        top = np.zeros(len(P)); top[ins] = col_top[jj[ins], ii[ins]]
        roof = occ & (P[:, 2] >= top - spz) & np.isin(bst.astype(int), (0, 3, 4))
        code = np.where(occ & roof, 1, code); code = np.where(occ & ~roof, 2, code)
        return code
    names = {1: 'roof_contact', 2: 'penetration', 3: 'outside_grid'}
    for i in range(config.n_steps):
        state = step(state, config)
        pos = state['pos']
        code = classify_vec(pos, state['bstate'])
        for c in (1, 2, 3):
            hits = np.nonzero(code == c)[0]
            if len(hits):
                cls_counts[names[c]] += int(len(hits))
                for n in hits:
                    per_bird.setdefault(int(n), {'roof_contact': 0, 'penetration': 0, 'outside_grid': 0})[names[c]] += 1
        d = pos - prev
        dist = np.linalg.norm(d, axis=1); md = float(dist.max())
        if md > max_disp:
            max_disp, max_disp_step = md, i + 1
        n_s = int(min(8, max(2, np.ceil(md / 1.0))))       # at least the midpoint of every step segment is checked
        for s_ in range(1, n_s):
            q = prev + d * (s_ / n_s)
            cq = classify_vec(q, state['bstate'])
            seg_samples += len(q)
            for c in (1, 2, 3):
                k_ = int((cq == c).sum())
                if k_:
                    seg_counts[names[c]] += k_
        prev = pos.copy()
        if (i + 1) % config.save_every == 0:
            light = float(day_fraction(state['time'], config))
            for k in ('pos', 'vel', 'bank', 'energy', 'valence', 'arousal'):
                if not np.isfinite(state[k]).all():
                    nonfinite[k] += 1
                frames[k].append(state[k].copy())
            if not np.isfinite(light):
                nonfinite['sky_light'] += 1
            frames['bstate'].append(state['bstate'].copy()); frames['time'].append(float(state['time'])); frames['sky_light'].append(light)
            state_counts.append(np.bincount(state['bstate'].astype(int), minlength=5).tolist())
        if (i + 1) % 1000 == 0:
            print(f'step {i + 1}/{config.n_steps} t={state["time"]:.1f}s wall={time.time() - wall0:.0f}s occ={cls_counts} seg={seg_counts} nonfinite={sum(nonfinite.values())}', flush=True)
        if args.checkpoint and (i + 1) % args.checkpoint == 0 and (i + 1) < config.n_steps:
            flush(f'ckpt{i + 1}')
    flush('final')
    wall = time.time() - wall0
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    resolved = {k: (v if isinstance(v, (int, float, str, bool, type(None))) else json.loads(json.dumps(v, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)))) for k, v in vars(config).items() if k != 'world'}
    evidence = {
        'schema': 'UWM_DEMO_REVISION_02_BIRD_CITY_RUN_V3',
        'source_snapshot': {'path': args.source, 'files_sha256': {f: sha256(os.path.join(args.source, f)) for f in ['sim/config.py', 'sim/integrator.py', 'sim/forces.py', 'sim/routing.py', 'sim/environment.py', 'sim/world_gen.py', 'sim/sites.py', 'sim/states.py', 'sim/foraging.py', 'sim/neighbors.py', 'sim/wind.py']}},
        'geometry': {'path': args.geometry, 'sha256': sha256(args.geometry), 'shape_zyx': list(G.shape), 'spacing': [sp, spz], 'origin': origin.tolist()},
        'clock': {'method': 'explicit day length: n_days = n_steps*dt/day_length_s (source formula kept, n_days chosen so day_length = day_length_s)',
                  'day_length_s': args.day_length_s, 'n_days': n_days, 'day_phase_start': args.day_phase_start, 'physical_seconds_per_city_second': 1.0,
                  'sky_light_first_last': [frames['sky_light'][0], frames['sky_light'][-1]] if frames['sky_light'] else None},
        'run': {'n_birds': config.n_birds, 'n_steps': config.n_steps, 'dt_s': config.dt, 'physical_time_s': float(state['time']), 'saved_frames': len(frames['time']),
                'first_frame_time_s': frames['time'][0] if frames['time'] else None, 'save_every': config.save_every, 'display_frame_dt_s': config.save_every * config.dt, 'seed': config.seed,
                'wall_s': round(wall, 1), 'seconds_per_step': round(wall / config.n_steps, 4), 'peak_rss_mb': round(rss_mb, 1)},
        'sites': {'auto_generated': auto_world, 'auto_site_reports': reports, 'replaced_invalid_sites': replaced, 'user_site_selection': user_selection, 'final_world': final_world, 'final_site_reports': final_site_reports,
                  'rule': f'inside grid, flat unobstructed surface, >= {args.site_road_margin} m from any drivable lane centreline (revision_02 road layer)'},
        'spawn': {'spawn_point': list(spawn), 'init_flock_radius_m': config.init_flock_radius, 'min_start_alt_m': config.min_start_alt, 'margin_m': args.spawn_margin,
                  'resampled_birds': resampled, 'clearance_m_min': round(min(spawn_clear), 2), 'all_valid': all(c >= args.spawn_margin for c in spawn_clear)},
        'checks': {'nonfinite_frames_by_channel': nonfinite, 'position_steps_by_class': cls_counts, 'segment_samples': seg_samples, 'segment_samples_by_class': seg_counts,
                   'birds_with_any_occupied_position': per_bird, 'max_displacement_per_step_m': round(max_disp, 3), 'max_displacement_step': max_disp_step,
                   'max_plausible_per_step_m': round(config.dt * config.v_max, 3) if hasattr(config, 'v_max') else None,
                   'state_counts_first_frame': state_counts[0] if state_counts else None, 'state_counts_last_frame': state_counts[-1] if state_counts else None,
                   'states_seen': sorted({int(s) for c in state_counts for s, n in enumerate(c) if n > 0})},
        'source_findings_kept': {'W1_world_gen_scaled_grid_origin': 'set equal to geometry grid_origin (wrapper), no source change',
                                 'separation_mode': f'config {config.separation_mode!r}; integrator.step does not forward it (effective baseline unchanged, not patched)',
                                 'predator': 'disabled (enable_predator=False)'},
        'resolved_config': resolved,
        'claim': 'Akira original init_state/step unchanged on the revision_02 campus voxel geometry; wrapper-level spawn/site validation and export fixes only. Not ecological validation, not wind/traffic/UAV coupling, soft obstacle forces are not a collision certificate.'}
    json.dump(evidence, open(args.out.replace('.npz', '_EVIDENCE.json'), 'w'), indent=1, default=str)
    print(json.dumps(evidence['run'])); print(json.dumps(evidence['checks'])); print('spawn', json.dumps({k: v for k, v in evidence['spawn'].items() if k != 'resampled_birds'}), 'resampled', len(resampled))
    print('sites valid:', [r['valid'] for r in final_site_reports], 'replaced:', len(replaced))


if __name__ == '__main__':
    main()
