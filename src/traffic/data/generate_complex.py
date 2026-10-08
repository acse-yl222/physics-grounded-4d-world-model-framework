"""
Multi-Intersection Irregular Road Network Simulation Dataset
"""

# Compatibility for direct source-script execution; package imports need no path changes.
if __name__ == '__main__' and not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import torch
import sys
import os

from traffic.configs.default import (
    GRID_SIZE, CELL_SIZE, MAX_SPEED, DT,
    TOTAL_FEAT_DIM, VEHICLE_DIM, HIST_STEPS, PRED_STEPS,
)

LEFT_HAND = False  # Left Travel Switch: True=Left Travel, False=Right Travel

#  Polyline Road Network
def _catmull_rom(points, n_per_seg=25):
    pts = np.asarray(points, dtype=float)
    if len(pts) < 3:
        return pts
    first = pts[0] - (pts[1] - pts[0])
    last = pts[-1] + (pts[-1] - pts[-2])
    p = np.vstack([first, pts, last])
    curve = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, n_per_seg, endpoint=False):
            t2, t3 = t * t, t * t * t
            pt = 0.5 * ((2 * p1) + (-p0 + p2) * t +
                        (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                        (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            curve.append(pt)
    curve.append(pts[-1])
    return np.array(curve)


def get_road_network():
    return _road_network_cached()


_ROADS_CACHE = None
def _road_network_cached():
    global _ROADS_CACHE
    if _ROADS_CACHE is not None:
        return _ROADS_CACHE
    roads = [
        # Main road: two-way, 4 lanes
        {"centerline": [(13.5, 2), (13.5, 15), (13.5, 28), (13.5, 41), (13.5, 54)],
         "lanes_per_dir": 2, "two_way": True},
        {"centerline": [(41.5, 2), (41.5, 15), (41.5, 28), (41.5, 41), (41.5, 54)],
         "lanes_per_dir": 2, "two_way": True},
        {"centerline": [(2, 13.5), (15, 13.5), (28, 13.5), (41, 13.5), (54, 13.5)],
         "lanes_per_dir": 2, "two_way": True},
        # Branch road: two-way, 2 lanes
        {"centerline": [(2, 41.5), (15, 41.5), (28, 41.5), (41, 41.5), (54, 41.5)],
         "lanes_per_dir": 1, "two_way": True},
        # Diagonal road: two-way, 2 lanes
        {"centerline": [(18, 2), (28, 12), (38, 22), (48, 32), (54, 38)],
         "lanes_per_dir": 1, "two_way": True},
        # Curved one-way road: one-way, 2 lanes
        {"centerline": [(2, 20), (12, 24), (22, 28), (32, 32), (42, 36), (54, 38)],
         "lanes_per_dir": 2, "two_way": False},
        # Three-way road: two-way, 2 lanes
        {"centerline": [(2, 28), (13.5, 28)],
         "lanes_per_dir": 1, "two_way": True},
    ]
    # Smooth the centerline into curves
    _ROADS_CACHE = [{"centerline": _catmull_rom(r["centerline"]),
                     "lanes_per_dir": r["lanes_per_dir"],
                     "two_way": r["two_way"]} for r in roads]
    return _ROADS_CACHE


def _point_segment_dist(p, a, b):
    """
    Perpendicular distance from point p=(row,col) to segment a->b, 
    and the coordinates of the nearest projection point
    """
    pr, pc = p
    ar, ac = a
    br, bc = b
    ab_r, ab_c = br - ar, bc - ac
    len_sq = ab_r * ab_r + ab_c * ab_c
    if len_sq < 1e-9:
        return np.hypot(pr - ar, pc - ac), (ar, ac)
    t = ((pr - ar) * ab_r + (pc - ac) * ab_c) / len_sq
    t = max(0.0, min(1.0, t))
    proj_r = ar + t * ab_r
    proj_c = ac + t * ab_c
    return np.hypot(pr - proj_r, pc - proj_c), (proj_r, proj_c)


def _lane_offsets(lanes_per_dir, two_way):
    n = lanes_per_dir
    if two_way:
        sign = +1 if LEFT_HAND else -1
        return [sign * (k + 0.5) for k in range(n)] + [-sign * (k + 0.5) for k in range(n)]
    return [k - (n - 1) / 2.0 for k in range(n)]


def _offset_polyline(polyline, offset):
    pts = np.asarray(polyline, dtype=float)
    n = len(pts)
    out = np.zeros_like(pts)
    for i in range(n):
        if i == 0:
            d = pts[1] - pts[0]
        elif i == n - 1:
            d = pts[-1] - pts[-2]
        else:
            d = pts[i + 1] - pts[i - 1]
        norm = np.hypot(d[0], d[1]) + 1e-9
        normal = np.array([-d[1] / norm, d[0] / norm])
        out[i] = pts[i] + offset * normal
    return out


_LANE_LINES_CACHE = None
def get_lane_centerlines(roads):
    global _LANE_LINES_CACHE
    if _LANE_LINES_CACHE is not None:
        return _LANE_LINES_CACHE
    lane_lines = []
    for road in roads:
        n = road["lanes_per_dir"]
        if road["two_way"]:
            sign = +1 if LEFT_HAND else -1
            for k in range(n):
                lane_lines.append((_offset_polyline(road["centerline"], sign * (k + 0.5)), +1))
            for k in range(n):
                lane_lines.append((_offset_polyline(road["centerline"], -sign * (k + 0.5)), -1))
        else:
            for k in range(n):
                off = k - (n - 1) / 2.0
                lane_lines.append((_offset_polyline(road["centerline"], off), +1))
    _LANE_LINES_CACHE = lane_lines
    return lane_lines


def _seg_intersect(p1, p2, p3, p4):
    d1 = p2 - p1
    d2 = p4 - p3
    denom = np.cross(d1, d2)
    if abs(denom) < 1e-9:
        return None
    t = np.cross(p3 - p1, d2) / denom
    u = np.cross(p3 - p1, d1) / denom
    if 0 <= t <= 1 and 0 <= u <= 1:
        return p1 + t * d1
    return None


_INTERSECTIONS_CACHE = None
def _detect_intersections(roads):
    global _INTERSECTIONS_CACHE
    if _INTERSECTIONS_CACHE is not None:
        return _INTERSECTIONS_CACHE
    cl = [r["centerline"] for r in roads]
    pts = []
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            for a in range(len(cl[i]) - 1):
                for b in range(len(cl[j]) - 1):
                    pt = _seg_intersect(cl[i][a], cl[i][a + 1], cl[j][b], cl[j][b + 1])
                    if pt is not None:
                        pts.append((pt[0], pt[1], i, j))

    groups = []
    for p in pts:
        placed = False
        for g in groups:
            if abs(p[0] - g[0][0]) < 3.0 and abs(p[1] - g[0][1]) < 3.0:
                g.append(p)
                placed = True
                break
        if not placed:
            groups.append([p])

    result = []
    for g in groups:
        center = (np.mean([p[0] for p in g]), np.mean([p[1] for p in g]))
        involved = tuple(sorted(set(idx for p in g for idx in (p[2], p[3]))))
        is_double_endpoint = True
        for p in g:
            for idx in (p[2], p[3]):
                poly = cl[idx]
                near = any(abs(p[0] - ep[0]) < 2.0 and abs(p[1] - ep[1]) < 2.0
                           for ep in (poly[0], poly[-1]))
                if not near:
                    is_double_endpoint = False
                    break
            if not is_double_endpoint:
                break
        if not is_double_endpoint:
            result.append((center, involved))

    _INTERSECTIONS_CACHE = result
    return result


def get_intersections(roads):
    return [pos for pos, _ in _detect_intersections(roads)]


def get_traffic_lights(roads):
    return [{"pos": pos, "roads": rds} for pos, rds in _detect_intersections(roads)]


def get_entries(roads):
    entries = []
    for i, road in enumerate(roads):
        poly = road["centerline"]
        for end_idx, direction in [(0, +1), (-1, -1)]:
            ep = poly[end_idx]
            r, c = ep
            at_edge = r < 3 or r > GRID_SIZE - 4 or c < 3 or c > GRID_SIZE - 4
            if not at_edge:
                continue
            # The endpoint must not lie on another road's centerline (otherwise it is an intersection/merge, not a boundary entry)
            on_other = False
            for j, other in enumerate(roads):
                if j == i:
                    continue
                for a in range(len(other["centerline"]) - 1):
                    d, _ = _point_segment_dist(ep, other["centerline"][a],
                                               other["centerline"][a + 1])
                    if d < 1.5:
                        on_other = True
                        break
                if on_other:
                    break
            if not on_other:
                entries.append((i, direction, (r, c)))

    return entries


_LANE_CACHE = None
def build_road_lane_centers(roads):
    global _LANE_CACHE
    if _LANE_CACHE is not None:
        return _LANE_CACHE

    lane = np.zeros((GRID_SIZE, GRID_SIZE, 2), dtype=np.float32)
    drivable = np.zeros((GRID_SIZE, GRID_SIZE, 1), dtype=np.float32)

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            best_lane_dist = float('inf')
            best_lane_pos = (0.0, 0.0)
            for road in roads:
                offsets = _lane_offsets(road["lanes_per_dir"], road["two_way"])
                half = max(abs(o) for o in offsets) + 0.5
                for i in range(len(road["centerline"]) - 1):
                    d, proj = _point_segment_dist((r, c), road["centerline"][i],
                                                  road["centerline"][i + 1])
                    if d > half + 0.01:
                        continue
                    drivable[r, c, 0] = 1.0
                    dr = road["centerline"][i + 1][0] - road["centerline"][i][0]
                    dc = road["centerline"][i + 1][1] - road["centerline"][i][1]
                    norm = np.hypot(dr, dc) + 1e-9
                    normal = (-dc / norm, dr / norm)
                    side = (r - proj[0]) * normal[0] + (c - proj[1]) * normal[1]
                    signed = side * d
                    nearest = min(offsets, key=lambda o: abs(o - signed))
                    lr = proj[0] + nearest * normal[0]
                    lc = proj[1] + nearest * normal[1]
                    lane_dist = np.hypot(r - lr, c - lc)
                    if lane_dist < best_lane_dist:
                        best_lane_dist = lane_dist
                        best_lane_pos = (lr, lc)
            if best_lane_dist < float('inf'):
                lane[r, c, 0] = best_lane_pos[0] / GRID_SIZE
                lane[r, c, 1] = best_lane_pos[1] / GRID_SIZE

    _LANE_CACHE = (lane, drivable)
    return _LANE_CACHE


S0 = 5.0       # Minimum Spacing (m)
T_HW = 1.5     # Safety Time Interval (s)
A_MAX = 2.0    # Maximum Acceleration (m/s²)
B_COMFORT = 3.0  # comfortable braking deceleration (m/s²)

def idm_acceleration(v, delta_v, gap, v_desired):
    """
    IDM(Intelligent Driver Model)  Acceleration Calculation
    a = a_max * [1 - (v/v0)^4 - (s*(v,Δv)/gap)^2]
    s* = s0 + v*T + v*Δv/(2*sqrt(a*b))
    """
    s_star = S0 + v * T_HW + v * delta_v / (2 * np.sqrt(A_MAX * B_COMFORT))
    s_star = np.maximum(s_star, S0)
    acc = A_MAX * (1 - (v / max(v_desired, 1e-6)) ** 4 - (s_star / max(gap, 1e-6)) ** 2)
    if acc > A_MAX:
        return A_MAX
    if acc < -B_COMFORT:
        return -B_COMFORT
    return acc


# Vehicle generation

def _road_path(roads, road_idx, direction):
    pts = roads[road_idx]["centerline"]
    return pts if direction > 0 else pts[::-1]


def _poly_interp(poly, t):
    t = max(0.0, min(float(t), len(poly) - 1.0))
    i = int(t)
    if i >= len(poly) - 1:
        i = len(poly) - 2
    frac = t - i
    p = poly[i] + frac * (poly[i + 1] - poly[i])
    d = poly[i + 1] - poly[i]
    norm = np.hypot(d[0], d[1]) + 1e-9
    tangent = d / norm
    normal = np.array([-tangent[1], tangent[0]])
    return p, tangent, normal


def _nearest_poly_t(poly, pt):
    best_t, best_d = 0.0, float('inf')
    for i in range(len(poly) - 1):
        d, proj = _point_segment_dist(pt, poly[i], poly[i + 1])
        seg_len = np.hypot(poly[i + 1][0] - poly[i][0], poly[i + 1][1] - poly[i][1])
        frac = np.hypot(proj[0] - poly[i][0], proj[1] - poly[i][1]) / (seg_len + 1e-9)
        t = i + frac
        if d < best_d:
            best_d, best_t = d, t
    return best_t


def _dest_to_road_dist(dest, centerline):
    """Shortest distance from the destination to a road's centerline"""
    best = float('inf')
    for i in range(len(centerline) - 1):
        d, _ = _point_segment_dist(dest, centerline[i], centerline[i + 1])
        if d < best:
            best = d
    return best


def _spawn_lane(road):
    n = road["lanes_per_dir"]
    if road["two_way"]:
        sign = +1 if LEFT_HAND else -1
        offsets = [sign * (k + 0.5) for k in range(n)]
    else:
        offsets = [k - (n - 1) / 2.0 for k in range(n)]
    return float(np.random.choice(offsets))


def _find_lead(ego, vehicles):
    best_gap = float('inf')
    best_lead = None
    for v in vehicles:
        if v is ego or v["arrived"]:
            continue
        if v["road"] != ego["road"] or v["direction"] != ego["direction"]:
            continue
        if abs(v["lane"] - ego["lane"]) > 0.4:   # Do not follow in different lanes
            continue
        # wp_idx always increases (_road_path is already ordered by direction); the larger one is ahead
        gap_idx = v["wp_idx"] - ego["wp_idx"]
        if gap_idx <= 0:
            continue
        gap_cells = np.hypot(v["row"] - ego["row"], v["col"] - ego["col"])
        if gap_cells < best_gap:
            best_gap = gap_cells
            best_lead = v
    return best_lead, best_gap


def simulate_trajectory(total_steps=70, seed=None):
    if seed is not None:
        np.random.seed(seed)
    roads = get_road_network()
    lane_centers, drivable = build_road_lane_centers(roads)
    lights = get_traffic_lights(roads)
    entries = get_entries(roads)

    # Random control parameters
    light_cycles = {i: int(np.random.choice([40, 60, 80])) for i in range(len(lights))}
    limit_approach = np.random.choice([50.0, 60.0, 70.0]) / 3.6
    max_limit_mps = 70.0 / 3.6
    arrival_rate = np.random.choice([0.1, 0.2, 0.3, 0.4, 0.5])

    vehicles = []
    vehicle_counter = 0
    vehicle_tracks = {}
    next_spawn_step = {i: 0 for i in range(len(entries))}
    mean_spawn_gap = 1.0 / (arrival_rate * DT + 1e-8)

    trajectory = np.zeros((total_steps, GRID_SIZE, GRID_SIZE, TOTAL_FEAT_DIM),
                          dtype=np.float32)
    for t in range(total_steps):
        trajectory[t, :, :, 9] = lane_centers[:, :, 0]
        trajectory[t, :, :, 10] = lane_centers[:, :, 1]
        trajectory[t, :, :, 11] = drivable[:, :, 0]

    for t in range(total_steps):
        for e_idx, (road_idx, direction, _) in enumerate(entries):
            if t >= next_spawn_step[e_idx]:
                # Entry occupancy check to avoid overlap
                entry_pt = _road_path(roads, road_idx, direction)[0]
                entry_blocked = any(
                    np.hypot(v["row"] - entry_pt[0], v["col"] - entry_pt[1]) < 5.0
                    for v in vehicles)
                if entry_blocked:
                    next_spawn_step[e_idx] = t + 1
                    continue
                inter_arrival = np.random.exponential(mean_spawn_gap)
                next_spawn_step[e_idx] = t + max(1, int(np.round(inter_arrival)))
                road = roads[road_idx]
                lane = _spawn_lane(road)
                poly = _road_path(roads, road_idx, direction)
                center, tangent, normal = _poly_interp(poly, 0.0)
                spawn_row = center[0] + lane * normal[0]
                spawn_col = center[1] + lane * normal[1]
                # Destination: randomly choose any entry (including the same road; vehicles can go straight or turn), excluding the current entry
                dest_idx = np.random.randint(len(entries))
                while dest_idx == e_idx:
                    dest_idx = np.random.randint(len(entries))
                dest = entries[dest_idx]
                vid = vehicle_counter
                vehicle_counter += 1
                vehicles.append({
                    "id": vid,
                    "row": spawn_row,
                    "col": spawn_col,
                    "speed": np.random.uniform(3.0, 8.0),
                    "road": road_idx,
                    "direction": direction,
                    "lane": lane,
                    "wp_idx": 0.0,
                    "dest": (dest[2][0], dest[2][1]),
                    "turn_count": 0,
                    "arrived": False,
                })
                vehicle_tracks[vid] = {'entry': f'road{road_idx}', 'positions': []}


        for v in vehicles:
            if v["arrived"]:
                continue
            poly = _road_path(roads, v["road"], v["direction"])
            center, tangent, normal = _poly_interp(poly, v["wp_idx"])

            move_dr = tangent[0]
            move_dc = tangent[1]

            # Traffic light
            red = False
            dist_light = 1e9
            for li, light in enumerate(lights):
                if v["road"] not in light["roads"]:
                    continue
                lr, lc = light["pos"]
                d = np.hypot(v["row"] - lr, v["col"] - lc)
                if d < 4.0:  # Approaching the intersection
                    cycle = light_cycles[li]
                    half = cycle // 2
                    phase_green = light["roads"][0] if (t % cycle) < half else light["roads"][1]
                    if v["road"] != phase_green:
                        red = True
                        dist_light = d
                        break

            # IDM
            lead, gap_cells = _find_lead(v, vehicles)
            if lead is not None:
                gap_m = gap_cells * CELL_SIZE
                delta_v = v["speed"] - lead["speed"]
            else:
                gap_m = 1000.0
                delta_v = 0.0
            acc = idm_acceleration(v["speed"], delta_v, gap_m, limit_approach)
            if red:
                acc_stop = idm_acceleration(v["speed"], v["speed"],
                                            dist_light * CELL_SIZE, 0.0)
                acc = min(acc, acc_stop)

            v["speed"] = max(0.0, v["speed"] + acc * DT)

            v["wp_idx"] += v["speed"] * DT / CELL_SIZE
            new_center, _, new_normal = _poly_interp(poly, v["wp_idx"])
            v["row"] = new_center[0] + v["lane"] * new_normal[0]
            v["col"] = new_center[1] + v["lane"] * new_normal[1]

            if v["turn_count"] < 2:
                for li, light in enumerate(lights):
                    if v["road"] not in light["roads"]:
                        continue
                    lr, lc = light["pos"]
                    if np.hypot(v["row"] - lr, v["col"] - lc) < 2.5:
                        # Do not turn on a red light (running a red light is forbidden)
                        cycle = light_cycles[li]
                        half = cycle // 2
                        phase_green = light["roads"][0] if (t % cycle) < half else light["roads"][1]
                        if v["road"] != phase_green:
                            break
                        other_road = light["roads"][0] if light["roads"][1] == v["road"] else light["roads"][1]
                        cur_dist = _dest_to_road_dist(v["dest"], roads[v["road"]]["centerline"])
                        other_dist = _dest_to_road_dist(v["dest"], roads[other_road]["centerline"])
                        if other_dist < cur_dist and np.random.random() < 0.7:
                            v["road"] = other_road
                            new_poly = roads[other_road]["centerline"]
                            d0 = np.hypot(v["dest"][0] - new_poly[0][0], v["dest"][1] - new_poly[0][1])
                            d1 = np.hypot(v["dest"][0] - new_poly[-1][0], v["dest"][1] - new_poly[-1][1])
                            if roads[other_road]["two_way"]:
                                v["direction"] = +1 if d1 < d0 else -1
                            else:
                                v["direction"] = +1   # A one-way road can only be traveled forward
                            other_path = _road_path(roads, other_road, v["direction"])
                            # Pass through the intersection (offset 2 cells forward) to avoid turning again immediately in the next frame
                            v["wp_idx"] = _nearest_poly_t(other_path, (lr, lc)) + 2.0
                            v["lane"] = _spawn_lane(roads[other_road])
                            v["turn_count"] += 1
                            break

            # Reached the destination
            dr, dc = v["dest"]
            if np.hypot(v["row"] - dr, v["col"] - dc) < 3.0:
                v["arrived"] = True

            if v["wp_idx"] >= len(_road_path(roads, v["road"], v["direction"])) - 0.5:
                v["arrived"] = True

        vehicles = [v for v in vehicles if not v["arrived"]]

        # Data output
        for v in vehicles:
            cell_r = int(np.clip(v["row"], 0, GRID_SIZE - 1))
            cell_c = int(np.clip(v["col"], 0, GRID_SIZE - 1))

            # Velocity direction = tangent along the road
            poly = _road_path(roads, v["road"], v["direction"])
            _, tangent, _ = _poly_interp(poly, v["wp_idx"])
            v_dr = tangent[0]
            v_dc = tangent[1]

            lim_ratio = limit_approach / max_limit_mps
            # Signal state: red/green of the vehicle's road at the nearest intersection
            sig = 1.0
            for li, light in enumerate(lights):
                if v["road"] not in light["roads"]:
                    continue
                lr, lc = light["pos"]
                if np.hypot(v["row"] - lr, v["col"] - lc) < 10.0:
                    cycle = light_cycles[li]
                    half = cycle // 2
                    phase_green = light["roads"][0] if (t % cycle) < half else light["roads"][1]
                    sig = 1.0 if v["road"] == phase_green else 0.0
                    break

            trajectory[t, cell_r, cell_c, 0] = v["row"] / GRID_SIZE
            trajectory[t, cell_r, cell_c, 1] = v["col"] / GRID_SIZE
            trajectory[t, cell_r, cell_c, 2] = v["speed"] * v_dr / MAX_SPEED
            trajectory[t, cell_r, cell_c, 3] = v["speed"] * v_dc / MAX_SPEED
            trajectory[t, cell_r, cell_c, 4] = lim_ratio
            trajectory[t, cell_r, cell_c, 5] = sig
            dr, dc = v["dest"]
            trajectory[t, cell_r, cell_c, 6] = (dr - v["row"]) / GRID_SIZE
            trajectory[t, cell_r, cell_c, 7] = (dc - v["col"]) / GRID_SIZE
            dest_angle = np.arctan2(dc - v["col"], dr - v["row"])
            vel_angle = np.arctan2(v_dc, v_dr)
            turn_angle = dest_angle - vel_angle
            if turn_angle > np.pi:
                turn_angle -= 2 * np.pi
            if turn_angle < -np.pi:
                turn_angle += 2 * np.pi
            trajectory[t, cell_r, cell_c, 8] = turn_angle / np.pi
            trajectory[t, cell_r, cell_c, 9] = lane_centers[cell_r, cell_c, 0]
            trajectory[t, cell_r, cell_c, 10] = lane_centers[cell_r, cell_c, 1]
            trajectory[t, cell_r, cell_c, 11] = drivable[cell_r, cell_c, 0]

            vehicle_tracks[v["id"]]['positions'].append(
                (t, v["row"], v["col"],
                 v["speed"] * v_dr / MAX_SPEED, v["speed"] * v_dc / MAX_SPEED))

    return trajectory, vehicle_tracks


def generate_dataset(n_trajectories, total_steps=None, seed_offset=0, return_tracks=False):
    if total_steps is None:
        total_steps = HIST_STEPS + PRED_STEPS + 20

    window_len = HIST_STEPS + PRED_STEPS
    max_windows_per_traj = total_steps - window_len
    all_inputs = []
    all_labels = []
    all_tracks = [] if return_tracks else None
    all_t_starts = [] if return_tracks else None
    for traj_idx in range(n_trajectories):
        seed = seed_offset + traj_idx
        traj, tracks = simulate_trajectory(total_steps=total_steps, seed=seed)
        for t_start in range(max_windows_per_traj):
            inp = traj[t_start : t_start + HIST_STEPS]
            lbl = traj[t_start + HIST_STEPS : t_start + HIST_STEPS + PRED_STEPS, :, :, :VEHICLE_DIM]
            if np.all(np.abs(inp[:, :, :, :VEHICLE_DIM]) < 1e-8):
                continue
            all_inputs.append(inp)
            all_labels.append(lbl)
            if return_tracks:
                win_tracks = {}
                t_end = t_start + window_len
                for vid, vt in tracks.items():
                    pos = [p for p in vt['positions'] if t_start <= p[0] < t_end]
                    if pos:
                        win_tracks[vid] = {'entry': vt['entry'], 'positions': pos}
                all_tracks.append(win_tracks)
                all_t_starts.append(t_start)

    if len(all_inputs) == 0:
        raise RuntimeError("No valid window has been generated")
    inputs = torch.tensor(np.array(all_inputs), dtype=torch.float32)
    labels = [torch.tensor(lbl, dtype=torch.float32) for lbl in all_labels]
    if return_tracks:
        return inputs, labels, all_tracks, all_t_starts
    return inputs, labels

if __name__ == "__main__":
    n_train = 2000
    n_validation = 200
    train_inputs, train_labels = generate_dataset(
        n_trajectories=2000, seed_offset=0
    )
    print(f"The training set has been generated ({n_train} trajectories)")
    val_inputs, val_labels = generate_dataset(
        n_trajectories=200, seed_offset=2000
    )
    print(f"The validation set has been generated ({n_validation} trajectories)")
    print(f"training set: inputs {list(train_inputs.shape)}, labels {list(train_labels.shape)}")
    print(f"Validation set: inputs {list(val_inputs.shape)}, labels {list(val_labels.shape)}")

