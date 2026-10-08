"""
VSP Emission Calculation + Bayesian Optimization Control Scheme
Reference:Understanding and Quantifying Motor Vehicle Emissions with Vehicle
          Specific Power and TILDAS Remote Sensing
          by José Luis Jiménez-Palacios
"""

# Compatibility for direct source-script execution; package imports need no path changes.
if __name__ == '__main__' and not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import numpy as np
import torch
import sys
import os
import argparse

from traffic.configs.default import (
    PRED_STEPS, MAX_SPEED, EVAL_SEED_OFFSET, GRID_SIZE, VEHICLE_DIM, DT,
)
from traffic.data.generate_intersection import generate_dataset
from traffic.evaluate import load_model, modify_regulation

VSP_BINS = [
    (-99,    0,  1.5, 0.3),   # Deceleration/Braking
    (0,      3,  2.0, 0.5),   # Idle/Low Speed
    (3,      6,  3.5, 1.2),   # Medium Speed Cruise
    (6,      9,  5.0, 2.0),   # Acceleration
    (9,     12,  7.0, 3.5),   # Rapid Acceleration
    (12,    99,  9.0, 5.0),   # Aggressive Acceleration
]


def compute_vsp(v_ms, a_ms2):
    return v_ms * (1.1 * a_ms2 + 0.132) + 0.000302 * v_ms ** 3


def vsp_to_emission_rate(vsp):
    for lo, hi, co2, nox in VSP_BINS:
        if lo <= vsp < hi:
            return co2, nox
    return VSP_BINS[-1][2], VSP_BINS[-1][3]


def trajectory_emissions(positions, velocities, dt=0.5):
    v_ms = np.sqrt(velocities[:, 0]**2 + velocities[:, 1]**2) * MAX_SPEED
    a_ms2 = np.diff(v_ms, prepend=v_ms[0]) / dt

    total_co2 = 0.0
    total_nox = 0.0
    vsps = []

    for t in range(len(v_ms)):
        vsp = compute_vsp(v_ms[t], a_ms2[t])
        co2_rate, nox_rate = vsp_to_emission_rate(vsp)
        total_co2 += co2_rate * dt
        total_nox += nox_rate * dt
        vsps.append(vsp)

    return {
        'CO2_g': total_co2,
        'NOx_mg': total_nox,
        'vsp_mean': np.mean(vsps),
    }


def evaluate_prediction_emissions(grid, pred_grid, last_frame, log=print):
    """Calculate emissions for all vehicles in one inference and return total CO2 (g)"""
    occupied = (last_frame[:, :, :VEHICLE_DIM].abs().sum(dim=-1) > 1e-6)
    cells = occupied.nonzero()

    total_co2 = 0.0
    n_vehicles = 0

    for idx in range(cells.shape[0]):
        r, c = cells[idx, 0].item(), cells[idx, 1].item()

        pred_pos = np.zeros((PRED_STEPS, 2))
        pred_vel = np.zeros((PRED_STEPS, 2))
        for t in range(PRED_STEPS):
            pred_pos[t, 0] = pred_grid[t, r, c, 0].item() * GRID_SIZE
            pred_pos[t, 1] = pred_grid[t, r, c, 1].item() * GRID_SIZE
            pred_vel[t, 0] = pred_grid[t, r, c, 2].item()
            pred_vel[t, 1] = pred_grid[t, r, c, 3].item()

        if np.abs(pred_pos).max() < 1e-6:
            continue

        em = trajectory_emissions(pred_pos, pred_vel, dt=DT)
        total_co2 += em['CO2_g']
        n_vehicles += 1

    return total_co2, n_vehicles


def optimize_control(sample_idx, model_date=None, init_points=5, n_iter=15, log=print):
    """
    Automatically search for the optimal signal_cycle and speed_factor
    """
    from bayes_opt import BayesianOptimization

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device, model_date, log=log)
    test_inputs, _ = generate_dataset(n_trajectories=50, seed_offset=EVAL_SEED_OFFSET)

    if sample_idx >= test_inputs.shape[0]:
        log(f"Sample {sample_idx} out of range")
        return

    grid_orig = test_inputs[sample_idx]
    last_frame = grid_orig[-1]

    def black_box(speed_factor):
        modified = modify_regulation(grid_orig, signal_mode=None,
                                      speed_factor=speed_factor)

        # Run the model
        pred_grid = model.predict_full_grid(modified.to(device), n_iters=1, alpha=0.3)

        # Calculate emissions
        total_co2, n_veh = evaluate_prediction_emissions(
            grid_orig, pred_grid.cpu(), last_frame)

        return -total_co2

    # Bayesian Optimization
    pbounds = {
        'speed_factor': (0.3, 1.0),
    }

    optimizer = BayesianOptimization(
        f=black_box,
        pbounds=pbounds,
        random_state=42,
        allow_duplicate_points=True,
    )

    log(f"Bayesian Optimization Control Scheme: Sample {sample_idx}")
    log(f"  Search Space: speed_factor ∈ [0.3, 1.0]")
    log(f"  Initially randomly sample {init_points} points, iterate {n_iter} rounds")

    optimizer.maximize(init_points=init_points, n_iter=n_iter)

    log(f"\nOptimal Result (Lower total CO2 is better):")
    best = optimizer.max
    log(f"  speed_factor  = {best['params']['speed_factor']:.3f}")
    log(f"  estimated CO2 = {-best['target']:.1f} g")

    baseline_co2 = black_box(1.0)
    log(f"\nbaseline (speed=1.0): CO2 = {-baseline_co2:.1f} g")
    log(f"Optimal Scheme Emission Reduction:{(-baseline_co2 + best['target']) / (-baseline_co2) * 100:.1f}%")

    return optimizer, best


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', '-s', type=int, default=0)
    parser.add_argument('--model', '-m', type=str, default=None)
    parser.add_argument('--init', type=int, default=5)   # Initial random sampling points
    parser.add_argument('--iter', type=int, default=15)  # Number of optimization iterations
    args = parser.parse_args()

    optimize_control(args.sample, args.model, args.init, args.iter)
