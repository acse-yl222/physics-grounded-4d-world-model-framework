# Compatibility for direct source-script execution; package imports need no path changes.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.runtime import trial_root
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
import os
import sys
from datetime import datetime

from traffic.configs.default import (
    GRID_SIZE,
    WINDOW_SIZE,
    HIST_STEPS,
    PRED_STEPS,
    VEHICLE_DIM,
    BATCH_SIZE,
    LR,
    EPOCHS,
    TRAIN_TRAJECTORIES,
    VAL_TRAJECTORIES,
)
from traffic.models.particle_mlp import ParticleTrafficModel
from traffic.data.generate_complex import generate_dataset


def track_vehicle_targets(label, start_r, start_c, last_frame):
    """
    Read the real position as the target instead of reading the zero value of the fixed cell (r,c)
    """
    target = torch.zeros(PRED_STEPS, VEHICLE_DIM)
    ref_pos = last_frame[start_r, start_c, :2].clone()

    for k in range(PRED_STEPS):
        frame = label[k]
        occ = frame[:, :, :VEHICLE_DIM].abs().sum(dim=-1) > 1e-6
        occ_cells = occ.nonzero()
        if occ_cells.shape[0] == 0:
            break
        best_dist = float("inf")
        best_cell = None
        for idx in range(occ_cells.shape[0]):
            rr, cc = occ_cells[idx, 0].item(), occ_cells[idx, 1].item()
            pos = frame[rr, cc, :2]
            dist = ((pos[0] - ref_pos[0]) ** 2 + (pos[1] - ref_pos[1]) ** 2).item()
            if dist < best_dist:
                best_dist = dist
                best_cell = (rr, cc)
        if best_cell is None:
            break
        rr, cc = best_cell
        target[k] = frame[rr, cc, :]
        ref_pos = frame[rr, cc, :2].clone()

    if target[:, :2].abs().sum() < 1e-8:
        return None
    return target


class WindowDataset(Dataset):
    def __init__(self, inputs, tracks, t_starts):
        # inputs: (N, HIST_STEPS, GRID_SIZE, GRID_SIZE, TOTAL_FEAT_DIM)
        # tracks: list of {vid: {'entry', 'positions': [(t,row,col,vd,vc), ...]}}
        half = WINDOW_SIZE // 2
        windows = []
        targets = []

        for i in range(inputs.shape[0]):
            t_last = t_starts[i] + HIST_STEPS - 1
            win_tracks = tracks[i]
            padded = F.pad(inputs[i], (0, 0, half, half, half, half))  # (HIST, R+2h, C+2h, F)

            for vt in win_tracks.values():
                # Anchor point of the vehicle at the last historical frame + positions in future frames
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

                # target: Relative Displacement + Velocity Component
                target = torch.zeros(PRED_STEPS, VEHICLE_DIM)
                for k in range(PRED_STEPS):
                    tk = t_last + 1 + k
                    if tk not in future:
                        break
                    frow, fcol, fvd, fvc = future[tk]
                    target[k, 0] = (frow - arow) / GRID_SIZE
                    target[k, 1] = (fcol - acol) / GRID_SIZE
                    target[k, 2] = fvd
                    target[k, 3] = fvc
                targets.append(target)

                windows.append(padded[:, r : r + WINDOW_SIZE, c : c + WINDOW_SIZE, :])

        if not windows:
            raise RuntimeError("No valid windows generated")
        self.windows = torch.stack(windows, dim=0)
        self.targets = torch.stack(targets, dim=0)

    def __len__(self):
        return self.windows.shape[0]

    def __getitem__(self, idx):
        return self.windows[idx], self.targets[idx]


def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    save_dir = str(trial_root("south_ken", "traffic_training"))
    os.makedirs(save_dir, exist_ok=True)
    date_str = os.environ.get("LOG_DATE", datetime.now().strftime("%m-%d_%H-%M-%S"))
    log_path = os.path.join(save_dir, f"train_log_{date_str}.txt")
    log_file = open(log_path, "w", buffering=1)

    def log(msg):
        print(msg)
        log_file.write(msg + "\n")

    log(f"Equipment: {device}")
    train_inputs, train_labels, train_tracks, train_t_starts = generate_dataset(
        TRAIN_TRAJECTORIES, return_tracks=True
    )
    val_inputs, val_labels, val_tracks, val_t_starts = generate_dataset(
        VAL_TRAJECTORIES, seed_offset=TRAIN_TRAJECTORIES, return_tracks=True
    )
    log(
        f"Trajectory Data - Training: {train_inputs.shape[0]} samples, Validation: {val_inputs.shape[0]} samples"
    )

    train_ds = WindowDataset(train_inputs, train_tracks, train_t_starts)
    val_ds = WindowDataset(val_inputs, val_tracks, val_t_starts)
    log(f"Number of Windows - Training: {len(train_ds)}, Validation: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    model = ParticleTrafficModel().to(device)
    log(f"Number of parameters: {sum(p.numel() for p in model.parameters()):,}")

    optimizer = torch.optim.Adam(
        model.parameters(), lr=LR, weight_decay=1e-4
    )  # L2 regularization to mitigate overfitting
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.5)
    criterion = nn.MSELoss()

    best_val = float("inf")

    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0
        for w, t in train_loader:
            w, t = w.to(device), t.to(device)
            pred = model(w)
            loss = criterion(pred, t)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * w.shape[0]
        train_loss /= len(train_ds)

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for w, t in val_loader:
                w, t = w.to(device), t.to(device)
                val_loss += criterion(model(w), t).item() * w.shape[0]
        val_loss /= len(val_ds)

        scheduler.step()

        if val_loss < best_val:
            best_val = val_loss
            best_path = os.path.join(save_dir, f"best_model_{date_str}.pt")
            torch.save(model.state_dict(), best_path)

        if (epoch + 1) % 10 == 0:
            log(f"Epoch {epoch + 1:3d} | Train: {train_loss:.6f} | Val: {val_loss:.6f}")

    log(f"Training completed. Best validation Loss: {best_val:.6f}")


if __name__ == "__main__":
    import argparse

    argparse.ArgumentParser(description="Train the particle traffic model").parse_args()
    train()
