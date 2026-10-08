from __future__ import annotations

import json
import math
import random
import gc
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset


TEMP_FILE = "temperature_fields_3d_c.npy"
SUMMARY_FILE = "temperature_3d_run_summary.json"


@dataclass
class SurrogateStats:
    temp_mean: float
    temp_std: float
    velocity_scale: float
    surface_temp_mean: float
    surface_temp_std: float
    surface_exchange_scale: float
    height_scale: float

    @classmethod
    def from_cases(
        cls,
        cases: Sequence["Temperature3DCase"],
        max_values_per_array: int = 50_000,
        progress: Callable[[str], None] | None = None,
    ) -> "SurrogateStats":
        temps = []
        velocities = []
        surface_temps = []
        surface_exchange = []
        heights = []

        def sample_values(arr: np.ndarray, max_values: int = max_values_per_array) -> np.ndarray:
            flat = np.asarray(arr).reshape(-1)
            if flat.size <= max_values:
                return np.asarray(flat, dtype=np.float32)
            # Sequential strided sampling is much friendlier to mmap-backed arrays
            # on network filesystems than random indexing.
            stride = max(1, flat.size // max_values)
            sampled = flat[::stride]
            if sampled.size > max_values:
                sampled = sampled[:max_values]
            return np.asarray(sampled, dtype=np.float32)

        for idx, case in enumerate(cases, start=1):
            if progress is not None:
                progress(f"[stats {idx}/{len(cases)}] sampling {case.case_dir.name}")
            temps.append(sample_values(case.temperature))
            velocities.extend([sample_values(case.u), sample_values(case.v), sample_values(case.w)])
            if case.ground_surface_temperature is not None:
                surface_temps.append(sample_values(case.ground_surface_temperature))
            if case.surface_exchange is not None:
                surface_exchange.append(sample_values(case.surface_exchange))
            if case.height_field is not None:
                heights.append(sample_values(case.height_field))

        if progress is not None:
            progress("[stats] reducing sampled values")
        temp = np.concatenate(temps)
        vel = np.concatenate(velocities)
        surf = np.concatenate(surface_temps) if surface_temps else temp
        exch = (
            np.concatenate(surface_exchange)
            if surface_exchange
            else np.array([1.0], dtype=np.float32)
        )
        height = np.concatenate(heights) if heights else np.array([1.0], dtype=np.float32)

        return cls(
            temp_mean=float(np.nanmean(temp)),
            temp_std=max(float(np.nanstd(temp)), 1e-6),
            velocity_scale=max(float(np.nanpercentile(np.abs(vel), 99)), 1e-6),
            surface_temp_mean=float(np.nanmean(surf)),
            surface_temp_std=max(float(np.nanstd(surf)), 1e-6),
            surface_exchange_scale=max(float(np.nanpercentile(np.abs(exch), 99)), 1e-6),
            height_scale=max(float(np.nanpercentile(np.abs(height), 99)), 1e-6),
        )


class Temperature3DCase:
    def __init__(self, case_dir: str | Path):
        self.case_dir = Path(case_dir)
        self.temperature = np.load(self.case_dir / TEMP_FILE, mmap_mode="r")
        self.summary = self._load_summary()
        velocity_dir = self._velocity_cache_dir()

        self.u = np.load(velocity_dir / "velocity_u_3d.npy", mmap_mode="r")
        self.v = np.load(velocity_dir / "velocity_v_3d.npy", mmap_mode="r")
        self.w = np.load(velocity_dir / "velocity_w_3d.npy", mmap_mode="r")
        self.solid_mask = np.load(velocity_dir / "solid_mask_3d.npy", mmap_mode="r")
        self.roof_mask = self._load_optional(velocity_dir / "roof_mask_3d.npy", bool)
        self.height_field = self._load_optional(velocity_dir / "height_field_2d.npy", np.float32)
        self.study_area_mask = self._load_optional(velocity_dir / "study_area_mask_2d.npy", bool)

        self.ground_surface_temperature = self._load_optional(
            self.case_dir / "ground_surface_temperature_c.npy",
            np.float32,
        )
        self.surface_exchange = self._load_optional(
            self.case_dir / "surface_exchange_coeff_per_s.npy",
            np.float32,
        )
        self.shade_field = self._load_optional(self.case_dir / "shade_field.npy", np.float32)
        self.ambient_temp_series = self._load_optional(
            self.case_dir / "ambient_temp_series_c.npy", np.float32
        )

        if self.temperature.ndim != 4:
            raise ValueError(f"{self.case_dir / TEMP_FILE} must have shape [time, z, y, x].")
        if self.u.ndim != 4:
            raise ValueError("Velocity fields must have shape [time, z, y, x].")

    def _load_summary(self) -> dict[str, object]:
        summary_path = self.case_dir / SUMMARY_FILE
        return json.loads(summary_path.read_text()) if summary_path.exists() else {}

    def _velocity_cache_dir(self) -> Path:
        raw = self.summary.get("shared_velocity_cache_summary_path")
        if raw:
            return Path(raw).parent
        fallback = self.case_dir.parent / "south_kensington_velocity_3d"
        if (fallback / "velocity_u_3d.npy").exists():
            return fallback
        raise FileNotFoundError(
            f"Could not locate velocity cache for {self.case_dir}. "
            f"Expected {SUMMARY_FILE} with shared_velocity_cache_summary_path."
        )

    @staticmethod
    def _load_optional(path: Path, dtype: object) -> np.ndarray | None:
        if not path.exists():
            return None
        return np.load(path, mmap_mode="r")

    @property
    def n_training_steps(self) -> int:
        return min(self.temperature.shape[0] - 1, self.u.shape[0])


def discover_case_dirs(root: str | Path) -> list[Path]:
    root = Path(root)
    if (root / TEMP_FILE).exists():
        return [root]
    case_dirs = sorted(
        path
        for path in root.rglob(TEMP_FILE)
        if SUMMARY_FILE in {p.name for p in path.parent.iterdir()}
    )
    return [path.parent for path in case_dirs]


class TemperatureSurrogateDataset(Dataset):
    def __init__(
        self,
        cases: Sequence[Temperature3DCase],
        stats: SurrogateStats,
        history_steps: int = 3,
        patch_size: tuple[int, int, int] | None = (8, 64, 64),
        samples_per_case: int = 256,
        random_crop: bool = True,
        include_speed: bool = True,
        deterministic_sampling: bool = False,
        seed: int = 7,
    ):
        self.cases = list(cases)
        self.stats = stats
        self.history_steps = int(history_steps)
        self.patch_size = patch_size
        self.samples_per_case = int(samples_per_case)
        self.random_crop = bool(random_crop)
        self.include_speed = bool(include_speed)
        self.deterministic_sampling = bool(deterministic_sampling)
        self.seed = int(seed)

        if self.history_steps < 1:
            raise ValueError("history_steps must be positive.")
        valid_cases = [case for case in self.cases if case.n_training_steps >= self.history_steps]
        if len(valid_cases) != len(self.cases):
            dropped = len(self.cases) - len(valid_cases)
            print(
                f"Dropped {dropped} case(s) with too few time steps for history_steps={self.history_steps}."
            )
        self.cases = valid_cases
        if not self.cases:
            raise ValueError("No cases have enough time steps for training.")

    def __len__(self) -> int:
        return len(self.cases) * self.samples_per_case

    @property
    def in_channels(self) -> int:
        return self.history_steps + 3 + int(self.include_speed) + 8

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        case = self.cases[index % len(self.cases)]
        rng = random.Random(self.seed + index) if self.deterministic_sampling else random
        t = rng.randint(self.history_steps - 1, case.n_training_steps - 1)
        z0, y0, x0 = self._crop_origin(case.temperature.shape[1:], rng)
        crop = self._crop_slices(z0, y0, x0)

        temp_history = case.temperature[t - self.history_steps + 1 : t + 1][(slice(None), *crop)]
        temp_history = np.asarray(temp_history, dtype=np.float32)
        target = np.asarray(case.temperature[t + 1][crop], dtype=np.float32)
        velocity_t = min(t, case.u.shape[0] - 1)
        u = np.asarray(case.u[velocity_t][crop], dtype=np.float32)
        v = np.asarray(case.v[velocity_t][crop], dtype=np.float32)
        w = np.asarray(case.w[velocity_t][crop], dtype=np.float32)
        speed = np.sqrt(u * u + v * v + w * w)

        channels = [self._norm_temp(frame) for frame in temp_history]
        channels.extend(
            [
                u / self.stats.velocity_scale,
                v / self.stats.velocity_scale,
                w / self.stats.velocity_scale,
            ]
        )
        if self.include_speed:
            channels.append(speed / self.stats.velocity_scale)
        channels.extend(self._static_channels(case, crop, t))

        x = np.stack(channels, axis=0).astype(np.float32)
        y = self._norm_temp(target)[None, ...].astype(np.float32)
        mask = self._fluid_mask(case, crop)[None, ...].astype(np.float32)

        return {
            "x": torch.from_numpy(x),
            "y": torch.from_numpy(y),
            "mask": torch.from_numpy(mask),
        }

    def _crop_origin(
        self,
        volume_shape: tuple[int, int, int],
        rng: random.Random | random.Random = random,
    ) -> tuple[int, int, int]:
        if self.patch_size is None:
            return 0, 0, 0
        starts = []
        for dim, patch in zip(volume_shape, self.patch_size):
            if patch > dim:
                raise ValueError(
                    f"Patch size {self.patch_size} exceeds volume shape {volume_shape}."
                )
            max_start = dim - patch
            starts.append(
                rng.randint(0, max_start) if self.random_crop and max_start > 0 else max_start // 2
            )
        return tuple(starts)

    def _crop_slices(self, z0: int, y0: int, x0: int) -> tuple[slice, slice, slice]:
        if self.patch_size is None:
            return slice(None), slice(None), slice(None)
        dz, dy, dx = self.patch_size
        return slice(z0, z0 + dz), slice(y0, y0 + dy), slice(x0, x0 + dx)

    def _norm_temp(self, value: np.ndarray) -> np.ndarray:
        return (value.astype(np.float32) - self.stats.temp_mean) / self.stats.temp_std

    def denorm_temp(self, value: torch.Tensor) -> torch.Tensor:
        return value * self.stats.temp_std + self.stats.temp_mean

    def _static_channels(
        self,
        case: Temperature3DCase,
        crop: tuple[slice, slice, slice],
        t: int,
    ) -> list[np.ndarray]:
        shape = case.temperature.shape[1:][0], case.temperature.shape[2], case.temperature.shape[3]
        solid_bool = np.asarray(case.solid_mask[crop], dtype=bool)
        solid = solid_bool.astype(np.float32)
        fluid = (~solid_bool).astype(np.float32)
        roof = (
            np.asarray(case.roof_mask[crop], dtype=bool)
            if case.roof_mask is not None
            else np.zeros_like(solid_bool)
        ).astype(np.float32)
        height = (
            self._broadcast_2d(case.height_field, shape, fill=0.0)[crop] / self.stats.height_scale
        )
        study = self._broadcast_2d(case.study_area_mask, shape, fill=True)[crop].astype(np.float32)
        surface_exchange = (
            self._broadcast_2d(case.surface_exchange, shape, fill=0.0)[crop]
            / self.stats.surface_exchange_scale
        )
        ground_surface = self._broadcast_2d(
            case.ground_surface_temperature, shape, fill=self.stats.temp_mean
        )[crop]
        ground_surface = (
            (ground_surface - self.stats.surface_temp_mean) / self.stats.surface_temp_std
        ).astype(np.float32)
        ambient = self._ambient_channel(case, shape, t)[crop]
        return [
            solid,
            fluid,
            roof,
            height.astype(np.float32),
            study,
            surface_exchange.astype(np.float32),
            ground_surface,
            ambient.astype(np.float32),
        ]

    def _ambient_channel(
        self, case: Temperature3DCase, shape: tuple[int, int, int], t: int
    ) -> np.ndarray:
        if case.ambient_temp_series is None:
            value = self.stats.temp_mean
        else:
            value = float(case.ambient_temp_series[min(t + 1, len(case.ambient_temp_series) - 1)])
        value = (value - self.stats.temp_mean) / self.stats.temp_std
        return np.full(shape, value, dtype=np.float32)

    @staticmethod
    def _broadcast_2d(
        arr: np.ndarray | None, shape: tuple[int, int, int], fill: float | bool
    ) -> np.ndarray:
        if arr is None:
            return np.full(shape, fill, dtype=np.float32)
        if arr.ndim == 3:
            return arr.astype(np.float32)
        return np.broadcast_to(arr[None, :, :], shape).astype(np.float32)

    def _fluid_mask(self, case: Temperature3DCase, crop: tuple[slice, slice, slice]) -> np.ndarray:
        study = self._broadcast_2d(case.study_area_mask, case.solid_mask.shape, fill=True).astype(
            bool
        )
        return (~np.asarray(case.solid_mask[crop], dtype=bool)) & study[crop]


class ConvBlock3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        groups = min(8, out_channels)
        while out_channels % groups != 0 and groups > 1:
            groups -= 1
        self.block = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.GroupNorm(groups, out_channels),
            nn.SiLU(inplace=True),
            nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.GroupNorm(groups, out_channels),
            nn.SiLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class UNet3D(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int = 1,
        base_channels: int = 24,
        depth: int = 3,
        upsample_mode: str = "trilinear",
    ):
        super().__init__()
        if depth < 1:
            raise ValueError("depth must be at least 1.")

        channels = [base_channels * (2**idx) for idx in range(depth + 1)]
        self.encoders = nn.ModuleList()
        prev_channels = in_channels
        for channels_out in channels:
            self.encoders.append(ConvBlock3D(prev_channels, channels_out))
            prev_channels = channels_out

        self.pool = nn.MaxPool3d(kernel_size=2)
        self.upsample_mode = upsample_mode
        self.upconvs = nn.ModuleList()
        self.decoders = nn.ModuleList()
        for idx in range(depth - 1, -1, -1):
            if upsample_mode == "transpose":
                self.upconvs.append(
                    nn.ConvTranspose3d(channels[idx + 1], channels[idx], kernel_size=2, stride=2)
                )
            elif upsample_mode == "trilinear":
                self.upconvs.append(
                    nn.Sequential(
                        nn.Upsample(scale_factor=2, mode="trilinear", align_corners=False),
                        nn.Conv3d(channels[idx + 1], channels[idx], kernel_size=1),
                    )
                )
            else:
                raise ValueError("upsample_mode must be 'trilinear' or 'transpose'.")
            self.decoders.append(ConvBlock3D(channels[idx] * 2, channels[idx]))

        self.out = nn.Conv3d(base_channels, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = []
        for encoder in self.encoders[:-1]:
            x = encoder(x)
            skips.append(x)
            x = self.pool(x)
        x = self.encoders[-1](x)

        for upconv, decoder, skip in zip(self.upconvs, self.decoders, reversed(skips)):
            x = upconv(x)
            x = self._match_shape(x, skip)
            x = torch.cat([skip, x], dim=1)
            x = decoder(x)
        return self.out(x)

    @staticmethod
    def _match_shape(x: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        dz = reference.shape[-3] - x.shape[-3]
        dy = reference.shape[-2] - x.shape[-2]
        dx = reference.shape[-1] - x.shape[-1]
        if dz == dy == dx == 0:
            return x
        if dz < 0 or dy < 0 or dx < 0:
            x = x[..., : reference.shape[-3], : reference.shape[-2], : reference.shape[-1]]
            dz = reference.shape[-3] - x.shape[-3]
            dy = reference.shape[-2] - x.shape[-2]
            dx = reference.shape[-1] - x.shape[-1]
        return nn.functional.pad(x, [0, dx, 0, dy, 0, dz])


def masked_mse(prediction: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    sq = (prediction - target) ** 2
    return (sq * mask).sum() / mask.sum().clamp_min(1.0)


def masked_mae_c(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    stats: SurrogateStats,
) -> torch.Tensor:
    pred_c = prediction * stats.temp_std + stats.temp_mean
    target_c = target * stats.temp_std + stats.temp_mean
    return (torch.abs(pred_c - target_c) * mask).sum() / mask.sum().clamp_min(1.0)


def train_one_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    stats: SurrogateStats,
    amp: bool = True,
) -> dict[str, float]:
    model.train()
    scaler = torch.amp.GradScaler("cuda", enabled=amp and device.type == "cuda")
    total_loss = 0.0
    total_mae = 0.0
    n_batches = 0
    for batch in loader:
        x = batch["x"].to(device, non_blocking=True)
        y = batch["y"].to(device, non_blocking=True)
        mask = batch["mask"].to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", enabled=amp and device.type == "cuda"):
            pred = model(x)
            loss = masked_mse(pred, y, mask)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        total_loss += float(loss.detach().cpu())
        total_mae += float(masked_mae_c(pred.detach(), y, mask, stats).cpu())
        n_batches += 1
        del x, y, mask, pred, loss, batch
    return {"loss": total_loss / max(n_batches, 1), "mae_c": total_mae / max(n_batches, 1)}


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
    stats: SurrogateStats,
) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_mae = 0.0
    n_batches = 0
    for batch in loader:
        x = batch["x"].to(device, non_blocking=True)
        y = batch["y"].to(device, non_blocking=True)
        mask = batch["mask"].to(device, non_blocking=True)
        pred = model(x)
        total_loss += float(masked_mse(pred, y, mask).cpu())
        total_mae += float(masked_mae_c(pred, y, mask, stats).cpu())
        n_batches += 1
        del x, y, mask, pred, batch
    return {"loss": total_loss / max(n_batches, 1), "mae_c": total_mae / max(n_batches, 1)}


def split_cases(cases: Sequence[Temperature3DCase], val_fraction: float = 0.2, seed: int = 7):
    cases = list(cases)
    rng = random.Random(seed)
    rng.shuffle(cases)
    n_val = max(1, int(math.ceil(len(cases) * val_fraction))) if len(cases) > 1 else 1
    return cases[n_val:], cases[:n_val]
