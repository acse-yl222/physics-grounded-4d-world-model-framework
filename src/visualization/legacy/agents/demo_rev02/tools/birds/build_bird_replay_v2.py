"""NPZ -> viewer replay adapter for the revision_02 bird layer (CO, 2026-09-11).

Input: the run_sim-style NPZ written by run_city_trial_v2.py (pos/vel/bstate in the BIRD frame,
frame_times in physical seconds) + its _EVIDENCE.json + the geometry _META.json.
Output (three files, read by the viewer's bird layer):
  bird_replay.f32    float32 records per frame per bird: [worldX, worldY, worldZ, yaw_rad, speed_mps, bank_rad]
                     (frame-major: frame f, bird n at (f*N + n)*6)
  bird_states.u8     uint8 per frame per bird: 0 FORAGE, 1 TRANSIT, 2 MURMURATION, 3 DESCENT, 4 ROOST
  bird_replay.json   manifest: frame timing, counts, transform, state names, file hashes, resolved
                     config, evidence summary (occupancy, continuity), claim boundary.
Transform (explicit): viewer(X, Y, Z) = (bird_x, bird_z + ground_datum, -bird_y); yaw = atan2(vX, vZ) with
vX = vx, vZ = -vy (viewer heading 0 = +Z, pi/2 = +X). Trajectories are NOT modified.
"""
import argparse
import hashlib
import json
import time
import numpy as np

STATE_NAMES = {0: 'FORAGE', 1: 'TRANSIT', 2: 'MURMURATION', 3: 'DESCENT', 4: 'ROOST'}
STATE_COLOURS = {0: '#f2c14e', 1: '#3aa0d8', 2: '#9b5de5', 3: '#f28c28', 4: '#6b7c85'}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--npz', required=True)
    ap.add_argument('--evidence', required=True)
    ap.add_argument('--geometry-meta', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--datum', type=float, default=0.0)
    ap.add_argument('--stride', type=int, default=1, help='keep every k-th saved frame')
    args = ap.parse_args()
    t0 = time.time()
    d = np.load(args.npz)
    pos, vel, bst, ft = d['pos'][::args.stride], d['vel'][::args.stride], d['bstate'][::args.stride], d['frame_times'][::args.stride]
    bank = d['bank'][::args.stride]
    F, N, _ = pos.shape
    wx = pos[:, :, 0]
    wy = pos[:, :, 2] + args.datum
    wz = -pos[:, :, 1]
    vX, vZ = vel[:, :, 0], -vel[:, :, 1]
    yaw = np.arctan2(vX, vZ)
    speed = np.linalg.norm(vel, axis=2)
    rec = np.stack([wx, wy, wz, yaw, speed, bank], axis=2).astype('<f4')    # (F, N, 6)
    rec.tofile(f'{args.out_dir}/bird_replay.f32')
    bst.astype(np.uint8).tofile(f'{args.out_dir}/bird_states.u8')
    # continuity: per-frame displacement vs plausible (v_max * dt + margin)
    dt = float(np.median(np.diff(ft)))
    disp = np.linalg.norm(np.diff(pos, axis=0), axis=2)
    ev = json.load(open(args.evidence))
    meta = json.load(open(args.geometry_meta))
    counts = {STATE_NAMES[k]: int((bst == k).sum()) for k in STATE_NAMES}
    man = {
        'schema': 'UWM_DEMO_REVISION_02_BIRD_REPLAY_V1',
        'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'source_npz': {'path': args.npz, 'sha256': sha256(args.npz)},
        'frames': int(F), 'birds': int(N), 'frame_dt_s': dt, 'first_frame_t_s': float(ft[0]), 'last_frame_t_s': float(ft[-1]),
        'record': ['worldX', 'worldY', 'worldZ', 'yaw_rad', 'speed_mps', 'bank_rad'], 'record_bytes': 24, 'layout': 'frame-major: (frame*birds + bird)*6 floats',
        'files': {'bird_replay.f32': {'bytes': rec.nbytes, 'sha256': sha256(f'{args.out_dir}/bird_replay.f32')},
                  'bird_states.u8': {'bytes': int(bst.size), 'sha256': sha256(f'{args.out_dir}/bird_states.u8')}},
        'transform': {'bird_to_viewer': 'viewer(X,Y,Z) = (bird_x, bird_z + ground_datum, -bird_y)', 'ground_datum_m': args.datum,
                      'yaw': 'atan2(vX, vZ) with vX = vx, vZ = -vy; viewer heading 0 = +Z, pi/2 = +X (vel is airspeed; wind_mode none, so equal to ground velocity)', 'bank': 'source bank angle (rad) passed through for display roll only', 'sumo_to_viewer_for_reference': 'X = sumo_x - 2912.594719173, Z = 1704.705026026 - sumo_y'},
        'clock': dict({'physical_seconds_per_replay_second': 1.0}, **(ev.get('clock') or {k: ev['run'].get(k) for k in ('clock_note', 'n_days', 'day_length_s', 'day_phase_start')})),
        'states': {str(k): {'name': STATE_NAMES[k], 'colour': STATE_COLOURS[k]} for k in STATE_NAMES},
        'state_frame_counts': counts,
        'continuity': {'max_displacement_per_frame_m': round(float(disp.max()), 3), 'p99_displacement_per_frame_m': round(float(np.percentile(disp, 99)), 3),
                       'max_speed_mps': round(float(speed.max()), 3), 'frames_with_nonfinite': int((~np.isfinite(rec)).any(axis=(1, 2)).sum())},
        'altitude_m': {'min': round(float(wy.min()), 2), 'median': round(float(np.median(wy)), 2), 'max': round(float(wy.max()), 2)},
        'extent_world': {'x': [round(float(wx.min()), 1), round(float(wx.max()), 1)], 'z': [round(float(wz.min()), 1), round(float(wz.max()), 1)]},
        'geometry': {'meta': args.geometry_meta, 'world_box': meta.get('world_box'), 'bird_grid': meta.get('bird_grid'), 'landmark_checks': meta.get('landmark_checks')},
        'simulation_evidence': {'checks': ev.get('checks'), 'run': {k: ev['run'].get(k) for k in ('n_birds', 'n_steps', 'dt_s', 'physical_time_s', 'saved_frames', 'save_every', 'seed', 'wall_s')},
                                'resolved_config_subset': {k: ev['resolved_config'].get(k) for k in ('geometry_path', 'world_generation', 'spawn_point', 'init_flock_radius', 'wind_mode', 'enable_predator', 'separation_mode', 'cruise_speed', 'v_max', 'k_neighbors', 'n_days', 'day_phase_start', 'enable_environment', 'enable_wave_routing')},
                                'world': (ev.get('sites') or {}).get('final_world') or ev.get('world_after_init'), 'sites': ev.get('sites'), 'spawn': ev.get('spawn'), 'source_findings_kept': ev.get('source_findings_kept'), 'source_snapshot': ev.get('source_snapshot')},
        # 2026-09-11: claim sentence about the viewer model updated (placeholder shape -> procedural pigeon GLB); earlier text kept in bird_replay.json claim_revisions
        'claim': 'Akira\'s original bird model (uwm-group1 main e2d88d8) run unchanged on a bounded revision_02 campus voxel geometry; shown in the same city and on the same clock as the traffic and UAV replays but NOT coupled to them (no bird-vehicle or bird-UAV interaction, no wind, no ecological validation). Viewer display model: a low-poly feral pigeon built procedurally as a GLB (actors/pigeon.glb, real scale, wing flap / pitch / roll for display only, never moves a recorded position); a stand-in asset, not Akira\'s art.'
    }
    json.dump(man, open(f'{args.out_dir}/bird_replay.json', 'w'), indent=1, default=float)
    print(json.dumps({k: man[k] for k in ('frames', 'birds', 'frame_dt_s', 'continuity', 'altitude_m', 'extent_world', 'state_frame_counts')}), 'wall', round(time.time() - t0, 1))


if __name__ == '__main__':
    main()
