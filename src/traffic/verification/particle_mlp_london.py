"""
It's a copy of particle_mlp.py.
Minor adjustments were made to adapt it to the London map scenario,
allowing the model to predict on grids of arbitrary resolution.
The model framework remains unchanged.
"""

import torch
import torch.nn as nn
import sys
import os

from traffic.configs.default import (
    WINDOW_SIZE,
    HIST_STEPS,
    PRED_STEPS,
    VEHICLE_DIM,
    REGULATION_DIM,
    TOTAL_FEAT_DIM,
    HIDDEN_DIM,
    EGO_HIDDEN_DIM,
    N_HIDDEN_LAYERS,
    JACOBI_ITERS,
)


class ParticleInteractionMLP(nn.Module):
    def __init__(self):
        super().__init__()
        input_dim = WINDOW_SIZE * WINDOW_SIZE * HIST_STEPS * TOTAL_FEAT_DIM
        output_dim = PRED_STEPS * VEHICLE_DIM
        self.DEST_INJECT_DIM = 3  # dest_row + dest_col + turn_angle

        self.fc1 = nn.Linear(input_dim, HIDDEN_DIM)

        # Vehicle coding
        ego_input_dim = HIST_STEPS * TOTAL_FEAT_DIM
        self.ego_fc = nn.Linear(ego_input_dim, EGO_HIDDEN_DIM)

        self.dest_amp = nn.Linear(3, self.DEST_INJECT_DIM)

        # Fusion: Global Interaction + Ego Vehicle + Destination
        self.fc2 = nn.Linear(HIDDEN_DIM + EGO_HIDDEN_DIM + self.DEST_INJECT_DIM, HIDDEN_DIM)
        self.fc3 = nn.Linear(HIDDEN_DIM, HIDDEN_DIM)
        self.fc4 = nn.Linear(HIDDEN_DIM, output_dim)
        self.dropout = nn.Dropout(0.1)

    # def forward(self, x, disable_ego=False):
    def forward(self, x):
        # x: (batch, HIST_STEPS, WINDOW_SIZE, WINDOW_SIZE, TOTAL_FEAT_DIM)
        b = x.shape[0]
        W = WINDOW_SIZE
        ctr = W // 2

        ego = x[:, :, ctr, ctr, :]  # (B, H, TOTAL_FEAT)
        ego = ego.reshape(b, -1)  # (B, H*TOTAL_FEAT)
        ego = torch.relu(self.ego_fc(ego))  # (B, EGO_HIDDEN_DIM)
        # if disable_ego:
        #     ego = torch.zeros_like(ego)

        dest = x[:, -1, ctr, ctr, 6:9]  # (B, 3)
        dest = torch.relu(self.dest_amp(dest))  # (B, DEST_INJECT_DIM)

        x = x.reshape(b, -1)  # (B, W*W*H*TOTAL_FEAT)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)

        # Three-path fusion
        x = torch.cat([x, ego, dest], dim=-1)  # (B, HIDDEN+EGO+DEST)
        x = torch.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.relu(self.fc3(x))
        x = self.fc4(x)
        x = x.reshape(b, PRED_STEPS, VEHICLE_DIM)
        return x


class ParticleTrafficModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.interaction_mlp = ParticleInteractionMLP()

    def forward(self, windows):
        # For training: Batch Window → Prediction
        return self.interaction_mlp(windows)

    @torch.no_grad()
    # def predict_full_grid(self, grid):
    # def predict_full_grid(self, grid, mask_neighbors=False, n_iters=None, alpha=0.3, disable_ego=False):  # debug
    def predict_full_grid(
        self, grid, mask_neighbors=False, n_iters=None, alpha=0.3, disp_scale=1.0
    ):
        """
        Add disp_scale to adjust the ratio between actual and simulated grids
        Modify grid_size for dynamic acquisition
        """
        device = grid.device
        half = WINDOW_SIZE // 2
        iters = n_iters if n_iters is not None else JACOBI_ITERS
        # Grid size is taken from the input (not the training-time GRID_SIZE constant),
        # so the same model can predict on any map resolution (e.g. London 138x138).
        grid_size = grid.shape[1]
        pred_grid = torch.zeros(PRED_STEPS, grid_size, grid_size, VEHICLE_DIM, device=device)
        occupied = grid[-1, :, :, :VEHICLE_DIM].abs().sum(dim=-1) > 1e-6  # cells with vehicles
        cells = occupied.nonzero()  # (N_vehicles, 2)
        if cells.shape[0] == 0:
            return pred_grid
        work_grid = grid.clone()

        # for _ in range(JACOBI_ITERS):
        for _ in range(iters):
            windows = []
            for idx in range(cells.shape[0]):
                r, c = cells[idx, 0].item(), cells[idx, 1].item()
                # outside the boundary set to 0
                w = torch.zeros(HIST_STEPS, WINDOW_SIZE, WINDOW_SIZE, TOTAL_FEAT_DIM, device=device)
                r_start = max(0, r - half)
                r_end = min(grid_size, r + half + 1)
                c_start = max(0, c - half)
                c_end = min(grid_size, c + half + 1)
                wr_start = r_start - (r - half)
                wc_start = c_start - (c - half)
                n_rows = min(r_end - r_start, WINDOW_SIZE - wr_start)
                n_cols = min(c_end - c_start, WINDOW_SIZE - wc_start)
                w[:, wr_start : wr_start + n_rows, wc_start : wc_start + n_cols, :] = work_grid[
                    :, r_start : r_start + n_rows, c_start : c_start + n_cols, :
                ]
                if mask_neighbors:
                    center = w[:, half, half, :].clone()
                    w.zero_()
                    w[:, half, half, :] = center
                windows.append(w)
            batch = torch.stack(windows)  # (N, HIST_STEPS, W, W, C)
            # preds = self.interaction_mlp(batch, disable_ego=disable_ego)
            preds = self.interaction_mlp(batch)
            # Displacement → Absolute Position
            for idx in range(cells.shape[0]):
                r, c = cells[idx, 0].item(), cells[idx, 1].item()
                start_pos = work_grid[-1, r, c, :2]
                pred_abs = preds[idx].clone()
                pred_abs[:, :2] = preds[idx, :, :2] * disp_scale + start_pos
                pred_grid[:, r, c, :] = pred_abs
                work_grid[-1, r, c, :VEHICLE_DIM] = (1 - alpha) * work_grid[
                    -1, r, c, :VEHICLE_DIM
                ] + alpha * pred_abs[0, :]
        return pred_grid
