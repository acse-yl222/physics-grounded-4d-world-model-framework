"""Core008 wind -> temperature run on the detailed campus core.

Stage 1: DIGIT wind rollout (unchanged run_digit_rollout) on a 768 m x 768 m x 128 m crop
         of the 2 m core008 voxel grid, run long enough to inspect frame-to-frame convergence.
Stage 2: coarsen the final wind frame to 4 m and drive (a) the controlled heat solver and
         (b) the frozen 15-channel one-step temperature U-Net from the teacher package,
         reusing those functions unchanged (cloud_workflow.py).

Outputs go to <project>/output/core008/physics. This is a transfer experiment on new geometry
with a synthetic steady inflow; there is no CFD or measured reference.
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import hashlib
import json
import sys
import time
import types
from pathlib import Path

import numpy as np
import torch

ROOT = repo_root()
DIGIT_CODE = ROOT / 'src/urban_flow/physics/environment-integration/members/yiqi_temperature/models/velocity_calculation'
TEACHER_CODE = ROOT / 'src/urban_flow/physics/wind_temperature_teacher/code'
TEMPERATURE_WEIGHTS = ROOT / 'project/south_ken/input/models/temperature_one_step.pt'
GEOMETRY = ROOT / 'output/core008/geometry/south_kensington_core008_voxel_2m_domain4096'
OUT = ROOT / 'output/core008/physics/digit'

sys.path.insert(0, str(DIGIT_CODE))
sys.path.insert(0, str(TEACHER_CODE))
# cloud_workflow imports h5py only for reading the old regression1024 wind archive, which is not used here.
sys.modules.setdefault('h5py', types.ModuleType('h5py'))
from south_kensington_jupyter import SouthKensingtonConfig, load_digit_model, run_digit_rollout, scale_back  # noqa: E402
import cloud_workflow as cw  # noqa: E402

# ----------------------------------------------------------------------------- settings
SPACING = 2                      # metres, source voxel grid
CROP_LOWER_XYZ = (2408, 1544, 0)   # padded-domain metres; covers the detailed 008 core (x 2505..3083, y 1543..2312)
CROP_SIZE_XYZ = (768, 768, 128)
WIND_FRAMES = 20                 # predicted frames (timesteppings = frames + 2)
WIND_ITERATIONS = 5
INLET = 0.25                     # normalised; source scale_back [-4,4] -> 1.0 in physical-style units
FACTOR = 2                       # 2 m wind -> 4 m temperature grid
THERMAL = {'ambient_c': 26.0, 'ground_c': 30.0, 'roof_c': 30.0, 'surface_exchange_per_s': 0.001,
           'diffusivity_m2_s': 1.0, 'cfl_safety': 0.8, 'forcing_layers': 2, 'temperature_steps': 5,
           'temperature_overlap': [4, 8, 8], 'fine_spacing_m': float(SPACING), 'factor': FACTOR,
           'wind_step_seconds': None, 'temperature_step_seconds': 90.0}

WIND_DIR = OUT / 'wind'
TEMP_DIR = OUT / 'temperature'
for folder in (WIND_DIR, TEMP_DIR):
    folder.mkdir(parents=True, exist_ok=True)

torch.manual_seed(0)
torch.set_num_threads(8)
assert torch.cuda.is_available()
device = torch.device('cuda')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


# ----------------------------------------------------------------------------- stage 1: wind
def wake_diagnostic(speed, fluid, solid):
    """Mean speed one cell downstream (+x) vs upstream (-x) of building faces, bottom 20 m."""
    zmax = 20 // SPACING
    down = np.zeros_like(fluid); down[:, :, 1:] = solid[:, :, :-1] & fluid[:, :, 1:]
    up = np.zeros_like(fluid); up[:, :, :-1] = solid[:, :, 1:] & fluid[:, :, :-1]
    down[zmax:] = False; up[zmax:] = False
    return {'mean_speed_plus_x_side_of_buildings': float(speed[down].mean()),
            'mean_speed_minus_x_side_of_buildings': float(speed[up].mean()),
            'cells_plus_x': int(down.sum()), 'cells_minus_x': int(up.sum())}


def run_wind():
    x0, y0, z0 = (v // SPACING for v in CROP_LOWER_XYZ)
    nx, ny, nz = (v // SPACING for v in CROP_SIZE_XYZ)
    full = np.load(GEOMETRY / 'solid.npy', mmap_mode='r')
    solid = np.array(full[z0:z0 + nz, y0:y0 + ny, x0:x0 + nx])
    del full
    assert solid.shape == (nz, ny, nx) and all(n % 8 == 0 for n in solid.shape)
    fluid = ~solid
    fluid[0] = False                           # source code forces the bottom voxel layer solid
    distribution = torch.from_numpy(fluid.astype(np.float32))[None, None]

    cfg = SouthKensingtonConfig(artifact_dir=str(ROOT / 'project/south_ken/input/models'), timesteppings=WIND_FRAMES + 2,
                                num_iterations=WIND_ITERATIONS, inlet_flow=INLET)
    cfg.model_resolution_m = SPACING; cfg.height_scale_m = SPACING
    model = load_digit_model(cfg, device)
    log(f'DIGIT rollout on {solid.shape} (z,y,x) at {SPACING} m, {WIND_FRAMES} frames')
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    prediction = run_digit_rollout(model, distribution, cfg, device)
    torch.cuda.synchronize()
    elapsed = time.time() - t0
    peak = torch.cuda.max_memory_allocated() / 1024 ** 3
    del model; torch.cuda.empty_cache()
    velocity = scale_back(prediction, -4, 4).numpy().astype(np.float32)   # [t, c, z, y, x]
    del prediction
    assert np.isfinite(velocity).all()
    assert not np.any(velocity[:, :, ~fluid])

    speed = np.linalg.norm(velocity, axis=1)
    interior = fluid.copy()
    for axis in range(3):
        interior &= np.roll(fluid, 1, axis) & np.roll(fluid, -1, axis)
    interior[[0, -1]] = False; interior[:, [0, -1]] = False; interior[:, :, [0, -1]] = False
    frames = []
    for t, v in enumerate(velocity):
        div = (np.gradient(v[0], SPACING, axis=2) + np.gradient(v[1], SPACING, axis=1)
               + np.gradient(v[2], SPACING, axis=0))
        frames.append({'frame': t + 1,
                       'fluid_speed_mean': float(speed[t][fluid].mean()),
                       'fluid_speed_p95': float(np.percentile(speed[t][fluid], 95)),
                       'fluid_speed_max': float(speed[t][fluid].max()),
                       'fluid_u_mean': float(v[0][fluid].mean()),
                       'interior_divergence_rms': float(np.sqrt(np.mean(div[interior] ** 2))),
                       'change_from_previous_rms': None if t == 0 else
                       float(np.sqrt(np.mean((velocity[t, :, fluid] - velocity[t - 1, :, fluid]) ** 2)))})
        log(f"wind frame {t + 1}: mean {frames[-1]['fluid_speed_mean']:.4f}  "
            f"change {frames[-1]['change_from_previous_rms']}")

    np.save(WIND_DIR / 'velocity_final_czyx.npy', velocity[-1])
    np.save(WIND_DIR / 'velocity_tczyx_float16.npy', velocity.astype(np.float16))
    np.save(WIND_DIR / 'solid_zyx.npy', solid)
    np.save(WIND_DIR / 'solver_fluid_zyx.npy', fluid)
    metrics = {'spacing_m': SPACING, 'shape_zyx': list(solid.shape), 'frames_predicted': WIND_FRAMES,
               'iterations_per_frame': WIND_ITERATIONS, 'rollout_seconds': elapsed,
               'gpu_peak_allocated_GiB': peak, 'all_finite': True, 'solid_velocity_zero': True,
               'building_fraction_of_crop': float(solid.mean()),
               'wake_check_final_frame': wake_diagnostic(speed[-1], fluid, solid),
               'frames': frames}
    (WIND_DIR / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    return solid, fluid, velocity[-1], metrics


# ----------------------------------------------------------------------------- stage 2: temperature
def coarsen_wind_masked(uvw, fine_fluid, factor):
    """Mean over fine fluid cells only, so the forced ground layer does not halve the lowest 4 m wind."""
    c, z, y, x = uvw.shape
    v = uvw.reshape(c, z // factor, factor, y // factor, factor, x // factor, factor)
    m = fine_fluid.reshape(z // factor, factor, y // factor, factor, x // factor, factor).astype(np.float32)
    num = (v * m[None]).sum(axis=(2, 4, 6))
    den = m.sum(axis=(1, 3, 5))
    return np.where(den[None] > 0, num / np.maximum(den[None], 1), 0.0).astype(np.float32)


def run_temperature(solid_fine, fluid_fine, wind_fine, wind_metrics):
    cfg = dict(THERMAL)
    geo = cw.coarse_geometry(solid_fine, factor=FACTOR, spacing=float(SPACING * FACTOR))
    uvw = coarsen_wind_masked(wind_fine, fluid_fine, FACTOR)
    uvw[:, geo['solid']] = 0          # DIGIT u,v,w already use increasing-index axes; no NN4PDEs sign flip
    assert np.isfinite(uvw).all()
    np.save(TEMP_DIR / 'wind_4m_czyx.npy', uvw)
    np.save(TEMP_DIR / 'solid_4m_zyx.npy', geo['solid'])
    np.save(TEMP_DIR / 'roof_4m_zyx.npy', geo['roof'])
    np.save(TEMP_DIR / 'height_4m_yx.npy', geo['height'])
    log(f"temperature grid {geo['solid'].shape} at 4 m; fluid fraction {float((~geo['solid']).mean()):.3f}")

    steps = cfg['temperature_steps']
    times = [-180, -90, 0] + [90 * k for k in range(1, steps + 1)]
    t = np.full(geo['solid'].shape, cfg['ambient_c'], np.float32)
    t[geo['roof']] = cfg['roof_c']
    refs = [t]
    solver_log = []
    for k in range(len(times) - 1):
        t0 = time.time()
        t, stats = cw.physical_step(refs[-1], uvw, geo, cfg, device='cuda')
        refs.append(t)
        solver_log.append({'time_seconds': times[k + 1], **stats, 'seconds': time.time() - t0,
                           'fluid_mean_c': float(t[~geo['solid']].mean()),
                           'fluid_max_c': float(t[~geo['solid']].max())})
        log(f"solver -> {times[k + 1]:+d} s: {stats['substeps']} substeps, mean {solver_log[-1]['fluid_mean_c']:.3f} C")
    for k, r in enumerate(refs):
        np.save(TEMP_DIR / f'reference_{k:03d}.npy', r)
    (TEMP_DIR / 'physical_solver.json').write_text(json.dumps(
        {'times_seconds': times, 'frames': solver_log,
         'wind': 'final DIGIT frame held constant for all frames (steady-wind assumption)',
         'initialization': 'ambient everywhere, roof cells at roof_c, warm-up from -180 s to 0 s'}, indent=2) + '\n')

    model, stats, patch = cw.load_temperature(TEMPERATURE_WEIGHTS, 'cuda')
    mask = ~geo['solid']
    history = np.stack(refs[:3])
    persistence = history[-1].copy()
    rows = []
    torch.cuda.reset_peak_memory_stats()
    for k in range(steps):
        target = refs[k + 3]
        outputs = {}
        for mode in ('recursive', 'one_step'):
            h = history if mode == 'recursive' else np.stack(refs[k:k + 3])
            pred = cw.predict(model, cw.make_input(h, uvw, geo, cfg, stats), stats, patch,
                              tuple(cfg['temperature_overlap']), 'cuda')
            np.save(TEMP_DIR / f'{mode}_{k + 1:03d}.npy', pred)
            outputs[mode] = pred
            rows.append({'time_seconds': (k + 1) * 90, 'mode': mode, **cw.metrics(pred, target, mask)})
        rows.append({'time_seconds': (k + 1) * 90, 'mode': 'persistence', **cw.metrics(persistence, target, mask)})
        history = np.concatenate([history[1:], outputs['recursive'][None]], axis=0)
        log(f"temperature +{(k + 1) * 90} s: recursive MAE {rows[-3]['mae_c']:.4f} C, "
            f"one-step MAE {rows[-2]['mae_c']:.4f} C, persistence MAE {rows[-1]['mae_c']:.4f} C")
    (TEMP_DIR / 'metrics.json').write_text(json.dumps(rows, indent=2) + '\n')
    return {'grid_shape_zyx': list(geo['solid'].shape), 'spacing_m': SPACING * FACTOR,
            'patch': list(patch), 'overlap': cfg['temperature_overlap'],
            'checkpoint_stats': {k: float(v) for k, v in stats.items()},
            'gpu_peak_allocated_GiB': torch.cuda.max_memory_allocated() / 1024 ** 3}


# ----------------------------------------------------------------------------- main
if __name__ == '__main__':
    run_config = {
        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'torch': torch.__version__, 'gpu': torch.cuda.get_device_name(), 'seed': 0,
        'geometry': str(GEOMETRY / 'solid.npy'),
        'geometry_metadata': json.loads((GEOMETRY / 'metadata.json').read_text()),
        'crop_domain_lower_xyz_m': list(CROP_LOWER_XYZ),
        'crop_domain_upper_xyz_m': [a + b for a, b in zip(CROP_LOWER_XYZ, CROP_SIZE_XYZ)],
        'crop_region_lower_xyz_m': [CROP_LOWER_XYZ[0] - 2116, CROP_LOWER_XYZ[1] - 2124, 0],
        'wind': {'model': 'DIGIT UNet_New, 3D, 10 input channels, 3 output channels',
                 'checkpoint': str(ROOT / 'project/south_ken/input/models/digit.pth'),
                 'checkpoint_sha256': sha256(ROOT / 'project/south_ken/input/models/digit.pth'),
                 'spacing_m': SPACING, 'frames': WIND_FRAMES, 'iterations_per_frame': WIND_ITERATIONS,
                 'normalized_inlet_u': INLET,
                 'velocity_conversion': 'source scale_back [-4,4]: physical-style velocity = normalized * 4',
                 'physical_time_per_frame_s': None},
        'temperature': {'model': 'Yi Qi one-step 3D U-Net, 15 input channels (teacher package export)',
                        'checkpoint': str(TEMPERATURE_WEIGHTS), 'checkpoint_sha256': sha256(TEMPERATURE_WEIGHTS),
                        'controlled_solver': 'cloud_workflow.physical_step (adapted upwind advection + diffusion + ground exchange)',
                        'scenario': THERMAL,
                        'wind_coupling': 'final DIGIT frame, masked block-mean 2 m -> 4 m, zero in conservative-solid cells, held steady'},
        'limits': [
            'No CFD or measured reference: wind accuracy has not been established.',
            'DIGIT checkpoint grid-scale transfer to 2 m has not been validated.',
            'Local crop boundary conditions from the source code; no coupling to the surrounding city.',
            'No physical seconds per DIGIT frame; the final frame is treated as a steady wind.',
            'Thermal scenario values are chosen experiment settings, not measurements.',
            'Temperature reference is the adapted controlled solver, not NN4PDEs or CFD.',
            'Conservative 4 m coarsening can close narrow streets.',
        ]}
    (OUT / 'run_config.json').write_text(json.dumps(run_config, indent=2) + '\n')

    solid, fluid, wind_final, wind_metrics = run_wind()
    temp_info = run_temperature(solid, fluid, wind_final, wind_metrics)
    run_config['temperature'].update(temp_info)
    run_config['wind'].update({'rollout_seconds': wind_metrics['rollout_seconds'],
                               'gpu_peak_allocated_GiB': wind_metrics['gpu_peak_allocated_GiB']})
    (OUT / 'run_config.json').write_text(json.dumps(run_config, indent=2) + '\n')
    log('Pipeline complete.')
