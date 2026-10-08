# Compatibility for direct source-script execution; package imports need no path changes.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.layout import scene_input
from common.runtime import trial_root
import torch
import numpy as np
import sys
import os
import glob

from traffic.configs.default import (
    VEHICLE_DIM,
    JACOBI_ITERS,
    HIST_STEPS,
    # Constant Velocity baseline
    MAX_SPEED,
    DT,
    CELL_SIZE,
    PRED_STEPS,
    GRID_SIZE,
    TRAIN_TRAJECTORIES,
    VAL_TRAJECTORIES,
    EVAL_SEED_OFFSET,
)
from traffic.models.particle_mlp import ParticleTrafficModel
from traffic.data.generate_complex import generate_dataset


def find_latest_model(date_filter=None):
    train_dir = str(scene_input("south_ken", "traffic", "models"))
    candidates = glob.glob(os.path.join(train_dir, "best_model_*.pt"))
    if date_filter is not None:
        candidates = [p for p in candidates if date_filter in os.path.basename(p)]
    if not candidates:
        raise FileNotFoundError(f"No model file matching '{date_filter}' was found")
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def compute_metrics(preds, targets):
    pos_err = torch.norm(preds[:, :, :2] - targets[:, :, :2], dim=-1)  # (N, PRED_STEPS)
    ade = pos_err.mean().item()
    fde = pos_err[:, -1].mean().item()
    return ade, fde


def vehicle_gt_from_tracks(win_tracks, t_last):
    results = []
    for vt in win_tracks.values():
        anchor = None
        future = {}
        for t, row, col, vd, vc in vt["positions"]:
            if t == t_last:
                anchor = (row, col)
            elif t_last < t <= t_last + PRED_STEPS:
                future[t] = (row, col, vd, vc)
        if anchor is None:
            continue
        arow, acol = anchor
        r = int(min(max(arow, 0), GRID_SIZE - 1))
        c = int(min(max(acol, 0), GRID_SIZE - 1))
        target = torch.zeros(PRED_STEPS, VEHICLE_DIM)
        for k in range(PRED_STEPS):
            tk = t_last + 1 + k
            if tk not in future:
                break
            frow, fcol, fvd, fvc = future[tk]
            target[k, 0] = frow / GRID_SIZE
            target[k, 1] = fcol / GRID_SIZE
            target[k, 2] = fvd
            target[k, 3] = fvc
        results.append((r, c, target))
    return results


def load_model(device, model_date=None, log=print):
    model = ParticleTrafficModel().to(device)
    model_path = find_latest_model(model_date)
    log(f"Load the model: {os.path.basename(model_path)}")
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    return model


def evaluate(model_date=None, log=print):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device, model_date, log=log)
    test_inputs, _, test_tracks, test_t_starts = generate_dataset(
        n_trajectories=50, seed_offset=EVAL_SEED_OFFSET, return_tracks=True
    )
    log(f"Number of test samples: {test_inputs.shape[0]}")

    all_preds = []
    all_targets = []

    with torch.no_grad():
        for i in range(test_inputs.shape[0]):
            grid = test_inputs[i].to(device)
            pred_grid = model.predict_full_grid(grid)
            t_last = test_t_starts[i] + HIST_STEPS - 1
            for r, c, target in vehicle_gt_from_tracks(test_tracks[i], t_last):
                all_preds.append(pred_grid[:, r, c, :].cpu())
                all_targets.append(target)

    if not all_targets:
        log("No valid test samples")
        return

    preds_t = torch.stack(all_preds)
    targets_t = torch.stack(all_targets)
    ade, fde = compute_metrics(preds_t, targets_t)
    log(f"[Jacobi iteration x{JACOBI_ITERS}] ADE: {ade:.6f}, FDE: {fde:.6f}")


# Control Intervention Analysis
def modify_regulation(grid, signal_mode=None, speed_factor=None):
    modified = grid.clone()
    for t in range(modified.shape[0]):
        frame = modified[t]
        occupied = frame[:, :, :VEHICLE_DIM].abs().sum(dim=-1) > 1e-6
        if signal_mode is not None:
            if signal_mode == "invert":
                frame[:, :, 5][occupied] = 1.0 - frame[:, :, 5][occupied]
            elif signal_mode == "all_green":
                frame[:, :, 5][occupied] = 1.0
            elif signal_mode == "all_red":
                frame[:, :, 5][occupied] = 0.0
        if speed_factor is not None:
            frame[:, :, 4][occupied] = frame[:, :, 4][occupied] * speed_factor
    return modified


def evaluate_counterfactual(model_date=None, log=print):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device, model_date, log=log)
    test_inputs, _, test_tracks, test_t_starts = generate_dataset(
        n_trajectories=50, seed_offset=EVAL_SEED_OFFSET, return_tracks=True
    )
    log(f"[Counterfactual] Number of test samples: {test_inputs.shape[0]}")
    scenarios = {
        "original": {"label": "Original Scenario", "signal": None, "speed": None},
        "signal_inv": {"label": "Signal reversal", "signal": "invert", "speed": None},
        "signal_red": {"label": "All red lights", "signal": "all_red", "speed": None},
        "speed_half": {"label": "Speed limit halved", "signal": None, "speed": 0.5},
    }
    all_preds = {name: [] for name in scenarios}
    all_targets = []
    with torch.no_grad():
        for i in range(test_inputs.shape[0]):
            grid_orig = test_inputs[i]
            t_last = test_t_starts[i] + HIST_STEPS - 1
            gts = vehicle_gt_from_tracks(test_tracks[i], t_last)
            if not gts:
                continue

            scenario_preds = {}
            for name, cfg in scenarios.items():
                modified = modify_regulation(grid_orig, cfg["signal"], cfg["speed"])
                scenario_preds[name] = model.predict_full_grid(modified.to(device), n_iters=1)

            for r, c, target in gts:
                for name in scenarios:
                    all_preds[name].append(scenario_preds[name][:, r, c, :].cpu())
                all_targets.append(target)

    log("\nControl Intervention Analysis")
    targets_t = torch.stack(all_targets)

    for name, cfg in scenarios.items():
        preds_t = torch.stack(all_preds[name])
        ade, fde = compute_metrics(preds_t, targets_t)
        log(f"[{cfg['label']}] ADE: {ade:.6f}, FDE: {fde:.6f}")

    orig = all_preds["original"]
    for name in ["signal_inv", "signal_red", "speed_half"]:
        cf = all_preds[name]
        disps = []
        for op, cp in zip(orig, cf):
            d = torch.norm(op[:, :2] - cp[:, :2], dim=-1)
            disps.append(d)
        disp_t = torch.stack(disps)
        avg_per_step = disp_t.mean(dim=0)
        log(f"[{scenarios[name]['label']}]")
        log(f"  Average displacement of each step: {[f'{v:.4f}' for v in avg_per_step.tolist()]}")
        log(
            f"  Average terminal displacement: {disp_t[:, -1].mean():.4f} (grid unit) "
            f"≈ {disp_t[:, -1].mean() * GRID_SIZE * CELL_SIZE:.1f} m"
        )
        log(f"  Proportion of affected vehicles: {(disp_t[:, -1] > 1e-4).float().mean():.2%}")


def evaluate_cv(log=print):
    test_inputs, _, test_tracks, test_t_starts = generate_dataset(
        n_trajectories=50, seed_offset=EVAL_SEED_OFFSET, return_tracks=True
    )
    log(f"[CV Baseline] Number of test samples: {test_inputs.shape[0]}")
    scale = MAX_SPEED * DT / (CELL_SIZE * GRID_SIZE)
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for i in range(test_inputs.shape[0]):
            grid = test_inputs[i]
            last_frame = grid[-1]
            t_last = test_t_starts[i] + HIST_STEPS - 1

            for r, c, target in vehicle_gt_from_tracks(test_tracks[i], t_last):
                x = last_frame[r, c, 0].item()
                y = last_frame[r, c, 1].item()
                vx = last_frame[r, c, 2].item()
                vy = last_frame[r, c, 3].item()

                pred_car = torch.zeros(PRED_STEPS, VEHICLE_DIM)
                for step in range(PRED_STEPS):
                    dt_factor = scale * (step + 1)
                    pred_car[step, 0] = x + vx * dt_factor
                    pred_car[step, 1] = y + vy * dt_factor
                    pred_car[step, 2] = vx
                    pred_car[step, 3] = vy
                all_preds.append(pred_car)
                all_targets.append(target)
    preds_t = torch.stack(all_preds)
    targets_t = torch.stack(all_targets)
    ade, fde = compute_metrics(preds_t, targets_t)
    log(f"[CV Baseline] ADE: {ade:.6f}, FDE: {fde:.6f}")


def evaluate_single_vehicle(model_date=None, log=print):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device, model_date, log=log)
    test_inputs, _, test_tracks, test_t_starts = generate_dataset(
        n_trajectories=50, seed_offset=EVAL_SEED_OFFSET, return_tracks=True
    )
    log(f"[Single-vehicle] Number of test samples: {test_inputs.shape[0]}")
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for i in range(test_inputs.shape[0]):
            grid = test_inputs[i].to(device)
            pred_grid = model.predict_full_grid(grid, mask_neighbors=True)
            t_last = test_t_starts[i] + HIST_STEPS - 1
            for r, c, target in vehicle_gt_from_tracks(test_tracks[i], t_last):
                all_preds.append(pred_grid[:, r, c, :].cpu())
                all_targets.append(target)
    preds_t = torch.stack(all_preds)
    targets_t = torch.stack(all_targets)
    ade, fde = compute_metrics(preds_t, targets_t)
    log(f"[Single-vehicle MLP] ADE: {ade:.6f}, FDE: {fde:.6f}")


def evaluate_no_iter(model_date=None, log=print):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device, model_date, log=log)
    test_inputs, _, test_tracks, test_t_starts = generate_dataset(
        n_trajectories=50, seed_offset=EVAL_SEED_OFFSET, return_tracks=True
    )
    log(f"[No-iteration] Number of test samples: {test_inputs.shape[0]}")
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for i in range(test_inputs.shape[0]):
            grid = test_inputs[i].to(device)
            pred_grid = model.predict_full_grid(grid, n_iters=1)
            t_last = test_t_starts[i] + HIST_STEPS - 1
            for r, c, target in vehicle_gt_from_tracks(test_tracks[i], t_last):
                all_preds.append(pred_grid[:, r, c, :].cpu())
                all_targets.append(target)
    preds_t = torch.stack(all_preds)
    targets_t = torch.stack(all_targets)
    ade, fde = compute_metrics(preds_t, targets_t)
    log(f"[No-iteration x1] ADE: {ade:.6f}, FDE: {fde:.6f}")


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", "-m", type=str, default=None)
    args = parser.parse_args()

    date_str = os.environ.get("LOG_DATE", datetime.now().strftime("%m-%d_%H-%M-%S"))
    log_dir = trial_root("south_ken", "traffic_evaluation")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = os.path.join(log_dir, f"eval_log_{date_str}.txt")
    log_file = open(log_path, "w", buffering=1)

    def log(msg):
        print(msg)
        log_file.write(msg + "\n")

    evaluate(args.model, log=log)
    log("")
    evaluate_cv(log=log)
    log("")
    evaluate_single_vehicle(args.model, log=log)
    log("")
    evaluate_no_iter(args.model, log=log)
    log("")
    evaluate_counterfactual(args.model, log=log)
