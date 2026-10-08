"""
Convert the model-predicted trajectories from a real road network
back to the world coordinate system and export them as JSON.

Note:
For the coordinate system transformation, AI was used with the assistance of explicit instructions.
I have confirmed that all modified or written AI code conforms to my intended purpose.
"""

# Compatibility for direct source-script execution; package imports need no path changes.
if __name__ == '__main__' and not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pathlib import Path
from common.layout import scene_input
from common.runtime import trial_root
import argparse
import json
import os
import sys

import numpy as np
import torch

import traffic.configs.default as C
from traffic.verification import generate_complex_london as gen
from traffic.verification.particle_mlp_london import ParticleTrafficModel

BASE = os.path.dirname(os.path.abspath(__file__))


def grid_to_lonlat(row, col, T):
    """grid coordinates -> (lon, lat)"""
    lon = T['origin_lon'] + (col - T['pad']) * T['cell_size_m'] / T['m_per_deg_lon']
    lat = T['origin_lat'] - (row - T['pad']) * T['cell_size_m'] / T['m_per_deg_lat']
    return lon, lat


def make_veh(roads, road_idx, direction, wp_idx, dest, speed=7.0):
    """Hot-start vehicle on a loaded real map."""
    poly = gen._road_path(roads, road_idx, direction)
    center, tangent, normal = gen._poly_interp(poly, wp_idx)
    lane = gen._spawn_lane(roads[road_idx])
    return {"row": center[0] + lane * normal[0],
            "col": center[1] + lane * normal[1],
            "speed": speed, "road": road_idx, "direction": direction,
            "lane": lane, "wp_idx": wp_idx, "dest": dest}


def road_len(roads, road_idx, direction):
    return len(gen._road_path(roads, road_idx, direction)) - 1


def auto_seed_vehicles(roads, n_vehicles, seed=0):
    """Place n_vehicles hot-start vehicles on a real map: random road, travel
    direction, position along the road, and a reachable destination (another
    road's endpoint in its travel direction)."""
    rng = np.random.default_rng(seed)
    dests = []
    for i, road in enumerate(roads):
        for d in (+1, -1):
            if not road["two_way"] and d == -1:
                continue
            poly = gen._road_path(roads, i, d)
            dests.append((poly[-1][0], poly[-1][1]))
    vehicles = []
    for _ in range(n_vehicles):
        road_idx = int(rng.integers(len(roads)))
        road = roads[road_idx]
        direction = int(rng.choice([+1, -1])) if road["two_way"] else +1
        wp_idx = road_len(roads, road_idx, direction) * float(rng.uniform(0.15, 0.7))
        dest = dests[int(rng.integers(len(dests)))]
        vehicles.append(make_veh(roads, road_idx, direction, wp_idx, dest,
                                 speed=float(rng.uniform(6.0, 8.0))))
    return vehicles


def _arrived_vids(tracks, initial, t_last):
    arrived = set()
    for vid, vt in tracks.items():
        for (t, row, col, vd, vc) in vt['positions']:
            if t == t_last:
                dr, dc = initial[vid]['dest']
                if np.hypot(row - dr, col - dc) < 3.0:
                    arrived.add(vid)
                break
    return arrived


def _anchor_pos(tracks, t_last):
    """The floating-point (row, col) position of each vehicle at time t_last"""
    pos = {}
    for vid, vt in tracks.items():
        for (t, row, col, vd, vc) in vt['positions']:
            if t == t_last:
                pos[vid] = (row, col)
                break
    return pos


def main():
    parser = argparse.ArgumentParser(
        description="Predict on a real (converted) road map and export lon/lat trajectories.")
    parser.add_argument('t_start', type=int, nargs='?', default=0,
                        help="window start step")
    parser.add_argument('--map', default=str(scene_input('south_ken','traffic','london_roads.json')),
                        help="converted road JSON (output of convert_london.py)")
    parser.add_argument('--model', default='09-10_core008',
                        help="model date (train/best_model_<date>.pt)")
    parser.add_argument('--left-hand', type=int, default=1, choices=[0, 1],
                        help="1 = left-hand traffic, 0 = right-hand")
    parser.add_argument('--vehicles', type=int, default=10,
                        help="number of hot-start vehicles")
    parser.add_argument('--seed', type=int, default=1, help="simulation seed")
    parser.add_argument('--steps', type=int, default=30, help="simulation steps")
    parser.add_argument('--out', default=str(trial_root('south_ken','traffic_prediction')/'predictions.json'))
    args = parser.parse_args()
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)

    # 1. Load the (generic) real road network and configure the simulator
    data = gen.load_map(args.map, left_hand=bool(args.left_hand))
    grid_size = int(data["grid_size"])
    T = data["transform"]
    roads = gen.get_road_network()

    # 2. Hot-start vehicles + short simulation for a consistent scene
    np.random.seed(args.seed)
    initial = auto_seed_vehicles(roads, args.vehicles, seed=args.seed)
    traj, tracks = gen.simulate_trajectory(
        total_steps=args.steps, seed=args.seed,
        initial_vehicles=initial, allow_spawn=False)

    model = ParticleTrafficModel()
    model.load_state_dict(torch.load(
        scene_input('south_ken','traffic','models',f'best_model_{args.model}.pt'),
        map_location='cpu'))
    model.eval()

    HIST_STEPS = C.HIST_STEPS
    PRED_STEPS = C.PRED_STEPS
    disp_scale = C.GRID_SIZE / grid_size

    t_start = args.t_start
    if not (0 <= t_start <= args.steps - HIST_STEPS - PRED_STEPS):
        raise ValueError(f"t_start must be in [0, {args.steps - HIST_STEPS - PRED_STEPS}]")

    # 3. Single-window prediction
    grid = torch.tensor(traj[t_start:t_start + HIST_STEPS], dtype=torch.float32)
    with torch.no_grad():
        pred = model.predict_full_grid(grid, disp_scale=disp_scale)  # (6, G, G, 4)

    t_last = t_start + HIST_STEPS - 1
    veh_cells = {}
    for vid, vt in tracks.items():
        for (t, row, col, vd, vc) in vt['positions']:
            if t == t_last:
                veh_cells[vid] = (int(np.clip(row, 0, grid_size - 1)),
                                  int(np.clip(col, 0, grid_size - 1)))

    # Fix the arrived vehicles during visualization
    arrived = _arrived_vids(tracks, initial, t_last)
    anchor_pos = _anchor_pos(tracks, t_last)

    # 4. Convert back to the world coordinate system
    trajectories = {}
    for vid, (r, c) in veh_cells.items():
        hist = []
        for (t, row, col, vd, vc) in tracks[vid]['positions']:
            if t_start <= t <= t_last:
                lon, lat = grid_to_lonlat(row, col, T)
                hist.append({"t_s": round(t * C.DT, 2), "lon": lon, "lat": lat})
        hist.sort(key=lambda p: p['t_s'])

        # predict
        pts = []
        for k in range(PRED_STEPS):
            if vid in arrived:
                row, col = anchor_pos[vid]
            else:
                row = pred[k, r, c, 0].item() * grid_size
                col = pred[k, r, c, 1].item() * grid_size
            lon, lat = grid_to_lonlat(row, col, T)
            pts.append({
                "t_s": round((t_last + 1 + k) * C.DT, 2),
                "lon": lon, "lat": lat,
            })
        # merge
        traj = hist + pts
        traj.sort(key=lambda p: p['t_s'])
        trajectories[str(vid)] = traj

    out = {
        "meta": {
            "coordinate_system": "WGS84 lon/lat (degrees); velocity/direction derivable from positions + timestamps",
            "time_step_s": C.DT,
            "history_steps": HIST_STEPS,
            "prediction_steps": PRED_STEPS,
            "history_window_s": HIST_STEPS * C.DT,
            "prediction_horizon_s": PRED_STEPS * C.DT,
            "grid_size": grid_size,
            "model": f"best_model_{args.model}.pt",
            "window_t_start": t_start,
            "transform": T,
        },
        "trajectories": trajectories,
    }

    with open(args.out, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"Export {len(trajectories)} vehicles -> {args.out}")

    # debug
    for i, (vid, tr) in enumerate(trajectories.items()):
        if i >= 3:
            break
        print(f"\nVehicle {vid}: {len(tr)} trajectory points")
        for p in tr:
            print(f"  t={p['t_s']:4.1f}s  lon={p['lon']:.6f}  lat={p['lat']:.6f}")


if __name__ == '__main__':
    main()
