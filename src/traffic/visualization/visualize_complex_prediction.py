"""
Visualization of Complex Intersection Prediction

Usage:
  python visualize_complex_prediction.py -s 0      # static image
  python visualize_complex_prediction.py -s 0 -a   # animation
  python visualize_complex_prediction.py -s 0 -m 08-16_07-31-30  # specify the model
"""

# Compatibility for direct source-script execution; package imports need no path changes.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
from matplotlib.animation import FuncAnimation
import numpy as np
import torch
import sys
import os
import argparse

from traffic.configs.default import (
    HIST_STEPS,
    PRED_STEPS,
    GRID_SIZE,
    EVAL_SEED_OFFSET,
)
from traffic.data.generate_complex import (
    get_road_network,
    build_road_lane_centers,
    get_lane_centerlines,
    generate_dataset,
)
from traffic.evaluate import load_model


def draw_network_base(ax):
    roads = get_road_network()
    lane, drivable = build_road_lane_centers(roads)
    lane_lines = get_lane_centerlines(roads)
    road_cmap = ListedColormap(["white", "#EAEAEA"])

    ax.imshow(
        drivable[:, :, 0], cmap=road_cmap, origin="upper", vmin=0, vmax=1, aspect="equal", zorder=0
    )
    for poly, direction in lane_lines:
        color = "#1F77B4" if direction > 0 else "#D62728"
        ax.plot(poly[:, 1], poly[:, 0], color=color, linewidth=0.5, alpha=0.4, zorder=1)

    ax.set_xlim(0, GRID_SIZE)
    ax.set_ylim(GRID_SIZE, 0)
    ax.set_xticks(np.arange(0, GRID_SIZE, 10))
    ax.set_yticks(np.arange(0, GRID_SIZE, 10))
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.15, linewidth=0.5)
    ax.set_aspect("equal")


def build_vehicle_data(grid, pred_grid, win_tracks, t_start):
    t_last = t_start + HIST_STEPS - 1
    vehicles = []
    for vid, vt in win_tracks.items():
        history = [None] * HIST_STEPS
        gt = []
        anchor = None
        for t, row, col, vd, vc in vt["positions"]:
            if t <= t_last:
                history[t - t_start] = (row, col)
                if t == t_last:
                    anchor = (row, col)
            else:
                gt.append((row, col))

        if anchor is None or sum(p is not None for p in history) < 2:
            continue

        r = int(min(max(anchor[0], 0), GRID_SIZE - 1))
        c = int(min(max(anchor[1], 0), GRID_SIZE - 1))
        pred = [
            (pred_grid[k, r, c, 0].item() * GRID_SIZE, pred_grid[k, r, c, 1].item() * GRID_SIZE)
            for k in range(PRED_STEPS)
        ]

        vehicles.append(
            {
                "id": vid,
                "color": plt.cm.tab20(vid % 20),
                "start": anchor,
                "history": history,
                "prediction": pred,
                "ground_truth": gt,
            }
        )
    return vehicles


def plot_prediction(sample_idx, model_date=None, output_path=None, alpha=0.3, log=print):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device, model_date, log=log)
    test_inputs, _, all_tracks, all_t_starts = generate_dataset(
        n_trajectories=50, seed_offset=EVAL_SEED_OFFSET, return_tracks=True
    )

    if sample_idx >= test_inputs.shape[0]:
        log(f"Sample number {sample_idx} is out of range (0~{test_inputs.shape[0] - 1})")
        return

    grid = test_inputs[sample_idx].to(device)
    pred_grid = model.predict_full_grid(grid, n_iters=1, alpha=alpha)
    vehicles = build_vehicle_data(
        grid.cpu(), pred_grid.cpu(), all_tracks[sample_idx], all_t_starts[sample_idx]
    )
    if not vehicles:
        log("No vehicle is present in this sample.")
        return

    fig, ax = plt.subplots(figsize=(10, 10))
    draw_network_base(ax)

    for v in vehicles:
        sr, sc = v["start"]
        hist = [p for p in v["history"] if p is not None]
        rows = [p[0] for p in hist]
        cols = [p[1] for p in hist]
        ax.plot(cols, rows, "-", color=v["color"], linewidth=2.0, alpha=0.8, zorder=4)

        pred = v["prediction"]
        if len(pred) >= 1:
            p_rows = [sr] + [p[0] for p in pred]
            p_cols = [sc] + [p[1] for p in pred]
            ax.plot(p_cols, p_rows, "--", color=v["color"], linewidth=1.8, alpha=0.8, zorder=4)

        gt = v["ground_truth"]
        if len(gt) >= 1:
            g_rows = [sr] + [g[0] for g in gt]
            g_cols = [sc] + [g[1] for g in gt]
            ax.plot(g_cols, g_rows, "-", color="#333333", linewidth=1.8, alpha=0.7, zorder=3)

    legend_elements = [
        Line2D([0], [0], color="#1F77B4", linewidth=1.5, label="Lane (+direction)"),
        Line2D([0], [0], color="#D62728", linewidth=1.5, label="Lane (-direction)"),
        Line2D([0], [0], color="gray", linewidth=2.0, label="History"),
        Line2D([0], [0], color="gray", linewidth=1.8, linestyle="--", label="Prediction"),
        Line2D([0], [0], color="#333333", linewidth=1.8, label="Ground truth"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=8, framealpha=0.9)

    hist_s = HIST_STEPS * 0.5
    total_s = PRED_STEPS * 0.5
    ax.set_title(
        f"Complex network | Sample {sample_idx} | {len(vehicles)} vehicles | "
        f"History {hist_s:.1f}s -> Prediction {total_s:.1f}s",
        fontsize=12,
        fontweight="bold",
    )

    if output_path is None:
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "train")
        os.makedirs(save_dir, exist_ok=True)
        output_path = os.path.join(save_dir, f"complex_pred_s{sample_idx:02d}.png")
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log(f"Saved: {output_path}")


def animate_prediction(
    sample_idx, model_date=None, output_path=None, alpha=0.3, fps=3, dpi=150, log=print
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device, model_date, log=log)
    test_inputs, _, all_tracks, all_t_starts = generate_dataset(
        n_trajectories=50, seed_offset=EVAL_SEED_OFFSET, return_tracks=True
    )

    if sample_idx >= test_inputs.shape[0]:
        log(f"Sample number {sample_idx} is out of range (0~{test_inputs.shape[0] - 1})")
        return

    grid = test_inputs[sample_idx].to(device)
    pred_grid = model.predict_full_grid(grid, n_iters=1, alpha=alpha)
    vehicles = build_vehicle_data(
        grid.cpu(), pred_grid.cpu(), all_tracks[sample_idx], all_t_starts[sample_idx]
    )
    if not vehicles:
        log("No vehicle is present in this sample.")
        return

    H = HIST_STEPS
    P = PRED_STEPS
    total_frames = H + P

    fig, ax = plt.subplots(figsize=(8, 8))
    draw_network_base(ax)
    title = ax.set_title("", fontsize=11, fontweight="bold")

    def update(frame):
        for child in list(ax.get_children()):
            if hasattr(child, "_dynamic"):
                child.remove()

        if frame < H:
            t = frame
            title.set_text(f"Sample {sample_idx} | History t={t * 0.5:.1f}s")
            for v in vehicles:
                hist = v["history"]
                if hist[t] is not None:
                    r, c = hist[t]
                    dot = ax.plot(c, r, "o", color=v["color"], markersize=8, zorder=6)[0]
                    dot._dynamic = True
                    if t > 0:
                        rows = [p[0] for p in hist[: t + 1] if p is not None]
                        cols = [p[1] for p in hist[: t + 1] if p is not None]
                        line = ax.plot(
                            cols, rows, "-", color=v["color"], linewidth=2.0, alpha=0.7, zorder=4
                        )[0]
                        line._dynamic = True
        else:
            k = frame - H
            title.set_text(
                f"Sample {sample_idx} | Prediction step {k + 1}/{P} ({(k + 1) * 0.5:.1f}s)"
            )
            for v in vehicles:
                sr, sc = v["start"]
                hist = [p for p in v["history"] if p is not None]
                if len(hist) >= 2:
                    rows = [p[0] for p in hist]
                    cols = [p[1] for p in hist]
                    line = ax.plot(
                        cols, rows, "-", color=v["color"], linewidth=1.0, alpha=0.35, zorder=3
                    )[0]
                    line._dynamic = True
                dot = ax.plot(sc, sr, "o", color=v["color"], markersize=6, alpha=0.6, zorder=5)[0]
                dot._dynamic = True

                pred = v["prediction"]
                if k < len(pred):
                    if k > 0:
                        p_rows = [sr] + [p[0] for p in pred[: k + 1]]
                        p_cols = [sc] + [p[1] for p in pred[: k + 1]]
                        line = ax.plot(
                            p_cols,
                            p_rows,
                            "--",
                            color=v["color"],
                            linewidth=2.0,
                            alpha=0.8,
                            zorder=4,
                        )[0]
                        line._dynamic = True
                    dot = ax.plot(
                        pred[k][1],
                        pred[k][0],
                        "s",
                        color=v["color"],
                        markersize=6,
                        alpha=0.9,
                        zorder=6,
                    )[0]
                    dot._dynamic = True

                gt = v["ground_truth"]
                if k < len(gt):
                    if k > 0:
                        g_rows = [sr] + [g[0] for g in gt[: k + 1]]
                        g_cols = [sc] + [g[1] for g in gt[: k + 1]]
                        line = ax.plot(
                            g_cols, g_rows, "-", color="#333333", linewidth=2.0, alpha=0.7, zorder=3
                        )[0]
                        line._dynamic = True
                    dot = ax.plot(
                        gt[k][1], gt[k][0], "o", color="#333333", markersize=6, alpha=0.9, zorder=6
                    )[0]
                    dot._dynamic = True

    ani = FuncAnimation(fig, update, frames=total_frames, interval=1000 // fps, blit=False)

    if output_path is None:
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "train")
        os.makedirs(save_dir, exist_ok=True)
        output_path = os.path.join(save_dir, f"complex_anim_s{sample_idx:02d}.gif")
    ani.save(output_path, writer="pillow", fps=fps, dpi=dpi)
    plt.close(fig)
    log(f"Saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", "-s", type=int, default=0)
    parser.add_argument("--model", "-m", type=str, default=None)
    parser.add_argument("--animate", "-a", action="store_true")
    args = parser.parse_args()

    if args.animate:
        animate_prediction(args.sample, args.model)
    else:
        plot_prediction(args.sample, args.model)
