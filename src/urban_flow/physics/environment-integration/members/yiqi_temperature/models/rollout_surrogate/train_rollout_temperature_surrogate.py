from __future__ import annotations

import gc
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


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
    discover_case_dirs,
    masked_mse,
    split_cases,
)


DATA_ROOT = BUNDLE_ROOT / "outputs" / "temperature_3d_surrogate_dataset_48"
ONE_STEP_RUN_DIR = BUNDLE_ROOT / "outputs" / "temperature_3d_unet_surrogate"
ONE_STEP_CHECKPOINT = ONE_STEP_RUN_DIR / "best_temperature_3d_unet_surrogate.pt"
RUN_DIR = BUNDLE_ROOT / "outputs" / "temperature_3d_unet_surrogate_rollout_k5_preserve_onestep_v1"
RUN_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_STEPS = 3
ROLLOUT_STEPS = 10
LONG_ROLLOUT_STEPS = 30
Z_CROP = None
PATCH_SIZE = (16, 32, 32)
PATCH_SIZES = (
    (8, 32, 32),
    (24, 16, 16),
)
DEPTH = 3
BASE_CHANNELS = 12
EPOCHS = 20
STEPS_PER_EPOCH = 128
VAL_ROLLOUTS = 32
LONG_VAL_ROLLOUTS = 8
LEARNING_RATE = 1e-5
WEIGHT_DECAY = 1e-4
GRAD_CLIP_NORM = 1.0
VAL_FRACTION = 0.2
SEED = 11
AMP = True
GRADIENT_LOSS_WEIGHT = 0.10
MULTISCALE_LOSS_WEIGHT = 0.10
MULTISCALE_FACTORS = (2, 4)
VERTICAL_PROFILE_LOSS_WEIGHT = 0.0
BIAS_LOSS_WEIGHT = 0.0
ROLLOUT_MEAN_BIAS_LOSS_WEIGHT = 0.0
STEP_DRIFT_BIAS_LOSS_WEIGHT = 1.50
FINAL_DRIFT_BIAS_LOSS_WEIGHT = 2.00
BEST_SCORE_ABS_BIAS_WEIGHT_C = 1.00
FIRST_STEP_ANCHOR_LOSS_WEIGHT = 1.0
LATE_STEP_LOSS_GAMMA = 1.0
USE_NEXT_VELOCITY = True
CORRECTION_ITERATIONS = 2
USE_IMPLICIT_FUTURE_GUESS = True
FUTURE_GUESS_MODE = "copy_current"
FUTURE_GUESS_CLIP_C = 1.5
USE_COOL_SURFACE_CHANNELS = True
USE_COOL_SURFACE_RELAXATION = False
USE_BOUNDARY_TEMPERATURE_CONSTRAINTS = False
COOL_SURFACE_RELAXATION = 0.0
OPEN_GROUND_RELAXATION = 0.0
COOL_SURFACE_VERTICAL_DECAY_LAYERS = 4.0
SURFACE_MASK_CACHE: dict[tuple[str, str], np.ndarray] = {}


def load_stats(checkpoint: dict[str, object], train_cases: list[Temperature3DCase]) -> SurrogateStats:
    payload = checkpoint.get("stats")
    if payload:
        return SurrogateStats(**payload)
    stats_cache = ONE_STEP_RUN_DIR / "surrogate_stats.json"
    if stats_cache.exists():
        cached = json.loads(stats_cache.read_text())
        if "stats" in cached:
            return SurrogateStats(**cached["stats"])
        return SurrogateStats(**cached)
    print("No cached stats found; recomputing from training cases.", flush=True)
    return SurrogateStats.from_cases(train_cases, progress=print)


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


def load_cases(case_dirs: list[Path]) -> list[Temperature3DCase]:
    return [apply_z_crop(Temperature3DCase(path)) for path in case_dirs]


def choose_patch_size(
    volume_shape: tuple[int, int, int],
    rng: random.Random,
    patch_sizes: tuple[tuple[int, int, int], ...] = PATCH_SIZES,
) -> tuple[int, int, int]:
    valid = [
        patch_size
        for patch_size in patch_sizes
        if all(patch <= dim for patch, dim in zip(patch_size, volume_shape))
    ]
    if not valid:
        raise ValueError(f"No patch size in {patch_sizes} fits volume shape {volume_shape}.")
    return rng.choice(valid)


def crop_slices(
    volume_shape: tuple[int, int, int],
    rng: random.Random,
    patch_size: tuple[int, int, int] = PATCH_SIZE,
) -> tuple[slice, slice, slice]:
    starts = []
    for dim, patch in zip(volume_shape, patch_size):
        if patch > dim:
            raise ValueError(f"Patch size {patch_size} exceeds volume shape {volume_shape}.")
        starts.append(rng.randint(0, dim - patch) if dim > patch else 0)
    z0, y0, x0 = starts
    dz, dy, dx = patch_size
    return slice(z0, z0 + dz), slice(y0, y0 + dy), slice(x0, x0 + dx)


def crop_slices_from_origin(origin: tuple[int, int, int], patch_size: tuple[int, int, int] = PATCH_SIZE) -> tuple[slice, slice, slice]:
    z0, y0, x0 = origin
    dz, dy, dx = patch_size
    return slice(z0, z0 + dz), slice(y0, y0 + dy), slice(x0, x0 + dx)


def random_crop_origin(volume_shape: tuple[int, int, int], rng: random.Random, patch_size: tuple[int, int, int] = PATCH_SIZE) -> tuple[int, int, int]:
    starts = []
    for dim, patch in zip(volume_shape, patch_size):
        if patch > dim:
            raise ValueError(f"Patch size {patch_size} exceeds volume shape {volume_shape}.")
        starts.append(rng.randint(0, dim - patch) if dim > patch else 0)
    return tuple(starts)


def crop_slices_for_case(case: Temperature3DCase, rng: random.Random, patch_size: tuple[int, int, int] = PATCH_SIZE) -> tuple[slice, slice, slice]:
    origin = random_crop_origin(case.temperature.shape[1:], rng, patch_size=patch_size)
    return crop_slices_from_origin(origin, patch_size=patch_size)


def np_to_device(value: np.ndarray, device: torch.device) -> torch.Tensor:
    return torch.as_tensor(np.asarray(value, dtype=np.float32).copy(), device=device)


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
        # Old order: TTT + vel[t](u,v,w,speed) + static(8)
        # New implicit order: TTT + T(t+1 guess) + vel[t] + vel[t+1] + static(8) + optional cool-surface masks.
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


def masked_gradient_loss(prediction: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    losses = []
    for dim in (-3, -2, -1):
        pred_grad = prediction.diff(dim=dim)
        target_grad = target.diff(dim=dim)
        if dim == -3:
            grad_mask = mask[..., 1:, :, :] * mask[..., :-1, :, :]
        elif dim == -2:
            grad_mask = mask[..., :, 1:, :] * mask[..., :, :-1, :]
        else:
            grad_mask = mask[..., :, :, 1:] * mask[..., :, :, :-1]
        losses.append((((pred_grad - target_grad) ** 2) * grad_mask).sum() / grad_mask.sum().clamp_min(1.0))
    return sum(losses) / len(losses)


def masked_multiscale_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    factors: tuple[int, ...] = MULTISCALE_FACTORS,
) -> torch.Tensor:
    losses = []
    for factor in factors:
        if any(size < factor for size in prediction.shape[-3:]):
            continue
        pooled_mask = F.avg_pool3d(mask, kernel_size=factor, stride=factor)
        pred_pool = F.avg_pool3d(prediction * mask, kernel_size=factor, stride=factor) / pooled_mask.clamp_min(1e-6)
        target_pool = F.avg_pool3d(target * mask, kernel_size=factor, stride=factor) / pooled_mask.clamp_min(1e-6)
        valid = (pooled_mask > 0.25).to(prediction.dtype)
        losses.append((((pred_pool - target_pool) ** 2) * valid).sum() / valid.sum().clamp_min(1.0))
    if not losses:
        return torch.zeros((), dtype=prediction.dtype, device=prediction.device)
    return sum(losses) / len(losses)


def masked_vertical_profile_loss(prediction: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    valid = mask.sum(dim=(-2, -1)).clamp_min(1.0)
    pred_profile = (prediction * mask).sum(dim=(-2, -1)) / valid
    target_profile = (target * mask).sum(dim=(-2, -1)) / valid
    layer_valid = (mask.sum(dim=(-2, -1)) > 0).to(prediction.dtype)
    zdim = prediction.shape[-3]
    z_weight = torch.linspace(1.0, 1.5, zdim, dtype=prediction.dtype, device=prediction.device).view(1, 1, zdim)
    weighted_valid = layer_valid * z_weight
    return (((pred_profile - target_profile) ** 2) * weighted_valid).sum() / weighted_valid.sum().clamp_min(1.0)


def masked_bias_loss(prediction: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    bias = ((prediction - target) * mask).sum() / mask.sum().clamp_min(1.0)
    return bias * bias


def detail_aware_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
) -> torch.Tensor:
    base = masked_mse(prediction, target, mask)
    grad = masked_gradient_loss(prediction, target, mask)
    multiscale = masked_multiscale_loss(prediction, target, mask)
    loss = (
        base
        + GRADIENT_LOSS_WEIGHT * grad
        + MULTISCALE_LOSS_WEIGHT * multiscale
    )
    if BIAS_LOSS_WEIGHT > 0.0:
        loss = loss + BIAS_LOSS_WEIGHT * masked_bias_loss(prediction, target, mask)
    if VERTICAL_PROFILE_LOSS_WEIGHT > 0.0:
        loss = loss + VERTICAL_PROFILE_LOSS_WEIGHT * masked_vertical_profile_loss(prediction, target, mask)
    return loss


def load_surface_mask_2d(case: Temperature3DCase, filename: str) -> np.ndarray:
    key = (str(case._velocity_cache_dir()), filename)
    if key in SURFACE_MASK_CACHE:
        return SURFACE_MASK_CACHE[key]
    path = case._velocity_cache_dir() / filename
    if path.exists():
        mask = np.asarray(np.load(path, mmap_mode="r"), dtype=bool)
    else:
        mask = np.zeros(case.temperature.shape[2:], dtype=bool)
    SURFACE_MASK_CACHE[key] = mask
    return mask


def cool_surface_masks(
    case: Temperature3DCase,
    crop: tuple[slice, slice, slice],
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    full_shape = case.temperature.shape[1:]
    vegetation_2d = load_surface_mask_2d(case, "vegetation_mask_2d.npy")
    open_ground_2d = load_surface_mask_2d(case, "open_ground_mask_2d.npy")
    vegetation_3d = np.broadcast_to(vegetation_2d[None, :, :], full_shape)[crop]
    open_ground_3d = np.broadcast_to(open_ground_2d[None, :, :], full_shape)[crop]
    vegetation = np_to_device(vegetation_3d.astype(np.float32), device)
    open_ground = np_to_device(open_ground_3d.astype(np.float32), device)
    return vegetation, open_ground


def cool_surface_channels(
    case: Temperature3DCase,
    crop: tuple[slice, slice, slice],
    device: torch.device,
) -> list[torch.Tensor]:
    if not USE_COOL_SURFACE_CHANNELS:
        return []
    vegetation, open_ground = cool_surface_masks(case, crop, device)
    return [vegetation, open_ground]


def build_rollout_input(
    helper: TemperatureSurrogateDataset,
    case: Temperature3DCase,
    stats: SurrogateStats,
    history: list[torch.Tensor],
    future_guess: torch.Tensor,
    crop: tuple[slice, slice, slice],
    t: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    velocity_t = min(t, case.u.shape[0] - 1)
    u = np_to_device(case.u[velocity_t][crop], device) / stats.velocity_scale
    v = np_to_device(case.v[velocity_t][crop], device) / stats.velocity_scale
    w = np_to_device(case.w[velocity_t][crop], device) / stats.velocity_scale
    speed = torch.sqrt(u * u + v * v + w * w)
    velocity_channels = [u, v, w, speed]
    if USE_NEXT_VELOCITY:
        next_velocity_t = min(t + 1, case.u.shape[0] - 1)
        u_next = np_to_device(case.u[next_velocity_t][crop], device) / stats.velocity_scale
        v_next = np_to_device(case.v[next_velocity_t][crop], device) / stats.velocity_scale
        w_next = np_to_device(case.w[next_velocity_t][crop], device) / stats.velocity_scale
        speed_next = torch.sqrt(u_next * u_next + v_next * v_next + w_next * w_next)
        velocity_channels.extend([u_next, v_next, w_next, speed_next])
    static = [
        np_to_device(channel, device)
        for channel in helper._static_channels(case, crop, t)
    ]
    static.extend(cool_surface_channels(case, crop, device))
    mask = np_to_device(helper._fluid_mask(case, crop)[None, ...], device)
    temperature_channels = history + ([future_guess] if USE_IMPLICIT_FUTURE_GUESS else [])
    channels = temperature_channels + velocity_channels + static
    return torch.stack(channels, dim=0).unsqueeze(0), mask.unsqueeze(0), speed


def initial_future_guess_from_stats(history: list[torch.Tensor], stats: SurrogateStats) -> torch.Tensor:
    if FUTURE_GUESS_MODE == "copy_current" or len(history) < 2:
        return history[-1].clone()
    if FUTURE_GUESS_MODE == "linear_extrapolation":
        delta = history[-1] - history[-2]
        clip_norm = float(FUTURE_GUESS_CLIP_C) / float(stats.temp_std)
        delta = delta.clamp(min=-clip_norm, max=clip_norm)
        return history[-1] + delta
    raise ValueError(f"Unknown FUTURE_GUESS_MODE: {FUTURE_GUESS_MODE}")


def impose_temperature_constraints(
    prediction: torch.Tensor,
    case: Temperature3DCase,
    stats: SurrogateStats,
    crop: tuple[slice, slice, slice],
    t: int,
    history: list[torch.Tensor],
    mask: torch.Tensor,
) -> torch.Tensor:
    pred_c = prediction * stats.temp_std + stats.temp_mean
    current_c = history[-1].unsqueeze(0).unsqueeze(0) * stats.temp_std + stats.temp_mean
    constrained = torch.where(mask > 0, pred_c, current_c)

    ambient_value = stats.temp_mean
    if case.ambient_temp_series is not None:
        ambient_value = float(case.ambient_temp_series[min(t + 1, len(case.ambient_temp_series) - 1)])
    ambient = torch.as_tensor(ambient_value, dtype=constrained.dtype, device=constrained.device)

    z_slice, y_slice, x_slice = crop
    full_z, full_y, full_x = case.temperature.shape[1:]
    z_start = 0 if z_slice.start is None else int(z_slice.start)
    z_stop = full_z if z_slice.stop is None else int(z_slice.stop)
    y_start = 0 if y_slice.start is None else int(y_slice.start)
    y_stop = full_y if y_slice.stop is None else int(y_slice.stop)
    x_start = 0 if x_slice.start is None else int(x_slice.start)
    x_stop = full_x if x_slice.stop is None else int(x_slice.stop)

    if USE_BOUNDARY_TEMPERATURE_CONSTRAINTS:
        if x_start == 0:
            left_fluid = mask[..., :, :, 0] > 0
            zdim = constrained.shape[-3]
            vertical_profile = torch.linspace(
                ambient_value + 0.1,
                ambient_value - 0.1,
                zdim,
                dtype=constrained.dtype,
                device=constrained.device,
            ).view(1, 1, zdim, 1)
            left = constrained[..., :, :, 0]
            constrained[..., :, :, 0] = torch.where(left_fluid, vertical_profile.expand_as(left), left)
        if x_stop == full_x and constrained.shape[-1] > 1:
            right_fluid = mask[..., :, :, -1] > 0
            right = constrained[..., :, :, -1]
            constrained[..., :, :, -1] = torch.where(right_fluid, constrained[..., :, :, -2], right)
        if y_start == 0 and constrained.shape[-2] > 1:
            north_fluid = mask[..., :, 0, :] > 0
            north = constrained[..., :, 0, :]
            constrained[..., :, 0, :] = torch.where(north_fluid, constrained[..., :, 1, :], north)
        if y_stop == full_y and constrained.shape[-2] > 1:
            south_fluid = mask[..., :, -1, :] > 0
            south = constrained[..., :, -1, :]
            constrained[..., :, -1, :] = torch.where(south_fluid, constrained[..., :, -2, :], south)
        if z_stop == full_z:
            top_fluid = mask[..., -1, :, :] > 0
            top = constrained[..., -1, :, :]
            constrained[..., -1, :, :] = torch.where(top_fluid, ambient.expand_as(top), top)

    if USE_COOL_SURFACE_CHANNELS and USE_COOL_SURFACE_RELAXATION:
        vegetation, open_ground = cool_surface_masks(case, crop, constrained.device)
        cool_weight = (
            COOL_SURFACE_RELAXATION * vegetation
            + OPEN_GROUND_RELAXATION * open_ground
        ).unsqueeze(0).unsqueeze(0)
        zdim = constrained.shape[-3]
        vertical_decay = torch.exp(
            -torch.arange(zdim, dtype=constrained.dtype, device=constrained.device)
            / float(COOL_SURFACE_VERTICAL_DECAY_LAYERS)
        ).view(1, 1, zdim, 1, 1)
        alpha = (cool_weight * vertical_decay * (mask > 0).to(constrained.dtype)).clamp(0.0, 0.6)
        ground_surface = np_to_device(
            TemperatureSurrogateDataset._broadcast_2d(
                case.ground_surface_temperature,
                case.temperature.shape[1:],
                fill=ambient_value,
            )[crop],
            constrained.device,
        ).unsqueeze(0).unsqueeze(0)
        cool_reference = torch.minimum(ground_surface, ambient + 0.5)
        constrained = constrained * (1.0 - alpha) + cool_reference * alpha

    return (constrained - stats.temp_mean) / stats.temp_std


def sample_rollout_loss(
    model: torch.nn.Module,
    case: Temperature3DCase,
    stats: SurrogateStats,
    helper: TemperatureSurrogateDataset,
    device: torch.device,
    rng: random.Random,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    max_start_t = case.n_training_steps - ROLLOUT_STEPS
    if max_start_t < HISTORY_STEPS - 1:
        raise ValueError(f"{case.case_dir.name} has too few frames for rollout length {ROLLOUT_STEPS}.")
    start_t = rng.randint(HISTORY_STEPS - 1, max_start_t)
    patch_size = choose_patch_size(case.temperature.shape[1:], rng)
    crop = crop_slices_for_case(case, rng, patch_size=patch_size)
    return rollout_loss_at(model, case, stats, helper, device, start_t, crop, rollout_steps=ROLLOUT_STEPS)


def rollout_loss_at(
    model: torch.nn.Module,
    case: Temperature3DCase,
    stats: SurrogateStats,
    helper: TemperatureSurrogateDataset,
    device: torch.device,
    start_t: int,
    crop: tuple[slice, slice, slice],
    rollout_steps: int = ROLLOUT_STEPS,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:

    raw_history = np.asarray(case.temperature[start_t - HISTORY_STEPS + 1 : start_t + 1][(slice(None), *crop)], dtype=np.float32)
    history = [
        (np_to_device(frame, device) - stats.temp_mean) / stats.temp_std
        for frame in raw_history
    ]

    total_loss = torch.zeros((), device=device)
    total_mae_c = torch.zeros((), device=device)
    total_bias_c = torch.zeros((), device=device)
    weighted_rollout_bias = torch.zeros((), device=device)
    weighted_drift_bias = torch.zeros((), device=device)
    final_drift_bias = torch.zeros((), device=device)
    weight_sum = 0.0
    for step in range(rollout_steps):
        t = start_t + step
        future_guess = initial_future_guess_from_stats(history, stats)
        pred = None
        mask = None
        for iteration in range(CORRECTION_ITERATIONS):
            guess_batch = future_guess.unsqueeze(0).unsqueeze(0)
            mask = np_to_device(helper._fluid_mask(case, crop)[None, ...], device).unsqueeze(0)
            informed_guess = impose_temperature_constraints(guess_batch, case, stats, crop, t, history, mask)
            x, mask, _speed = build_rollout_input(
                helper,
                case,
                stats,
                history,
                informed_guess[0, 0],
                crop,
                t,
                device,
            )
            pred = model(x)
            pred = impose_temperature_constraints(pred, case, stats, crop, t, history, mask)
            alpha = float(iteration + 1) / float(CORRECTION_ITERATIONS)
            updated = informed_guess * (1.0 - alpha) + pred * alpha
            updated = impose_temperature_constraints(updated, case, stats, crop, t, history, mask)
            future_guess = updated[0, 0]
            pred = updated
        if pred is None or mask is None:
            raise RuntimeError("CORRECTION_ITERATIONS must be at least 1.")
        target_c = np_to_device(case.temperature[t + 1][crop], device)
        target = ((target_c - stats.temp_mean) / stats.temp_std).unsqueeze(0).unsqueeze(0)
        step_loss = detail_aware_loss(pred, target, mask)
        step_weight = 1.0 + LATE_STEP_LOSS_GAMMA * (float(step) / float(max(rollout_steps - 1, 1)))
        total_loss = total_loss + step_weight * step_loss
        if step == 0 and FIRST_STEP_ANCHOR_LOSS_WEIGHT > 0.0:
            total_loss = total_loss + FIRST_STEP_ANCHOR_LOSS_WEIGHT * step_loss
        err_norm = pred - target
        step_bias_norm = (err_norm * mask).sum() / mask.sum().clamp_min(1.0)
        if ROLLOUT_MEAN_BIAS_LOSS_WEIGHT > 0.0:
            weighted_rollout_bias = weighted_rollout_bias + step_weight * step_bias_norm
        step_drift_bias = step_bias_norm * step_bias_norm
        weighted_drift_bias = weighted_drift_bias + step_weight * step_drift_bias
        if step == rollout_steps - 1:
            final_drift_bias = step_drift_bias
        weight_sum += step_weight
        err_c = (pred * stats.temp_std + stats.temp_mean) - target_c.unsqueeze(0).unsqueeze(0)
        total_mae_c = total_mae_c + (torch.abs(err_c) * mask).sum() / mask.sum().clamp_min(1.0)
        total_bias_c = total_bias_c + (err_c * mask).sum() / mask.sum().clamp_min(1.0)
        history = history[1:] + [pred[0, 0]]

    mean_loss = total_loss / max(weight_sum, 1e-6)
    if ROLLOUT_MEAN_BIAS_LOSS_WEIGHT > 0.0:
        rollout_bias = weighted_rollout_bias / max(weight_sum, 1e-6)
        mean_loss = mean_loss + ROLLOUT_MEAN_BIAS_LOSS_WEIGHT * rollout_bias * rollout_bias
    if STEP_DRIFT_BIAS_LOSS_WEIGHT > 0.0:
        mean_drift_bias = weighted_drift_bias / max(weight_sum, 1e-6)
        mean_loss = mean_loss + STEP_DRIFT_BIAS_LOSS_WEIGHT * mean_drift_bias
    if FINAL_DRIFT_BIAS_LOSS_WEIGHT > 0.0:
        mean_loss = mean_loss + FINAL_DRIFT_BIAS_LOSS_WEIGHT * final_drift_bias

    return mean_loss, total_mae_c / rollout_steps, total_bias_c / rollout_steps


def make_fixed_validation_samples(
    cases: list[Temperature3DCase],
    count: int = VAL_ROLLOUTS,
    seed: int = SEED + 20_000,
    patch_size: tuple[int, int, int] | None = PATCH_SIZE,
    patch_sizes: tuple[tuple[int, int, int], ...] = PATCH_SIZES,
    rollout_steps: int = ROLLOUT_STEPS,
) -> list[dict[str, object]]:
    rng = random.Random(seed)
    samples: list[dict[str, object]] = []
    valid_case_indices = [
        idx for idx, case in enumerate(cases)
        if case.n_training_steps - rollout_steps >= HISTORY_STEPS - 1
    ]
    if not valid_case_indices:
        raise ValueError("No validation cases have enough frames for fixed rollout validation.")

    for _ in range(count):
        case_index = rng.choice(valid_case_indices)
        case = cases[case_index]
        max_start_t = case.n_training_steps - rollout_steps
        start_t = rng.randint(HISTORY_STEPS - 1, max_start_t)
        sample_patch_size = patch_size or choose_patch_size(case.temperature.shape[1:], rng, patch_sizes=patch_sizes)
        crop_origin = random_crop_origin(case.temperature.shape[1:], rng, patch_size=sample_patch_size)
        samples.append(
            {
                "case_index": int(case_index),
                "case_id": case.case_dir.name,
                "start_t": int(start_t),
                "crop_origin": [int(v) for v in crop_origin],
                "patch_size": [int(v) for v in sample_patch_size],
            }
        )
    return samples


@torch.no_grad()
def evaluate_fixed_rollout(
    model: torch.nn.Module,
    cases: list[Temperature3DCase],
    stats: SurrogateStats,
    helper: TemperatureSurrogateDataset,
    device: torch.device,
    fixed_samples: list[dict[str, object]],
    patch_size: tuple[int, int, int] | None = PATCH_SIZE,
    rollout_steps: int = ROLLOUT_STEPS,
) -> dict[str, float]:
    model.eval()
    losses = []
    maes = []
    biases = []
    abs_biases = []
    for sample in fixed_samples:
        case = cases[int(sample["case_index"])]
        crop_origin = tuple(int(v) for v in sample["crop_origin"])
        sample_patch_size = tuple(int(v) for v in sample.get("patch_size", patch_size or PATCH_SIZE))
        crop = crop_slices_from_origin(crop_origin, patch_size=sample_patch_size)
        loss, mae, bias = rollout_loss_at(
            model,
            case,
            stats,
            helper,
            device,
            int(sample["start_t"]),
            crop,
            rollout_steps=rollout_steps,
        )
        losses.append(float(loss.cpu()))
        mae_c = float(mae.cpu())
        bias_c = float(bias.cpu())
        maes.append(mae_c)
        biases.append(bias_c)
        abs_biases.append(abs(bias_c))
    mean_loss = float(np.mean(losses))
    mean_abs_bias_c = float(np.mean(abs_biases))
    return {
        "loss": mean_loss,
        "mae_c": float(np.mean(maes)),
        "bias_c": float(np.mean(biases)),
        "abs_bias_c": mean_abs_bias_c,
        "drift_aware_score": mean_loss + BEST_SCORE_ABS_BIAS_WEIGHT_C * mean_abs_bias_c,
    }


@torch.no_grad()
def evaluate_rollout(
    model: torch.nn.Module,
    cases: list[Temperature3DCase],
    stats: SurrogateStats,
    helper: TemperatureSurrogateDataset,
    device: torch.device,
    rng: random.Random,
) -> dict[str, float]:
    model.eval()
    losses = []
    maes = []
    biases = []
    for _ in range(VAL_ROLLOUTS):
        case = rng.choice(cases)
        loss, mae, bias = sample_rollout_loss(model, case, stats, helper, device, rng)
        losses.append(float(loss.cpu()))
        maes.append(float(mae.cpu()))
        biases.append(float(bias.cpu()))
    return {"loss": float(np.mean(losses)), "mae_c": float(np.mean(maes)), "bias_c": float(np.mean(biases))}


def main() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
        if hasattr(torch, "set_float32_matmul_precision"):
            torch.set_float32_matmul_precision("high")

    case_dirs = discover_case_dirs(DATA_ROOT)
    cases = load_cases(case_dirs)
    train_cases, val_cases = split_cases(cases, val_fraction=VAL_FRACTION, seed=SEED)
    if not train_cases:
        train_cases = val_cases

    if not ONE_STEP_CHECKPOINT.exists():
        raise FileNotFoundError(f"Missing one-step checkpoint: {ONE_STEP_CHECKPOINT}")
    checkpoint = torch.load(ONE_STEP_CHECKPOINT, map_location="cpu")
    stats = load_stats(checkpoint, train_cases)
    ckpt_config = checkpoint.get("config", {})
    in_channels = input_channel_count(HISTORY_STEPS)

    model = UNet3D(
        in_channels=in_channels,
        out_channels=1,
        base_channels=int(ckpt_config.get("base_channels", BASE_CHANNELS)),
        depth=int(ckpt_config.get("depth", DEPTH)),
    ).to(device)
    model.load_state_dict(adapt_state_dict_for_velocity_window(checkpoint["model_state_dict"], model))

    helper = TemperatureSurrogateDataset(
        train_cases,
        stats,
        history_steps=HISTORY_STEPS,
        patch_size=PATCH_SIZE,
        samples_per_case=1,
        random_crop=True,
        deterministic_sampling=False,
        seed=SEED,
    )
    val_helper = TemperatureSurrogateDataset(
        val_cases,
        stats,
        history_steps=HISTORY_STEPS,
        patch_size=PATCH_SIZE,
        samples_per_case=1,
        random_crop=True,
        deterministic_sampling=True,
        seed=SEED + 10_000,
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)
    scaler = torch.amp.GradScaler("cuda", enabled=AMP and device.type == "cuda")
    train_rng = random.Random(SEED + 1)
    val_rng = random.Random(SEED + 2)
    fixed_val_samples = make_fixed_validation_samples(
        val_cases,
        count=VAL_ROLLOUTS,
        seed=SEED + 20_000,
        patch_size=None,
        patch_sizes=PATCH_SIZES,
        rollout_steps=ROLLOUT_STEPS,
    )
    fixed_long_val_samples = make_fixed_validation_samples(
        val_cases,
        count=LONG_VAL_ROLLOUTS,
        seed=SEED + 30_000,
        patch_size=None,
        patch_sizes=PATCH_SIZES,
        rollout_steps=LONG_ROLLOUT_STEPS,
    )
    (RUN_DIR / "fixed_validation_samples.json").write_text(json.dumps(fixed_val_samples, indent=2))
    (RUN_DIR / "fixed_long_validation_samples.json").write_text(json.dumps(fixed_long_val_samples, indent=2))

    best_val = float("inf")
    best_score = float("inf")
    history = {
        "train_loss": [],
        "train_mae_c": [],
        "val_loss": [],
        "val_mae_c": [],
        "val_bias_c": [],
        "long_val_loss": [],
        "long_val_mae_c": [],
        "long_val_bias_c": [],
        "val_abs_bias_c": [],
        "long_val_abs_bias_c": [],
        "val_drift_aware_score": [],
        "long_val_drift_aware_score": [],
    }
    config = {
        "mode": "rollout_finetune",
        "created_from_checkpoint": str(ONE_STEP_CHECKPOINT),
        "history_steps": HISTORY_STEPS,
        "rollout_steps": ROLLOUT_STEPS,
        "long_rollout_steps": LONG_ROLLOUT_STEPS,
        "z_crop": Z_CROP,
        "patch_size": PATCH_SIZE,
        "patch_sizes": [list(patch_size) for patch_size in PATCH_SIZES],
        "steps_per_epoch": STEPS_PER_EPOCH,
        "epochs": EPOCHS,
        "val_rollouts": VAL_ROLLOUTS,
        "long_val_rollouts": LONG_VAL_ROLLOUTS,
        "learning_rate": LEARNING_RATE,
        "loss": {
            "base": "masked_mse",
            "gradient_loss_weight": GRADIENT_LOSS_WEIGHT,
            "multiscale_loss_weight": MULTISCALE_LOSS_WEIGHT,
            "multiscale_factors": list(MULTISCALE_FACTORS),
            "vertical_profile_loss_weight": VERTICAL_PROFILE_LOSS_WEIGHT,
            "bias_loss_weight": BIAS_LOSS_WEIGHT,
            "rollout_mean_bias_loss_weight": ROLLOUT_MEAN_BIAS_LOSS_WEIGHT,
            "step_drift_bias_loss_weight": STEP_DRIFT_BIAS_LOSS_WEIGHT,
            "final_drift_bias_loss_weight": FINAL_DRIFT_BIAS_LOSS_WEIGHT,
            "best_score_abs_bias_weight_c": BEST_SCORE_ABS_BIAS_WEIGHT_C,
            "first_step_anchor_loss_weight": FIRST_STEP_ANCHOR_LOSS_WEIGHT,
            "late_step_loss_gamma": LATE_STEP_LOSS_GAMMA,
        },
        "output_mode": "temperature_normalized",
        "use_next_velocity": USE_NEXT_VELOCITY,
        "use_implicit_future_guess": USE_IMPLICIT_FUTURE_GUESS,
        "future_guess_mode": FUTURE_GUESS_MODE,
        "future_guess_clip_c": FUTURE_GUESS_CLIP_C,
        "correction_iterations": CORRECTION_ITERATIONS,
        "use_cool_surface_channels": USE_COOL_SURFACE_CHANNELS,
        "use_cool_surface_relaxation": USE_COOL_SURFACE_RELAXATION,
        "use_boundary_temperature_constraints": USE_BOUNDARY_TEMPERATURE_CONSTRAINTS,
        "cool_surface_relaxation": COOL_SURFACE_RELAXATION,
        "open_ground_relaxation": OPEN_GROUND_RELAXATION,
        "cool_surface_vertical_decay_layers": COOL_SURFACE_VERTICAL_DECAY_LAYERS,
        "cool_surface_oversampling": False,
        "state_dict_adaptation": "zero_init_new_channels_preserve_onestep",
        "in_channels": in_channels,
        "base_channels": int(ckpt_config.get("base_channels", BASE_CHANNELS)),
        "depth": int(ckpt_config.get("depth", DEPTH)),
        "train_cases": [str(case.case_dir) for case in train_cases],
        "val_cases": [str(case.case_dir) for case in val_cases],
        "fixed_validation_samples_path": str(RUN_DIR / "fixed_validation_samples.json"),
        "fixed_long_validation_samples_path": str(RUN_DIR / "fixed_long_validation_samples.json"),
    }
    (RUN_DIR / "rollout_training_config.json").write_text(json.dumps(config, indent=2))

    print("Bundle root:", BUNDLE_ROOT)
    print("Device:", device)
    print("Train cases:", len(train_cases), "Val cases:", len(val_cases))
    print("Rollout steps:", ROLLOUT_STEPS, "Patch sizes:", PATCH_SIZES, "Z crop:", Z_CROP)
    print("Long validation rollout steps:", LONG_ROLLOUT_STEPS, "samples:", LONG_VAL_ROLLOUTS)
    print("Use velocity[t+1]:", USE_NEXT_VELOCITY)
    print("Use implicit future guess:", USE_IMPLICIT_FUTURE_GUESS)
    print("Future guess mode:", FUTURE_GUESS_MODE, "clip:", FUTURE_GUESS_CLIP_C, "C")
    print("Correction iterations per time step:", CORRECTION_ITERATIONS)
    print("Use cool-surface channels:", USE_COOL_SURFACE_CHANNELS)
    print("Use cool-surface relaxation:", USE_COOL_SURFACE_RELAXATION)
    print("Use boundary temperature constraints:", USE_BOUNDARY_TEMPERATURE_CONSTRAINTS)
    print("Vertical-profile loss weight:", VERTICAL_PROFILE_LOSS_WEIGHT)
    print("First-step anchor loss weight:", FIRST_STEP_ANCHOR_LOSS_WEIGHT)
    print("Bias loss weight:", BIAS_LOSS_WEIGHT)
    print("Rollout mean bias loss weight:", ROLLOUT_MEAN_BIAS_LOSS_WEIGHT)
    print("Step drift-bias loss weight:", STEP_DRIFT_BIAS_LOSS_WEIGHT)
    print("Final drift-bias loss weight:", FINAL_DRIFT_BIAS_LOSS_WEIGHT)
    print("Best-score absolute-bias weight (C):", BEST_SCORE_ABS_BIAS_WEIGHT_C)
    print("Late-step loss gamma:", LATE_STEP_LOSS_GAMMA)
    print("Cool-surface oversampling: False")
    print("Input channels:", in_channels)
    print("Run dir:", RUN_DIR)

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_losses = []
        train_maes = []
        for step in range(1, STEPS_PER_EPOCH + 1):
            case = train_rng.choice(train_cases)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=AMP and device.type == "cuda"):
                loss, mae, bias = sample_rollout_loss(model, case, stats, helper, device, train_rng)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP_NORM)
            scaler.step(optimizer)
            scaler.update()
            train_losses.append(float(loss.detach().cpu()))
            train_maes.append(float(mae.detach().cpu()))

            if step % 64 == 0:
                print(f"epoch {epoch:02d} step {step:04d}/{STEPS_PER_EPOCH}: loss={np.mean(train_losses[-64:]):.5f}, mae={np.mean(train_maes[-64:]):.3f} C", flush=True)
            del loss, mae, bias

        val_metrics = evaluate_fixed_rollout(
            model,
            val_cases,
            stats,
            val_helper,
            device,
            fixed_val_samples,
            patch_size=None,
            rollout_steps=ROLLOUT_STEPS,
        )
        long_val_metrics = evaluate_fixed_rollout(
            model,
            val_cases,
            stats,
            val_helper,
            device,
            fixed_long_val_samples,
            patch_size=None,
            rollout_steps=LONG_ROLLOUT_STEPS,
        )
        train_loss = float(np.mean(train_losses))
        train_mae = float(np.mean(train_maes))
        scheduler.step(val_metrics["loss"])
        history["train_loss"].append(train_loss)
        history["train_mae_c"].append(train_mae)
        history["val_loss"].append(val_metrics["loss"])
        history["val_mae_c"].append(val_metrics["mae_c"])
        history["val_bias_c"].append(val_metrics["bias_c"])
        history["long_val_loss"].append(long_val_metrics["loss"])
        history["long_val_mae_c"].append(long_val_metrics["mae_c"])
        history["long_val_bias_c"].append(long_val_metrics["bias_c"])
        history["val_abs_bias_c"].append(val_metrics["abs_bias_c"])
        history["long_val_abs_bias_c"].append(long_val_metrics["abs_bias_c"])
        history["val_drift_aware_score"].append(val_metrics["drift_aware_score"])
        history["long_val_drift_aware_score"].append(long_val_metrics["drift_aware_score"])
        (RUN_DIR / "rollout_training_history.json").write_text(json.dumps(history, indent=2))

        selection_score = 0.5 * val_metrics["drift_aware_score"] + 0.5 * long_val_metrics["drift_aware_score"]
        is_best = selection_score < best_score
        if is_best:
            best_val = val_metrics["loss"]
            best_score = selection_score
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "stats": stats.__dict__,
                    "config": config,
                    "history": history,
                    "epoch": epoch,
                    "best_val_loss": best_val,
                    "best_drift_aware_score": best_score,
                    "long_val_loss": long_val_metrics["loss"],
                    "long_val_mae_c": long_val_metrics["mae_c"],
                    "long_val_bias_c": long_val_metrics["bias_c"],
                    "long_val_abs_bias_c": long_val_metrics["abs_bias_c"],
                },
                RUN_DIR / "best_temperature_3d_unet_surrogate_rollout.pt",
            )
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "stats": stats.__dict__,
                "config": config,
                "history": history,
                "epoch": epoch,
                "best_val_loss": best_val,
                "best_drift_aware_score": best_score,
                "long_val_loss": long_val_metrics["loss"],
                "long_val_mae_c": long_val_metrics["mae_c"],
                "long_val_bias_c": long_val_metrics["bias_c"],
                "long_val_abs_bias_c": long_val_metrics["abs_bias_c"],
            },
            RUN_DIR / "last_temperature_3d_unet_surrogate_rollout.pt",
        )
        print(
            f"Epoch {epoch}/{EPOCHS}: train loss={train_loss:.5f}, train MAE={train_mae:.3f} C | "
            f"val loss={val_metrics['loss']:.5f}, val MAE={val_metrics['mae_c']:.3f} C, "
            f"val bias={val_metrics['bias_c']:+.3f} C, val abs bias={val_metrics['abs_bias_c']:.3f} C | "
            f"long val loss={long_val_metrics['loss']:.5f}, long val MAE={long_val_metrics['mae_c']:.3f} C, "
            f"long bias={long_val_metrics['bias_c']:+.3f} C, long abs bias={long_val_metrics['abs_bias_c']:.3f} C | "
            f"selection score={selection_score:.5f} | "
            f"best={is_best}",
            flush=True,
        )
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
