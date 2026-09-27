from common.runtime import trial_root
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.animation import FuncAnimation
import numpy as np
import torch
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from configs.default import (
    GRID_SIZE, CELL_SIZE, DT, HIST_STEPS, PRED_STEPS,
    VEHICLE_DIM, TOTAL_FEAT_DIM, EVAL_SEED_OFFSET,
)
from evaluate import load_model, find_latest_model
from data.generate_complex import (
    get_road_network, build_road_lane_centers, get_lane_centerlines,
    simulate_trajectory,
)


def draw_network_base(ax):
    """Draw the complex road network (identical style to the other visualisations)."""
    roads = get_road_network()
    lane, drivable = build_road_lane_centers(roads)
    lane_lines = get_lane_centerlines(roads)
    road_cmap = ListedColormap(['white', '#EAEAEA'])

    ax.imshow(drivable[:, :, 0], cmap=road_cmap, origin='upper',
              vmin=0, vmax=1, aspect='equal', zorder=0)
    for poly, direction in lane_lines:
        color = '#1F77B4' if direction > 0 else '#D62728'
        ax.plot(poly[:, 1], poly[:, 0], color=color, linewidth=0.5,
                alpha=0.4, zorder=1)

    ax.set_xlim(0, GRID_SIZE)
    ax.set_ylim(GRID_SIZE, 0)
    ax.set_xticks(np.arange(0, GRID_SIZE, 10))
    ax.set_yticks(np.arange(0, GRID_SIZE, 10))
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.15, linewidth=0.5)
    ax.set_aspect('equal')


def anchor_to_gt_vid(tracks, t_last):
    """Map each occupied cell (r, c) at t_last to a ground-truth vehicle id."""
    mapping = {}
    for vid, vt in tracks.items():
        for (t, row, col, vd, vc) in vt['positions']:
            if t == t_last:
                r = int(np.clip(row, 0, GRID_SIZE - 1))
                c = int(np.clip(col, 0, GRID_SIZE - 1))
                mapping[(r, c)] = vid
    return mapping


def gt_future_positions(tracks, gt_vid, t_last, horizon_steps):
    """Normalised ground-truth positions of one vehicle over the horizon (None if absent)."""
    pos_by_t = {t: (row / GRID_SIZE, col / GRID_SIZE)
                for (t, row, col, vd, vc) in tracks[gt_vid]['positions']}
    out = []
    for h in range(horizon_steps):
        t = t_last + 1 + h
        out.append(pos_by_t.get(t))
    return out


def rolling_predict(model, device, W, static, vehicles, n_rolls, log):
    """Roll the window forward n_rolls times; append each predicted position to vehicles."""
    for roll in range(n_rolls):
        grid = torch.tensor(W, dtype=torch.float32, device=device)
        pred_grid = model.predict_full_grid(grid, n_iters=1)  # (PRED_STEPS, G, G, VEHICLE_DIM)
        pg = pred_grid.cpu().numpy()

        new_frames = np.zeros((PRED_STEPS, GRID_SIZE, GRID_SIZE, TOTAL_FEAT_DIM),
                              dtype=np.float32)
        new_frames[:, :, :, 9:12] = static[None, :, :, :]  # lane centre + drivable (static)

        for v in vehicles:
            r, c = v['cell']
            for k in range(PRED_STEPS):
                pos_n = pg[k, r, c, :2]                     # normalised absolute position
                vel_n = pg[k, r, c, 2:4]                    # normalised velocity
                nr = int(np.clip(round(pos_n[0] * GRID_SIZE), 0, GRID_SIZE - 1))
                nc = int(np.clip(round(pos_n[1] * GRID_SIZE), 0, GRID_SIZE - 1))

                # destination offset (ch6-7)
                d6 = v['dest_row_n'] - pos_n[0]
                d7 = v['dest_col_n'] - pos_n[1]
                # turn angle (ch8): angle-to-destination minus velocity heading
                dest_ang = np.arctan2(v['dest_col_n'] - pos_n[1],
                                      v['dest_row_n'] - pos_n[0])
                vel_ang = np.arctan2(vel_n[1], vel_n[0])
                ta = dest_ang - vel_ang
                ta = (ta + np.pi) % (2 * np.pi) - np.pi       # wrap to [-pi, pi]

                new_frames[k, nr, nc, 0] = pos_n[0]
                new_frames[k, nr, nc, 1] = pos_n[1]
                new_frames[k, nr, nc, 2] = vel_n[0]
                new_frames[k, nr, nc, 3] = vel_n[1]
                new_frames[k, nr, nc, 4] = v['lim']
                new_frames[k, nr, nc, 5] = v['sig']           # frozen (open-loop)
                new_frames[k, nr, nc, 6] = d6
                new_frames[k, nr, nc, 7] = d7
                new_frames[k, nr, nc, 8] = ta / np.pi

                v['pred_pos'].append(pos_n.copy())
                if k == PRED_STEPS - 1:
                    v['cell'] = (nr, nc)                      # advance for next roll

        W = np.concatenate([W[PRED_STEPS:], new_frames], axis=0)
        log(f"  roll {roll + 1}/{n_rolls} done ({len(vehicles)} vehicles)")
    return W


def plot_trajectories(vehicles, tracks, t_start, t_last, output_path, sample_idx,
                      horizon_s, model_name):
    fig, ax = plt.subplots(figsize=(10, 10))
    draw_network_base(ax)

    for v in vehicles:
        color = v['color']
        vid = v['gt_vid']

        # history (ground truth)
        hist = [(row, col) for (t, row, col, vd, vc) in tracks[vid]['positions']
                if t_start <= t <= t_last]
        if len(hist) >= 2:
            ax.plot([p[1] for p in hist], [p[0] for p in hist], '-',
                    color=color, linewidth=2.0, alpha=0.8, zorder=4)

        # prediction (dashed, same colour)
        pred = v['pred_pos']
        if len(pred) >= 1:
            rows = [p[0] * GRID_SIZE for p in pred]
            cols = [p[1] * GRID_SIZE for p in pred]
            ax.plot(cols, rows, '--', color=color, linewidth=1.6, alpha=0.8, zorder=4)

        # ground-truth future (dark)
        gt = gt_future_positions(tracks, vid, t_last, len(pred))
        gt = [g for g in gt if g is not None]
        if len(gt) >= 1:
            ax.plot([g[1] * GRID_SIZE for g in gt], [g[0] * GRID_SIZE for g in gt],
                    '-', color='#333333', linewidth=1.8, alpha=0.7, zorder=3)

    legend_elements = [
        Line2D([0], [0], color='gray', linewidth=2.0, label='History'),
        Line2D([0], [0], color='gray', linewidth=1.6, linestyle='--', label='Prediction (rolled)'),
        Line2D([0], [0], color='#333333', linewidth=1.8, label='Ground truth'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=8, framealpha=0.9)
    ax.set_title(f'Long-horizon rolling | Sample {sample_idx} | {horizon_s:.0f}s | '
                 f'{len(vehicles)} vehicles | model {model_name}',
                 fontsize=12, fontweight='bold')
    fig.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close(fig)


def plot_ade_curve(ade_by_step, output_path, sample_idx, horizon_s):
    times = [(h + 1) * DT for h in range(len(ade_by_step))]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(times, ade_by_step, marker='o', linewidth=2, color='#E91E63')
    ax.set_xlabel('Horizon (s)')
    ax.set_ylabel('ADE (m)')
    ax.set_title(f'ADE vs horizon (rolling prediction) | Sample {sample_idx} | {horizon_s:.0f}s')
    ax.grid(True, alpha=0.3)
    for s in [3, 6, 9, 12, 15]:
        if s <= horizon_s:
            ax.axvline(s, color='gray', linestyle='--', alpha=0.4, linewidth=0.8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close(fig)


def animate_long_horizon(vehicles, tracks, t_start, t_last, horizon_steps,
                         horizon_s, sample_idx, model_name, output_path,
                         fps=4, dpi=130):
    """Animate the rolling prediction: history frames, then predicted frames (+ GT dots)."""
    H = HIST_STEPS
    P = horizon_steps

    # time-aligned positions per vehicle (absolute grid cells; None if absent)
    for v in vehicles:
        pos_by_t = {t: (row, col) for (t, row, col, vd, vc) in tracks[v['gt_vid']]['positions']}
        v['hist_cells'] = [pos_by_t.get(t) for t in range(t_start, t_last + 1)]
        v['pred_cells'] = [(p[0] * GRID_SIZE, p[1] * GRID_SIZE) for p in v['pred_pos']]
        v['gt_cells'] = [pos_by_t.get(t_last + 1 + h) for h in range(P)]

    fig, ax = plt.subplots(figsize=(8, 8))
    draw_network_base(ax)
    title = ax.set_title('', fontsize=11, fontweight='bold')

    def update(frame):
        for child in list(ax.get_children()):
            if hasattr(child, '_dynamic'):
                child.remove()
        if frame < H:
            t = frame
            title.set_text(f'Sample {sample_idx} | History t={t * DT:.1f}s')
            for v in vehicles:
                cells = v['hist_cells']
                if t < len(cells) and cells[t] is not None:
                    r, c = cells[t]
                    dot = ax.plot(c, r, 'o', color=v['color'], markersize=7, zorder=6)[0]
                    dot._dynamic = True
                    if t > 0:
                        seg = [p for p in cells[:t + 1] if p is not None]
                        if len(seg) >= 2:
                            line = ax.plot([p[1] for p in seg], [p[0] for p in seg], '-',
                                           color=v['color'], linewidth=2.0, alpha=0.7, zorder=4)[0]
                            line._dynamic = True
        else:
            k = frame - H
            title.set_text(f'Sample {sample_idx} | Prediction {(k + 1) * DT:.1f}s / {horizon_s:.0f}s')
            for v in vehicles:
                hist = [p for p in v['hist_cells'] if p is not None]
                if len(hist) >= 2:
                    line = ax.plot([p[1] for p in hist], [p[0] for p in hist], '-',
                                   color=v['color'], linewidth=1.0, alpha=0.3, zorder=3)[0]
                    line._dynamic = True
                pred = v['pred_cells']
                if k < len(pred):
                    seg = pred[:k + 1]
                    line = ax.plot([p[1] for p in seg], [p[0] for p in seg], '--',
                                   color=v['color'], linewidth=1.8, alpha=0.8, zorder=4)[0]
                    line._dynamic = True
                    dot = ax.plot(pred[k][1], pred[k][0], 's', color=v['color'],
                                  markersize=6, alpha=0.9, zorder=6)[0]
                    dot._dynamic = True
                gt = v['gt_cells']
                if k < len(gt) and gt[k] is not None:
                    gdot = ax.plot(gt[k][1], gt[k][0], 'o', color='#333333',
                                   markersize=5, alpha=0.7, zorder=5)[0]
                    gdot._dynamic = True

    ani = FuncAnimation(fig, update, frames=H + P, interval=1000 // fps, blit=False)
    ani.save(output_path, writer='pillow', fps=fps, dpi=dpi)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Long-horizon rolling prediction")
    parser.add_argument('--model', '-m', type=str, default=None,
                        help="Model date (default: latest in train/)")
    parser.add_argument('--sample', '-s', type=int, default=0,
                        help="Sample index (seed = EVAL_SEED_OFFSET + sample)")
    parser.add_argument('--horizon', type=float, default=12.0,
                        help="Total prediction horizon in seconds (default 12)")
    parser.add_argument('--t-start', type=int, default=None,
                        help="Starting timestep of the initial window (auto-picked if omitted)")
    parser.add_argument('--animate', '-a', action='store_true',
                        help="Generate a GIF animation instead of static plots")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device, args.model)
    model_name = os.path.basename(find_latest_model(args.model))

    horizon_steps = int(round(args.horizon / DT))
    if horizon_steps <= 0:
        raise ValueError("--horizon must be positive")
    n_rolls = (horizon_steps + PRED_STEPS - 1) // PRED_STEPS

    total_steps = max(70, HIST_STEPS + horizon_steps + 40)
    seed = EVAL_SEED_OFFSET + args.sample
    traj, tracks = simulate_trajectory(total_steps=total_steps, seed=seed)

    # pick t_start (max number of vehicles at the last history frame)
    if args.t_start is None:
        best_ts, best_cnt = 10, -1
        for ts in range(10, total_steps - HIST_STEPS - horizon_steps):
            occ = np.abs(traj[ts + HIST_STEPS - 1, :, :, :VEHICLE_DIM]).sum(-1) > 1e-6
            cnt = int(occ.sum())
            if cnt > best_cnt:
                best_cnt, best_ts = cnt, ts
        t_start = best_ts
    else:
        t_start = args.t_start

    t_last = t_start + HIST_STEPS - 1
    W = traj[t_start:t_start + HIST_STEPS].copy()
    occ = np.abs(W[-1, :, :, :VEHICLE_DIM]).sum(-1) > 1e-6
    anchors = [(int(r), int(c)) for r, c in zip(*np.nonzero(occ))]
    if not anchors:
        raise RuntimeError("No vehicle in the initial window; try another -s or --t-start")

    gt_vid_map = anchor_to_gt_vid(tracks, t_last)

    static = traj[0, :, :, 9:12].copy()  # lane centre + drivable (same every frame)

    vehicles = []
    for idx, (r, c) in enumerate(sorted(anchors)):
        last = W[-1, r, c]
        vehicles.append({
            'color': plt.cm.tab20(idx % 20),
            'cell': (r, c),
            'dest_row_n': last[0] + last[6],
            'dest_col_n': last[1] + last[7],
            'lim': last[4],
            'sig': last[5],
            'gt_vid': gt_vid_map.get((r, c)),
            'pred_pos': [],
        })

    print(f"Sample {args.sample} | t_start={t_start} | {len(vehicles)} vehicles | "
          f"horizon {args.horizon:.1f}s ({horizon_steps} steps, {n_rolls} rolls)")
    W = rolling_predict(model, device, W, static, vehicles, n_rolls, log=print)

    # clip predictions to the requested horizon
    for v in vehicles:
        v['pred_pos'] = v['pred_pos'][:horizon_steps]

    # ADE vs horizon (only vehicles with a matching GT track)
    ade_by_step = []
    for h in range(horizon_steps):
        errs = []
        for v in vehicles:
            if v['gt_vid'] is None:
                continue
            gt = gt_future_positions(tracks, v['gt_vid'], t_last, horizon_steps)[h]
            if gt is None:
                continue
            p = v['pred_pos'][h]
            errs.append(np.hypot(p[0] - gt[0], p[1] - gt[1]) * GRID_SIZE * CELL_SIZE)
        ade_by_step.append(np.mean(errs) if errs else np.nan)

    print("\nADE vs horizon:")
    step3 = int(round(3.0 / DT))  # steps per 3-second block
    for h in range(step3 - 1, horizon_steps, step3):
        print(f"  {(h + 1) * DT:>3.0f}s: {ade_by_step[h]:.2f} m")
    if not np.isnan(ade_by_step[-1]):
        print(f"  FDE @ {args.horizon:.1f}s: {ade_by_step[-1]:.2f} m")

    save_dir = str(trial_root('south_ken','traffic_prediction'))
    os.makedirs(save_dir, exist_ok=True)
    stem = f"long_horizon_s{args.sample:02d}_{args.horizon:.0f}s"

    if args.animate:
        anim_path = os.path.join(save_dir, f"{stem}_anim.gif")
        animate_long_horizon(vehicles, tracks, t_start, t_last, horizon_steps,
                             args.horizon, args.sample, model_name, anim_path)
        print(f"\nSaved animation: {anim_path}")
    else:
        traj_path = os.path.join(save_dir, f"{stem}.png")
        plot_trajectories(vehicles, tracks, t_start, t_last, traj_path,
                          args.sample, args.horizon, model_name)
        print(f"\nSaved trajectory plot: {traj_path}")

        ade_path = os.path.join(save_dir, f"{stem}_ade.png")
        plot_ade_curve(ade_by_step, ade_path, args.sample, args.horizon)
        print(f"Saved ADE curve:      {ade_path}")


if __name__ == '__main__':
    main()
