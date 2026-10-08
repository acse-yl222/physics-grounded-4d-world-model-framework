from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import numpy as np

try:
    import torch

    TORCH_AVAILABLE = True
except ModuleNotFoundError:
    torch = None
    TORCH_AVAILABLE = False

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
from south_kensington_jupyter import rotate_2d_field
from south_kensington_temperature import (
    compute_building_shadow_field,
    compute_solar_position_deg,
    embed_in_velocity_grid,
    parse_utc_datetime,
    resize_nearest_2d,
)


BUNDLE_ROOT = Path(__file__).resolve().parent


@dataclass
class Temperature3DScenarioConfig:
    output_dir: str = str(BUNDLE_ROOT / "outputs" / "south_kensington_temperature_3d")
    reuse_velocity_output_dir: str = str(BUNDLE_ROOT / "outputs" / "south_kensington_velocity_3d")
    frame_duration_s: float = 90.0
    max_courant: float = 0.30
    diffusion_coeff_m2_s: float = 1.0
    velocity_scale: float = 1.0
    ambient_temp_c: float = 24.2
    inflow_temp_c: float = 24.2
    ambient_relative_humidity_pct: float = 47.19
    air_pressure_pa: float = 101325.0
    cloud_cover_fraction: float = 0.47
    reference_wind_speed_m_s: float = 3.09
    reference_wind_direction_deg: float = 268.41
    site_latitude_deg: float = 51.505763
    site_longitude_deg: float = -0.189031
    analysis_time_utc: str = "2025-07-25T13:00:00+00:00"
    background_temp_reference_hour_local: float = 14.0
    background_temp_delta_hours_local: tuple[float, ...] = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    background_temp_delta_c: tuple[float, ...] = (0.0, 0.1, 0.4, 0.8, 0.9, 0.8, -0.3)
    shadow_soften_passes: int = 2
    reference_crop_albedo: float = 0.23
    priestley_taylor_alpha: float = 1.26
    urban_albedo: float = 0.18
    open_ground_albedo: float = 0.20
    vegetation_albedo: float = 0.23
    urban_emissivity: float = 0.95
    open_ground_emissivity: float = 0.95
    vegetation_emissivity: float = 0.97
    urban_storage_fraction: float = 0.55
    open_ground_storage_fraction: float = 0.45
    vegetation_storage_fraction: float = 0.25
    urban_evaporation_fraction_of_et0: float = 0.05
    open_ground_evaporation_fraction_of_et0: float = 0.20
    vegetation_basal_crop_coefficient: float = 1.00
    anthropogenic_heat_flux_w_m2: float = 15.0
    air_heat_capacity_j_kg_k: float = 1005.0
    save_animation: bool = True
    save_overview_figure: bool = True
    temperature_solver_backend: str = "auto"
    temperature_solver_device: str = "cuda"


def per_hour_to_per_second(value: float) -> float:
    return value / 3600.0


def saturation_vapour_pressure_pa(temp_c: float | np.ndarray) -> np.ndarray:
    temp_c = np.asarray(temp_c, dtype=np.float64)
    return 611.2 * np.exp((17.67 * temp_c) / (temp_c + 243.5))


def slope_svp_curve_kpa_per_c(temp_c: float) -> float:
    es_kpa = 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    return 4098.0 * es_kpa / ((temp_c + 237.3) ** 2)


def psychrometric_constant_kpa_per_c(pressure_pa: float) -> float:
    return 0.000665 * (pressure_pa / 1000.0)


def clear_sky_ghi_haurwitz_w_m2(solar_zenith_deg: float) -> float:
    cos_zenith = max(math.cos(math.radians(solar_zenith_deg)), 0.0)
    if cos_zenith <= 0.0:
        return 0.0
    return float(1098.0 * cos_zenith * math.exp(-0.059 / cos_zenith))


def cloud_transmittance_kasten_czeplak(cloud_cover_fraction: float) -> float:
    cloud_fraction = float(np.clip(cloud_cover_fraction, 0.0, 1.0))
    return float(np.clip(1.0 - 0.75 * (cloud_fraction**3.4), 0.0, 1.0))


def estimate_reference_et0_mm_per_hour(
    temp_c: float,
    pressure_pa: float,
    solar_elevation_deg: float,
    cloud_cover_fraction: float,
    reference_crop_albedo: float,
    priestley_taylor_alpha: float,
) -> dict[str, float]:
    solar_zenith_deg = 90.0 - solar_elevation_deg
    ghi_clear_w_m2 = clear_sky_ghi_haurwitz_w_m2(solar_zenith_deg)
    ghi_w_m2 = ghi_clear_w_m2 * cloud_transmittance_kasten_czeplak(cloud_cover_fraction)
    net_shortwave_w_m2 = max((1.0 - reference_crop_albedo) * ghi_w_m2, 0.0)
    delta = slope_svp_curve_kpa_per_c(temp_c)
    gamma = psychrometric_constant_kpa_per_c(pressure_pa)
    latent_heat_j_kg = 2.45e6
    et0_mm_per_hour = (
        priestley_taylor_alpha
        * (delta / max(delta + gamma, 1e-6))
        * net_shortwave_w_m2
        / latent_heat_j_kg
        * 3600.0
    )
    return {
        "ghi_clear_w_m2": float(ghi_clear_w_m2),
        "ghi_w_m2": float(ghi_w_m2),
        "net_shortwave_w_m2": float(net_shortwave_w_m2),
        "et0_mm_per_hour": float(max(et0_mm_per_hour, 0.0)),
    }


def air_density_kg_m3(temp_c: float, pressure_pa: float) -> float:
    return float(pressure_pa / (287.05 * (temp_c + 273.15)))


def vapour_pressure_pa(temp_c: float, relative_humidity_pct: float) -> float:
    return float(
        (np.clip(relative_humidity_pct, 0.0, 100.0) / 100.0) * saturation_vapour_pressure_pa(temp_c)
    )


def estimate_downwelling_longwave_w_m2(
    temp_c: float,
    relative_humidity_pct: float,
    cloud_cover_fraction: float,
) -> float:
    air_temp_k = temp_c + 273.15
    vapour_pressure_hpa = vapour_pressure_pa(temp_c, relative_humidity_pct) / 100.0
    eps_clear = 1.24 * (max(vapour_pressure_hpa, 1e-6) / max(air_temp_k, 1e-6)) ** (1.0 / 7.0)
    eps_sky = (1.0 - cloud_cover_fraction) * eps_clear + cloud_cover_fraction
    sigma = 5.670374419e-8
    return float(np.clip(eps_sky, 0.0, 1.0) * sigma * air_temp_k**4)


def convective_heat_transfer_coeff_w_m2_k(local_speed_m_s: np.ndarray) -> np.ndarray:
    local_speed_m_s = np.maximum(np.asarray(local_speed_m_s, dtype=np.float32), 0.0)
    return np.where(
        local_speed_m_s <= 5.0,
        6.15 + 4.18 * local_speed_m_s,
        7.51 * np.maximum(local_speed_m_s, 1e-6) ** 0.78,
    ).astype(np.float32)


def solve_surface_temperature_excess_c(
    absorbed_shortwave_w_m2: np.ndarray,
    emissivity: np.ndarray,
    latent_heat_flux_w_m2: np.ndarray,
    storage_fraction: np.ndarray,
    convective_coeff_w_m2_k: np.ndarray,
    downwelling_longwave_w_m2: float,
    ambient_temp_c: float,
    anthropogenic_heat_flux_w_m2: np.ndarray | float,
) -> np.ndarray:
    sigma = 5.670374419e-8
    air_temp_k = ambient_temp_c + 273.15
    radiative_coeff = 4.0 * emissivity * sigma * air_temp_k**3
    net_longwave_w_m2 = emissivity * (downwelling_longwave_w_m2 - sigma * air_temp_k**4)
    available_flux_w_m2 = (
        absorbed_shortwave_w_m2 * (1.0 - storage_fraction)
        + net_longwave_w_m2
        + np.asarray(anthropogenic_heat_flux_w_m2, dtype=np.float32)
        - latent_heat_flux_w_m2
    )
    denom = np.maximum(convective_coeff_w_m2_k + radiative_coeff, 1e-6)
    return (available_flux_w_m2 / denom).astype(np.float32)


def build_ambient_temperature_series_c(
    temp3d_config: Temperature3DScenarioConfig,
    n_frames: int,
) -> np.ndarray:
    analysis_time_utc = parse_utc_datetime(temp3d_config.analysis_time_utc).astimezone(timezone.utc)
    analysis_time_local = analysis_time_utc.astimezone(ZoneInfo("Europe/London"))
    start_hour_local = (
        analysis_time_local.hour
        + analysis_time_local.minute / 60.0
        + analysis_time_local.second / 3600.0
    )
    schedule_hours = temp3d_config.background_temp_reference_hour_local + np.asarray(
        temp3d_config.background_temp_delta_hours_local, dtype=np.float32
    )
    schedule_temps = temp3d_config.ambient_temp_c + np.asarray(
        temp3d_config.background_temp_delta_c,
        dtype=np.float32,
    )
    elapsed_hours = (
        np.arange(n_frames, dtype=np.float32) * float(temp3d_config.frame_duration_s) / 3600.0
    )
    query_hours = start_hour_local + elapsed_hours
    return np.interp(
        query_hours,
        schedule_hours,
        schedule_temps,
        left=float(schedule_temps[0]),
        right=float(schedule_temps[-1]),
    ).astype(np.float32)


def load_cached_full_velocity_fields(
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
) -> dict[str, np.ndarray] | None:
    cache_dir = Path(temp3d_config.reuse_velocity_output_dir)
    summary_path = cache_dir / "velocity_3d_cache_summary.json"
    required = [
        cache_dir / "velocity_u_3d.npy",
        cache_dir / "velocity_v_3d.npy",
        cache_dir / "velocity_w_3d.npy",
        cache_dir / "velocity_speed_3d.npy",
        cache_dir / "building_mask_2d.npy",
        cache_dir / "vegetation_mask_2d.npy",
        cache_dir / "urban_mask_2d.npy",
        cache_dir / "open_ground_mask_2d.npy",
        cache_dir / "study_area_mask_2d.npy",
        cache_dir / "height_field_2d.npy",
        cache_dir / "solid_mask_3d.npy",
        cache_dir / "roof_mask_3d.npy",
    ]
    if not summary_path.exists() or any(not path.exists() for path in required):
        return None
    if any(path.stat().st_size == 0 for path in required):
        return None

    try:
        summary = json.loads(summary_path.read_text())
    except json.JSONDecodeError:
        return None

    cached_velocity_config = summary.get("velocity_config", {})
    if (
        int(cached_velocity_config.get("timesteppings", -1)) != int(velocity_config.timesteppings)
        or not np.isclose(
            float(cached_velocity_config.get("inlet_flow", np.nan)),
            float(velocity_config.inlet_flow),
        )
        or not np.isclose(
            float(cached_velocity_config.get("model_resolution_m", np.nan)),
            float(velocity_config.model_resolution_m),
        )
        or int(cached_velocity_config.get("z_dim", -1)) != int(velocity_config.z_dim)
        or int(cached_velocity_config.get("geometry_rotation_deg", 0)) % 360
        != int(getattr(velocity_config, "geometry_rotation_deg", 0)) % 360
        or not np.isclose(
            float(cached_velocity_config.get("height_scale_m", np.nan)),
            float(velocity_config.height_scale_m),
        )
    ):
        return None

    try:
        return {
            "u": np.load(cache_dir / "velocity_u_3d.npy").astype(np.float32),
            "v": np.load(cache_dir / "velocity_v_3d.npy").astype(np.float32),
            "w": np.load(cache_dir / "velocity_w_3d.npy").astype(np.float32),
            "speed": np.load(cache_dir / "velocity_speed_3d.npy").astype(np.float32),
            "building_mask_2d": np.load(cache_dir / "building_mask_2d.npy").astype(bool),
            "vegetation_mask_2d": np.load(cache_dir / "vegetation_mask_2d.npy").astype(bool),
            "urban_mask_2d": np.load(cache_dir / "urban_mask_2d.npy").astype(bool),
            "open_ground_mask_2d": np.load(cache_dir / "open_ground_mask_2d.npy").astype(bool),
            "study_area_mask_2d": np.load(cache_dir / "study_area_mask_2d.npy").astype(bool),
            "height_field_2d": np.load(cache_dir / "height_field_2d.npy").astype(np.float32),
            "solid_mask_3d": np.load(cache_dir / "solid_mask_3d.npy").astype(bool),
            "roof_mask_3d": np.load(cache_dir / "roof_mask_3d.npy").astype(bool),
            "cache_reused": np.array([1], dtype=np.int32),
        }
    except (OSError, ValueError, EOFError) as exc:
        print(f"[velocity-cache] invalid cache at {cache_dir}: {exc}. Regenerating.")
        return None


def shift_up_boolean(field: np.ndarray) -> np.ndarray:
    shifted = np.zeros_like(field, dtype=bool)
    shifted[:-1, :, :] = field[1:, :, :]
    return shifted


def extract_full_3d_fields(
    velocity_results: dict[str, object],
    velocity_config: SouthKensingtonConfig,
) -> dict[str, np.ndarray]:
    predictions_3d = np.asarray(velocity_results["predictions_3d"], dtype=np.float32)
    u = predictions_3d[:, 0, :, :, :]
    v = predictions_3d[:, 1, :, :, :]
    w = predictions_3d[:, 2, :, :, :]
    speed = np.sqrt(u**2 + v**2 + w**2)

    volume_shape = u.shape[1:]
    _, vol_y, vol_x = volume_shape
    building_mask_small = np.asarray(velocity_results["mask_resampled"], dtype=bool)
    height_field_small = np.asarray(velocity_results["height_resampled"], dtype=np.float32)
    land_cover = np.load(Path(velocity_config.static_dir) / "land_cover.npy")
    land_cover = rotate_2d_field(
        land_cover, int(getattr(velocity_config, "geometry_rotation_deg", 0))
    )
    if land_cover.shape != building_mask_small.shape:
        land_cover = resize_nearest_2d(land_cover, building_mask_small.shape)

    offset_y = int(velocity_config.embed_pad_y)
    offset_x = int(velocity_config.embed_pad_x)
    target_shape = (vol_y, vol_x)
    building_mask_2d = embed_in_velocity_grid(
        building_mask_small.astype(np.uint8), target_shape, offset_y, offset_x, fill_value=0
    ).astype(bool)
    height_field_2d = embed_in_velocity_grid(
        height_field_small.astype(np.float32), target_shape, offset_y, offset_x, fill_value=0.0
    )
    vegetation_mask_2d = embed_in_velocity_grid(
        np.asarray(land_cover == 10, dtype=np.uint8), target_shape, offset_y, offset_x, fill_value=0
    ).astype(bool)
    urban_mask_2d = embed_in_velocity_grid(
        (np.asarray(land_cover == 50, dtype=np.uint8) & (~building_mask_small).astype(np.uint8)),
        target_shape,
        offset_y,
        offset_x,
        fill_value=0,
    ).astype(bool)
    study_area_mask_2d = embed_in_velocity_grid(
        np.ones_like(building_mask_small, dtype=np.uint8),
        target_shape,
        offset_y,
        offset_x,
        fill_value=0,
    ).astype(bool)
    open_ground_mask_2d = (
        study_area_mask_2d & (~building_mask_2d) & (~vegetation_mask_2d) & (~urban_mask_2d)
    )

    dz = float(velocity_config.height_scale_m)
    z_bottoms = np.arange(volume_shape[0], dtype=np.float32)[:, None, None] * dz
    solid_mask_3d = z_bottoms < height_field_2d[None, :, :]
    roof_mask_3d = solid_mask_3d & (~shift_up_boolean(solid_mask_3d))

    return {
        "u": u,
        "v": v,
        "w": w,
        "speed": speed,
        "building_mask_2d": building_mask_2d,
        "vegetation_mask_2d": vegetation_mask_2d,
        "urban_mask_2d": urban_mask_2d,
        "open_ground_mask_2d": open_ground_mask_2d,
        "study_area_mask_2d": study_area_mask_2d,
        "height_field_2d": height_field_2d,
        "solid_mask_3d": solid_mask_3d.astype(bool),
        "roof_mask_3d": roof_mask_3d.astype(bool),
        "cache_reused": np.array([0], dtype=np.int32),
    }


def save_shared_full_velocity_cache(
    fields: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
) -> str:
    cache_dir = Path(temp3d_config.reuse_velocity_output_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / "velocity_u_3d.npy", fields["u"])
    np.save(cache_dir / "velocity_v_3d.npy", fields["v"])
    np.save(cache_dir / "velocity_w_3d.npy", fields["w"])
    np.save(cache_dir / "velocity_speed_3d.npy", fields["speed"])
    np.save(cache_dir / "building_mask_2d.npy", fields["building_mask_2d"])
    np.save(cache_dir / "vegetation_mask_2d.npy", fields["vegetation_mask_2d"])
    np.save(cache_dir / "urban_mask_2d.npy", fields["urban_mask_2d"])
    np.save(cache_dir / "open_ground_mask_2d.npy", fields["open_ground_mask_2d"])
    np.save(cache_dir / "study_area_mask_2d.npy", fields["study_area_mask_2d"])
    np.save(cache_dir / "height_field_2d.npy", fields["height_field_2d"])
    np.save(cache_dir / "solid_mask_3d.npy", fields["solid_mask_3d"])
    np.save(cache_dir / "roof_mask_3d.npy", fields["roof_mask_3d"])
    summary = {
        "velocity_config": asdict(velocity_config),
        "velocity_shape": list(fields["u"].shape),
    }
    summary_path = cache_dir / "velocity_3d_cache_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    return str(summary_path)


def extract_or_load_full_velocity_fields(
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
) -> tuple[dict[str, object], dict[str, np.ndarray], bool]:
    cached_fields = load_cached_full_velocity_fields(velocity_config, temp3d_config)
    if cached_fields is not None:
        return (
            {"config": velocity_config, "grid": {}, "cache_mode": "shared_velocity_3d_output"},
            cached_fields,
            True,
        )

    velocity_results = run_pipeline(velocity_config)
    fields = extract_full_3d_fields(velocity_results, velocity_config)
    return velocity_results, fields, False


def build_surface_temperature_fields(
    fields: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
) -> dict[str, np.ndarray]:
    building_mask_2d = fields["building_mask_2d"]
    vegetation_mask_2d = fields["vegetation_mask_2d"]
    urban_mask_2d = fields["urban_mask_2d"]
    open_ground_mask_2d = fields["open_ground_mask_2d"]
    study_area_mask_2d = fields["study_area_mask_2d"]
    height_field_2d = fields["height_field_2d"]
    ambient_temp_series_c = build_ambient_temperature_series_c(
        temp3d_config,
        fields["u"].shape[0] + 1,
    )

    analysis_time_utc = parse_utc_datetime(temp3d_config.analysis_time_utc)
    solar_elevation_deg, solar_azimuth_deg = compute_solar_position_deg(
        temp3d_config.site_latitude_deg,
        temp3d_config.site_longitude_deg,
        analysis_time_utc,
    )
    radiation = estimate_reference_et0_mm_per_hour(
        temp_c=temp3d_config.ambient_temp_c,
        pressure_pa=temp3d_config.air_pressure_pa,
        solar_elevation_deg=solar_elevation_deg,
        cloud_cover_fraction=temp3d_config.cloud_cover_fraction,
        reference_crop_albedo=temp3d_config.reference_crop_albedo,
        priestley_taylor_alpha=temp3d_config.priestley_taylor_alpha,
    )
    shade_field = compute_building_shadow_field(
        building_mask=building_mask_2d,
        height_field=height_field_2d,
        grid_resolution_m=float(velocity_config.model_resolution_m),
        solar_elevation_deg=solar_elevation_deg,
        solar_azimuth_deg=solar_azimuth_deg,
        soften_passes=temp3d_config.shadow_soften_passes,
    )
    local_radiation_factor = np.clip(1.0 - shade_field, 0.0, 1.0).astype(np.float32)
    ghi_w_m2 = float(radiation["ghi_w_m2"])
    et0_mm_per_hour = float(radiation["et0_mm_per_hour"])
    downwelling_longwave_w_m2 = estimate_downwelling_longwave_w_m2(
        temp3d_config.ambient_temp_c,
        temp3d_config.ambient_relative_humidity_pct,
        temp3d_config.cloud_cover_fraction,
    )
    convective_coeff_value = float(
        convective_heat_transfer_coeff_w_m2_k(
            np.array([temp3d_config.reference_wind_speed_m_s], dtype=np.float32)
        )[0]
    )
    convective_coeff_w_m2_k = np.full(
        study_area_mask_2d.shape,
        convective_coeff_value,
        dtype=np.float32,
    )

    urban_albedo = np.full(study_area_mask_2d.shape, temp3d_config.urban_albedo, dtype=np.float32)
    urban_emissivity = np.full(
        study_area_mask_2d.shape, temp3d_config.urban_emissivity, dtype=np.float32
    )
    urban_storage_fraction = np.full(
        study_area_mask_2d.shape,
        temp3d_config.urban_storage_fraction,
        dtype=np.float32,
    )

    open_albedo = np.full(
        study_area_mask_2d.shape, temp3d_config.open_ground_albedo, dtype=np.float32
    )
    open_emissivity = np.full(
        study_area_mask_2d.shape, temp3d_config.open_ground_emissivity, dtype=np.float32
    )
    open_storage_fraction = np.full(
        study_area_mask_2d.shape,
        temp3d_config.open_ground_storage_fraction,
        dtype=np.float32,
    )

    vegetation_albedo = np.full(
        study_area_mask_2d.shape, temp3d_config.vegetation_albedo, dtype=np.float32
    )
    vegetation_emissivity = np.full(
        study_area_mask_2d.shape,
        temp3d_config.vegetation_emissivity,
        dtype=np.float32,
    )
    vegetation_storage_fraction = np.full(
        study_area_mask_2d.shape,
        temp3d_config.vegetation_storage_fraction,
        dtype=np.float32,
    )

    urban_sw_abs = ((1.0 - urban_albedo) * ghi_w_m2 * local_radiation_factor).astype(np.float32)
    open_sw_abs = ((1.0 - open_albedo) * ghi_w_m2 * local_radiation_factor).astype(np.float32)
    vegetation_sw_abs = ((1.0 - vegetation_albedo) * ghi_w_m2 * local_radiation_factor).astype(
        np.float32
    )

    latent_heat_flux_vegetation_w_m2 = (
        temp3d_config.vegetation_basal_crop_coefficient
        * et0_mm_per_hour
        / 3600.0
        * 2.45e6
        * local_radiation_factor
        * vegetation_mask_2d.astype(np.float32)
    ).astype(np.float32)
    latent_heat_flux_open_ground_w_m2 = (
        temp3d_config.open_ground_evaporation_fraction_of_et0
        * et0_mm_per_hour
        / 3600.0
        * 2.45e6
        * local_radiation_factor
        * open_ground_mask_2d.astype(np.float32)
    ).astype(np.float32)
    latent_heat_flux_urban_w_m2 = (
        temp3d_config.urban_evaporation_fraction_of_et0
        * et0_mm_per_hour
        / 3600.0
        * 2.45e6
        * local_radiation_factor
        * urban_mask_2d.astype(np.float32)
    ).astype(np.float32)

    urban_surface_excess_c = solve_surface_temperature_excess_c(
        absorbed_shortwave_w_m2=urban_sw_abs,
        emissivity=urban_emissivity,
        latent_heat_flux_w_m2=latent_heat_flux_urban_w_m2,
        storage_fraction=urban_storage_fraction,
        convective_coeff_w_m2_k=convective_coeff_w_m2_k,
        downwelling_longwave_w_m2=downwelling_longwave_w_m2,
        ambient_temp_c=temp3d_config.ambient_temp_c,
        anthropogenic_heat_flux_w_m2=np.full(
            study_area_mask_2d.shape,
            temp3d_config.anthropogenic_heat_flux_w_m2,
            dtype=np.float32,
        ),
    )
    open_surface_excess_c = solve_surface_temperature_excess_c(
        absorbed_shortwave_w_m2=open_sw_abs,
        emissivity=open_emissivity,
        latent_heat_flux_w_m2=latent_heat_flux_open_ground_w_m2,
        storage_fraction=open_storage_fraction,
        convective_coeff_w_m2_k=convective_coeff_w_m2_k,
        downwelling_longwave_w_m2=downwelling_longwave_w_m2,
        ambient_temp_c=temp3d_config.ambient_temp_c,
        anthropogenic_heat_flux_w_m2=0.0,
    )
    vegetation_surface_excess_c = solve_surface_temperature_excess_c(
        absorbed_shortwave_w_m2=vegetation_sw_abs,
        emissivity=vegetation_emissivity,
        latent_heat_flux_w_m2=latent_heat_flux_vegetation_w_m2,
        storage_fraction=vegetation_storage_fraction,
        convective_coeff_w_m2_k=convective_coeff_w_m2_k,
        downwelling_longwave_w_m2=downwelling_longwave_w_m2,
        ambient_temp_c=temp3d_config.ambient_temp_c,
        anthropogenic_heat_flux_w_m2=0.0,
    )

    ground_surface_temperature_excess_c = np.zeros(study_area_mask_2d.shape, dtype=np.float32)
    ground_surface_temperature_excess_c[urban_mask_2d] = urban_surface_excess_c[urban_mask_2d]
    ground_surface_temperature_excess_c[open_ground_mask_2d] = open_surface_excess_c[
        open_ground_mask_2d
    ]
    ground_surface_temperature_excess_c[vegetation_mask_2d] = vegetation_surface_excess_c[
        vegetation_mask_2d
    ]
    ground_surface_temperature_excess_c[building_mask_2d] = urban_surface_excess_c[building_mask_2d]
    ground_surface_temperature_excess_c[~study_area_mask_2d] = 0.0

    building_surface_temperature_excess_c = np.zeros(study_area_mask_2d.shape, dtype=np.float32)
    building_surface_temperature_excess_c[building_mask_2d] = urban_surface_excess_c[
        building_mask_2d
    ]
    roof_surface_temperature_excess_3d = np.zeros_like(fields["solid_mask_3d"], dtype=np.float32)
    roof_surface_temperature_excess_3d[fields["roof_mask_3d"]] = np.broadcast_to(
        building_surface_temperature_excess_c[None, :, :],
        fields["solid_mask_3d"].shape,
    )[fields["roof_mask_3d"]]

    ground_surface_temperature_c = ambient_temp_series_c[0] + ground_surface_temperature_excess_c
    building_surface_temperature_2d = (
        ambient_temp_series_c[0] + building_surface_temperature_excess_c
    )
    solid_temperature_3d = np.full(
        fields["solid_mask_3d"].shape, ambient_temp_series_c[0], dtype=np.float32
    )
    solid_temperature_3d[fields["roof_mask_3d"]] = (
        ambient_temp_series_c[0] + roof_surface_temperature_excess_3d[fields["roof_mask_3d"]]
    )

    air_density = air_density_kg_m3(temp3d_config.ambient_temp_c, temp3d_config.air_pressure_pa)
    surface_forcing_layer_count = int(min(3, max(1, int(velocity_config.z_dim))))
    surface_exchange_coeff_per_s = (
        convective_coeff_w_m2_k
        / (
            air_density
            * temp3d_config.air_heat_capacity_j_kg_k
            * float(velocity_config.height_scale_m)
            * surface_forcing_layer_count
        )
    ).astype(np.float32)

    return {
        "ground_surface_temperature_c": ground_surface_temperature_c.astype(np.float32),
        "ground_surface_temperature_excess_c": ground_surface_temperature_excess_c.astype(
            np.float32
        ),
        "solid_temperature_3d": solid_temperature_3d,
        "building_surface_temperature_excess_c": building_surface_temperature_excess_c.astype(
            np.float32
        ),
        "roof_surface_temperature_excess_3d": roof_surface_temperature_excess_3d.astype(np.float32),
        "shade_field": shade_field.astype(np.float32),
        "local_radiation_factor": local_radiation_factor,
        "convective_coeff_w_m2_k": convective_coeff_w_m2_k.astype(np.float32),
        "surface_exchange_coeff_per_s": surface_exchange_coeff_per_s.astype(np.float32),
        "building_surface_temperature_c": building_surface_temperature_2d.astype(np.float32),
        "ambient_temp_series_c": ambient_temp_series_c.astype(np.float32),
        "inflow_temp_series_c": ambient_temp_series_c.astype(np.float32),
        "ghi_w_m2": np.array([ghi_w_m2], dtype=np.float32),
        "et0_mm_per_hour": np.array([et0_mm_per_hour], dtype=np.float32),
        "downwelling_longwave_w_m2": np.array([downwelling_longwave_w_m2], dtype=np.float32),
        "air_density_kg_m3": np.array([air_density], dtype=np.float32),
        "surface_forcing_layer_count": np.array([surface_forcing_layer_count], dtype=np.int32),
        "solar_elevation_deg": np.array([solar_elevation_deg], dtype=np.float32),
        "solar_azimuth_deg": np.array([solar_azimuth_deg], dtype=np.float32),
    }


def shift_with_edge(field: np.ndarray, axis: int, step: int) -> np.ndarray:
    shifted = np.roll(field, step, axis=axis)
    if step > 0:
        index = [slice(None)] * field.ndim
        index[axis] = slice(0, step)
        edge_slice = np.take(field, indices=[0], axis=axis)
        shifted[tuple(index)] = edge_slice
    elif step < 0:
        index = [slice(None)] * field.ndim
        index[axis] = slice(step, None)
        edge_slice = np.take(field, indices=[field.shape[axis] - 1], axis=axis)
        shifted[tuple(index)] = edge_slice
    return shifted


def impose_boundary_conditions_3d(
    temperature_c: np.ndarray,
    fields: dict[str, np.ndarray],
    boundary_fields: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
    current_ambient_temp_c: float,
    current_inflow_temp_c: float,
) -> None:
    solid_mask = fields["solid_mask_3d"]
    study_area_3d = np.broadcast_to(fields["study_area_mask_2d"][None, :, :], temperature_c.shape)
    fluid_mask = (~solid_mask) & study_area_3d

    current_solid_temperature_3d = np.full(
        temperature_c.shape, current_ambient_temp_c, dtype=np.float32
    )
    current_solid_temperature_3d[fields["roof_mask_3d"]] = (
        current_ambient_temp_c
        + boundary_fields["roof_surface_temperature_excess_3d"][fields["roof_mask_3d"]]
    )
    temperature_c[solid_mask] = current_solid_temperature_3d[solid_mask]

    left_fluid = fluid_mask[:, :, 0]
    vertical_profile = np.linspace(
        current_inflow_temp_c + 0.1,
        current_inflow_temp_c - 0.1,
        temperature_c.shape[0],
        dtype=np.float32,
    )[:, None]
    temperature_c[:, :, 0][left_fluid] = np.broadcast_to(
        vertical_profile, temperature_c[:, :, 0].shape
    )[left_fluid]

    temperature_c[:, :, -1] = np.where(
        fluid_mask[:, :, -1], temperature_c[:, :, -2], temperature_c[:, :, -1]
    )
    temperature_c[:, 0, :] = np.where(
        fluid_mask[:, 0, :], temperature_c[:, 1, :], temperature_c[:, 0, :]
    )
    temperature_c[:, -1, :] = np.where(
        fluid_mask[:, -1, :], temperature_c[:, -2, :], temperature_c[:, -1, :]
    )
    temperature_c[-1, :, :] = np.where(
        fluid_mask[-1, :, :], current_ambient_temp_c, temperature_c[-1, :, :]
    )
    outside_mask = ~study_area_3d
    temperature_c[outside_mask] = current_ambient_temp_c


def solve_temperature_fields_3d_numpy(
    fields: dict[str, np.ndarray],
    boundary_fields: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
) -> dict[str, object]:
    u_frames = temp3d_config.velocity_scale * fields["u"]
    v_frames = temp3d_config.velocity_scale * fields["v"]
    w_frames = temp3d_config.velocity_scale * fields["w"]
    solid_mask = fields["solid_mask_3d"]
    study_area_3d = np.broadcast_to(fields["study_area_mask_2d"][None, :, :], solid_mask.shape)
    fluid_mask = (~solid_mask) & study_area_3d

    dx = float(velocity_config.model_resolution_m)
    dy = dx
    dz = float(velocity_config.height_scale_m)

    max_speed = float(np.max(np.sqrt(u_frames**2 + v_frames**2 + w_frames**2)))
    stable_dt = temp3d_config.max_courant * min(dx, dy, dz) / max(max_speed, 1e-6)
    diffusion_dt = 0.18 * min(dx, dy, dz) ** 2 / max(temp3d_config.diffusion_coeff_m2_s, 1e-6)
    dt = min(stable_dt, diffusion_dt, temp3d_config.frame_duration_s)
    substeps = max(1, int(math.ceil(temp3d_config.frame_duration_s / max(dt, 1e-6))))
    dt = temp3d_config.frame_duration_s / substeps
    bottom_exchange_coeff = boundary_fields["surface_exchange_coeff_per_s"].astype(np.float32)
    surface_forcing_layer_count = int(boundary_fields["surface_forcing_layer_count"][0])
    ambient_temp_series_c = boundary_fields["ambient_temp_series_c"].astype(np.float32)
    inflow_temp_series_c = boundary_fields["inflow_temp_series_c"].astype(np.float32)

    temperature_c = np.full(solid_mask.shape, float(ambient_temp_series_c[0]), dtype=np.float32)
    impose_boundary_conditions_3d(
        temperature_c,
        fields,
        boundary_fields,
        velocity_config,
        temp3d_config,
        current_ambient_temp_c=float(ambient_temp_series_c[0]),
        current_inflow_temp_c=float(inflow_temp_series_c[0]),
    )

    frames = [temperature_c.copy()]
    frame_means = [float(np.mean(temperature_c[fluid_mask]))]

    for frame_idx in range(u_frames.shape[0]):
        u = np.where(fluid_mask, u_frames[frame_idx], 0.0)
        v = np.where(fluid_mask, v_frames[frame_idx], 0.0)
        w = np.where(fluid_mask, w_frames[frame_idx], 0.0)
        current_ambient_temp_c = float(
            ambient_temp_series_c[min(frame_idx + 1, ambient_temp_series_c.shape[0] - 1)]
        )
        current_inflow_temp_c = float(
            inflow_temp_series_c[min(frame_idx + 1, inflow_temp_series_c.shape[0] - 1)]
        )
        current_ground_surface_temperature_c = (
            current_ambient_temp_c + boundary_fields["ground_surface_temperature_excess_c"]
        ).astype(np.float32)

        for _ in range(substeps):
            left = shift_with_edge(temperature_c, axis=2, step=1)
            right = shift_with_edge(temperature_c, axis=2, step=-1)
            north = shift_with_edge(temperature_c, axis=1, step=1)
            south = shift_with_edge(temperature_c, axis=1, step=-1)
            below = shift_with_edge(temperature_c, axis=0, step=1)
            above = shift_with_edge(temperature_c, axis=0, step=-1)
            below[0, :, :] = temperature_c[0, :, :]

            dtdx_backward = (temperature_c - left) / dx
            dtdx_forward = (right - temperature_c) / dx
            dtdy_backward = (temperature_c - north) / dy
            dtdy_forward = (south - temperature_c) / dy
            dtdz_backward = (temperature_c - below) / dz
            dtdz_forward = (above - temperature_c) / dz

            adv_x = np.where(u >= 0.0, u * dtdx_backward, u * dtdx_forward)
            adv_y = np.where(v >= 0.0, v * dtdy_backward, v * dtdy_forward)
            adv_z = np.where(w >= 0.0, w * dtdz_backward, w * dtdz_forward)
            laplacian = (
                (left - 2.0 * temperature_c + right) / (dx**2)
                + (north - 2.0 * temperature_c + south) / (dy**2)
                + (below - 2.0 * temperature_c + above) / (dz**2)
            )
            surface_exchange_term = np.zeros_like(temperature_c, dtype=np.float32)
            bottom_fluid = fluid_mask[0]
            for layer_idx in range(surface_forcing_layer_count):
                layer_fluid = fluid_mask[layer_idx] & bottom_fluid
                surface_exchange_term[layer_idx, layer_fluid] = bottom_exchange_coeff[
                    layer_fluid
                ] * (
                    current_ground_surface_temperature_c[layer_fluid]
                    - temperature_c[layer_idx, layer_fluid]
                )

            next_temperature = temperature_c + dt * (
                -(adv_x + adv_y + adv_z)
                + temp3d_config.diffusion_coeff_m2_s * laplacian
                + surface_exchange_term
            )
            temperature_c[fluid_mask] = next_temperature[fluid_mask]
            impose_boundary_conditions_3d(
                temperature_c,
                fields,
                boundary_fields,
                velocity_config,
                temp3d_config,
                current_ambient_temp_c=current_ambient_temp_c,
                current_inflow_temp_c=current_inflow_temp_c,
            )

        frames.append(temperature_c.copy())
        frame_means.append(float(np.mean(temperature_c[fluid_mask])))

    temperature_array = np.stack(frames, axis=0)
    masked = temperature_array.copy()
    masked[:, solid_mask | (~study_area_3d)] = np.nan
    return {
        "temperature_fields_c": temperature_array,
        "temperature_fields_masked_c": masked,
        "fluid_mask": fluid_mask,
        "dt_seconds": float(dt),
        "substeps_per_frame": int(substeps),
        "frame_means_c": np.asarray(frame_means, dtype=np.float32),
        "solver_backend": "numpy",
    }


def shift_with_edge_torch(field: "torch.Tensor", axis: int, step: int) -> "torch.Tensor":
    shifted = torch.roll(field, shifts=step, dims=axis)
    if step > 0:
        index = [slice(None)] * field.ndim
        index[axis] = slice(0, step)
        edge_index = [slice(None)] * field.ndim
        edge_index[axis] = slice(0, 1)
        shifted[tuple(index)] = field[tuple(edge_index)]
    elif step < 0:
        index = [slice(None)] * field.ndim
        index[axis] = slice(step, None)
        edge_index = [slice(None)] * field.ndim
        edge_index[axis] = slice(field.shape[axis] - 1, field.shape[axis])
        shifted[tuple(index)] = field[tuple(edge_index)]
    return shifted


def impose_boundary_conditions_3d_torch(
    temperature_c: "torch.Tensor",
    solid_mask: "torch.Tensor",
    roof_mask: "torch.Tensor",
    study_area_3d: "torch.Tensor",
    roof_surface_temperature_excess_3d: "torch.Tensor",
    current_ambient_temp_c: float,
    current_inflow_temp_c: float,
) -> None:
    fluid_mask = (~solid_mask) & study_area_3d
    current_solid_temperature_3d = torch.full_like(temperature_c, float(current_ambient_temp_c))
    current_solid_temperature_3d[roof_mask] = (
        float(current_ambient_temp_c) + roof_surface_temperature_excess_3d[roof_mask]
    )
    temperature_c[solid_mask] = current_solid_temperature_3d[solid_mask]

    left_fluid = fluid_mask[:, :, 0]
    vertical_profile = torch.linspace(
        float(current_inflow_temp_c) + 0.1,
        float(current_inflow_temp_c) - 0.1,
        temperature_c.shape[0],
        dtype=temperature_c.dtype,
        device=temperature_c.device,
    )[:, None]
    left_boundary = temperature_c[:, :, 0]
    left_boundary[left_fluid] = vertical_profile.expand_as(left_boundary)[left_fluid]
    temperature_c[:, :, 0] = left_boundary

    temperature_c[:, :, -1] = torch.where(
        fluid_mask[:, :, -1],
        temperature_c[:, :, -2],
        temperature_c[:, :, -1],
    )
    temperature_c[:, 0, :] = torch.where(
        fluid_mask[:, 0, :],
        temperature_c[:, 1, :],
        temperature_c[:, 0, :],
    )
    temperature_c[:, -1, :] = torch.where(
        fluid_mask[:, -1, :],
        temperature_c[:, -2, :],
        temperature_c[:, -1, :],
    )
    temperature_c[-1, :, :] = torch.where(
        fluid_mask[-1, :, :],
        torch.as_tensor(
            float(current_ambient_temp_c), dtype=temperature_c.dtype, device=temperature_c.device
        ),
        temperature_c[-1, :, :],
    )
    temperature_c[~study_area_3d] = float(current_ambient_temp_c)


def solve_temperature_fields_3d_torch(
    fields: dict[str, np.ndarray],
    boundary_fields: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
) -> dict[str, object]:
    if not TORCH_AVAILABLE:
        raise RuntimeError("temperature_solver_backend='cuda' requires PyTorch.")

    requested_device = str(temp3d_config.temperature_solver_device)
    if requested_device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(
            "temperature_solver_device requests CUDA, but torch.cuda.is_available() is False."
        )
    device = torch.device(
        requested_device
        if requested_device != "auto"
        else ("cuda" if torch.cuda.is_available() else "cpu")
    )

    u_frames_np = (temp3d_config.velocity_scale * fields["u"]).astype(np.float32)
    v_frames_np = (temp3d_config.velocity_scale * fields["v"]).astype(np.float32)
    w_frames_np = (temp3d_config.velocity_scale * fields["w"]).astype(np.float32)
    solid_mask_np = fields["solid_mask_3d"].astype(bool)
    study_area_3d_np = np.broadcast_to(
        fields["study_area_mask_2d"][None, :, :], solid_mask_np.shape
    ).astype(bool)
    fluid_mask_np = (~solid_mask_np) & study_area_3d_np

    dx = float(velocity_config.model_resolution_m)
    dy = dx
    dz = float(velocity_config.height_scale_m)

    max_speed = float(np.max(np.sqrt(u_frames_np**2 + v_frames_np**2 + w_frames_np**2)))
    stable_dt = temp3d_config.max_courant * min(dx, dy, dz) / max(max_speed, 1e-6)
    diffusion_dt = 0.18 * min(dx, dy, dz) ** 2 / max(temp3d_config.diffusion_coeff_m2_s, 1e-6)
    dt = min(stable_dt, diffusion_dt, temp3d_config.frame_duration_s)
    substeps = max(1, int(math.ceil(temp3d_config.frame_duration_s / max(dt, 1e-6))))
    dt = temp3d_config.frame_duration_s / substeps

    u_frames = torch.as_tensor(u_frames_np, dtype=torch.float32, device=device)
    v_frames = torch.as_tensor(v_frames_np, dtype=torch.float32, device=device)
    w_frames = torch.as_tensor(w_frames_np, dtype=torch.float32, device=device)
    solid_mask = torch.as_tensor(solid_mask_np, dtype=torch.bool, device=device)
    roof_mask = torch.as_tensor(
        fields["roof_mask_3d"].astype(bool), dtype=torch.bool, device=device
    )
    study_area_3d = torch.as_tensor(study_area_3d_np, dtype=torch.bool, device=device)
    fluid_mask = (~solid_mask) & study_area_3d
    bottom_fluid = fluid_mask[0]
    bottom_exchange_coeff = torch.as_tensor(
        boundary_fields["surface_exchange_coeff_per_s"].astype(np.float32),
        dtype=torch.float32,
        device=device,
    )
    ground_surface_temperature_excess_c = torch.as_tensor(
        boundary_fields["ground_surface_temperature_excess_c"].astype(np.float32),
        dtype=torch.float32,
        device=device,
    )
    roof_surface_temperature_excess_3d = torch.as_tensor(
        boundary_fields["roof_surface_temperature_excess_3d"].astype(np.float32),
        dtype=torch.float32,
        device=device,
    )
    ambient_temp_series_c = boundary_fields["ambient_temp_series_c"].astype(np.float32)
    inflow_temp_series_c = boundary_fields["inflow_temp_series_c"].astype(np.float32)
    surface_forcing_layer_count = int(boundary_fields["surface_forcing_layer_count"][0])

    temperature_c = torch.full(
        solid_mask.shape,
        float(ambient_temp_series_c[0]),
        dtype=torch.float32,
        device=device,
    )
    impose_boundary_conditions_3d_torch(
        temperature_c,
        solid_mask,
        roof_mask,
        study_area_3d,
        roof_surface_temperature_excess_3d,
        current_ambient_temp_c=float(ambient_temp_series_c[0]),
        current_inflow_temp_c=float(inflow_temp_series_c[0]),
    )

    frames = [temperature_c.detach().cpu().numpy().copy()]
    frame_means = [float(temperature_c[fluid_mask].mean().detach().cpu())]
    diffusion_coeff = float(temp3d_config.diffusion_coeff_m2_s)

    with torch.no_grad():
        for frame_idx in range(u_frames.shape[0]):
            u = torch.where(
                fluid_mask, u_frames[frame_idx], torch.zeros((), dtype=torch.float32, device=device)
            )
            v = torch.where(
                fluid_mask, v_frames[frame_idx], torch.zeros((), dtype=torch.float32, device=device)
            )
            w = torch.where(
                fluid_mask, w_frames[frame_idx], torch.zeros((), dtype=torch.float32, device=device)
            )
            current_ambient_temp_c = float(
                ambient_temp_series_c[min(frame_idx + 1, ambient_temp_series_c.shape[0] - 1)]
            )
            current_inflow_temp_c = float(
                inflow_temp_series_c[min(frame_idx + 1, inflow_temp_series_c.shape[0] - 1)]
            )
            current_ground_surface_temperature_c = (
                float(current_ambient_temp_c) + ground_surface_temperature_excess_c
            )

            for _ in range(substeps):
                left = shift_with_edge_torch(temperature_c, axis=2, step=1)
                right = shift_with_edge_torch(temperature_c, axis=2, step=-1)
                north = shift_with_edge_torch(temperature_c, axis=1, step=1)
                south = shift_with_edge_torch(temperature_c, axis=1, step=-1)
                below = shift_with_edge_torch(temperature_c, axis=0, step=1)
                above = shift_with_edge_torch(temperature_c, axis=0, step=-1)
                below[0, :, :] = temperature_c[0, :, :]

                dtdx_backward = (temperature_c - left) / dx
                dtdx_forward = (right - temperature_c) / dx
                dtdy_backward = (temperature_c - north) / dy
                dtdy_forward = (south - temperature_c) / dy
                dtdz_backward = (temperature_c - below) / dz
                dtdz_forward = (above - temperature_c) / dz

                adv_x = torch.where(u >= 0.0, u * dtdx_backward, u * dtdx_forward)
                adv_y = torch.where(v >= 0.0, v * dtdy_backward, v * dtdy_forward)
                adv_z = torch.where(w >= 0.0, w * dtdz_backward, w * dtdz_forward)
                laplacian = (
                    (left - 2.0 * temperature_c + right) / (dx**2)
                    + (north - 2.0 * temperature_c + south) / (dy**2)
                    + (below - 2.0 * temperature_c + above) / (dz**2)
                )

                surface_exchange_term = torch.zeros_like(temperature_c)
                for layer_idx in range(surface_forcing_layer_count):
                    layer_fluid = fluid_mask[layer_idx] & bottom_fluid
                    surface_exchange_term[layer_idx, layer_fluid] = bottom_exchange_coeff[
                        layer_fluid
                    ] * (
                        current_ground_surface_temperature_c[layer_fluid]
                        - temperature_c[layer_idx, layer_fluid]
                    )

                next_temperature = temperature_c + float(dt) * (
                    -(adv_x + adv_y + adv_z) + diffusion_coeff * laplacian + surface_exchange_term
                )
                temperature_c[fluid_mask] = next_temperature[fluid_mask]
                impose_boundary_conditions_3d_torch(
                    temperature_c,
                    solid_mask,
                    roof_mask,
                    study_area_3d,
                    roof_surface_temperature_excess_3d,
                    current_ambient_temp_c=current_ambient_temp_c,
                    current_inflow_temp_c=current_inflow_temp_c,
                )

            frames.append(temperature_c.detach().cpu().numpy().copy())
            frame_means.append(float(temperature_c[fluid_mask].mean().detach().cpu()))

    temperature_array = np.stack(frames, axis=0).astype(np.float32)
    masked = temperature_array.copy()
    masked[:, solid_mask_np | (~study_area_3d_np)] = np.nan
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return {
        "temperature_fields_c": temperature_array,
        "temperature_fields_masked_c": masked,
        "fluid_mask": fluid_mask_np,
        "dt_seconds": float(dt),
        "substeps_per_frame": int(substeps),
        "frame_means_c": np.asarray(frame_means, dtype=np.float32),
        "solver_backend": f"torch:{device}",
    }


def solve_temperature_fields_3d(
    fields: dict[str, np.ndarray],
    boundary_fields: dict[str, np.ndarray],
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
) -> dict[str, object]:
    backend = str(getattr(temp3d_config, "temperature_solver_backend", "auto")).lower()
    if backend in {"cuda", "gpu", "torch"}:
        return solve_temperature_fields_3d_torch(
            fields, boundary_fields, velocity_config, temp3d_config
        )
    if backend in {"numpy", "cpu"}:
        return solve_temperature_fields_3d_numpy(
            fields, boundary_fields, velocity_config, temp3d_config
        )
    if backend != "auto":
        raise ValueError(
            "temperature_solver_backend must be one of: auto, cuda, torch, numpy, cpu."
        )
    if TORCH_AVAILABLE and torch.cuda.is_available():
        return solve_temperature_fields_3d_torch(
            fields, boundary_fields, velocity_config, temp3d_config
        )
    return solve_temperature_fields_3d_numpy(
        fields, boundary_fields, velocity_config, temp3d_config
    )


def plot_temperature_3d_panels(
    temperature_fields_c: np.ndarray,
    boundary_fields: dict[str, np.ndarray],
    fields: dict[str, np.ndarray],
    z_indices: list[int],
    frame_idx: int = -1,
) -> object:
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("matplotlib is required for plotting.")

    n_z = temperature_fields_c.shape[1]
    safe_frame = (
        min(max(frame_idx, 0), temperature_fields_c.shape[0] - 1)
        if frame_idx >= 0
        else temperature_fields_c.shape[0] - 1
    )
    safe_z = [min(max(int(z), 0), n_z - 1) for z in z_indices]
    volume = temperature_fields_c[safe_frame]
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))

    surface_temp = np.where(
        fields["study_area_mask_2d"], boundary_fields["ground_surface_temperature_c"], np.nan
    )
    shade_display = np.where(fields["study_area_mask_2d"], boundary_fields["shade_field"], np.nan)
    building_display = np.where(
        fields["study_area_mask_2d"], fields["building_mask_2d"].astype(float), np.nan
    )

    im0 = axes[0, 0].imshow(surface_temp, cmap="YlOrRd", origin="upper")
    axes[0, 0].set_title("Ground Surface Temperature")
    fig.colorbar(im0, ax=axes[0, 0], shrink=0.8)

    im1 = axes[0, 1].imshow(shade_display, cmap="Greys", origin="upper")
    axes[0, 1].set_title("Building Shadow Field")
    fig.colorbar(im1, ax=axes[0, 1], shrink=0.8)

    im2 = axes[0, 2].imshow(building_display, cmap="Blues", origin="upper", vmin=0.0, vmax=1.0)
    axes[0, 2].set_title("Building Footprint")
    fig.colorbar(im2, ax=axes[0, 2], shrink=0.8)

    vmin = float(np.nanmin(temperature_fields_c))
    vmax = float(np.nanmax(temperature_fields_c))
    for ax, z_idx in zip(axes[1], safe_z):
        im = ax.imshow(volume[z_idx], cmap="YlOrRd", origin="upper", vmin=vmin, vmax=vmax)
        ax.set_title(f"Temperature Slice z={z_idx}")
        fig.colorbar(im, ax=ax, shrink=0.8)

    fig.tight_layout()
    return fig


def show_vertical_temperature_section_animation(
    run_outputs: dict[str, object], section_y_idx: int | None = None
) -> object:
    if not MATPLOTLIB_AVAILABLE or HTML is None:
        raise RuntimeError("Animation output requires matplotlib and IPython.")

    frames = run_outputs["temperature_results"]["temperature_fields_masked_c"]
    solid_mask = run_outputs["fields"]["solid_mask_3d"]
    reference = frames[0]
    safe_section_y = (
        reference.shape[1] // 2
        if section_y_idx is None
        else min(max(int(section_y_idx), 0), reference.shape[1] - 1)
    )
    sections = frames[:, :, safe_section_y, :].copy()
    solids = solid_mask[:, safe_section_y, :]
    sections[:, solids] = np.nan

    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(
        sections[0],
        cmap="YlOrRd",
        origin="lower",
        aspect="auto",
        vmin=float(np.nanmin(sections)),
        vmax=float(np.nanmax(sections)),
    )
    fig.colorbar(im, ax=ax, shrink=0.8)

    def update(frame_idx: int) -> None:
        im.set_array(sections[frame_idx])
        ax.set_title(f"Vertical Temperature Section Frame {frame_idx} (y={safe_section_y})")

    ani = mpl_animation.FuncAnimation(fig, update, frames=range(sections.shape[0]))
    return HTML(ani.to_jshtml())


def save_vertical_temperature_section_animation(
    run_outputs: dict[str, object],
    output_dir: str | Path,
    section_y_idx: int | None = None,
    filename_prefix: str = "temperature_3d_vertical_section",
) -> dict[str, str]:
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("Animation output requires matplotlib.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = run_outputs["temperature_results"]["temperature_fields_masked_c"]
    solid_mask = run_outputs["fields"]["solid_mask_3d"]
    reference = frames[0]
    safe_section_y = (
        reference.shape[1] // 2
        if section_y_idx is None
        else min(max(int(section_y_idx), 0), reference.shape[1] - 1)
    )
    sections = frames[:, :, safe_section_y, :].copy()
    solids = solid_mask[:, safe_section_y, :]
    sections[:, solids] = np.nan

    html_path = output_dir / f"{filename_prefix}_animation.html"
    gif_path = output_dir / f"{filename_prefix}_animation.gif"
    saved = {"html": str(html_path)}

    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(
        sections[0],
        cmap="YlOrRd",
        origin="lower",
        aspect="auto",
        vmin=float(np.nanmin(sections)),
        vmax=float(np.nanmax(sections)),
    )
    fig.colorbar(im, ax=ax, shrink=0.8)

    def update(frame_idx: int) -> None:
        im.set_array(sections[frame_idx])
        ax.set_title(f"Vertical Temperature Section Frame {frame_idx} (y={safe_section_y})")

    ani = mpl_animation.FuncAnimation(fig, update, frames=range(sections.shape[0]))
    html_path.write_text(ani.to_jshtml())

    try:
        writer = mpl_animation.PillowWriter(fps=6)
        ani.save(gif_path, writer=writer)
        saved["gif"] = str(gif_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to save vertical section GIF to {gif_path}") from exc
    finally:
        plt.close(fig)

    return saved


def show_horizontal_temperature_slice_animation(
    run_outputs: dict[str, object],
    z_idx: int | None = None,
) -> object:
    if not MATPLOTLIB_AVAILABLE or HTML is None:
        raise RuntimeError("Animation output requires matplotlib and IPython.")

    frames = run_outputs["temperature_results"]["temperature_fields_masked_c"]
    safe_z = (
        min(3, frames.shape[1] - 1)
        if z_idx is None
        else min(max(int(z_idx), 0), frames.shape[1] - 1)
    )
    slices = frames[:, safe_z, :, :]

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(
        slices[0],
        cmap="YlOrRd",
        origin="upper",
        vmin=float(np.nanmin(slices)),
        vmax=float(np.nanmax(slices)),
    )
    fig.colorbar(im, ax=ax, shrink=0.8)

    def update(frame_idx: int) -> None:
        im.set_array(slices[frame_idx])
        ax.set_title(f"Horizontal Temperature Slice Frame {frame_idx} (z={safe_z})")

    ani = mpl_animation.FuncAnimation(fig, update, frames=range(slices.shape[0]))
    return HTML(ani.to_jshtml())


def save_horizontal_temperature_slice_animation(
    run_outputs: dict[str, object],
    output_dir: str | Path,
    z_idx: int | None = None,
    filename_prefix: str = "temperature_3d_horizontal_slice",
) -> dict[str, str]:
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("Animation output requires matplotlib.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = run_outputs["temperature_results"]["temperature_fields_masked_c"]
    safe_z = (
        min(3, frames.shape[1] - 1)
        if z_idx is None
        else min(max(int(z_idx), 0), frames.shape[1] - 1)
    )
    slices = frames[:, safe_z, :, :]

    html_path = output_dir / f"{filename_prefix}_animation.html"
    gif_path = output_dir / f"{filename_prefix}_animation.gif"
    saved = {"html": str(html_path)}

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(
        slices[0],
        cmap="YlOrRd",
        origin="upper",
        vmin=float(np.nanmin(slices)),
        vmax=float(np.nanmax(slices)),
    )
    fig.colorbar(im, ax=ax, shrink=0.8)

    def update(frame_idx: int) -> None:
        im.set_array(slices[frame_idx])
        ax.set_title(f"Horizontal Temperature Slice Frame {frame_idx} (z={safe_z})")

    ani = mpl_animation.FuncAnimation(fig, update, frames=range(slices.shape[0]))
    html_path.write_text(ani.to_jshtml())

    try:
        writer = mpl_animation.PillowWriter(fps=6)
        ani.save(gif_path, writer=writer)
        saved["gif"] = str(gif_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to save horizontal slice GIF to {gif_path}") from exc
    finally:
        plt.close(fig)

    return saved


def save_results(
    velocity_results: dict[str, object],
    fields: dict[str, np.ndarray],
    boundary_fields: dict[str, np.ndarray],
    temperature_results: dict[str, object],
    velocity_config: SouthKensingtonConfig,
    temp3d_config: Temperature3DScenarioConfig,
    cache_reused: bool,
) -> dict[str, object]:
    out_dir = Path(temp3d_config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shared_cache_summary_path = save_shared_full_velocity_cache(
        fields, velocity_config, temp3d_config
    )

    np.save(out_dir / "temperature_fields_3d_c.npy", temperature_results["temperature_fields_c"])
    np.save(
        out_dir / "temperature_fields_3d_masked_c.npy",
        temperature_results["temperature_fields_masked_c"],
    )
    np.save(
        out_dir / "ground_surface_temperature_c.npy",
        boundary_fields["ground_surface_temperature_c"],
    )
    np.save(
        out_dir / "building_surface_temperature_c.npy",
        boundary_fields["building_surface_temperature_c"],
    )
    np.save(out_dir / "shade_field.npy", boundary_fields["shade_field"])
    np.save(out_dir / "local_radiation_factor.npy", boundary_fields["local_radiation_factor"])
    np.save(
        out_dir / "surface_exchange_coeff_per_s.npy",
        boundary_fields["surface_exchange_coeff_per_s"],
    )
    np.save(out_dir / "ambient_temp_series_c.npy", boundary_fields["ambient_temp_series_c"])
    np.save(out_dir / "frame_mean_temperature_c.npy", temperature_results["frame_means_c"])

    figure_path = None
    if temp3d_config.save_overview_figure and MATPLOTLIB_AVAILABLE:
        z_dim = temperature_results["temperature_fields_c"].shape[1]
        z_indices = sorted({0, min(3, z_dim - 1), min(6, z_dim - 1)})
        fig = plot_temperature_3d_panels(
            temperature_results["temperature_fields_masked_c"],
            boundary_fields,
            fields,
            z_indices=z_indices,
            frame_idx=-1,
        )
        figure_path = out_dir / "temperature_3d_overview.png"
        fig.savefig(figure_path, dpi=180, bbox_inches="tight")
        plt.close(fig)

    animation_paths = {}
    if temp3d_config.save_animation and MATPLOTLIB_AVAILABLE and HTML is not None:
        animation_inputs = {
            "temperature_results": temperature_results,
            "fields": fields,
        }
        vertical_paths = save_vertical_temperature_section_animation(
            animation_inputs,
            out_dir,
        )
        animation_paths["vertical_section_html"] = vertical_paths["html"]
        if "gif" in vertical_paths:
            animation_paths["vertical_section_gif"] = vertical_paths["gif"]

        horizontal_paths = save_horizontal_temperature_slice_animation(
            animation_inputs,
            out_dir,
        )
        animation_paths["horizontal_slice_html"] = horizontal_paths["html"]
        if "gif" in horizontal_paths:
            animation_paths["horizontal_slice_gif"] = horizontal_paths["gif"]

    summary = {
        "velocity_config": asdict(velocity_config),
        "temperature_3d_config": asdict(temp3d_config),
        "cache_reused": bool(cache_reused),
        "shared_velocity_cache_summary_path": shared_cache_summary_path,
        "grid": velocity_results["grid"],
        "velocity_shape": list(fields["u"].shape),
        "temperature_shape": list(temperature_results["temperature_fields_c"].shape),
        "temperature_solver_backend_used": temperature_results.get("solver_backend", "unknown"),
        "dt_seconds": float(temperature_results["dt_seconds"]),
        "substeps_per_frame": int(temperature_results["substeps_per_frame"]),
        "temperature_min_c": float(np.nanmin(temperature_results["temperature_fields_masked_c"])),
        "temperature_max_c": float(np.nanmax(temperature_results["temperature_fields_masked_c"])),
        "ground_surface_temperature_min_c": float(
            np.nanmin(boundary_fields["ground_surface_temperature_c"])
        ),
        "ground_surface_temperature_max_c": float(
            np.nanmax(boundary_fields["ground_surface_temperature_c"])
        ),
        "solar_elevation_deg": float(boundary_fields["solar_elevation_deg"][0]),
        "solar_azimuth_deg": float(boundary_fields["solar_azimuth_deg"][0]),
        "reference_wind_speed_m_s": float(temp3d_config.reference_wind_speed_m_s),
        "reference_wind_direction_deg": float(temp3d_config.reference_wind_direction_deg),
        "ambient_temp_series_min_c": float(np.min(boundary_fields["ambient_temp_series_c"])),
        "ambient_temp_series_max_c": float(np.max(boundary_fields["ambient_temp_series_c"])),
        "ghi_w_m2": float(boundary_fields["ghi_w_m2"][0]),
        "et0_mm_per_hour": float(boundary_fields["et0_mm_per_hour"][0]),
        "downwelling_longwave_w_m2": float(boundary_fields["downwelling_longwave_w_m2"][0]),
        "surface_forcing_layer_count": int(boundary_fields["surface_forcing_layer_count"][0]),
        "figure_path": str(figure_path) if figure_path else None,
        "animation_paths": animation_paths,
        "method_references": [
            "Baik, Kim, and Fernando (2003): 3D CFD framework solving the Reynolds-averaged heat equation under the Boussinesq approximation with eddy-diffusivity closure.",
            "Kim and Baik (1999): urban thermal-flow simulations driven by heated walls and heated street-canyon bottoms.",
            "Li et al. (2010): urban thermal stratification and temperature evolution in CFD are strongly modified by ground heating under the Boussinesq approximation.",
            "Allen et al. (1998, FAO-56): reference short grass albedo 0.23 and crop-coefficient / reference-evapotranspiration framework used here to estimate vegetation latent cooling.",
            "Priestley and Taylor (1972): equilibrium-evaporation coefficient alpha = 1.26 used for midday reference evapotranspiration.",
            "Brutsaert (1975): clear-sky atmospheric emissivity used to estimate downwelling longwave radiation, blended with cloud fraction for all-sky conditions.",
            "SUEWS / urban energy-balance literature (Ward et al., 2016; Järvi et al., 2011): typical urban-versus-vegetation surface radiative properties and the importance of daytime storage flux over paved urban surfaces.",
            "Jürges-type outdoor convective heat-transfer relation as summarized in contemporary urban heat-transfer literature: used to convert surface-air temperature difference into sensible heat exchange.",
        ],
        "scenario_note": "This simplified 3D temperature model is tuned to the South Kensington summer-afternoon case of 2025-07-25 13:00 UTC (24.2 C, RH 47.19%, wind speed 3.09 m/s from 268.41 deg, cloud cover 47%). Ground thermal forcing comes from building-shadow-modulated shortwave absorption, vegetation/open-ground/urban latent cooling scaled from reference evapotranspiration, literature-based daytime storage fractions, modest daytime anthropogenic heat over urban fabric, and convective surface-air exchange set from the observed background wind speed.",
    }
    summary_path = out_dir / "temperature_3d_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    summary["summary_path"] = str(summary_path)
    return summary


def run_temperature_3d_pipeline(
    velocity_config: SouthKensingtonConfig | None = None,
    temp3d_config: Temperature3DScenarioConfig | None = None,
    keep_outputs: bool = True,
) -> dict[str, object]:
    velocity_config = velocity_config or SouthKensingtonConfig()
    temp3d_config = temp3d_config or Temperature3DScenarioConfig()

    velocity_results, fields, cache_reused = extract_or_load_full_velocity_fields(
        velocity_config, temp3d_config
    )
    boundary_fields = build_surface_temperature_fields(fields, velocity_config, temp3d_config)
    temperature_results = solve_temperature_fields_3d(
        fields, boundary_fields, velocity_config, temp3d_config
    )
    summary = save_results(
        velocity_results,
        fields,
        boundary_fields,
        temperature_results,
        velocity_config,
        temp3d_config,
        cache_reused,
    )
    if not keep_outputs:
        return {"summary": summary}
    return {
        "velocity_results": velocity_results,
        "fields": fields,
        "boundary_fields": boundary_fields,
        "temperature_results": temperature_results,
        "summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a simplified 3D South Kensington temperature field from DIGIT 3D velocity."
    )
    parser.add_argument("--timesteppings", type=int, default=50)
    parser.add_argument("--model-resolution-m", type=float, default=4.0)
    parser.add_argument("--z-dim", type=int, default=10)
    parser.add_argument("--height-scale-m", type=float, default=4.0)
    parser.add_argument("--ambient-temp-c", type=float, default=24.2)
    parser.add_argument(
        "--analysis-time-utc", default=Temperature3DScenarioConfig.analysis_time_utc
    )
    parser.add_argument(
        "--temperature-solver-backend",
        default="auto",
        choices=["auto", "cuda", "torch", "numpy", "cpu"],
    )
    parser.add_argument("--temperature-solver-device", default="cuda")
    parser.add_argument("--no-animation", action="store_true")
    parser.add_argument("--no-overview-figure", action="store_true")
    parser.add_argument(
        "--output-dir",
        default=str(BUNDLE_ROOT / "outputs" / "south_kensington_temperature_3d"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    velocity_config = SouthKensingtonConfig(
        timesteppings=args.timesteppings,
        model_resolution_m=args.model_resolution_m,
        z_dim=args.z_dim,
        height_scale_m=args.height_scale_m,
        output_dir=str(BUNDLE_ROOT / "outputs" / "south_kensington_velocity"),
    )
    temp3d_config = Temperature3DScenarioConfig(
        output_dir=args.output_dir,
        ambient_temp_c=args.ambient_temp_c,
        inflow_temp_c=args.ambient_temp_c,
        analysis_time_utc=args.analysis_time_utc,
        save_animation=not args.no_animation,
        save_overview_figure=not args.no_overview_figure,
        temperature_solver_backend=args.temperature_solver_backend,
        temperature_solver_device=args.temperature_solver_device,
    )
    run_outputs = run_temperature_3d_pipeline(velocity_config, temp3d_config)
    print(json.dumps(run_outputs["summary"], indent=2))


if __name__ == "__main__":
    main()
