"""Couple the NN4PDEs solar model (src/urban_flow/physics/solar_np.py) to Yi Qi's 3-D physical temperature model
(south_kensington_temperature_3d.py, unchanged file) on the core008 domain with SCALED wind.

Two runs at the model's own scenario time (2025-07-25 13:00 UTC, 24.2 C, cloud 0.47, wind 3.09 m/s):
  native         : the model's own per-building shadow loop (shade in {0,1}, smoothed twice), uniform GHI and longwave
  solar_coupled  : compute_building_shadow_field is replaced by  1 - GHI_cell / GHI_open  from ShadowNet (1 m shadows pooled to
                   4 m sunlit fraction) + diffuse x SVF + one ground reflection; the downwelling longwave becomes
                   L_sky x SVF + sigma T_air^4 x (1 - SVF)  (walls at air temperature). Everything else identical.
Wind: SCALED scaled_latent 4 m frames 81..100 (statistically steady), 16 layers x 4 m, 90 s per frame -> 30 min.
Usage: python run_core008_temperature3d_solar.py [--frames 81-100] [--time 2025-07-25T13:00:00+00:00]
Outputs: output/core008/physics/scaled_latent/temperature3d_solar/{velocity_cache, native, solar_coupled, compare}
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import argparse
import importlib.util
import json
import math
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

ROOT = repo_root()
RUN = ROOT / 'output/core008/physics/scaled_latent'
OUT = RUN / 'temperature3d_solar'
CACHE = OUT / 'velocity_cache'
MODEL_DIR = ROOT / 'src/urban_flow/physics/environment-integration/members/yiqi_temperature/models/physical_model'
LANDCOVER = ROOT / 'output/core008/geometry/south_kensington_core008_landcover_4m'
TERRAIN = RUN / 'flood/terrain'
SOLAR = RUN / 'solar'
for d in (OUT, CACHE):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(MODEL_DIR)); sys.path.insert(0, str(MODEL_DIR.parent / 'velocity_calculation')); sys.path.insert(0, str(ROOT / 'src/common/pipeline/physics'))
import south_kensington_jupyter as _skj  # noqa: E402
if not hasattr(_skj, 'rotate_2d_field'):          # newer 3-D model expects this helper; only used in the bypassed geometry extraction
    _skj.rotate_2d_field = lambda field, deg: np.rot90(field, k=int(round(deg / 90.0)) % 4) if deg % 360 else field
spec = importlib.util.spec_from_file_location('south_kensington_temperature_3d', MODEL_DIR / 'south_kensington_temperature_3d.py')
M3 = importlib.util.module_from_spec(spec); sys.modules['south_kensington_temperature_3d'] = M3; spec.loader.exec_module(M3)
from south_kensington_jupyter import SouthKensingtonConfig  # noqa: E402
from solar_np import ShadowNet, clear_sky, sun_position  # noqa: E402

CELL = 4.0
X0, Y0 = 480, 640
EXTENT_M = ((625, 3474), (754, 3348))
CANOPY_TRANSMITTANCE, ALBEDO = 0.3, 0.2
SIGMA = 5.670374419e-8


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def to_image(a):
    """domain array (row 0 = south) -> model array (row 0 = north)."""
    return np.ascontiguousarray(a[::-1] if a.ndim == 2 else a[..., ::-1, :])


def build_cache(first, last, velocity_config, temp_config):
    height = np.load(RUN / 'temperature/height_4m_yx.npy').astype(np.float32)      # 4 m roof height, domain orientation (4 m where no building: z=0 layer convention)
    building = np.load(RUN / 'temperature/solid_4m_zyx.npy')[1]                      # footprint = 4-8 m layer of the conservative voxels
    height = np.where(building, height, 0.0).astype(np.float32)
    ny, nx = building.shape
    oy, ox = int(Y0 // CELL), int(X0 // CELL)
    vegetation = np.load(LANDCOVER / 'vegetation_4m_yx.npy')[oy:oy + ny, ox:ox + nx] & ~building
    study = np.zeros_like(building)
    (x0, x1), (y0, y1) = EXTENT_M
    study[int((y0 - Y0) // CELL):int(np.ceil((y1 - Y0) / CELL)), int((x0 - X0) // CELL):int(np.ceil((x1 - X0) / CELL))] = True
    urban = study & ~building & ~vegetation
    open_ground = study & ~building & ~vegetation & ~urban
    u, v, w = [], [], []
    for k in range(first, last + 1):
        f = np.load(RUN / f'wind/wind4m_{k:03d}.npy')            # [3,16,704,768] m/s, +x east, +y north, row 0 south
        u.append(to_image(f[0])); v.append(to_image(-f[1])); w.append(to_image(f[2]))
    u = np.stack(u).astype(np.float32); v = np.stack(v).astype(np.float32); w = np.stack(w).astype(np.float32)
    zb = np.arange(u.shape[1], dtype=np.float32)[:, None, None] * CELL
    height_img = to_image(height)
    solid = zb < height_img[None]
    roof = solid & ~M3.shift_up_boolean(solid)
    fields = {'u': u, 'v': v, 'w': w, 'speed': np.sqrt(u ** 2 + v ** 2 + w ** 2).astype(np.float32),
              'building_mask_2d': to_image(building), 'vegetation_mask_2d': to_image(vegetation), 'urban_mask_2d': to_image(urban),
              'open_ground_mask_2d': to_image(open_ground), 'study_area_mask_2d': to_image(study), 'height_field_2d': height_img,
              'solid_mask_3d': solid, 'roof_mask_3d': roof}
    M3.save_shared_full_velocity_cache(fields, velocity_config, temp_config)
    return {'frames': u.shape[0], 'shape_zyx': list(u.shape[1:]), 'building_cells': int(building.sum()), 'vegetation_cells': int(vegetation.sum()),
            'urban_cells': int(urban.sum()), 'study_cells': int(study.sum()), 'max_speed_m_s': float(fields['speed'].max()),
            'mean_speed_layer1_study_m_s': float(fields['speed'][:, 1][:, to_image(study & ~building)].mean())}


def solar_ratio_fields(alt, az, month, cloud, ghi_model):
    """Per-4 m-cell ratio of received GHI to open-sky GHI (domain orientation), from 1 m ShadowNet + SVF."""
    dev = torch.device('cuda')
    H = np.load(TERRAIN / 'bed_block_1m_yx.npy'); foot1 = np.load(TERRAIN / 'footprint_1m_yx.npy')
    ny1, nx1 = H.shape
    oy, ox = int(Y0 // CELL), int(X0 // CELL)
    canopy4 = np.load(LANDCOVER / 'canopy_4m_yx.npy')[oy:oy + ny1 // 4, ox:ox + nx1 // 4]
    sn = ShadowNet(H, 1.0, dev)
    shadow = sn(alt, az)
    sunlit4 = (~shadow).float().reshape(ny1 // 4, 4, nx1 // 4, 4).mean(dim=(1, 3)).cpu().numpy()
    svf4 = np.load(SOLAR / 'svf/svf_4m_yx.npy')
    dni, dhi = clear_sky(alt, month)
    sin_a = math.sin(math.radians(alt))
    # cloud: the beam is blocked for a fraction ~ cloud cover; the rest of the model GHI is diffuse
    direct_h = (1.0 - cloud) * dni * sin_a
    direct_h = min(direct_h, ghi_model)
    diffuse = max(ghi_model - direct_h, 0.0)
    trans = np.where(canopy4, CANOPY_TRANSMITTANCE, 1.0)
    ghi_cell = sunlit4 * direct_h * trans + diffuse * svf4 + ALBEDO * ghi_model * (1.0 - svf4)
    ratio = ghi_cell / max(ghi_model, 1e-6)
    return {'ratio': ratio.astype(np.float32), 'sunlit_fraction': sunlit4.astype(np.float32), 'svf': svf4.astype(np.float32),
            'direct_h_w_m2': direct_h, 'diffuse_w_m2': diffuse, 'dni_clear': dni, 'dhi_clear': dhi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', default='81-100'); ap.add_argument('--time', default=M3.Temperature3DScenarioConfig.analysis_time_utc)
    a = ap.parse_args()
    first, last = map(int, a.frames.split('-'))
    velocity_config = SouthKensingtonConfig(timesteppings=last - first + 1, model_resolution_m=CELL, z_dim=16, height_scale_m=CELL,
                                            output_dir=str(OUT / 'velocity_unused'))
    base = dict(reuse_velocity_output_dir=str(CACHE), analysis_time_utc=a.time, save_animation=False, save_overview_figure=False,
                temperature_solver_backend='cuda', temperature_solver_device='cuda')
    t0 = time.time()
    stats = build_cache(first, last, velocity_config, M3.Temperature3DScenarioConfig(output_dir=str(OUT / 'native'), **base))
    log(f'velocity cache built: {stats}')

    results = {}
    # ---- native
    cfg_native = M3.Temperature3DScenarioConfig(output_dir=str(OUT / 'native'), **base)
    ts = time.time(); out_native = M3.run_temperature_3d_pipeline(velocity_config, cfg_native)
    results['native'] = {**{k: v for k, v in out_native['summary'].items() if k not in ('velocity_config', 'temperature_3d_config', 'method_references')}, 'seconds': time.time() - ts}
    log(f"native done in {time.time() - ts:.0f} s: T {results['native']['temperature_min_c']:.2f}..{results['native']['temperature_max_c']:.2f} C, "
        f"ground surface {results['native']['ground_surface_temperature_min_c']:.2f}..{results['native']['ground_surface_temperature_max_c']:.2f} C")

    # ---- solar coupled: monkeypatch the shadow function and the surface energy balance's longwave term
    cfg_solar = M3.Temperature3DScenarioConfig(output_dir=str(OUT / 'solar_coupled'), **base)
    dt_utc = M3.parse_utc_datetime(a.time)
    alt_m, az_m = M3.compute_solar_position_deg(cfg_solar.site_latitude_deg, cfg_solar.site_longitude_deg, dt_utc)
    alt_n, az_n = sun_position(cfg_solar.site_latitude_deg, cfg_solar.site_longitude_deg, dt_utc.year, dt_utc.month, dt_utc.day,
                               dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600)
    ghi_model = float(M3.estimate_reference_et0_mm_per_hour(temp_c=cfg_solar.ambient_temp_c, pressure_pa=cfg_solar.air_pressure_pa, solar_elevation_deg=alt_m,
                                                            cloud_cover_fraction=cfg_solar.cloud_cover_fraction, reference_crop_albedo=cfg_solar.reference_crop_albedo,
                                                            priestley_taylor_alpha=cfg_solar.priestley_taylor_alpha)['ghi_w_m2'])
    sol = solar_ratio_fields(alt_m, az_m, dt_utc.month, cfg_solar.cloud_cover_fraction, ghi_model)
    ratio_img = to_image(sol['ratio']); svf_img = to_image(sol['svf'])
    np.save(OUT / 'solar_coupled_inputs_ratio_img.npy', ratio_img); np.save(OUT / 'solar_coupled_inputs_svf_img.npy', svf_img)
    np.save(OUT / 'solar_coupled_inputs_sunlit_fraction_img.npy', to_image(sol['sunlit_fraction']))
    log(f"sun: model alt {alt_m:.2f} az {az_m:.2f} | NOAA alt {alt_n:.2f} az {az_n:.2f} | model GHI {ghi_model:.0f} W/m2 -> direct_h {sol['direct_h_w_m2']:.0f}, diffuse {sol['diffuse_w_m2']:.0f}; "
        f"ratio mean {ratio_img.mean():.3f}, sunlit fraction mean {sol['sunlit_fraction'].mean():.3f}")

    def shadow_from_solar(building_mask, height_field, grid_resolution_m, solar_elevation_deg, solar_azimuth_deg, soften_passes=0):
        return np.clip(1.0 - ratio_img, 0.0, 1.0).astype(np.float32)

    orig_solve = M3.solve_surface_temperature_excess_c

    def solve_with_svf(absorbed_shortwave_w_m2, emissivity, latent_heat_flux_w_m2, storage_fraction, convective_coeff_w_m2_k,
                       downwelling_longwave_w_m2, ambient_temp_c, anthropogenic_heat_flux_w_m2):
        t_air4 = (ambient_temp_c + 273.15) ** 4
        l_down = downwelling_longwave_w_m2 * svf_img + SIGMA * t_air4 * (1.0 - svf_img)
        return orig_solve(absorbed_shortwave_w_m2, emissivity, latent_heat_flux_w_m2, storage_fraction, convective_coeff_w_m2_k,
                          l_down.astype(np.float32), ambient_temp_c, anthropogenic_heat_flux_w_m2)

    M3.compute_building_shadow_field = shadow_from_solar
    M3.solve_surface_temperature_excess_c = solve_with_svf
    ts = time.time(); out_solar = M3.run_temperature_3d_pipeline(velocity_config, cfg_solar)
    results['solar_coupled'] = {**{k: v for k, v in out_solar['summary'].items() if k not in ('velocity_config', 'temperature_3d_config', 'method_references')}, 'seconds': time.time() - ts}
    log(f"solar_coupled done in {time.time() - ts:.0f} s: T {results['solar_coupled']['temperature_min_c']:.2f}..{results['solar_coupled']['temperature_max_c']:.2f} C, "
        f"ground surface {results['solar_coupled']['ground_surface_temperature_min_c']:.2f}..{results['solar_coupled']['ground_surface_temperature_max_c']:.2f} C")

    # ---- comparison (domain orientation for saved arrays)
    cmp = OUT / 'compare'; cmp.mkdir(exist_ok=True)
    fields = out_native['fields']; study = fields['study_area_mask_2d']; bmask = fields['building_mask_2d']
    ground = study & ~bmask
    gs_n = out_native['boundary_fields']['ground_surface_temperature_c']; gs_s = out_solar['boundary_fields']['ground_surface_temperature_c']
    T_n = out_native['temperature_results']['temperature_fields_c']; T_s = out_solar['temperature_results']['temperature_fields_c']
    fluid0 = out_native['temperature_results']['fluid_mask'][0]
    air_n = T_n[-1, 0]; air_s = T_s[-1, 0]
    d_air = air_s - air_n; d_gs = gs_s - gs_n
    shade_n = out_native['boundary_fields']['shade_field']; shade_s = out_solar['boundary_fields']['shade_field']
    np.save(cmp / 'ground_surface_native_c_yx.npy', to_image(gs_n)); np.save(cmp / 'ground_surface_solar_c_yx.npy', to_image(gs_s))
    np.save(cmp / 'air_layer0_final_native_c_yx.npy', to_image(air_n)); np.save(cmp / 'air_layer0_final_solar_c_yx.npy', to_image(air_s))
    np.save(cmp / 'shade_native_yx.npy', to_image(shade_n)); np.save(cmp / 'shade_solar_yx.npy', to_image(shade_s))
    np.save(cmp / 'air_layer0_frames_solar_c_tyx.npy', to_image(T_s[:, 0]).astype(np.float16)); np.save(cmp / 'air_layer0_frames_native_c_tyx.npy', to_image(T_n[:, 0]).astype(np.float16))
    np.save(cmp / 'air_layer3_final_solar_c_yx.npy', to_image(T_s[-1, 3])); np.save(cmp / 'air_layer3_final_native_c_yx.npy', to_image(T_n[-1, 3]))
    q = lambda x, p: float(np.percentile(x, p))
    stats_cmp = {
        'scenario_time_utc': a.time, 'sun_model_alt_az': [alt_m, az_m], 'sun_noaa_alt_az': [alt_n, az_n], 'ghi_model_w_m2': ghi_model,
        'solar_split': {k: sol[k] for k in ('direct_h_w_m2', 'diffuse_w_m2', 'dni_clear', 'dhi_clear')},
        'shade_native': {'mean_ground': float(shade_n[ground].mean()), 'fraction_ground_shaded_gt_0.5': float((shade_n[ground] > 0.5).mean())},
        'shade_solar': {'mean_ground': float(shade_s[ground].mean()), 'fraction_ground_ratio_lt_0.5': float((shade_s[ground] > 0.5).mean()),
                        'sunlit_fraction_ground_mean': float(sol['sunlit_fraction'][to_image(ground)].mean()), 'svf_ground_mean': float(sol['svf'][to_image(ground)].mean())},
        'ground_surface_c': {'native_mean': float(gs_n[ground].mean()), 'solar_mean': float(gs_s[ground].mean()), 'diff_mean': float(d_gs[ground].mean()),
                             'diff_p5': q(d_gs[ground], 5), 'diff_p95': q(d_gs[ground], 95), 'diff_min': float(d_gs[ground].min()), 'diff_max': float(d_gs[ground].max()),
                             'native_p5_p95': [q(gs_n[ground], 5), q(gs_n[ground], 95)], 'solar_p5_p95': [q(gs_s[ground], 5), q(gs_s[ground], 95)]},
        'air_layer0_final_c': {'native_mean': float(air_n[fluid0].mean()), 'solar_mean': float(air_s[fluid0].mean()), 'diff_mean': float(d_air[fluid0].mean()),
                               'diff_p5': q(d_air[fluid0], 5), 'diff_p95': q(d_air[fluid0], 95), 'abs_diff_mean': float(np.abs(d_air[fluid0]).mean()),
                               'corr': float(np.corrcoef(air_n[fluid0], air_s[fluid0])[0, 1])},
        'frame_means_c': {'native': out_native['temperature_results']['frame_means_c'].tolist(), 'solar': out_solar['temperature_results']['frame_means_c'].tolist()},
        'orientation_note': 'compare/*.npy are domain orientation (row 0 = south); native/ and solar_coupled/ folders keep the model orientation (row 0 = north)',
    }
    (cmp / 'comparison.json').write_text(json.dumps(stats_cmp, indent=2))
    (OUT / 'run_summary.json').write_text(json.dumps({
        'date': time.strftime('%Y-%m-%d %H:%M:%S'), 'wind': f'SCALED scaled_latent wind4m steps {first}..{last}, 16 x 4 m layers, v negated + rows flipped to the model frame, 90 s per frame',
        'cache_stats': stats, 'velocity_config': asdict(velocity_config), 'temperature_config_base': base,
        'coupling': {'shadow': '1 - GHI_cell/GHI_open with GHI_cell = sunlit_fraction(1 m ShadowNet pooled to 4 m) * direct_h * canopy + diffuse * SVF + albedo * GHI * (1 - SVF)',
                     'direct_h': '(1 - cloud) * DNI_clear(ASHRAE) * sin(alt), capped by the model GHI; diffuse = model GHI - direct_h',
                     'longwave': 'downwelling = L_sky * SVF + sigma T_air^4 * (1 - SVF)', 'unchanged': 'everything else in south_kensington_temperature_3d.py (file untouched, functions replaced at runtime)'},
        'results': results, 'seconds': time.time() - t0}, indent=2))
    log(f'done in {time.time() - t0:.0f} s; comparison: ' + json.dumps({k: stats_cmp[k] for k in ('ground_surface_c', 'air_layer0_final_c')}))


if __name__ == '__main__':
    main()
