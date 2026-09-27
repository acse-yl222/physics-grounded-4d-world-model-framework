"""
Intersection Simulation Dataset
"""
import numpy as np
import torch
import sys
import os
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configs.default import (
    INTERSECTION_CENTER, ROAD_HALF_WIDTH, SIGNAL_CYCLE,
    TURN_PROB_STRAIGHT, TURN_PROB_LEFT, TURN_PROB_RIGHT,
    TURN_RADIUS_RIGHT, TURN_RADIUS_LEFT, GRID_SIZE,
    CELL_SIZE, MAX_SPEED, DT, ARRIVAL_RATE,TOTAL_FEAT_DIM,
    VEHICLE_DIM, HIST_STEPS, PRED_STEPS
)


def get_intersection_geometry():
    """
    Define all geometric parameters of a four-way intersection
    """
    ctr_row, ctr_col = INTERSECTION_CENTER
    hw = ROAD_HALF_WIDTH
    signal_half = SIGNAL_CYCLE // 2

    h_road_rows = (ctr_row - hw, ctr_row + hw - 1)  # [26, 29]
    v_road_cols = (ctr_col - hw, ctr_col + hw - 1)  # [26, 29]

    entries = {
        "south": {
            "spawn_rows": (50, 55),
            "spawn_cols": (28, 29),
            "direction": (-1, 0),   # north
            "stop_line_row": h_road_rows[1] + 1,
            "stop_line_range": (h_road_rows[1] + 1, h_road_rows[1] + 2),
        },
        "north": {
            "spawn_rows": (0, 5),
            "spawn_cols": (26, 27),
            "direction": (1, 0),
            "stop_line_row": h_road_rows[0] - 1,
            "stop_line_range": (h_road_rows[0] - 2, h_road_rows[0] - 1),
        },
        "east": {
            "spawn_cols": (50, 55),
            "spawn_rows": (26, 27),
            "direction": (0, -1),
            "stop_line_col": v_road_cols[1] + 1,
            "stop_line_range": (v_road_cols[1] + 1, v_road_cols[1] + 2),
        },
        "west": {
            "spawn_cols": (0, 5),
            "spawn_rows": (28, 29),
            "direction": (0, 1),
            "stop_line_col": v_road_cols[0] - 1,
            "stop_line_range": (v_road_cols[0] - 2, v_road_cols[0] - 1),
        },
    }

    exits = {
        "north": (54, 28),
        "south": (1, 27),
        "east":  (28, 54),
        "west":  (27, 1),
    }

    turn_map = {
        "south": {"straight": "north", "left": "west",  "right": "east"},
        "north": {"straight": "south", "left": "east",  "right": "west"},
        "east":  {"straight": "west",  "left": "south", "right": "north"},
        "west":  {"straight": "east",  "left": "north", "right": "south"},
    }

    return {
        "h_road_rows": h_road_rows,
        "v_road_cols": v_road_cols,
        "entries": entries,
        "exits": exits,
        "turn_map": turn_map,
        "signal_half": signal_half,
    }


def build_lane_centers(geometry):
    """
    Precompute the lane centerline for each cell (ch9=row, ch10=col, normalized)
    Set values to 0 for the intersection core area and non-road surfaces
    """
    hr0, hr1 = geometry['h_road_rows']  # [26, 29]
    vc0, vc1 = geometry['v_road_cols']  # [26, 29]
    lane = np.zeros((GRID_SIZE, GRID_SIZE, 2), dtype=np.float32)
    mid_h = hr0 + (hr1 - hr0 + 1) // 2   # First line of the second paragraph (28)
    mid_v = vc0 + (vc1 - vc0 + 1) // 2   # First column of the right half (28)

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            on_h = hr0 <= r <= hr1
            on_v = vc0 <= c <= vc1
            if on_h and on_v:
                continue
            if on_h:
                if r < mid_h:
                    center_r = (hr0 + mid_h - 1) / 2.0
                else:
                    center_r = (mid_h + hr1) / 2.0
                lane[r, c, 0] = center_r / GRID_SIZE
                lane[r, c, 1] = c / GRID_SIZE

            elif on_v:
                if c < mid_v:
                    center_c = (vc0 + mid_v - 1) / 2.0
                else:
                    center_c = (mid_v + vc1) / 2.0
                lane[r, c, 0] = r / GRID_SIZE
                lane[r, c, 1] = center_c / GRID_SIZE

    return lane


def assign_vehicle_mission(entry, geometry, perturb_range=2):
    """
    Randomly assign turning tasks and destinations to vehicles entering from designated entrances
    """
    r = np.random.random()
    if r < TURN_PROB_STRAIGHT:
        turn_type = "straight"
    elif r < TURN_PROB_STRAIGHT + TURN_PROB_LEFT:
        turn_type = "left"
    else:
        turn_type = "right"

    exit_name = geometry["turn_map"][entry][turn_type]
    base_row, base_col = geometry["exits"][exit_name]
    # Add random perturbations to simulate individual differences in parking positions at the same exit
    d_row = np.random.randint(-perturb_range, perturb_range + 1)
    d_col = np.random.randint(-perturb_range, perturb_range + 1)
    dest_row = np.clip(base_row + d_row, 0, GRID_SIZE - 1)
    dest_col = np.clip(base_col + d_col, 0, GRID_SIZE - 1)
    if turn_type == "straight":
        radius = None
    elif turn_type == "right":
        radius = TURN_RADIUS_RIGHT
    else:
        radius = TURN_RADIUS_LEFT
    return {
        "turn_type": turn_type,
        "exit_name": exit_name,
        "dest_cell": (int(dest_row), int(dest_col)),
        "radius": radius,
    }

def build_reference_path(entry, geometry, mission, num_waypoints=20):
    turn_type = mission["turn_type"]
    exit_name = mission["exit_name"]
    dest_row, dest_col = mission["dest_cell"]
    radius = mission["radius"]

    h_road_rows = geometry["h_road_rows"]
    v_road_cols = geometry["v_road_cols"]
    v_center = (v_road_cols[0] + v_road_cols[1]) / 2.0
    h_center = (h_road_rows[0] + h_road_rows[1]) / 2.0

    e = geometry["entries"][entry]
    spawn_r = (e["spawn_rows"][0] + e["spawn_rows"][1]) / 2.0
    spawn_c = (e["spawn_cols"][0] + e["spawn_cols"][1]) / 2.0

    # four road corners
    corners = {
        "SE": (h_road_rows[1], v_road_cols[1]),
        "SW": (h_road_rows[1], v_road_cols[0]),
        "NE": (h_road_rows[0], v_road_cols[1]),
        "NW": (h_road_rows[0], v_road_cols[0]),
    }

    if turn_type == "straight":
        if entry in ("south", "north"):
            start = (spawn_r, v_center)
        else:
            start = (h_center, spawn_c)
        end = (float(dest_row), float(dest_col))
        key_points = np.array([start, end])

    elif turn_type == "right":
        if entry == "south":
            cr, cc = corners["SE"]
            arc_start = (float(cr), float(cc - radius))              # (29, 27)
            arc_end   = (float(cr - radius), float(cc))              # (27, 29)
            angles = np.linspace(np.pi, np.pi / 2, num_waypoints // 3)
        elif entry == "north":
            cr, cc = corners["NW"]
            arc_start = (float(cr), float(cc + radius))              # (26, 28)
            arc_end   = (float(cr + radius), float(cc))              # (28, 26)
            angles = np.linspace(0, -np.pi / 2, num_waypoints // 3)
        elif entry == "east":
            cr, cc = corners["NE"]
            arc_start = (float(cr + radius), float(cc))              # (28, 29)
            arc_end   = (float(cr), float(cc - radius))              # (26, 27)
            angles = np.linspace(-np.pi / 2, 0, num_waypoints // 3)
        else:  # west
            cr, cc = corners["SW"]
            arc_start = (float(cr - radius), float(cc))              # (27, 26)
            arc_end   = (float(cr), float(cc + radius))              # (29, 28)
            angles = np.linspace(np.pi / 2, np.pi, num_waypoints // 3)
        arc_pts = np.column_stack([
            cr - radius * np.cos(angles),
            cc + radius * np.sin(angles),
        ])

        approach_start = (spawn_r if entry in ("south", "north") else h_center,
                          v_center if entry in ("south", "north") else spawn_c)
        exit_end = (float(dest_row), float(dest_col))
        key_points = np.vstack([
            [approach_start],
            [arc_start],
            arc_pts,
            [arc_end],
            [exit_end],
        ])

    else:
        if entry == "south":
            cr, cc = corners["SW"]
            arc_start = (float(cr), float(cc + radius))              # (29, 29)
            arc_end   = (float(cr - radius), float(cc))              # (26, 26)
            angles = np.linspace(np.pi, np.pi / 2, num_waypoints // 3)
        elif entry == "north":
            cr, cc = corners["NE"]
            arc_start = (float(cr), float(cc - radius))              # (26, 26)
            arc_end   = (float(cr + radius), float(cc))              # (29, 29)
            angles = np.linspace(0, -np.pi / 2, num_waypoints // 3)
        elif entry == "east":
            cr, cc = corners["SE"]
            arc_start = (float(cr - radius), float(cc))              # (26, 29)
            arc_end   = (float(cr), float(cc - radius))              # (29, 26)
            angles = np.linspace(-np.pi / 2, 0, num_waypoints // 3)
        else:  # west
            cr, cc = corners["NW"]
            arc_start = (float(cr + radius), float(cc))              # (29, 26)
            arc_end   = (float(cr), float(cc + radius))              # (26, 29)
            angles = np.linspace(np.pi / 2, np.pi, num_waypoints // 3)

        arc_pts = np.column_stack([
            cr - radius * np.cos(angles),
            cc + radius * np.sin(angles),
        ])

        approach_start = (spawn_r if entry in ("south", "north") else h_center,
                          v_center if entry in ("south", "north") else spawn_c)
        exit_end = (float(dest_row), float(dest_col))
        key_points = np.vstack([
            [approach_start],
            [arc_start],
            arc_pts,
            [arc_end],
            [exit_end],
        ])
    # Uniform Interpolation
    diffs = np.diff(key_points, axis=0)
    seg_lengths = np.sqrt((diffs ** 2).sum(axis=1))
    cumulative = np.concatenate([[0.0], np.cumsum(seg_lengths)])
    total_length = cumulative[-1]
    t_uniform = np.linspace(0, total_length, num_waypoints)
    waypoints = np.zeros((num_waypoints, 2))
    for d in range(2):
        waypoints[:, d] = np.interp(t_uniform, cumulative, key_points[:, d])
    return waypoints

def get_vehicle_lane(vehicle, geometry):
    """
    Determine the road section and lane where the vehicle is currently located
    """
    row, col = vehicle["row"], vehicle["col"]
    entry_name = vehicle["entry"]
    entry_cfg = geometry["entries"][entry_name]
    dr, dc = entry_cfg["direction"]
    core_row_0, core_row_1 = geometry["h_road_rows"]
    core_col_0, core_col_1 = geometry["v_road_cols"]
    if dr != 0:         # south / north
        stop_pos = entry_cfg["stop_line_row"]
        along = row
        core_far = core_row_0 if dr < 0 else core_row_1
    else:
        stop_pos = entry_cfg["stop_line_col"]
        along = col
        core_far = core_col_0 if dc < 0 else core_col_1

    heading_toward_origin = (dr < 0 or dc < 0)

    if heading_toward_origin:
        if along > stop_pos:
            segment = "approach"
        elif along >= core_far:
            segment = "intersection"
        else:
            segment = "exit"
    else:
        if along < stop_pos:
            segment = "approach"
        elif along <= core_far:
            segment = "intersection"
        else:
            segment = "exit"
    lane_id = f"{entry_name}_{segment}"
    # Scope requiring response to traffic lights
    at_stop_line = abs(along - stop_pos) <= 10.0  # 10 cells × 3m = 30m red-light response zone

    return {
        "segment": segment,
        "lane_id": lane_id,
        "at_stop_line": at_stop_line,
    }

def find_lead_vehicle(ego, vehicles, geometry):
    """
    Find the closest vehicle ahead of the ego vehicle in the same lane
    """
    lane = get_vehicle_lane(ego, geometry)
    lane_id = lane["lane_id"]
    same_lane = [v for v in vehicles if v is not ego
                 and get_vehicle_lane(v, geometry)["lane_id"] == lane_id]
    if not same_lane:
        return None, None
    dr, dc = geometry["entries"][ego["entry"]]["direction"]
    ego_proj = ego["row"] * dr + ego["col"] * dc # The larger the value, the higher the priority
    best_gap = float("inf")
    best_lead = None
    for v in same_lane:
        v_proj = v["row"] * dr + v["col"] * dc
        forward_gap = v_proj - ego_proj
        if forward_gap > 0 and forward_gap < best_gap:
            best_gap = forward_gap
            best_lead = v
    return (best_lead, best_gap) if best_lead else (None, None)


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

def simulate_trajectory(total_steps=70, seed=None):
    if seed is not None:
        np.random.seed(seed)
    geometry = get_intersection_geometry()
    lane_centers = build_lane_centers(geometry)  # Precompute lane centerlines
    # Randomized control parameters
    signal_cycle = int(np.random.choice([40, 60, 80]))
    half_cycle = signal_cycle // 2
    limit_approach = np.random.choice([50.0, 60.0, 70.0]) / 3.6
    limit_intersection = np.random.choice([15.0, 25.0, 35.0, 45.0]) / 3.6
    max_limit_mps = 70.0 / 3.6  # update
    arrival_rate = np.random.choice([0.1, 0.2, 0.3, 0.4, 0.5])
    vehicles = []      # Active vehicles
    vehicle_counter = 0
    vehicle_tracks = {}  # {vid: {'entry': str, 'positions': [(t, row, col), ...]}}
    next_spawn_step = {entry: 0 for entry in geometry["entries"]}
    mean_spawn_gap = 1.0 / (arrival_rate * DT + 1e-8)
    trajectory = np.zeros((total_steps, GRID_SIZE, GRID_SIZE, TOTAL_FEAT_DIM),
                          dtype=np.float32)
    for t in range(total_steps):
        ns_green = (t % signal_cycle) < half_cycle
        # ew_green = not ns_green
        
        # Generate new vehicles
        for entry_name, entry_cfg in geometry["entries"].items():
            if t >= next_spawn_step[entry_name]:
                inter_arrival = np.random.exponential(mean_spawn_gap)
                next_spawn_step[entry_name] = t + max(1, int(np.round(inter_arrival)))
                spawn_row = np.random.uniform(*entry_cfg["spawn_rows"])
                spawn_col = np.random.uniform(*entry_cfg["spawn_cols"])
                init_speed = np.random.uniform(3.0, 8.0)
                dr, dc = entry_cfg["direction"]
                mission = assign_vehicle_mission(entry_name, geometry)
                ref_path = build_reference_path(entry_name, geometry, mission)
                vid = vehicle_counter
                vehicle_counter += 1
                vehicles.append({
                    "id":        vid,
                    "row":       spawn_row,
                    "col":       spawn_col,
                    "speed":     init_speed,
                    "dr":        dr,
                    "dc":        dc,
                    "entry":     entry_name,
                    "mission":   mission,
                    "ref_path":  ref_path,
                    "wp_idx":    0,
                    "arrived":   False,
                })
                vehicle_tracks[vid] = {'entry': entry_name, 'positions': []}
        # Update vehicle status
        for v in vehicles:
            if v["arrived"]:
                continue
            is_ns = v["entry"] in ("south", "north")
            green = ns_green if is_ns else not ns_green

            lane = get_vehicle_lane(v, geometry)
            segment = lane["segment"]

            desired_speed = limit_intersection if segment == "intersection" else limit_approach
            lead, gap_cells = find_lead_vehicle(v, vehicles, geometry)
            if lead is not None and gap_cells is not None:
                gap_m = gap_cells * CELL_SIZE
                delta_v = v["speed"] - lead["speed"]
            else:
                gap_m = 1000.0
                delta_v = 0.0
            acc = idm_acceleration(v["speed"], delta_v, gap_m, desired_speed)
            if lane["at_stop_line"] and not green:
                if is_ns:
                    stop_pos = geometry["entries"][v["entry"]]["stop_line_row"]
                    dist_stop = abs(v["row"] - stop_pos) * CELL_SIZE
                else:
                    stop_pos = geometry["entries"][v["entry"]]["stop_line_col"]
                    dist_stop = abs(v["col"] - stop_pos) * CELL_SIZE
                acc_stop = idm_acceleration(v["speed"], v["speed"], dist_stop, 0.0)
                acc = min(acc, acc_stop)
            v["speed"] = max(0.0, v["speed"] + acc * DT)
            # Update location
            if segment == "intersection":
                ref = v["ref_path"]
                wp_idx = v["wp_idx"]
                while wp_idx < len(ref) - 1:
                    wp_r, wp_c = ref[wp_idx]
                    # Determine whether the current waypoint is behind
                    ahead = (wp_r - v["row"]) * v["dr"] + (wp_c - v["col"]) * v["dc"]
                    if ahead > 0:
                        break
                    wp_idx += 1
                v["wp_idx"] = wp_idx

                # Move toward the target waypoint
                target_r, target_c = ref[min(wp_idx, len(ref) - 1)]
                dir_r = target_r - v["row"]
                dir_c = target_c - v["col"]
                norm = np.sqrt(dir_r ** 2 + dir_c ** 2) + 1e-8
                move_dr = dir_r / norm
                move_dc = dir_c / norm
                v["row"] += v["speed"] * move_dr * DT / CELL_SIZE
                v["col"] += v["speed"] * move_dc * DT / CELL_SIZE
                # Update the actual movement direction 
                # fix the bug where dr/dc remains the entry direction after turning
                v["dr"] = move_dr
                v["dc"] = move_dc
                # # exit
                # if wp_idx >= len(ref) - 1:
                #     dist_final = np.sqrt((v["row"] - ref[-1][0]) ** 2
                #                          + (v["col"] - ref[-1][1]) ** 2)
                #     if dist_final < 3.0:
                #         # The direction points to the final destination
                #         v["dr"] = 1 if ref[-1][0] > ref[0][0] else -1
                #         v["dc"] = 0
            else:
                # Go straight
                v["row"] += v["speed"] * v["dr"] * DT / CELL_SIZE
                v["col"] += v["speed"] * v["dc"] * DT / CELL_SIZE

            dest_r, dest_c = v["mission"]["dest_cell"]
            dist_to_dest = np.sqrt((v["row"] - dest_r) ** 2 + (v["col"] - dest_c) ** 2)
            if dist_to_dest < 3.0:  # 9m
                v["arrived"] = True  # Whether to reach the destination
        
        vehicles = [v for v in vehicles if not v["arrived"]]  # remove arrived vehicles

        for v in vehicles:
            cell_r = int(np.clip(v["row"], 0, GRID_SIZE - 1))
            cell_c = int(np.clip(v["col"], 0, GRID_SIZE - 1))
            lane = get_vehicle_lane(v, geometry)
            in_intersection = (lane["segment"] == "intersection")
            # Control
            # Unified normalization: speed limit / maximum speed limit, applicable to both road sections and intersections
            current_limit = limit_intersection if in_intersection else limit_approach
            lim_ratio = current_limit / max_limit_mps
            is_ns = v["entry"] in ("south", "north")
            sig = 1.0 if (ns_green if is_ns else not ns_green) else 0.0

            trajectory[t, cell_r, cell_c, 0] = v["row"] / GRID_SIZE
            trajectory[t, cell_r, cell_c, 1] = v["col"] / GRID_SIZE
            trajectory[t, cell_r, cell_c, 2] = v["speed"] * v["dr"] / MAX_SPEED
            trajectory[t, cell_r, cell_c, 3] = v["speed"] * v["dc"] / MAX_SPEED
            trajectory[t, cell_r, cell_c, 4] = lim_ratio
            trajectory[t, cell_r, cell_c, 5] = sig
            trajectory[t, cell_r, cell_c, 6] = (v["mission"]["dest_cell"][0] - v["row"]) / GRID_SIZE
            trajectory[t, cell_r, cell_c, 7] = (v["mission"]["dest_cell"][1] - v["col"]) / GRID_SIZE
            dest_dr = v["mission"]["dest_cell"][0] - v["row"]
            dest_dc = v["mission"]["dest_cell"][1] - v["col"]
            dest_angle = np.arctan2(dest_dc, dest_dr)
            vel_angle = np.arctan2(v["dc"], v["dr"])
            turn_angle = dest_angle - vel_angle
            if turn_angle > np.pi:
                turn_angle -= 2 * np.pi
            if turn_angle < -np.pi:
                turn_angle += 2 * np.pi
            trajectory[t, cell_r, cell_c, 8] = turn_angle / np.pi
            trajectory[t, cell_r, cell_c, 9] = lane_centers[cell_r, cell_c, 0]
            trajectory[t, cell_r, cell_c, 10] = lane_centers[cell_r, cell_c, 1]

            vehicle_tracks[v["id"]]['positions'].append(
                (t, v["row"], v["col"],
                 v["speed"] * v["dr"] / MAX_SPEED, v["speed"] * v["dc"] / MAX_SPEED))

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
        n_trajectories=200, seed_offset=2000    # Seed offset, no duplication with the training set
    )
    print(f"The validation set has been generated ({n_validation} trajectories)")
    print(f"training set: inputs {list(train_inputs.shape)}, labels {list(train_labels.shape)}")
    print(f"Validation set: inputs {list(val_inputs.shape)}, labels {list(val_labels.shape)}")

