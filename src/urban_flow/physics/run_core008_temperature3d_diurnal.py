"""Diurnal (sunrise-to-night) run of Yi Qi's 3-D temperature model driven hour by hour by the NN4PDEs solar model.

Each hour: sun position -> ShadowNet (1 m) sunlit fraction + SVF -> per-cell shortwave ratio and SVF-weighted longwave ->
the model's own surface energy balance (build_surface_temperature_fields, with the shadow and longwave functions replaced at
runtime) -> its torch advection-diffusion solver for 60 min (40 frames x 90 s, SCALED wind frames 81..100 looped), carrying the
air temperature field from hour to hour. The solver is the model's solve_temperature_fields_3d_torch copied verbatim except for an
initial-temperature argument (the original always starts from uniform ambient). Ambient air follows a clear-sky June sinusoid.

Usage: python run_core008_temperature3d_diurnal.py [--date 2026-06-21] [--hours 4-23] [--cloud 0.0] [--tmin 15 --tmax 26]
Outputs: output/core008/physics/scaled_latent/temperature3d_solar/diurnal_<date>/
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import argparse
import importlib.util
import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import torch

ROOT = repo_root()
RUN = ROOT / "output/core008/physics/scaled_latent"
BASE = RUN / "temperature3d_solar"
CACHE = BASE / "velocity_cache"
MODEL_DIR = (
    ROOT
    / "src/urban_flow/physics/environment-integration/members/yiqi_temperature/models/physical_model"
)
LANDCOVER = ROOT / "output/core008/geometry/south_kensington_core008_landcover_4m"
TERRAIN = RUN / "flood/terrain"
SOLAR = RUN / "solar"
sys.path.insert(0, str(MODEL_DIR))
sys.path.insert(0, str(MODEL_DIR.parent / "velocity_calculation"))
sys.path.insert(0, str(ROOT / "src/common/pipeline/physics"))
import south_kensington_jupyter as _skj  # noqa: E402

if not hasattr(_skj, "rotate_2d_field"):
    _skj.rotate_2d_field = lambda field, deg: (
        np.rot90(field, k=int(round(deg / 90.0)) % 4) if deg % 360 else field
    )
spec = importlib.util.spec_from_file_location(
    "south_kensington_temperature_3d", MODEL_DIR / "south_kensington_temperature_3d.py"
)
M3 = importlib.util.module_from_spec(spec)
sys.modules["south_kensington_temperature_3d"] = M3
spec.loader.exec_module(M3)
from south_kensington_jupyter import SouthKensingtonConfig  # noqa: E402
from solar_np import ShadowNet, clear_sky  # noqa: E402

CELL = 4.0
X0, Y0 = 480, 640
CANOPY_TRANSMITTANCE, ALBEDO, SIGMA = 0.3, 0.2, 5.670374419e-8


def log(fh, msg):
    line = time.strftime("%H:%M:%S") + " " + msg
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def to_image(a):
    return np.ascontiguousarray(a[::-1] if a.ndim == 2 else a[..., ::-1, :])


def ambient_c(hour_local, tmin, tmax):
    """clear-sky summer day: minimum at 05:00, maximum at 15:00, cosine rise over 10 h and cosine fall over 14 h."""
    h = hour_local % 24.0
    mid, amp = 0.5 * (tmin + tmax), 0.5 * (tmax - tmin)
    if 5.0 <= h <= 15.0:
        return mid - amp * math.cos(math.pi * (h - 5.0) / 10.0)
    dh = (h - 15.0) % 24.0
    return mid + amp * math.cos(math.pi * dh / 14.0)


def solve_from_state(
    fields, boundary_fields, velocity_config, temp3d_config, initial_temperature_c
):
    """Copy of M3.solve_temperature_fields_3d_torch with an initial temperature field (only change marked ###)."""
    device = torch.device(temp3d_config.temperature_solver_device)
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
    u_frames = torch.as_tensor(u_frames_np, device=device)
    v_frames = torch.as_tensor(v_frames_np, device=device)
    w_frames = torch.as_tensor(w_frames_np, device=device)
    solid_mask = torch.as_tensor(solid_mask_np, device=device)
    roof_mask = torch.as_tensor(fields["roof_mask_3d"].astype(bool), device=device)
    study_area_3d = torch.as_tensor(study_area_3d_np, device=device)
    fluid_mask = (~solid_mask) & study_area_3d
    bottom_fluid = fluid_mask[0]
    bottom_exchange_coeff = torch.as_tensor(
        boundary_fields["surface_exchange_coeff_per_s"].astype(np.float32), device=device
    )
    ground_surface_temperature_excess_c = torch.as_tensor(
        boundary_fields["ground_surface_temperature_excess_c"].astype(np.float32), device=device
    )
    roof_surface_temperature_excess_3d = torch.as_tensor(
        boundary_fields["roof_surface_temperature_excess_3d"].astype(np.float32), device=device
    )
    ambient_temp_series_c = boundary_fields["ambient_temp_series_c"].astype(np.float32)
    inflow_temp_series_c = boundary_fields["inflow_temp_series_c"].astype(np.float32)
    surface_forcing_layer_count = int(boundary_fields["surface_forcing_layer_count"][0])
    temperature_c = torch.as_tensor(
        np.ascontiguousarray(initial_temperature_c, dtype=np.float32), device=device
    ).clone()  ### initial state instead of uniform ambient
    M3.impose_boundary_conditions_3d_torch(
        temperature_c,
        solid_mask,
        roof_mask,
        study_area_3d,
        roof_surface_temperature_excess_3d,
        current_ambient_temp_c=float(ambient_temp_series_c[0]),
        current_inflow_temp_c=float(inflow_temp_series_c[0]),
    )
    frame_means = [float(temperature_c[fluid_mask].mean())]
    diffusion_coeff = float(temp3d_config.diffusion_coeff_m2_s)
    zero = torch.zeros((), device=device)
    with torch.no_grad():
        for frame_idx in range(u_frames.shape[0]):
            u = torch.where(fluid_mask, u_frames[frame_idx], zero)
            v = torch.where(fluid_mask, v_frames[frame_idx], zero)
            w = torch.where(fluid_mask, w_frames[frame_idx], zero)
            current_ambient_temp_c = float(
                ambient_temp_series_c[min(frame_idx + 1, len(ambient_temp_series_c) - 1)]
            )
            current_inflow_temp_c = float(
                inflow_temp_series_c[min(frame_idx + 1, len(inflow_temp_series_c) - 1)]
            )
            current_ground_surface_temperature_c = (
                current_ambient_temp_c + ground_surface_temperature_excess_c
            )
            for _ in range(substeps):
                sh = M3.shift_with_edge_torch
                left = sh(temperature_c, 2, 1)
                right = sh(temperature_c, 2, -1)
                north = sh(temperature_c, 1, 1)
                south = sh(temperature_c, 1, -1)
                below = sh(temperature_c, 0, 1)
                above = sh(temperature_c, 0, -1)
                below[0] = temperature_c[0]
                adv_x = torch.where(
                    u >= 0, u * (temperature_c - left) / dx, u * (right - temperature_c) / dx
                )
                adv_y = torch.where(
                    v >= 0, v * (temperature_c - north) / dy, v * (south - temperature_c) / dy
                )
                adv_z = torch.where(
                    w >= 0, w * (temperature_c - below) / dz, w * (above - temperature_c) / dz
                )
                laplacian = (
                    (left - 2 * temperature_c + right) / dx**2
                    + (north - 2 * temperature_c + south) / dy**2
                    + (below - 2 * temperature_c + above) / dz**2
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
                nxt = temperature_c + dt * (
                    -(adv_x + adv_y + adv_z) + diffusion_coeff * laplacian + surface_exchange_term
                )
                temperature_c[fluid_mask] = nxt[fluid_mask]
                M3.impose_boundary_conditions_3d_torch(
                    temperature_c,
                    solid_mask,
                    roof_mask,
                    study_area_3d,
                    roof_surface_temperature_excess_3d,
                    current_ambient_temp_c=current_ambient_temp_c,
                    current_inflow_temp_c=current_inflow_temp_c,
                )
            frame_means.append(float(temperature_c[fluid_mask].mean()))
    return (
        temperature_c.cpu().numpy(),
        fluid_mask_np,
        {"dt_seconds": dt, "substeps_per_frame": substeps, "frame_means_c": frame_means},
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-06-21")
    ap.add_argument("--hours", default="4-23")
    ap.add_argument("--cloud", type=float, default=0.0)
    ap.add_argument("--tmin", type=float, default=15.0)
    ap.add_argument("--tmax", type=float, default=26.0)
    ap.add_argument("--rh", type=float, default=55.0)
    ap.add_argument("--frames_per_hour", type=int, default=40)
    a = ap.parse_args()
    out = BASE / f"diurnal_{a.date}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "hourly").mkdir(exist_ok=True)
    fh = open(out / "run.log", "a")
    t0 = time.time()
    y, mo, d = map(int, a.date.split("-"))
    h0, h1 = map(int, a.hours.split("-"))
    utc_off = 1 if 4 <= mo <= 9 else 0
    velocity_config = SouthKensingtonConfig(
        timesteppings=20,
        model_resolution_m=CELL,
        z_dim=16,
        height_scale_m=CELL,
        output_dir=str(BASE / "velocity_unused"),
    )
    cfg0 = M3.Temperature3DScenarioConfig(
        output_dir=str(out / "model_unused"),
        reuse_velocity_output_dir=str(CACHE),
        save_animation=False,
        save_overview_figure=False,
        temperature_solver_backend="cuda",
        temperature_solver_device="cuda",
        cloud_cover_fraction=a.cloud,
        ambient_relative_humidity_pct=a.rh,
        background_temp_delta_c=(0.0,) * 7,
        frame_duration_s=90.0,
    )
    fields = M3.load_cached_full_velocity_fields(velocity_config, cfg0)
    assert fields is not None, (
        "velocity cache missing: run run_core008_temperature3d_solar.py first"
    )
    reps = int(np.ceil(a.frames_per_hour / fields["u"].shape[0]))
    for k in ("u", "v", "w", "speed"):
        fields[k] = np.concatenate([fields[k]] * reps)[: a.frames_per_hour]
    ground_img = fields["study_area_mask_2d"] & ~fields["building_mask_2d"]
    veg_img = fields["vegetation_mask_2d"]
    urb_img = fields["urban_mask_2d"]

    # solar inputs (1 m ShadowNet on the flood terrain; SVF from the solar run)
    dev = torch.device("cuda")
    H = np.load(TERRAIN / "bed_block_1m_yx.npy")
    ny1, nx1 = H.shape
    oy, ox = int(Y0 // CELL), int(X0 // CELL)
    canopy4 = np.load(LANDCOVER / "canopy_4m_yx.npy")[oy : oy + ny1 // 4, ox : ox + nx1 // 4]
    trans4 = np.where(canopy4, CANOPY_TRANSMITTANCE, 1.0).astype(np.float32)
    svf4 = np.load(SOLAR / "svf/svf_4m_yx.npy")
    svf_img = to_image(svf4)
    sn = ShadowNet(H, 1.0, dev)
    state = {"ratio_img": np.ones_like(svf_img, np.float32)}

    def shadow_from_solar(
        building_mask,
        height_field,
        grid_resolution_m,
        solar_elevation_deg,
        solar_azimuth_deg,
        soften_passes=0,
    ):
        return np.clip(1.0 - state["ratio_img"], 0.0, 1.0).astype(np.float32)

    orig_solve = M3.solve_surface_temperature_excess_c

    def solve_with_svf(
        absorbed_shortwave_w_m2,
        emissivity,
        latent_heat_flux_w_m2,
        storage_fraction,
        convective_coeff_w_m2_k,
        downwelling_longwave_w_m2,
        ambient_temp_c,
        anthropogenic_heat_flux_w_m2,
    ):
        l_down = downwelling_longwave_w_m2 * svf_img + SIGMA * (ambient_temp_c + 273.15) ** 4 * (
            1.0 - svf_img
        )
        return orig_solve(
            absorbed_shortwave_w_m2,
            emissivity,
            latent_heat_flux_w_m2,
            storage_fraction,
            convective_coeff_w_m2_k,
            l_down.astype(np.float32),
            ambient_temp_c,
            anthropogenic_heat_flux_w_m2,
        )

    M3.compute_building_shadow_field = shadow_from_solar
    M3.solve_surface_temperature_excess_c = solve_with_svf

    T = None
    series = []
    hourly_surface = []
    hourly_air0 = []
    hourly_air3 = []
    for hour in range(h0, h1 + 1):
        ts = time.time()
        t_amb0 = ambient_c(hour, a.tmin, a.tmax)
        t_amb1 = ambient_c(hour + 1, a.tmin, a.tmax)
        hour_utc = hour - utc_off
        cfg = replace(
            cfg0,
            ambient_temp_c=t_amb0,
            inflow_temp_c=t_amb0,
            analysis_time_utc=f"{a.date}T{hour_utc % 24:02d}:00:00+00:00",
            background_temp_reference_hour_local=float(hour),
            background_temp_delta_hours_local=(0.0, 1.0),
            background_temp_delta_c=(0.0, t_amb1 - t_amb0),
        )
        dt_utc = M3.parse_utc_datetime(cfg.analysis_time_utc)
        alt, az = M3.compute_solar_position_deg(
            cfg.site_latitude_deg, cfg.site_longitude_deg, dt_utc
        )
        if alt > 0:
            ghi_model = float(
                M3.estimate_reference_et0_mm_per_hour(
                    temp_c=t_amb0,
                    pressure_pa=cfg.air_pressure_pa,
                    solar_elevation_deg=alt,
                    cloud_cover_fraction=a.cloud,
                    reference_crop_albedo=cfg.reference_crop_albedo,
                    priestley_taylor_alpha=cfg.priestley_taylor_alpha,
                )["ghi_w_m2"]
            )
            sunlit4 = (
                (~sn(alt, az))
                .float()
                .reshape(ny1 // 4, 4, nx1 // 4, 4)
                .mean(dim=(1, 3))
                .cpu()
                .numpy()
            )
            dni, dhi = clear_sky(alt, mo)
            direct_h = min((1 - a.cloud) * dni * math.sin(math.radians(alt)), ghi_model)
            diffuse = max(ghi_model - direct_h, 0.0)
            ghi_cell = (
                sunlit4 * direct_h * trans4 + diffuse * svf4 + ALBEDO * ghi_model * (1 - svf4)
            )
            state["ratio_img"] = to_image(ghi_cell / max(ghi_model, 1e-6)).astype(np.float32)
        else:
            ghi_model, sunlit4, direct_h, diffuse = 0.0, np.zeros_like(svf4), 0.0, 0.0
            state["ratio_img"] = np.ones_like(svf_img, np.float32)
        bf = M3.build_surface_temperature_fields(fields, velocity_config, cfg)
        if T is None:
            T = np.full(fields["solid_mask_3d"].shape, t_amb0, np.float32)
        T, fluid, info = solve_from_state(fields, bf, velocity_config, cfg, T)
        gs = bf["ground_surface_temperature_c"]
        air0 = T[0]
        air3 = T[3]
        f0 = fluid[0]
        f3 = fluid[3]
        rec = {
            "hour_local": hour + 1,
            "hour_utc": (hour_utc + 1) % 24,
            "sun_alt_deg_start": alt,
            "sun_az_deg_start": az,
            "ambient_c_end": t_amb1,
            "ghi_open_w_m2": ghi_model,
            "direct_h_w_m2": direct_h,
            "diffuse_w_m2": diffuse,
            "sunlit_fraction_ground": float(sunlit4[ground_img[::-1]].mean()) if alt > 0 else 0.0,
            "surface_mean_ground_c": float(gs[ground_img].mean()),
            "surface_mean_urban_c": float(gs[urb_img].mean()),
            "surface_mean_vegetation_c": float(gs[veg_img].mean()),
            "surface_p5_p95_c": [
                float(np.percentile(gs[ground_img], 5)),
                float(np.percentile(gs[ground_img], 95)),
            ],
            "air0_mean_c": float(air0[f0].mean()),
            "air0_p5_p95_c": [
                float(np.percentile(air0[f0], 5)),
                float(np.percentile(air0[f0], 95)),
            ],
            "air0_urban_mean_c": float(air0[f0 & urb_img].mean()),
            "air0_vegetation_mean_c": float(air0[f0 & veg_img].mean()),
            "air3_mean_c": float(air3[f3].mean()),
            "air_excess_over_ambient_c": float(air0[f0].mean() - t_amb1),
            "dt_s": info["dt_seconds"],
            "substeps": info["substeps_per_frame"],
            "seconds": time.time() - ts,
        }
        series.append(rec)
        hourly_surface.append(to_image(gs).astype(np.float16))
        hourly_air0.append(to_image(air0).astype(np.float16))
        hourly_air3.append(to_image(air3).astype(np.float16))
        log(
            fh,
            f"{a.date} {hour + 1:02d}:00 local | sun alt {alt:5.1f} | GHI {ghi_model:4.0f} | ambient {t_amb1:.1f} | surface ground {rec['surface_mean_ground_c']:.2f} (urban {rec['surface_mean_urban_c']:.2f}, veg {rec['surface_mean_vegetation_c']:.2f}) | "
            f"air 0-4 m {rec['air0_mean_c']:.2f} (+{rec['air_excess_over_ambient_c']:.2f}) | {rec['seconds']:.0f} s",
        )
    np.save(out / "hourly_ground_surface_c_tyx.npy", np.stack(hourly_surface))
    np.save(out / "hourly_air_0_4m_c_tyx.npy", np.stack(hourly_air0))
    np.save(out / "hourly_air_12_16m_c_tyx.npy", np.stack(hourly_air3))
    np.save(out / "final_air_3d_c_zyx.npy", T.astype(np.float16))
    (out / "series.json").write_text(json.dumps(series, indent=1))
    (out / "run_config.json").write_text(
        json.dumps(
            {
                "date": a.date,
                "hours_local": [h0 + 1, h1 + 1],
                "utc_offset_h": utc_off,
                "ambient": f"sinusoid {a.tmin}-{a.tmax} C, min 05:00, max 15:00",
                "cloud": a.cloud,
                "rh_pct": a.rh,
                "wind": "SCALED scaled_latent 4 m frames 81..100 looped, 40 x 90 s per hour",
                "solver": "M3.solve_temperature_fields_3d_torch copied with initial state; boundary fields from M3.build_surface_temperature_fields with ShadowNet/SVF patches",
                "arrays": {
                    "hourly_*_tyx": "index k = end of hour hours_local[0]+k local, domain orientation (row 0 = south), float16",
                    "final_air_3d_c_zyx": "[16,704,768] at the last hour",
                },
                "temperature_config_base": asdict(cfg0),
                "seconds": time.time() - t0,
            },
            indent=2,
        )
    )
    log(fh, f"done in {time.time() - t0:.0f} s")
    fh.close()


if __name__ == "__main__":
    main()
