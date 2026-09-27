from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import numpy as np

try:
    import matplotlib.animation as mpl_animation
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ModuleNotFoundError:
    mpl_animation = None
    plt = None
    MATPLOTLIB_AVAILABLE = False

try:
    from IPython.display import HTML
except ModuleNotFoundError:
    HTML = None

VELOCITY_MODEL_DIR = Path(__file__).resolve().parents[1] / "velocity_calculation"
if str(VELOCITY_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(VELOCITY_MODEL_DIR))

from south_kensington_jupyter import SouthKensingtonConfig, run_pipeline


BUNDLE_ROOT = Path(__file__).resolve().parent


@dataclass
class TemperatureScenarioConfig:
    output_dir: str = str(BUNDLE_ROOT / "outputs" / "south_kensington_temperature")
    reuse_velocity_output_dir: str = str(BUNDLE_ROOT / "outputs" / "south_kensington_velocity")
    slice_idx: int = 4
    frame_duration_s: float = 90.0
    max_courant: float = 0.35
    diffusion_coeff_m2_s: float = 1.0
    velocity_scale: float = 0.65
    ambient_temp_c: float = 31.5
    inflow_temp_c: float = 31.8
    background_source_c_per_hour: float = 0.08
    urban_source_c_per_hour: float = 0.30
    vegetation_cooling_c_per_hour: float = 0.28
    shade_cooling_c_per_hour: float = 0.18
    site_latitude_deg: float = 51.505763
    site_longitude_deg: float = -0.189031
    analysis_time_utc: str = "2025-07-25T13:00:00+00:00"
    shadow_soften_passes: int = 2
    afternoon_source_decay: float = 0.0
    ambient_cooling_c_per_hour: float = 0.22
    initial_urban_excess_c: float = 0.55
    initial_vegetation_cooling_c: float = 0.35
    fixed_building_temp_c: float = 30.5
    save_animation: bool = True


def per_hour_to_per_second(value: float) -> float:
    return value / 3600.0


def smooth_field(field: np.ndarray, passes: int = 6) -> np.ndarray:
    smoothed = np.asarray(field, dtype=np.float32).copy()
    for _ in range(max(passes, 0)):
        smoothed = (
            4.0 * smoothed
            + np.roll(smoothed, 1, axis=0)
            + np.roll(smoothed, -1, axis=0)
            + np.roll(smoothed, 1, axis=1)
            + np.roll(smoothed, -1, axis=1)
        ) / 8.0
        smoothed[0, :] = smoothed[1, :]
        smoothed[-1, :] = smoothed[-2, :]
        smoothed[:, 0] = smoothed[:, 1]
        smoothed[:, -1] = smoothed[:, -2]
    return smoothed


def normalise_field(field: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    field = np.asarray(field, dtype=np.float32)
    span = float(field.max() - field.min())
    if span < eps:
        return np.zeros_like(field, dtype=np.float32)
    return (field - field.min()) / span


def parse_utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def compute_solar_position_deg(
    latitude_deg: float,
    longitude_deg: float,
    when_utc: datetime,
) -> tuple[float, float]:
    when_utc = when_utc.astimezone(timezone.utc)
    day_of_year = when_utc.timetuple().tm_yday
    hour_decimal = (
        when_utc.hour
        + when_utc.minute / 60.0
        + when_utc.second / 3600.0
        + when_utc.microsecond / 3_600_000_000.0
    )
    fractional_year = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (hour_decimal - 12.0) / 24.0)
    equation_of_time = 229.18 * (
        0.000075
        + 0.001868 * math.cos(fractional_year)
        - 0.032077 * math.sin(fractional_year)
        - 0.014615 * math.cos(2.0 * fractional_year)
        - 0.040849 * math.sin(2.0 * fractional_year)
    )
    solar_declination = (
        0.006918
        - 0.399912 * math.cos(fractional_year)
        + 0.070257 * math.sin(fractional_year)
        - 0.006758 * math.cos(2.0 * fractional_year)
        + 0.000907 * math.sin(2.0 * fractional_year)
        - 0.002697 * math.cos(3.0 * fractional_year)
        + 0.00148 * math.sin(3.0 * fractional_year)
    )

    true_solar_time_min = (
        hour_decimal * 60.0 + equation_of_time + 4.0 * float(longitude_deg)
    ) % 1440.0
    hour_angle_deg = true_solar_time_min / 4.0 - 180.0
    if hour_angle_deg < -180.0:
        hour_angle_deg += 360.0

    latitude_rad = math.radians(float(latitude_deg))
    hour_angle_rad = math.radians(hour_angle_deg)
    cos_zenith = (
        math.sin(latitude_rad) * math.sin(solar_declination)
        + math.cos(latitude_rad) * math.cos(solar_declination) * math.cos(hour_angle_rad)
    )
    cos_zenith = min(1.0, max(-1.0, cos_zenith))
    solar_zenith_rad = math.acos(cos_zenith)
    solar_elevation_deg = 90.0 - math.degrees(solar_zenith_rad)

    azimuth_rad = math.atan2(
        math.sin(hour_angle_rad),
        math.cos(hour_angle_rad) * math.sin(latitude_rad)
        - math.tan(solar_declination) * math.cos(latitude_rad),
    )
    solar_azimuth_deg = (math.degrees(azimuth_rad) + 180.0) % 360.0
    return float(solar_elevation_deg), float(solar_azimuth_deg)


def compute_building_shadow_field(
    building_mask: np.ndarray,
    height_field: np.ndarray,
    grid_resolution_m: float,
    solar_elevation_deg: float,
    solar_azimuth_deg: float,
    soften_passes: int = 2,
) -> np.ndarray:
    building_mask = np.asarray(building_mask, dtype=bool)
    height_field = np.asarray(height_field, dtype=np.float32)
    shadow = np.zeros_like(height_field, dtype=np.float32)

    solar_elevation_rad = math.radians(float(np.clip(solar_elevation_deg, 1.0, 89.0)))
    solar_azimuth_rad = math.radians(float(solar_azimuth_deg) % 360.0)
    resolution_m = max(float(grid_resolution_m), 1e-6)
    tangent = math.tan(solar_elevation_rad)

    # Azimuth is clockwise from north. Grid columns grow eastward and rows grow southward.
    shadow_dir_x = -math.sin(solar_azimuth_rad)
    shadow_dir_y = math.cos(solar_azimuth_rad)

    building_rows, building_cols = np.nonzero(building_mask)
    for row, col in zip(building_rows.tolist(), building_cols.tolist()):
        height_m = float(height_field[row, col])
        if height_m <= 0.0:
            continue
        shadow_length_cells = int(math.ceil((height_m / tangent) / resolution_m))
        if shadow_length_cells <= 0:
            continue

        for step in range(1, shadow_length_cells + 1):
            target_row = int(round(row + shadow_dir_y * step))
            target_col = int(round(col + shadow_dir_x * step))
            if (
                target_row < 0
                or target_row >= shadow.shape[0]
                or target_col < 0
                or target_col >= shadow.shape[1]
            ):
                break
            if building_mask[target_row, target_col]:
                continue

            remaining_height = height_m - step * resolution_m * tangent
            shadow[target_row, target_col] = max(
                shadow[target_row, target_col],
                max(remaining_height / max(height_m, 1e-6), 0.0),
            )

    if soften_passes > 0:
        shadow = smooth_field(shadow, passes=soften_passes)

    shadow[building_mask] = 0.0
    return np.clip(shadow, 0.0, 1.0).astype(np.float32)


def resize_nearest_2d(array: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    src_h, src_w = array.shape
    dst_h, dst_w = target_shape
    row_idx = np.clip(
        np.round(np.linspace(0, src_h - 1, dst_h)).astype(int),
        0,
        src_h - 1,
    )
    col_idx = np.clip(
        np.round(np.linspace(0, src_w - 1, dst_w)).astype(int),
        0,
        src_w - 1,
    )
    return array[np.ix_(row_idx, col_idx)]


def embed_in_velocity_grid(
    field: np.ndarray,
    target_shape: tuple[int, int],
    offset_y: int,
    offset_x: int,
    fill_value: float | int = 0,
) -> np.ndarray:
    target = np.full(target_shape, fill_value, dtype=field.dtype)
    src_y, src_x = field.shape
    end_y = min(offset_y + src_y, target_shape[0])
    end_x = min(offset_x + src_x, target_shape[1])
    copy_y = max(end_y - offset_y, 0)
    copy_x = max(end_x - offset_x, 0)
    if copy_y > 0 and copy_x > 0:
        target[offset_y:end_y, offset_x:end_x] = field[:copy_y, :copy_x]
    return target


def extract_slice_fields(
    velocity_results: dict[str, object],
    velocity_config: SouthKensingtonConfig,
    temp_config: TemperatureScenarioConfig,
) -> dict[str, np.ndarray]:
    predictions_3d = np.asarray(velocity_results["predictions_3d"], dtype=np.float32)
    grid_shape = predictions_3d.shape
    safe_slice = min(max(temp_config.slice_idx, 0), grid_shape[2] - 1)

    u = predictions_3d[:, 0, safe_slice, :, :]
    v = predictions_3d[:, 1, safe_slice, :, :]
    speed = np.sqrt(u**2 + v**2)
    velocity_shape = u.shape[1:]

    building_mask_small = np.asarray(velocity_results["mask_resampled"], dtype=bool)
    height_field_small = np.asarray(velocity_results["height_resampled"], dtype=np.float32)
    land_cover = np.load(Path(velocity_config.static_dir) / "land_cover.npy")
    if land_cover.shape != building_mask_small.shape:
        land_cover = resize_nearest_2d(land_cover, building_mask_small.shape)

    offset_y = int(velocity_config.embed_pad_y)
    offset_x = int(velocity_config.embed_pad_x)
    building_mask = embed_in_velocity_grid(
        building_mask_small.astype(np.uint8),
        velocity_shape,
        offset_y,
        offset_x,
        fill_value=0,
    ).astype(bool)
    height_field = embed_in_velocity_grid(
        height_field_small.astype(np.float32),
        velocity_shape,
        offset_y,
        offset_x,
        fill_value=0.0,
    )
    vegetation_mask = embed_in_velocity_grid(
        np.asarray(land_cover == 10, dtype=np.uint8),
        velocity_shape,
        offset_y,
        offset_x,
        fill_value=0,
    ).astype(bool)
    urban_mask = embed_in_velocity_grid(
        (np.asarray(land_cover == 50, dtype=np.uint8) & (~building_mask_small).astype(np.uint8)),
        velocity_shape,
        offset_y,
        offset_x,
        fill_value=0,
    ).astype(bool)
    study_area_mask = embed_in_velocity_grid(
        np.ones_like(building_mask_small, dtype=np.uint8),
        velocity_shape,
        offset_y,
        offset_x,
        fill_value=0,
    ).astype(bool)

    return {
        "u": u,
        "v": v,
        "speed": speed,
        "building_mask": building_mask,
        "vegetation_mask": vegetation_mask,
        "urban_mask": urban_mask,
        "height_field": height_field,
        "study_area_mask": study_area_mask,
        "slice_idx": np.array([safe_slice], dtype=np.int32),
    }


def load_cached_flow_fields(
    velocity_config: SouthKensingtonConfig,
    temp_config: TemperatureScenarioConfig,
) -> dict[str, np.ndarray] | None:
    cache_dir = Path(temp_config.reuse_velocity_output_dir)
    summary_path = cache_dir / "velocity_cache_summary.json"
    required = [
        cache_dir / "velocity_u_slice.npy",
        cache_dir / "velocity_v_slice.npy",
        cache_dir / "building_mask.npy",
        cache_dir / "study_area_mask.npy",
        cache_dir / "vegetation_mask.npy",
        cache_dir / "urban_mask.npy",
        cache_dir / "height_field.npy",
    ]
    if not summary_path.exists() or any(not path.exists() for path in required):
        return None

    try:
        summary = json.loads(summary_path.read_text())
    except json.JSONDecodeError:
        return None

    cached_velocity_config = summary.get("velocity_config", {})
    cached_slice_idx = int(summary.get("slice_idx", -1))
    if (
        int(cached_velocity_config.get("timesteppings", -1)) != int(velocity_config.timesteppings)
        or not np.isclose(
            float(cached_velocity_config.get("model_resolution_m", np.nan)),
            float(velocity_config.model_resolution_m),
        )
        or int(cached_velocity_config.get("z_dim", -1)) != int(velocity_config.z_dim)
        or not np.isclose(
            float(cached_velocity_config.get("height_scale_m", np.nan)),
            float(velocity_config.height_scale_m),
        )
        or cached_slice_idx != int(temp_config.slice_idx)
    ):
        return None

    u = np.load(cache_dir / "velocity_u_slice.npy")
    v = np.load(cache_dir / "velocity_v_slice.npy")
    speed = np.sqrt(u**2 + v**2)
    return {
        "u": u.astype(np.float32),
        "v": v.astype(np.float32),
        "speed": speed.astype(np.float32),
        "building_mask": np.load(cache_dir / "building_mask.npy").astype(bool),
        "study_area_mask": np.load(cache_dir / "study_area_mask.npy").astype(bool),
        "vegetation_mask": np.load(cache_dir / "vegetation_mask.npy").astype(bool),
        "urban_mask": np.load(cache_dir / "urban_mask.npy").astype(bool),
        "height_field": np.load(cache_dir / "height_field.npy").astype(np.float32),
        "slice_idx": np.array([cached_slice_idx], dtype=np.int32),
        "cache_reused": np.array([1], dtype=np.int32),
    }


def extract_or_load_flow_fields(
    velocity_config: SouthKensingtonConfig,
    temp_config: TemperatureScenarioConfig,
) -> tuple[dict[str, object], dict[str, np.ndarray], bool]:
    cached_fields = load_cached_flow_fields(velocity_config, temp_config)
    if cached_fields is not None:
        return {"config": velocity_config, "grid": {}, "cache_mode": "shared_velocity_output"}, cached_fields, True

    velocity_results = run_pipeline(velocity_config)
    fields = extract_slice_fields(velocity_results, velocity_config, temp_config)
    fields["cache_reused"] = np.array([0], dtype=np.int32)
    return velocity_results, fields, False


def save_shared_velocity_cache(
    fields: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp_config: TemperatureScenarioConfig,
) -> str:
    cache_dir = Path(temp_config.reuse_velocity_output_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / "velocity_u_slice.npy", fields["u"])
    np.save(cache_dir / "velocity_v_slice.npy", fields["v"])
    np.save(cache_dir / "velocity_speed_slice.npy", fields["speed"])
    np.save(cache_dir / "building_mask.npy", fields["building_mask"])
    np.save(cache_dir / "study_area_mask.npy", fields["study_area_mask"])
    np.save(cache_dir / "vegetation_mask.npy", fields["vegetation_mask"])
    np.save(cache_dir / "urban_mask.npy", fields["urban_mask"])
    np.save(cache_dir / "height_field.npy", fields["height_field"])
    summary = {
        "velocity_config": asdict(velocity_config),
        "slice_idx": int(fields["slice_idx"][0]),
        "velocity_shape": list(fields["u"].shape),
    }
    summary_path = cache_dir / "velocity_cache_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    return str(summary_path)


def build_summer_afternoon_source(
    fields: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp_config: TemperatureScenarioConfig,
) -> dict[str, np.ndarray]:
    building_mask = fields["building_mask"]
    vegetation_mask = fields["vegetation_mask"]
    urban_mask = fields["urban_mask"]
    height_field = fields["height_field"]
    study_area_mask = fields["study_area_mask"]

    hotspot = np.zeros_like(height_field, dtype=np.float32)
    analysis_time_utc = parse_utc_datetime(temp_config.analysis_time_utc)
    solar_elevation_deg, solar_azimuth_deg = compute_solar_position_deg(
        temp_config.site_latitude_deg,
        temp_config.site_longitude_deg,
        analysis_time_utc,
    )

    shade_field = compute_building_shadow_field(
        building_mask,
        height_field,
        grid_resolution_m=float(velocity_config.model_resolution_m),
        solar_elevation_deg=solar_elevation_deg,
        solar_azimuth_deg=solar_azimuth_deg,
        soften_passes=temp_config.shadow_soften_passes,
    )
    source_c_per_hour = (
        temp_config.background_source_c_per_hour
        + temp_config.urban_source_c_per_hour * urban_mask.astype(np.float32)
        - temp_config.vegetation_cooling_c_per_hour * vegetation_mask.astype(np.float32)
        - temp_config.shade_cooling_c_per_hour * shade_field
    ).astype(np.float32)

    initial_temperature_c = (
        temp_config.ambient_temp_c
        + temp_config.initial_urban_excess_c * urban_mask.astype(np.float32)
        - temp_config.initial_vegetation_cooling_c * vegetation_mask.astype(np.float32)
        - 0.5 * shade_field
    ).astype(np.float32)

    source_c_per_hour[building_mask] = 0.0
    initial_temperature_c[building_mask] = temp_config.fixed_building_temp_c
    source_c_per_hour[~study_area_mask] = 0.0
    initial_temperature_c[~study_area_mask] = temp_config.ambient_temp_c

    return {
        "source_c_per_hour": source_c_per_hour,
        "source_c_per_second": per_hour_to_per_second(source_c_per_hour),
        "initial_temperature_c": initial_temperature_c,
        "hotspot": hotspot,
        "shade_field": shade_field,
        "study_area_mask": study_area_mask,
        "solar_elevation_deg": np.array([solar_elevation_deg], dtype=np.float32),
        "solar_azimuth_deg": np.array([solar_azimuth_deg], dtype=np.float32),
    }


def neighbour_views(field: np.ndarray, solid_mask: np.ndarray) -> tuple[np.ndarray, ...]:
    left = np.empty_like(field)
    right = np.empty_like(field)
    up = np.empty_like(field)
    down = np.empty_like(field)

    left[:, 0] = field[:, 0]
    left[:, 1:] = field[:, :-1]
    right[:, -1] = field[:, -1]
    right[:, :-1] = field[:, 1:]
    up[0, :] = field[0, :]
    up[1:, :] = field[:-1, :]
    down[-1, :] = field[-1, :]
    down[:-1, :] = field[1:, :]

    solid_left = np.empty_like(solid_mask)
    solid_right = np.empty_like(solid_mask)
    solid_up = np.empty_like(solid_mask)
    solid_down = np.empty_like(solid_mask)

    solid_left[:, 0] = True
    solid_left[:, 1:] = solid_mask[:, :-1]
    solid_right[:, -1] = True
    solid_right[:, :-1] = solid_mask[:, 1:]
    solid_up[0, :] = True
    solid_up[1:, :] = solid_mask[:-1, :]
    solid_down[-1, :] = True
    solid_down[:-1, :] = solid_mask[1:, :]

    left = np.where(solid_left, field, left)
    right = np.where(solid_right, field, right)
    up = np.where(solid_up, field, up)
    down = np.where(solid_down, field, down)

    return left, right, up, down


def impose_boundary_conditions(
    temperature_c: np.ndarray,
    fluid_mask: np.ndarray,
    temp_config: TemperatureScenarioConfig,
) -> None:
    rows = temperature_c.shape[0]
    vertical_profile = np.linspace(
        temp_config.inflow_temp_c + 0.3,
        temp_config.inflow_temp_c - 0.2,
        rows,
        dtype=np.float32,
    )

    left_fluid = fluid_mask[:, 0]
    temperature_c[left_fluid, 0] = vertical_profile[left_fluid]
    temperature_c[:, -1] = np.where(
        fluid_mask[:, -1],
        temperature_c[:, -2],
        temperature_c[:, -1],
    )
    temperature_c[0, :] = np.where(fluid_mask[0, :], temperature_c[1, :], temperature_c[0, :])
    temperature_c[-1, :] = np.where(
        fluid_mask[-1, :],
        temperature_c[-2, :],
        temperature_c[-1, :],
    )


def solve_temperature_fields(
    fields: dict[str, np.ndarray],
    scenario: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp_config: TemperatureScenarioConfig,
) -> dict[str, object]:
    u_frames = fields["u"]
    v_frames = fields["v"]
    building_mask = fields["building_mask"]
    study_area_mask = fields["study_area_mask"]
    fluid_mask = (~building_mask) & study_area_mask
    source_c_per_second = scenario["source_c_per_second"]
    dx = float(velocity_config.model_resolution_m)
    dy = dx
    cooling_relaxation_per_second = per_hour_to_per_second(
        temp_config.ambient_cooling_c_per_hour
    )
    source_decay = float(np.clip(temp_config.afternoon_source_decay, 0.0, 1.0))

    u_frames = temp_config.velocity_scale * u_frames
    v_frames = temp_config.velocity_scale * v_frames
    max_speed = float(
        np.max(np.sqrt(u_frames**2 + v_frames**2))
    )
    stable_dt = temp_config.max_courant * min(dx, dy) / max(max_speed, 1e-6)
    diffusion_dt = 0.24 * min(dx, dy) ** 2 / max(temp_config.diffusion_coeff_m2_s, 1e-6)
    dt = min(stable_dt, diffusion_dt, temp_config.frame_duration_s)
    substeps = max(1, int(math.ceil(temp_config.frame_duration_s / max(dt, 1e-6))))
    dt = temp_config.frame_duration_s / substeps

    temperature_c = scenario["initial_temperature_c"].astype(np.float32).copy()
    impose_boundary_conditions(temperature_c, fluid_mask, temp_config)

    temperature_frames = [temperature_c.copy()]
    frame_means = [float(np.mean(temperature_c[fluid_mask]))]

    for frame_idx in range(u_frames.shape[0]):
        u = u_frames[frame_idx]
        v = v_frames[frame_idx]
        if u_frames.shape[0] <= 1:
            source_scale = 1.0
        else:
            progress = frame_idx / float(u_frames.shape[0] - 1)
            source_scale = 1.0 - source_decay * progress
        frame_source_c_per_second = source_c_per_second * source_scale

        for _ in range(substeps):
            left, right, up, down = neighbour_views(temperature_c, building_mask)

            dtdx_backward = (temperature_c - left) / dx
            dtdx_forward = (right - temperature_c) / dx
            dtdy_backward = (temperature_c - up) / dy
            dtdy_forward = (down - temperature_c) / dy

            adv_x = np.where(u >= 0.0, u * dtdx_backward, u * dtdx_forward)
            adv_y = np.where(v >= 0.0, v * dtdy_backward, v * dtdy_forward)
            laplacian = (left - 2.0 * temperature_c + right) / (dx**2) + (
                up - 2.0 * temperature_c + down
            ) / (dy**2)
            ambient_cooling = cooling_relaxation_per_second * (
                temp_config.ambient_temp_c - temperature_c
            )

            next_temperature = temperature_c + dt * (
                -(adv_x + adv_y)
                + temp_config.diffusion_coeff_m2_s * laplacian
                + frame_source_c_per_second
                + ambient_cooling
            )

            next_temperature[building_mask] = temp_config.fixed_building_temp_c
            next_temperature[~study_area_mask] = temp_config.ambient_temp_c
            temperature_c = next_temperature
            impose_boundary_conditions(temperature_c, fluid_mask, temp_config)

        temperature_frames.append(temperature_c.copy())
        frame_means.append(float(np.mean(temperature_c[fluid_mask])))

    temperature_array = np.stack(temperature_frames, axis=0)
    masked_array = temperature_array.copy()
    masked_array[:, building_mask | (~study_area_mask)] = np.nan

    return {
        "temperature_fields_c": temperature_array,
        "temperature_fields_masked_c": masked_array,
        "fluid_mask": fluid_mask,
        "study_area_mask": study_area_mask,
        "dt_seconds": float(dt),
        "substeps_per_frame": int(substeps),
        "frame_means_c": np.asarray(frame_means, dtype=np.float32),
    }


def plot_temperature_panels(
    temperature_fields_c: np.ndarray,
    source_c_per_hour: np.ndarray,
    scenario: dict[str, np.ndarray],
    time_indices: list[int],
) -> object:
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("matplotlib is required for plotting temperature panels.")

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    source_ax, hotspot_ax, shade_ax = axes[0]
    study_area_mask = scenario["study_area_mask"]
    source_display = np.where(study_area_mask, source_c_per_hour, np.nan)
    hotspot_display = np.where(study_area_mask, scenario["hotspot"], np.nan)
    shade_display = np.where(study_area_mask, scenario["shade_field"], np.nan)

    source_im = source_ax.imshow(source_display, cmap="YlOrRd", origin="upper")
    source_ax.set_title("Heat Source (C/hour)")
    fig.colorbar(source_im, ax=source_ax, shrink=0.8)

    hotspot_im = hotspot_ax.imshow(hotspot_display, cmap="Oranges", origin="upper")
    hotspot_ax.set_title("Hotspot Weight (Disabled)")
    fig.colorbar(hotspot_im, ax=hotspot_ax, shrink=0.8)

    shade_im = shade_ax.imshow(shade_display, cmap="Greys", origin="upper")
    shade_ax.set_title("Solar Shadow Cooling")
    fig.colorbar(shade_im, ax=shade_ax, shrink=0.8)

    safe_indices = [min(max(idx, 0), temperature_fields_c.shape[0] - 1) for idx in time_indices]
    temp_vmin = float(np.nanmin(temperature_fields_c))
    temp_vmax = float(np.nanmax(temperature_fields_c))
    for ax, idx in zip(axes[1], safe_indices):
        temp_im = ax.imshow(
            temperature_fields_c[idx],
            cmap="YlOrRd",
            origin="upper",
            vmin=temp_vmin,
            vmax=temp_vmax,
        )
        ax.set_title(f"Temperature Frame {idx}")
        fig.colorbar(temp_im, ax=ax, shrink=0.8)

    fig.tight_layout()
    return fig


def save_temperature_animation(
    temperature_fields_masked_c: np.ndarray,
    output_dir: Path,
    filename_prefix: str = "temperature",
) -> dict[str, Path]:
    if not MATPLOTLIB_AVAILABLE or HTML is None:
        return {}

    frames = temperature_fields_masked_c
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(
        frames[0],
        cmap="YlOrRd",
        origin="upper",
        vmin=float(np.nanmin(frames)),
        vmax=float(np.nanmax(frames)),
    )
    ax.set_title("Temperature Field")
    fig.colorbar(image, ax=ax, shrink=0.8)

    def update(frame_idx: int) -> None:
        image.set_array(frames[frame_idx])
        ax.set_title(f"Temperature Field Frame {frame_idx}")

    stride = max(1, frames.shape[0] // 40)
    frame_ids = list(range(0, frames.shape[0], stride))
    animation = mpl_animation.FuncAnimation(fig, update, frames=frame_ids)

    html_path = output_dir / f"{filename_prefix}_animation.html"
    html_path.write_text(animation.to_jshtml())

    saved: dict[str, Path] = {"html": html_path}
    try:
        gif_path = output_dir / f"{filename_prefix}_animation.gif"
        animation.save(gif_path, writer="pillow", fps=8)
        saved["gif"] = gif_path
    except Exception:
        pass
    finally:
        plt.close(fig)

    return saved


def save_results(
    velocity_results: dict[str, object],
    fields: dict[str, np.ndarray],
    scenario: dict[str, np.ndarray],
    temperature_results: dict[str, object],
    velocity_config: SouthKensingtonConfig,
    temp_config: TemperatureScenarioConfig,
    cache_reused: bool,
) -> dict[str, object]:
    out_dir = Path(temp_config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shared_cache_summary_path = save_shared_velocity_cache(fields, velocity_config, temp_config)

    np.save(out_dir / "velocity_u_slice.npy", fields["u"])
    np.save(out_dir / "velocity_v_slice.npy", fields["v"])
    np.save(out_dir / "velocity_speed_slice.npy", fields["speed"])
    np.save(out_dir / "building_mask.npy", fields["building_mask"])
    np.save(out_dir / "study_area_mask.npy", fields["study_area_mask"])
    np.save(out_dir / "vegetation_mask.npy", fields["vegetation_mask"])
    np.save(out_dir / "urban_mask.npy", fields["urban_mask"])
    np.save(out_dir / "height_field.npy", fields["height_field"])
    np.save(out_dir / "source_c_per_hour.npy", scenario["source_c_per_hour"])
    np.save(out_dir / "initial_temperature_c.npy", scenario["initial_temperature_c"])
    np.save(out_dir / "temperature_fields_c.npy", temperature_results["temperature_fields_c"])
    np.save(
        out_dir / "temperature_fields_masked_c.npy",
        temperature_results["temperature_fields_masked_c"],
    )
    np.save(out_dir / "frame_mean_temperature_c.npy", temperature_results["frame_means_c"])

    figure_path = None
    if MATPLOTLIB_AVAILABLE:
        n_frames = temperature_results["temperature_fields_c"].shape[0]
        time_indices = [0, n_frames // 2, n_frames - 1]
        fig = plot_temperature_panels(
            temperature_results["temperature_fields_masked_c"],
            scenario["source_c_per_hour"],
            scenario,
            time_indices,
        )
        figure_path = out_dir / "temperature_overview.png"
        fig.savefig(figure_path, dpi=180, bbox_inches="tight")
        plt.close(fig)

    animation_paths = {}
    if temp_config.save_animation:
        animation_paths = save_temperature_animation(
            temperature_results["temperature_fields_masked_c"],
            out_dir,
        )

    summary = {
        "velocity_config": asdict(velocity_config),
        "temperature_config": asdict(temp_config),
        "grid": velocity_results["grid"],
        "cache_reused": bool(cache_reused),
        "shared_velocity_cache_summary_path": shared_cache_summary_path,
        "slice_idx": int(fields["slice_idx"][0]),
        "velocity_shape": list(fields["u"].shape),
        "temperature_shape": list(temperature_results["temperature_fields_c"].shape),
        "dt_seconds": float(temperature_results["dt_seconds"]),
        "substeps_per_frame": int(temperature_results["substeps_per_frame"]),
        "temperature_min_c": float(np.nanmin(temperature_results["temperature_fields_masked_c"])),
        "temperature_max_c": float(np.nanmax(temperature_results["temperature_fields_masked_c"])),
        "figure_path": str(figure_path) if figure_path else None,
        "animation_paths": {key: str(path) for key, path in animation_paths.items()},
        "scenario_note": "Summer afternoon urban heating over South Kensington with solar-position-based building shadow cooling and vegetation cooling, without an imposed local hotspot.",
        "solar_elevation_deg": float(scenario["solar_elevation_deg"][0]),
        "solar_azimuth_deg": float(scenario["solar_azimuth_deg"][0]),
    }
    summary_path = out_dir / "temperature_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    summary["summary_path"] = str(summary_path)
    return summary


def run_temperature_label_pipeline(
    velocity_config: SouthKensingtonConfig | None = None,
    temp_config: TemperatureScenarioConfig | None = None,
) -> dict[str, object]:
    velocity_config = velocity_config or SouthKensingtonConfig()
    temp_config = temp_config or TemperatureScenarioConfig()

    velocity_results, fields, cache_reused = extract_or_load_flow_fields(velocity_config, temp_config)
    scenario = build_summer_afternoon_source(fields, velocity_config, temp_config)
    temperature_results = solve_temperature_fields(fields, scenario, velocity_config, temp_config)
    summary = save_results(
        velocity_results,
        fields,
        scenario,
        temperature_results,
        velocity_config,
        temp_config,
        cache_reused,
    )
    return {
        "velocity_results": velocity_results,
        "fields": fields,
        "scenario": scenario,
        "temperature_results": temperature_results,
        "summary": summary,
    }


def show_temperature_animation(run_outputs: dict[str, object]) -> object:
    if not MATPLOTLIB_AVAILABLE or HTML is None:
        raise RuntimeError("Animation display requires matplotlib and IPython.")
    frames = run_outputs["temperature_results"]["temperature_fields_masked_c"]
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(
        frames[0],
        cmap="YlOrRd",
        origin="upper",
        vmin=float(np.nanmin(frames)),
        vmax=float(np.nanmax(frames)),
    )
    fig.colorbar(image, ax=ax, shrink=0.8)

    def update(frame_idx: int) -> None:
        image.set_array(frames[frame_idx])
        ax.set_title(f"Temperature Frame {frame_idx}")

    animation = mpl_animation.FuncAnimation(fig, update, frames=range(frames.shape[0]))
    return HTML(animation.to_jshtml())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate South Kensington temperature labels from DIGIT velocity fields."
    )
    parser.add_argument("--timesteppings", type=int, default=70, help="Number of DIGIT rollout steps.")
    parser.add_argument("--model-resolution-m", type=float, default=4.0, help="Horizontal model resolution.")
    parser.add_argument("--slice-idx", type=int, default=4, help="Vertical slice index for the temperature solve.")
    parser.add_argument(
        "--frame-duration-s",
        type=float,
        default=90.0,
        help="Physical duration represented by each DIGIT velocity frame.",
    )
    parser.add_argument(
        "--diffusion-coeff",
        type=float,
        default=1.0,
        help="Effective thermal diffusion coefficient in m^2/s.",
    )
    parser.add_argument(
        "--afternoon-source-decay",
        type=float,
        default=0.0,
        help="Fractional reduction in the heating source from the first to the last frame.",
    )
    parser.add_argument(
        "--ambient-cooling-per-hour",
        type=float,
        default=0.22,
        help="Weak relaxation rate pulling temperatures back toward ambient conditions.",
    )
    parser.add_argument(
        "--site-latitude-deg",
        type=float,
        default=TemperatureScenarioConfig.site_latitude_deg,
        help="Site latitude in degrees for the solar-position calculation.",
    )
    parser.add_argument(
        "--site-longitude-deg",
        type=float,
        default=TemperatureScenarioConfig.site_longitude_deg,
        help="Site longitude in degrees for the solar-position calculation.",
    )
    parser.add_argument(
        "--analysis-time-utc",
        default=TemperatureScenarioConfig.analysis_time_utc,
        help="UTC timestamp used to compute the solar elevation and azimuth, e.g. 2025-07-25T13:00:00+00:00.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(BUNDLE_ROOT / "outputs" / "south_kensington_temperature"),
        help="Directory for saved temperature labels and figures.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    velocity_config = SouthKensingtonConfig(
        timesteppings=args.timesteppings,
        model_resolution_m=args.model_resolution_m,
        output_dir=str(BUNDLE_ROOT / "outputs" / "south_kensington_velocity"),
    )
    temp_config = TemperatureScenarioConfig(
        output_dir=args.output_dir,
        slice_idx=args.slice_idx,
        frame_duration_s=args.frame_duration_s,
        diffusion_coeff_m2_s=args.diffusion_coeff,
        site_latitude_deg=args.site_latitude_deg,
        site_longitude_deg=args.site_longitude_deg,
        analysis_time_utc=args.analysis_time_utc,
        afternoon_source_decay=args.afternoon_source_decay,
        ambient_cooling_c_per_hour=args.ambient_cooling_per_hour,
    )
    run_outputs = run_temperature_label_pipeline(velocity_config, temp_config)
    print(json.dumps(run_outputs["summary"], indent=2))


if __name__ == "__main__":
    main()
