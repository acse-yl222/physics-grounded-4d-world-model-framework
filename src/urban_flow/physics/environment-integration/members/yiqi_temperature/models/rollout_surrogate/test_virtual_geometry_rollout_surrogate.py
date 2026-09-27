from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.animation import FuncAnimation, PillowWriter


def find_bundle_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1],
        Path.cwd().resolve(),
        Path.cwd().resolve() / "temperature_field_bundle",
        Path.home() / "Velocity" / "temperature_field_bundle",
        Path.home() / "Velocity" / "velocity" / "temperature_field_bundle",
    ]
    for candidate in candidates:
        if (candidate / "temperature_surrogate_3d.py").exists():
            return candidate.resolve()
    raise FileNotFoundError("Could not find temperature_field_bundle with temperature_surrogate_3d.py")


BUNDLE_ROOT = find_bundle_root()
if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(BUNDLE_ROOT))

from temperature_surrogate_3d import (  # noqa: E402
    Temperature3DCase,
    TemperatureSurrogateDataset,
    SurrogateStats,
    UNet3D,
)


ROLLOUT_RUN_DIR = BUNDLE_ROOT / "outputs" / "temperature_3d_unet_surrogate_rollout_k5_preserve_onestep_v1"
ROLLOUT_CHECKPOINT = ROLLOUT_RUN_DIR / "best_temperature_3d_unet_surrogate_rollout.pt"
FALLBACK_CHECKPOINT = BUNDLE_ROOT / "outputs" / "temperature_3d_unet_surrogate" / "best_temperature_3d_unet_surrogate.pt"
CASE_DIR = (
    BUNDLE_ROOT
    / "outputs"
    / "virtual_geometry_real_pipeline_test"
    / "cases"
    / "case_virtual_simple_v035_t01"
)
OUT_DIR = ROLLOUT_RUN_DIR / "virtual_geometry_rollout_test"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_STEPS = 3
Z_CROP = None
PATCH_SIZE = (16, 32, 32)
OVERLAP = (4, 8, 8)
GIF_FRAME_STRIDE = 2
GIF_FPS = 4
USE_NEXT_VELOCITY = True
CORRECTION_ITERATIONS = 3
USE_IMPLICIT_FUTURE_GUESS = True
FUTURE_GUESS_MODE = "copy_current"
FUTURE_GUESS_CLIP_C = 1.5
USE_COOL_SURFACE_CHANNELS = True
USE_COOL_SURFACE_RELAXATION = False
USE_BOUNDARY_TEMPERATURE_CONSTRAINTS = False
COOL_SURFACE_RELAXATION = 0.0
OPEN_GROUND_RELAXATION = 0.0
COOL_SURFACE_VERTICAL_DECAY_LAYERS = 4.0
SCRIPT_VERSION = "rollout_test_preserve_onestep_init_normal_height_2026_08_19"
PANEL_TEMP_LIMITS_C = (22.0, 32.0)

__all__ = [
    "BUNDLE_ROOT",
    "CASE_DIR",
    "CORRECTION_ITERATIONS",
    "FALLBACK_CHECKPOINT",
    "FUTURE_GUESS_CLIP_C",
    "FUTURE_GUESS_MODE",
    "HISTORY_STEPS",
    "OUT_DIR",
    "PATCH_SIZE",
    "ROLLOUT_CHECKPOINT",
    "ROLLOUT_RUN_DIR",
    "SCRIPT_VERSION",
    "SurrogateStats",
    "Temperature3DCase",
    "USE_COOL_SURFACE_CHANNELS",
    "USE_COOL_SURFACE_RELAXATION",
    "USE_BOUNDARY_TEMPERATURE_CONSTRAINTS",
    "USE_IMPLICIT_FUTURE_GUESS",
    "USE_NEXT_VELOCITY",
    "Z_CROP",
    "apply_z_crop",
    "autoregressive_rollout",
    "input_channel_count",
    "load_model_from_checkpoint",
    "save_final_panel",
    "save_gifs",
]


def input_channel_count(history_steps: int = HISTORY_STEPS, include_speed: bool = True) -> int:
    temperature_channels = history_steps + int(USE_IMPLICIT_FUTURE_GUESS)
    velocity_channels = 3 + int(include_speed)
    velocity_window_channels = velocity_channels * (2 if USE_NEXT_VELOCITY else 1)
    cool_surface_channels = 2 if USE_COOL_SURFACE_CHANNELS else 0
    return temperature_channels + velocity_window_channels + 8 + cool_surface_channels


def adapt_state_dict_for_velocity_window(state_dict: dict[str, torch.Tensor], model: torch.nn.Module) -> dict[str, torch.Tensor]:
    model_state = model.state_dict()
    first_key = "encoders.0.block.0.weight"
    if first_key not in state_dict or first_key not in model_state:
        return state_dict
    old_weight = state_dict[first_key]
    new_weight = model_state[first_key]
    if old_weight.shape == new_weight.shape:
        return state_dict
    if old_weight.ndim != 5 or new_weight.ndim != 5:
        return state_dict
    if old_weight.shape[0] != new_weight.shape[0] or old_weight.shape[2:] != new_weight.shape[2:]:
        return state_dict

    # Preserve the one-step function when widening the input tensor.  Newly
    # introduced rollout channels must start at zero influence; duplicating
    # velocity/history weights changes the first prediction before training.
    adapted = torch.zeros_like(new_weight)
    old_channels = old_weight.shape[1]
    new_channels = new_weight.shape[1]
    if old_channels == 15 and new_channels in {19, 21, 22}:
        adapted[:, 0:3] = old_weight[:, 0:3]
        if USE_IMPLICIT_FUTURE_GUESS:
            adapted[:, 4:8] = old_weight[:, 3:7]
            adapted[:, 12:20] = old_weight[:, 7:15]
        else:
            adapted[:, 3:7] = old_weight[:, 3:7]
            adapted[:, 11:19] = old_weight[:, 7:15]
    elif old_channels == 19 and new_channels in {21, 22}:
        if USE_IMPLICIT_FUTURE_GUESS and new_channels == 22:
            adapted[:, 0:3] = old_weight[:, 0:3]
            adapted[:, 4:12] = old_weight[:, 3:11]
            adapted[:, 12:20] = old_weight[:, 11:19]
        else:
            adapted[:, 0:19] = old_weight
    elif old_channels == 21 and new_channels == 22:
        adapted[:, 0:3] = old_weight[:, 0:3]
        adapted[:, 4:22] = old_weight[:, 3:21]
    elif old_channels == 22 and new_channels == 21:
        adapted[:, 0:19] = old_weight
        adapted[:, 19:21] = old_weight[:, 20:22]
    else:
        copy_channels = min(old_channels, new_channels)
        adapted[:, :copy_channels] = old_weight[:, :copy_channels]
    state_dict = dict(state_dict)
    state_dict[first_key] = adapted
    return state_dict


def load_model_from_checkpoint(checkpoint: dict[str, object], device: torch.device) -> UNet3D:
    config = checkpoint.get("config", {})
    model = UNet3D(
        in_channels=input_channel_count(HISTORY_STEPS),
        out_channels=1,
        base_channels=int(config.get("base_channels", 12)),
        depth=int(config.get("depth", 3)),
    ).to(device)
    model.load_state_dict(adapt_state_dict_for_velocity_window(checkpoint["model_state_dict"], model))
    model.eval()
    return model


def apply_z_crop(case: Temperature3DCase, z_crop: int | None = Z_CROP) -> Temperature3DCase:
    if z_crop is None:
        return case
    full_z = int(case.temperature.shape[1])
    cropped_z = min(int(z_crop), full_z)
    if cropped_z <= 0:
        raise ValueError(f"Z_CROP must be positive, got {z_crop}.")
    if cropped_z == full_z:
        return case

    case.temperature = case.temperature[:, :cropped_z]
    case.u = case.u[:, :cropped_z]
    case.v = case.v[:, :cropped_z]
    case.w = case.w[:, :cropped_z]
    case.solid_mask = case.solid_mask[:cropped_z]
    if case.roof_mask is not None:
        case.roof_mask = case.roof_mask[:cropped_z]
    return case


def sliding_starts(size: int, tile: int, overlap: int) -> list[int]:
    if tile >= size:
        return [0]
    stride = max(1, tile - overlap)
    starts = list(range(0, size - tile + 1, stride))
    if starts[-1] != size - tile:
        starts.append(size - tile)
    return starts


def np_to_device(value: np.ndarray, device: torch.device) -> torch.Tensor:
    return torch.as_tensor(np.asarray(value, dtype=np.float32).copy(), device=device)


def load_surface_mask_2d(case: Temperature3DCase, filename: str) -> np.ndarray:
    path = case._velocity_cache_dir() / filename
    if path.exists():
        return np.asarray(np.load(path, mmap_mode="r"), dtype=bool)
    return np.zeros(case.temperature.shape[2:], dtype=bool)


def cool_surface_channels(case: Temperature3DCase, crop: tuple[slice, slice, slice]) -> list[np.ndarray]:
    if not USE_COOL_SURFACE_CHANNELS:
        return []
    full_shape = case.temperature.shape[1:]
    vegetation_2d = load_surface_mask_2d(case, "vegetation_mask_2d.npy")
    open_ground_2d = load_surface_mask_2d(case, "open_ground_mask_2d.npy")
    vegetation = np.broadcast_to(vegetation_2d[None, :, :], full_shape)[crop].astype(np.float32)
    open_ground = np.broadcast_to(open_ground_2d[None, :, :], full_shape)[crop].astype(np.float32)
    return [vegetation, open_ground]


def make_input(
    case: Temperature3DCase,
    helper: TemperatureSurrogateDataset,
    stats: SurrogateStats,
    history_c: list[np.ndarray],
    future_guess_c: np.ndarray,
    t: int,
    device: torch.device,
) -> np.ndarray:
    crop = (slice(None), slice(None), slice(None))
    velocity_t = min(t, case.u.shape[0] - 1)
    u = np.asarray(case.u[velocity_t], dtype=np.float32)
    v = np.asarray(case.v[velocity_t], dtype=np.float32)
    w = np.asarray(case.w[velocity_t], dtype=np.float32)
    speed = np.sqrt(u * u + v * v + w * w)
    channels = [helper._norm_temp(frame) for frame in history_c]
    if USE_IMPLICIT_FUTURE_GUESS:
        channels.append(helper._norm_temp(future_guess_c))
    channels.extend([u / stats.velocity_scale, v / stats.velocity_scale, w / stats.velocity_scale])
    if helper.include_speed:
        channels.append(speed / stats.velocity_scale)
    if USE_NEXT_VELOCITY:
        next_velocity_t = min(t + 1, case.u.shape[0] - 1)
        u_next = np.asarray(case.u[next_velocity_t], dtype=np.float32)
        v_next = np.asarray(case.v[next_velocity_t], dtype=np.float32)
        w_next = np.asarray(case.w[next_velocity_t], dtype=np.float32)
        speed_next = np.sqrt(u_next * u_next + v_next * v_next + w_next * w_next)
        channels.extend([u_next / stats.velocity_scale, v_next / stats.velocity_scale, w_next / stats.velocity_scale])
        if helper.include_speed:
            channels.append(speed_next / stats.velocity_scale)
    channels.extend(helper._static_channels(case, crop, t))
    channels.extend(cool_surface_channels(case, crop))
    return np.stack(channels, axis=0).astype(np.float32)


def initial_future_guess(history_c: list[np.ndarray]) -> np.ndarray:
    if FUTURE_GUESS_MODE == "copy_current" or len(history_c) < 2:
        return np.asarray(history_c[-1], dtype=np.float32).copy()
    if FUTURE_GUESS_MODE == "linear_extrapolation":
        current = np.asarray(history_c[-1], dtype=np.float32)
        previous = np.asarray(history_c[-2], dtype=np.float32)
        delta = np.clip(current - previous, -float(FUTURE_GUESS_CLIP_C), float(FUTURE_GUESS_CLIP_C))
        return (current + delta).astype(np.float32)
    raise ValueError(f"Unknown FUTURE_GUESS_MODE: {FUTURE_GUESS_MODE}")


def impose_temperature_constraints(
    prediction_c: np.ndarray,
    case: Temperature3DCase,
    stats: SurrogateStats,
    t: int,
    history_c: list[np.ndarray],
    mask: np.ndarray,
) -> np.ndarray:
    constrained = np.asarray(prediction_c, dtype=np.float32).copy()
    current = np.asarray(history_c[-1], dtype=np.float32)
    constrained[~mask] = current[~mask]

    ambient_value = stats.temp_mean
    if case.ambient_temp_series is not None:
        ambient_value = float(case.ambient_temp_series[min(t + 1, len(case.ambient_temp_series) - 1)])

    zdim, ydim, xdim = constrained.shape
    if USE_BOUNDARY_TEMPERATURE_CONSTRAINTS:
        if xdim > 0:
            vertical_profile = np.linspace(ambient_value + 0.1, ambient_value - 0.1, zdim, dtype=np.float32)
            left_fluid = mask[:, :, 0]
            constrained[:, :, 0] = np.where(left_fluid, vertical_profile[:, None], constrained[:, :, 0])
        if xdim > 1:
            right_fluid = mask[:, :, -1]
            constrained[:, :, -1] = np.where(right_fluid, constrained[:, :, -2], constrained[:, :, -1])
        if ydim > 1:
            north_fluid = mask[:, 0, :]
            south_fluid = mask[:, -1, :]
            constrained[:, 0, :] = np.where(north_fluid, constrained[:, 1, :], constrained[:, 0, :])
            constrained[:, -1, :] = np.where(south_fluid, constrained[:, -2, :], constrained[:, -1, :])
        if zdim > 0:
            top_fluid = mask[-1, :, :]
            constrained[-1, :, :] = np.where(top_fluid, ambient_value, constrained[-1, :, :])

    if USE_COOL_SURFACE_CHANNELS and USE_COOL_SURFACE_RELAXATION:
        crop = (slice(None), slice(None), slice(None))
        vegetation, open_ground = cool_surface_channels(case, crop)
        cool_weight = COOL_SURFACE_RELAXATION * vegetation + OPEN_GROUND_RELAXATION * open_ground
        vertical_decay = np.exp(
            -np.arange(zdim, dtype=np.float32) / float(COOL_SURFACE_VERTICAL_DECAY_LAYERS)
        )[:, None, None]
        alpha = np.clip(cool_weight * vertical_decay * mask.astype(np.float32), 0.0, 0.6)
        if case.ground_surface_temperature is None:
            ground_surface = np.full_like(constrained, ambient_value, dtype=np.float32)
        else:
            ground_surface = TemperatureSurrogateDataset._broadcast_2d(
                case.ground_surface_temperature,
                case.temperature.shape[1:],
                fill=ambient_value,
            ).astype(np.float32)
        cool_reference = np.minimum(ground_surface, ambient_value + 0.5).astype(np.float32)
        constrained = constrained * (1.0 - alpha) + cool_reference * alpha

    return constrained.astype(np.float32)


@torch.no_grad()
def predict_volume_tiled(
    model: torch.nn.Module,
    x_full: np.ndarray,
    stats: SurrogateStats,
    device: torch.device,
) -> np.ndarray:
    _, zdim, ydim, xdim = x_full.shape
    tz, ty, tx = PATCH_SIZE
    oz, oy, ox = OVERLAP
    pred_sum = np.zeros((zdim, ydim, xdim), dtype=np.float32)
    pred_count = np.zeros((zdim, ydim, xdim), dtype=np.float32)
    z_starts = sliding_starts(zdim, tz, oz)
    y_starts = sliding_starts(ydim, ty, oy)
    x_starts = sliding_starts(xdim, tx, ox)
    for z0 in z_starts:
        for y0 in y_starts:
            for x0 in x_starts:
                tile = x_full[:, z0 : z0 + tz, y0 : y0 + ty, x0 : x0 + tx]
                xt = torch.from_numpy(tile[None, ...]).to(device, non_blocking=True)
                with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                    pred_norm = model(xt)[0, 0]
                pred_c = (pred_norm.float().cpu().numpy() * stats.temp_std + stats.temp_mean).astype(np.float32)
                pred_sum[z0 : z0 + tz, y0 : y0 + ty, x0 : x0 + tx] += pred_c
                pred_count[z0 : z0 + tz, y0 : y0 + ty, x0 : x0 + tx] += 1.0
    return pred_sum / np.maximum(pred_count, 1.0)


def autoregressive_rollout(
    case: Temperature3DCase,
    model: torch.nn.Module,
    stats: SurrogateStats,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    case = apply_z_crop(case)
    helper = TemperatureSurrogateDataset(
        [case],
        stats,
        history_steps=HISTORY_STEPS,
        patch_size=None,
        samples_per_case=1,
        random_crop=False,
        deterministic_sampling=True,
    )
    mask = helper._fluid_mask(case, (slice(None), slice(None), slice(None))).astype(bool)
    history = [np.asarray(frame, dtype=np.float32) for frame in case.temperature[:HISTORY_STEPS]]
    pred_frames = []
    true_frames = []
    frame_ids = []
    for target_frame in range(HISTORY_STEPS, case.temperature.shape[0]):
        t = target_frame - 1
        print(f"[rollout test] predicting frame {target_frame}", flush=True)
        correction_history = history[-HISTORY_STEPS:]
        future_guess = initial_future_guess(correction_history)
        pred = None
        for iteration in range(CORRECTION_ITERATIONS):
            informed_guess = impose_temperature_constraints(future_guess, case, stats, t, correction_history, mask)
            x_full = make_input(case, helper, stats, correction_history, informed_guess, t, device)
            pred = predict_volume_tiled(model, x_full, stats, device)
            pred = impose_temperature_constraints(pred, case, stats, t, correction_history, mask)
            alpha = float(iteration + 1) / float(CORRECTION_ITERATIONS)
            future_guess = informed_guess * (1.0 - alpha) + pred * alpha
            future_guess = impose_temperature_constraints(future_guess, case, stats, t, correction_history, mask)
            pred = future_guess.astype(np.float32)
        if pred is None:
            raise RuntimeError("CORRECTION_ITERATIONS must be at least 1.")
        pred_frames.append(pred.astype(np.float32))
        true_frames.append(np.asarray(case.temperature[target_frame], dtype=np.float32))
        frame_ids.append(target_frame)
        history.append(pred.astype(np.float32))
    return (
        np.asarray(pred_frames, dtype=np.float32),
        np.asarray(true_frames, dtype=np.float32),
        mask,
        np.asarray(frame_ids, dtype=np.int32),
    )


def masked(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = arr.copy()
    out[~mask] = np.nan
    return out


def expanded_temperature_limits(values: np.ndarray, lower_pct: float = 1.0, upper_pct: float = 99.0, padding_fraction: float = 0.12) -> tuple[float, float]:
    finite = np.asarray(values, dtype=np.float32)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return 0.0, 1.0
    vmin = float(np.nanpercentile(finite, lower_pct))
    vmax = float(np.nanpercentile(finite, upper_pct))
    if not np.isfinite(vmin) or not np.isfinite(vmax):
        return 0.0, 1.0
    span = max(vmax - vmin, 0.5)
    pad = span * float(padding_fraction)
    return vmin - pad, vmax + pad


def save_final_panel(
    pred: np.ndarray,
    true: np.ndarray,
    mask: np.ndarray,
    frame_id: int,
    building_mask_2d: np.ndarray,
    out_filename: str = "final_frame_horizontal_panels.png",
) -> None:
    temp_cmap = plt.get_cmap("YlOrRd").copy()
    temp_cmap.set_bad("white")
    err_cmap = plt.get_cmap("coolwarm").copy()
    err_cmap.set_bad("white")
    err = pred - true
    z_levels = [min(4, pred.shape[0] - 1), min(11, pred.shape[0] - 1)]
    vmin, vmax = PANEL_TEMP_LIMITS_C
    err_lim = float(np.nanpercentile(np.abs(err[mask]), 98))
    fig, axes = plt.subplots(len(z_levels), 3, figsize=(14, 4.2 * len(z_levels)), constrained_layout=True)
    if len(z_levels) == 1:
        axes = axes[None, :]
    im_temp = None
    for row, z_idx in enumerate(z_levels):
        slice_mask = mask[z_idx]
        bias = float(np.mean(err[z_idx][slice_mask]))
        mae = float(np.mean(np.abs(err[z_idx][slice_mask])))
        im_temp = axes[row, 0].imshow(masked(true[z_idx], slice_mask), cmap=temp_cmap, vmin=vmin, vmax=vmax, origin="upper")
        axes[row, 0].set_title(f"Physical model T\nframe {frame_id} | z={z_idx}")
        axes[row, 1].imshow(masked(pred[z_idx], slice_mask), cmap=temp_cmap, vmin=vmin, vmax=vmax, origin="upper")
        axes[row, 1].set_title(f"Rollout-finetuned surrogate T\nz={z_idx}")
        im_err = axes[row, 2].imshow(masked(err[z_idx], slice_mask), cmap=err_cmap, vmin=-err_lim, vmax=err_lim, origin="upper")
        axes[row, 2].set_title(f"Error: surrogate - physical\nbias={bias:+.3f} C | MAE={mae:.3f} C")
        for ax in axes[row]:
            ax.contour(building_mask_2d.astype(float), levels=[0.5], colors="black", linewidths=0.5, alpha=0.75)
            ax.set_xlabel("x index")
            ax.set_ylabel("y index")
    if im_temp is not None:
        fig.colorbar(im_temp, ax=axes[:, :2], shrink=0.85, label="Temperature (deg C)")
    fig.colorbar(im_err, ax=axes[:, 2], shrink=0.85, label="deg C")
    fig.suptitle("Virtual geometry autoregressive rollout test | rollout-finetuned checkpoint", fontsize=14)
    fig.savefig(OUT_DIR / out_filename, dpi=180)
    plt.close(fig)


def save_gifs(pred_seq: np.ndarray, true_seq: np.ndarray, mask: np.ndarray, frame_ids: np.ndarray, building_mask_2d: np.ndarray) -> None:
    temp_cmap = plt.get_cmap("YlOrRd").copy()
    temp_cmap.set_bad("white")
    err_cmap = plt.get_cmap("coolwarm").copy()
    err_cmap.set_bad("white")
    seq_idx = list(range(0, len(frame_ids), GIF_FRAME_STRIDE))
    pred = pred_seq[seq_idx]
    true = true_seq[seq_idx]
    frames = [int(frame_ids[idx]) for idx in seq_idx]
    mask_seq = np.broadcast_to(mask, true.shape)
    err = pred - true
    vmin, vmax = expanded_temperature_limits(np.concatenate([pred[mask_seq], true[mask_seq]]))
    err_lim = float(np.nanpercentile(np.abs(err[mask_seq]), 98))

    z_idx = min(4, true.shape[1] - 1)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), constrained_layout=True)
    ims = [
        axes[0].imshow(masked(true[0, z_idx], mask[z_idx]), cmap=temp_cmap, vmin=vmin, vmax=vmax, origin="upper"),
        axes[1].imshow(masked(pred[0, z_idx], mask[z_idx]), cmap=temp_cmap, vmin=vmin, vmax=vmax, origin="upper"),
        axes[2].imshow(masked(err[0, z_idx], mask[z_idx]), cmap=err_cmap, vmin=-err_lim, vmax=err_lim, origin="upper"),
    ]
    for ax in axes:
        ax.contour(building_mask_2d.astype(float), levels=[0.5], colors="black", linewidths=0.45, alpha=0.75)
    fig.colorbar(ims[1], ax=axes[:2], shrink=0.82, label="Temperature (deg C)")
    fig.colorbar(ims[2], ax=axes[2], shrink=0.82, label="Error (deg C)")

    def update_horizontal(i: int):
        slice_mask = mask[z_idx]
        ims[0].set_data(masked(true[i, z_idx], slice_mask))
        ims[1].set_data(masked(pred[i, z_idx], slice_mask))
        ims[2].set_data(masked(err[i, z_idx], slice_mask))
        bias = float(np.mean(err[i, z_idx][slice_mask]))
        mae = float(np.mean(np.abs(err[i, z_idx][slice_mask])))
        axes[0].set_title(f"Physical model T\nframe {frames[i]} | z={z_idx}")
        axes[1].set_title(f"Rollout-finetuned surrogate T\nz={z_idx}")
        axes[2].set_title(f"Error\nbias={bias:+.3f} C | MAE={mae:.3f} C")
        return ims

    anim = FuncAnimation(fig, update_horizontal, frames=len(frames), interval=1000 / GIF_FPS, blit=False)
    anim.save(OUT_DIR / f"horizontal_z{z_idx:02d}_rollout_finetuned.gif", writer=PillowWriter(fps=GIF_FPS), dpi=120)
    plt.close(fig)

    # Changed vertical view: fixed y plane, x-z section. This follows the main
    # inlet-flow direction better than the previous fixed-x y-z section.
    y_idx = true.shape[2] // 2
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), constrained_layout=True)
    section_mask = mask[:, y_idx, :]
    ims = [
        axes[0].imshow(masked(true[0, :, y_idx, :], section_mask), cmap=temp_cmap, vmin=vmin, vmax=vmax, origin="lower", aspect="auto"),
        axes[1].imshow(masked(pred[0, :, y_idx, :], section_mask), cmap=temp_cmap, vmin=vmin, vmax=vmax, origin="lower", aspect="auto"),
        axes[2].imshow(masked(err[0, :, y_idx, :], section_mask), cmap=err_cmap, vmin=-err_lim, vmax=err_lim, origin="lower", aspect="auto"),
    ]
    for ax in axes:
        ax.set_xlabel("x index")
        ax.set_ylabel("z index")
    fig.colorbar(ims[1], ax=axes[:2], shrink=0.82, label="Temperature (deg C)")
    fig.colorbar(ims[2], ax=axes[2], shrink=0.82, label="Error (deg C)")

    def update_vertical(i: int):
        ims[0].set_data(masked(true[i, :, y_idx, :], section_mask))
        ims[1].set_data(masked(pred[i, :, y_idx, :], section_mask))
        ims[2].set_data(masked(err[i, :, y_idx, :], section_mask))
        bias = float(np.mean(err[i, :, y_idx, :][section_mask]))
        mae = float(np.mean(np.abs(err[i, :, y_idx, :][section_mask])))
        axes[0].set_title(f"Physical model T\nframe {frames[i]} | y={y_idx}")
        axes[1].set_title(f"Rollout-finetuned surrogate T\ny={y_idx}")
        axes[2].set_title(f"Error\nbias={bias:+.3f} C | MAE={mae:.3f} C")
        return ims

    anim = FuncAnimation(fig, update_vertical, frames=len(frames), interval=1000 / GIF_FPS, blit=False)
    anim.save(OUT_DIR / f"vertical_y{y_idx:03d}_xz_rollout_finetuned.gif", writer=PillowWriter(fps=GIF_FPS), dpi=120)
    plt.close(fig)


def main() -> None:
    global CORRECTION_ITERATIONS

    if not CASE_DIR.exists():
        raise FileNotFoundError(
            f"Missing virtual geometry case: {CASE_DIR}\n"
            "Run Test_Virtual_Geometry_3D_UNet_Surrogate.ipynb once to generate the physical reference case."
        )
    checkpoint_path = ROLLOUT_CHECKPOINT if ROLLOUT_CHECKPOINT.exists() else FALLBACK_CHECKPOINT
    if checkpoint_path == FALLBACK_CHECKPOINT:
        print("Rollout checkpoint not found; falling back to one-step checkpoint for comparison.", flush=True)
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    config = checkpoint.get("config", {})
    CORRECTION_ITERATIONS = int(config.get("correction_iterations", CORRECTION_ITERATIONS))
    stats = SurrogateStats(**checkpoint["stats"])
    history_steps = int(config.get("history_steps", HISTORY_STEPS))
    if history_steps != HISTORY_STEPS:
        raise ValueError(f"This script expects HISTORY_STEPS={HISTORY_STEPS}, checkpoint has {history_steps}.")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model_from_checkpoint(checkpoint, device)

    case = apply_z_crop(Temperature3DCase(CASE_DIR))
    pred_seq, true_seq, mask, frame_ids = autoregressive_rollout(case, model, stats, device)
    err = pred_seq - true_seq
    frame_bias_c = [float(np.mean(frame_err[mask])) for frame_err in err]
    frame_mae_c = [float(np.mean(np.abs(frame_err[mask]))) for frame_err in err]
    frame_rmse_c = [float(np.sqrt(np.mean(frame_err[mask] ** 2))) for frame_err in err]
    metrics = {
        "checkpoint": str(checkpoint_path),
        "case_dir": str(CASE_DIR),
        "mode": "autoregressive_rollout",
        "use_next_velocity": USE_NEXT_VELOCITY,
        "use_implicit_future_guess": USE_IMPLICIT_FUTURE_GUESS,
        "future_guess_mode": FUTURE_GUESS_MODE,
        "future_guess_clip_c": FUTURE_GUESS_CLIP_C,
        "correction_iterations": CORRECTION_ITERATIONS,
        "z_crop": Z_CROP,
        "patch_size": list(PATCH_SIZE),
        "use_cool_surface_channels": USE_COOL_SURFACE_CHANNELS,
        "use_cool_surface_relaxation": USE_COOL_SURFACE_RELAXATION,
        "use_boundary_temperature_constraints": USE_BOUNDARY_TEMPERATURE_CONSTRAINTS,
        "cool_surface_relaxation": COOL_SURFACE_RELAXATION,
        "open_ground_relaxation": OPEN_GROUND_RELAXATION,
        "cool_surface_vertical_decay_layers": COOL_SURFACE_VERTICAL_DECAY_LAYERS,
        "state_dict_adaptation": "zero_init_new_channels_preserve_onestep",
        "in_channels": input_channel_count(HISTORY_STEPS),
        "frames": [int(v) for v in frame_ids],
        "first_predicted_frame": int(frame_ids[0]),
        "first_step_bias_c": float(np.mean(err[0][mask])),
        "first_step_mae_c": float(np.mean(np.abs(err[0][mask]))),
        "first_step_rmse_c": float(np.sqrt(np.mean(err[0][mask] ** 2))),
        "final_frame": int(frame_ids[-1]),
        "final_bias_c": float(np.mean(err[-1][mask])),
        "final_mae_c": float(np.mean(np.abs(err[-1][mask]))),
        "final_rmse_c": float(np.sqrt(np.mean(err[-1][mask] ** 2))),
        "rollout_bias_c": float(np.mean(err[:, mask])),
        "rollout_mae_c": float(np.mean(np.abs(err[:, mask]))),
        "rollout_rmse_c": float(np.sqrt(np.mean(err[:, mask] ** 2))),
        "coldest_step_bias_c": float(np.min(frame_bias_c)),
        "warmest_step_bias_c": float(np.max(frame_bias_c)),
        "max_abs_step_bias_c": float(np.max(np.abs(frame_bias_c))),
        "frame_bias_c": frame_bias_c,
        "frame_mae_c": frame_mae_c,
        "frame_rmse_c": frame_rmse_c,
    }
    (OUT_DIR / "virtual_geometry_rollout_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))

    velocity_dir = case._velocity_cache_dir()
    building_mask_path = velocity_dir / "building_mask_2d.npy"
    building_mask_2d = np.load(building_mask_path).astype(bool) if building_mask_path.exists() else np.any(case.solid_mask, axis=0)
    save_final_panel(pred_seq[-1], true_seq[-1], mask, int(frame_ids[-1]), building_mask_2d)
    save_gifs(pred_seq, true_seq, mask, frame_ids, building_mask_2d)
    print("Saved outputs to:", OUT_DIR)


if __name__ == "__main__":
    main()
