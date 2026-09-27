"""Core008 full building extent: SCALED latent wind surrogate (domain decomposition) -> temperature.

Wind: SCALED-Tutorial released weights (weight/inference.pth latent U-Net, weight/compression.pth VAE),
      run with the same 256 m patch / 32 m halo physical-space domain decomposition that the
      teacher package uses for the 1024 m case (wind_core.tiles), generalised to any domain size.
      Grid is the 1 m core008 voxel grid, bottom 64 m (the model's training depth), covering every
      building in the region plus margin. Starts from rest; each model step = 50 NN4PDEs steps
      = 25 s under the teacher package's explicit SI interpretation (dt 0.5 s, 1 m spacing).
Temperature: unchanged teacher-package functions (cloud_workflow.py): 1 m wind -> 4 m grid with the
      NN4PDEs sign conversion, controlled heat solver, frozen 15-channel one-step U-Net.

Resumable: wind state is checkpointed every step; rerun to continue.
Outputs: <project>/output/core008/physics/scaled
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import hashlib
import importlib.metadata
import json
import math
import sys
import time
import types
from pathlib import Path

import numpy as np
import torch

_orig_version = importlib.metadata.version
importlib.metadata.version = lambda n: '1.24.4' if n == 'numpy' else _orig_version(n)   # tutorial's diffusers shim

ROOT = repo_root()
SCALED_REPO = Path('/home/yl222/workspace/SCALED-Tutorial')
TEACHER_CODE = ROOT / 'src/urban_flow/physics/wind_temperature_teacher/code'
TEMPERATURE_WEIGHTS = ROOT / 'project/south_ken/input/models/temperature_one_step.pt'
GEOMETRY = ROOT / 'output/core008/geometry/south_kensington_core008_voxel_1m_domain4096'
OUT = ROOT / 'output/core008/physics/scaled'
WIND_DIR, TEMP_DIR = OUT / 'wind', OUT / 'temperature'
for folder in (WIND_DIR, TEMP_DIR):
    folder.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SCALED_REPO))
sys.path.insert(0, str(TEACHER_CODE))
sys.modules.setdefault('h5py', types.ModuleType('h5py'))
from scaled.model.autoencoders.autoencoder3dv1 import AutoencoderKL  # noqa: E402
from scaled.model.unets.unet_3ds import UNet3DsModel  # noqa: E402
from wind_core import extract, tiles  # noqa: E402
import cloud_workflow as cw  # noqa: E402

# ----------------------------------------------------------------------------- settings
DOMAIN_LOWER_XYZ = (448, 576, 0)        # padded-domain metres; buildings span x 625..3474, y 754..3348
DOMAIN_SIZE_XYZ = (3136, 2944, 64)      # 1 m cells, each = 256 + 192 k so the halo tiling covers exactly once; 64 m = SCALED training depth
TILE, HALO = 256, 32
WIND_STEPS = 40                         # model steps from rest
SPINUP_STEPS = 22                       # frames 22..40 (19 frames) give 0..450 s at 25 s/step for temperature
STEP_SECONDS = 25.0
FACTOR = 4                              # 1 m -> 4 m temperature grid
THERMAL = {'ambient_c': 26.0, 'ground_c': 30.0, 'roof_c': 30.0, 'surface_exchange_per_s': 0.001,
           'diffusivity_m2_s': 1.0, 'cfl_safety': 0.8, 'forcing_layers': 2, 'temperature_steps': 5,
           'temperature_overlap': [4, 8, 8], 'fine_spacing_m': 1.0, 'factor': FACTOR,
           'wind_step_seconds': STEP_SECONDS, 'temperature_step_seconds': 90.0, 'seed': 0}

assert torch.cuda.is_available()
device = 'cuda'
torch.set_num_threads(8)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def atomic_save(path, array):
    tmp = path.with_suffix('.partial')
    with open(tmp, 'wb') as f:
        np.save(f, array)
    tmp.rename(path)


# ----------------------------------------------------------------------------- wind
def load_wind_models():
    encoder = AutoencoderKL(in_channels=3, out_channels=3, down_block_types=['DownEncoderBlock3D'] * 3,
                            up_block_types=['UpDecoderBlock3D'] * 3, block_out_channels=[128, 256, 384],
                            latent_channels=4)
    encoder.load_state_dict(torch.load(SCALED_REPO / 'weight/compression.pth', map_location='cpu',
                                       weights_only=True), strict=True)
    wind = UNet3DsModel(in_channels=8, out_channels=4, down_block_types=('DownBlock3D',) * 4,
                        up_block_types=('UpBlock3D',) * 4, block_out_channels=(128, 256, 384, 512),
                        add_attention=False)
    wind.load_state_dict(torch.load(SCALED_REPO / 'weight/inference.pth', map_location='cpu',
                                    weights_only=True), strict=True)
    return (wind.eval().requires_grad_(False).to(device), encoder.eval().requires_grad_(False).to(device))


@torch.inference_mode()
def wind_step(x, solid, wind, encoder):
    """Teacher wind_core.wind_step with the domain size taken from x instead of the fixed 1024."""
    result = np.zeros_like(x, dtype=np.float32)
    count = np.zeros(x.shape[-2:], np.uint8)
    for y, z, sy, sx in tiles(x.shape[-2], x.shape[-1], TILE, HALO):
        patch = torch.from_numpy(x[:, :, y:y + TILE, z:z + TILE].copy())[None].to(device)
        fluid = torch.from_numpy((~solid[:, y:y + TILE, z:z + TILE]).astype(np.float32))[None, None].to(device)
        bg = fluid.expand(1, 3, -1, -1, -1).contiguous()
        a = extract(encoder.encode(patch)) / 10
        b = extract(encoder.encode(bg)) / 10
        latent = extract(wind(torch.cat([a, b], 1), torch.zeros(1, dtype=torch.long, device=device)))
        pred = (extract(encoder.decode(latent * 10)) * fluid)[0].float().cpu().numpy()
        oy, ox = slice(y + sy.start, y + sy.stop), slice(z + sx.start, z + sx.stop)
        result[:, :, oy, ox] += pred[:, :, sy, sx]
        count[oy, ox] += 1
    if not np.all(count == 1):
        raise RuntimeError('Invalid wind coverage')
    return result


def wake_diagnostic(uvw4, solid4, zmax_cells=5):
    """Coarse grid, increasing-index convention: +x side of buildings should be slower if u>0 dominates."""
    fluid = ~solid4
    speed = np.linalg.norm(uvw4, axis=0)
    down = np.zeros_like(fluid); down[:, :, 1:] = solid4[:, :, :-1] & fluid[:, :, 1:]
    up = np.zeros_like(fluid); up[:, :, :-1] = solid4[:, :, 1:] & fluid[:, :, :-1]
    down[zmax_cells:] = False; up[zmax_cells:] = False
    return {'mean_speed_plus_x_side': float(speed[down].mean()), 'mean_speed_minus_x_side': float(speed[up].mean()),
            'mean_u_fluid': float(uvw4[0][fluid].mean())}


def run_wind(solid, geo):
    state_file = WIND_DIR / 'resume.pt'
    metrics_file = WIND_DIR / 'metrics.json'
    metrics = json.loads(metrics_file.read_text()) if metrics_file.exists() else {'steps': []}
    if state_file.exists():
        state = torch.load(state_file, map_location='cpu', weights_only=True)
        x, start = state['x'].numpy(), int(state['index'])
        log(f'Resuming wind from step {start}')
    else:
        x, start = np.zeros((3, *solid.shape), np.float32), 0
        atomic_save(WIND_DIR / 'wind4m_000.npy', cw.coarse_wind(x * 3, geo['solid'], FACTOR))
        state = None
    if start >= WIND_STEPS:
        log('Wind already complete')
        return metrics
    wind, encoder = load_wind_models()
    if state is not None:
        torch.set_rng_state(state['cpu_rng']); torch.cuda.set_rng_state(state['cuda_rng'])
    else:
        torch.manual_seed(THERMAL['seed'])
    n_tiles = len(list(tiles(solid.shape[-2], solid.shape[-1], TILE, HALO)))
    log(f'SCALED wind on {solid.shape} (z,y,x) at 1 m, {n_tiles} tiles per step, steps {start + 1}..{WIND_STEPS}')
    prev4 = np.load(WIND_DIR / f'wind4m_{start:03d}.npy')
    for k in range(start + 1, WIND_STEPS + 1):
        t0 = time.time()
        torch.cuda.reset_peak_memory_stats()
        x = wind_step(x, solid, wind, encoder)
        if not np.isfinite(x).all():
            raise RuntimeError('Non-finite wind forecast')
        u4 = cw.coarse_wind(x * 3, geo['solid'], FACTOR)        # physical units, increasing-index axes
        atomic_save(WIND_DIR / f'wind4m_{k:03d}.npy', u4)
        fluid4 = ~geo['solid']
        speed = np.linalg.norm(u4, axis=0)[fluid4]
        entry = {'step': k, 'time_seconds': k * STEP_SECONDS, 'seconds': time.time() - t0,
                 'gpu_peak_allocated_GiB': torch.cuda.max_memory_allocated() / 1024 ** 3,
                 'fluid_speed_mean': float(speed.mean()), 'fluid_speed_p95': float(np.percentile(speed, 95)),
                 'fluid_speed_max': float(speed.max()),
                 'change_from_previous_rms_4m': float(np.sqrt(np.mean((u4[:, fluid4] - prev4[:, fluid4]) ** 2))),
                 **wake_diagnostic(u4, geo['solid'])}
        metrics['steps'] = [s for s in metrics['steps'] if s['step'] < k] + [entry]
        metrics_file.write_text(json.dumps(metrics, indent=2) + '\n')
        if k % 5 == 0 or k == WIND_STEPS:
            torch.save({'x': torch.from_numpy(x), 'index': k, 'cpu_rng': torch.get_rng_state(),
                        'cuda_rng': torch.cuda.get_rng_state()}, state_file.with_suffix('.partial'))
            state_file.with_suffix('.partial').rename(state_file)
        prev4 = u4
        log(f"wind step {k}/{WIND_STEPS}: {entry['seconds']:.0f}s  mean {entry['fluid_speed_mean']:.4f}  "
            f"max {entry['fluid_speed_max']:.3f}  change {entry['change_from_previous_rms_4m']:.5f}  "
            f"u_mean {entry['mean_u_fluid']:+.4f}")
    # final full-resolution field in physical units and the NN4PDEs raw convention (u along decreasing x)
    atomic_save(WIND_DIR / 'velocity_final_1m_raw_czyx_float16.npy', (x * 3).astype(np.float16))
    del wind, encoder
    torch.cuda.empty_cache()
    return metrics


# ----------------------------------------------------------------------------- temperature
def wind_at(seconds):
    """Wind at forecast time t (s): frames SPINUP_STEPS.. are 0, 25, 50 ... s; linear interpolation."""
    seconds = max(float(seconds), 0.0)
    lo = int(math.floor(seconds / STEP_SECONDS)); frac = seconds / STEP_SECONDS - lo
    a = np.load(WIND_DIR / f'wind4m_{SPINUP_STEPS + lo:03d}.npy')
    if frac < 1e-10:
        return a
    b = np.load(WIND_DIR / f'wind4m_{SPINUP_STEPS + lo + 1:03d}.npy')
    return ((1 - frac) * a + frac * b).astype(np.float32)


def run_temperature(geo):
    cfg = dict(THERMAL)
    steps = cfg['temperature_steps']
    times = [-180, -90, 0] + [90 * k for k in range(1, steps + 1)]
    np.save(TEMP_DIR / 'solid_4m_zyx.npy', geo['solid']); np.save(TEMP_DIR / 'roof_4m_zyx.npy', geo['roof'])
    np.save(TEMP_DIR / 'height_4m_yx.npy', geo['height'])
    t = np.full(geo['solid'].shape, cfg['ambient_c'], np.float32)
    t[geo['roof']] = cfg['roof_c']
    refs = [t]; solver_log = []
    for k in range(len(times) - 1):
        t0 = time.time()
        t, stats = cw.physical_step(refs[-1], wind_at(times[k]), geo, cfg, device)
        refs.append(t)
        solver_log.append({'time_seconds': times[k + 1], **stats, 'seconds': time.time() - t0,
                           'fluid_mean_c': float(t[~geo['solid']].mean()), 'fluid_max_c': float(t[~geo['solid']].max())})
        log(f"solver -> {times[k + 1]:+d} s: {stats['substeps']} substeps, mean {solver_log[-1]['fluid_mean_c']:.3f} C")
    for k, r in enumerate(refs):
        np.save(TEMP_DIR / f'reference_{k:03d}.npy', r)
    (TEMP_DIR / 'physical_solver.json').write_text(json.dumps(
        {'times_seconds': times, 'frames': solver_log,
         'wind': f'SCALED frames {SPINUP_STEPS}..{WIND_STEPS} = 0..{(WIND_STEPS - SPINUP_STEPS) * STEP_SECONDS:g} s, '
                 'linearly interpolated to each frame start and held during its 90 s; warm-up uses the 0 s wind',
         'initialization': 'ambient everywhere, roof cells at roof_c, warm-up from -180 s to 0 s'}, indent=2) + '\n')

    model, stats, patch = cw.load_temperature(TEMPERATURE_WEIGHTS, device)
    mask = ~geo['solid']
    history = np.stack(refs[:3]); persistence = history[-1].copy(); rows = []
    torch.cuda.reset_peak_memory_stats()
    for k in range(steps):
        uvw = wind_at(k * 90); target = refs[k + 3]; outputs = {}
        for mode in ('recursive', 'one_step'):
            h = history if mode == 'recursive' else np.stack(refs[k:k + 3])
            pred = cw.predict(model, cw.make_input(h, uvw, geo, cfg, stats), stats, patch,
                              tuple(cfg['temperature_overlap']), device)
            np.save(TEMP_DIR / f'{mode}_{k + 1:03d}.npy', pred); outputs[mode] = pred
            rows.append({'time_seconds': (k + 1) * 90, 'mode': mode, **cw.metrics(pred, target, mask)})
        rows.append({'time_seconds': (k + 1) * 90, 'mode': 'persistence', **cw.metrics(persistence, target, mask)})
        history = np.concatenate([history[1:], outputs['recursive'][None]], axis=0)
        log(f"temperature +{(k + 1) * 90} s: recursive MAE {rows[-3]['mae_c']:.4f} C, "
            f"one-step MAE {rows[-2]['mae_c']:.4f} C, persistence MAE {rows[-1]['mae_c']:.4f} C")
    (TEMP_DIR / 'metrics.json').write_text(json.dumps(rows, indent=2) + '\n')
    return {'grid_shape_zyx': list(geo['solid'].shape), 'spacing_m': FACTOR, 'patch': list(patch),
            'overlap': cfg['temperature_overlap'], 'checkpoint_stats': {k: float(v) for k, v in stats.items()},
            'gpu_peak_allocated_GiB': torch.cuda.max_memory_allocated() / 1024 ** 3}


# ----------------------------------------------------------------------------- main
if __name__ == '__main__':
    x0, y0, z0 = DOMAIN_LOWER_XYZ; nx, ny, nz = DOMAIN_SIZE_XYZ
    full = np.load(GEOMETRY / 'solid.npy', mmap_mode='r')
    solid = np.array(full[z0:z0 + nz, y0:y0 + ny, x0:x0 + nx]); del full
    assert solid.shape == (nz, ny, nx)
    geo = cw.coarse_geometry(solid, factor=FACTOR, spacing=float(FACTOR))
    np.save(WIND_DIR / 'solid_1m_zyx.npy', solid)

    config_file = OUT / 'run_config.json'
    run_config = json.loads(config_file.read_text()) if config_file.exists() else {
        'date': time.strftime('%Y-%m-%d %H:%M:%S'), 'torch': torch.__version__, 'gpu': torch.cuda.get_device_name(),
        'geometry': str(GEOMETRY / 'solid.npy'), 'geometry_metadata': json.loads((GEOMETRY / 'metadata.json').read_text()),
        'domain_lower_xyz_m': list(DOMAIN_LOWER_XYZ),
        'domain_upper_xyz_m': [a + b for a, b in zip(DOMAIN_LOWER_XYZ, DOMAIN_SIZE_XYZ)],
        'domain_region_lower_xyz_m': [x0 - 2116, y0 - 2124, 0],
        'building_fraction_1m': float(solid.mean()),
        'wind': {'model': 'SCALED latent regression surrogate: AutoencoderKL (ratio 4, 4 latent ch) + UNet3Ds (8 in, 4 out)',
                 'repo': 'https://github.com/acse-yl222/SCALED-Tutorial.git',
                 'inference_weight': str(SCALED_REPO / 'weight/inference.pth'),
                 'inference_sha256': sha256(SCALED_REPO / 'weight/inference.pth'),
                 'compression_weight': str(SCALED_REPO / 'weight/compression.pth'),
                 'compression_sha256': sha256(SCALED_REPO / 'weight/compression.pth'),
                 'domain_decomposition': f'{TILE} m patches, {HALO} m halo, physical-space assembly (teacher wind_core.tiles)',
                 'tiles_per_step': len(list(tiles(ny, nx, TILE, HALO))),
                 'steps': WIND_STEPS, 'spinup_steps': SPINUP_STEPS, 'step_seconds': STEP_SECONDS,
                 'initial_state': 'rest (zero velocity), boundary condition = geometry only (bc_mode geometry)',
                 'units': 'model state x = physical uvw / 3; latent scaled by 1/10; raw u is along decreasing x index',
                 'precision': 'float32'},
        'temperature': {'model': 'Yi Qi one-step 3D U-Net, 15 input channels (teacher package export)',
                        'checkpoint': str(TEMPERATURE_WEIGHTS), 'checkpoint_sha256': sha256(TEMPERATURE_WEIGHTS),
                        'controlled_solver': 'cloud_workflow.physical_step', 'scenario': THERMAL,
                        'wind_coupling': 'cloud_workflow.coarse_wind (4x4x4 block mean, u sign flipped, zero in conservative solid)'},
        'limits': [
            'No CFD or measured reference for this geometry: wind accuracy has not been established.',
            'SCALED weights were trained on the original South Kensington 1024 m case; this is a new-geometry transfer.',
            'Buildings above 64 m are truncated by the 64 m model depth.',
            'Flow starts from rest; the 25 s per step mapping follows the teacher package interpretation.',
            'Thermal scenario values are chosen experiment settings, not measurements.',
            'Temperature reference is the adapted controlled solver, not NN4PDEs or CFD.',
            'Conservative 4 m coarsening can close narrow streets.']}
    config_file.write_text(json.dumps(run_config, indent=2) + '\n')

    wind_metrics = run_wind(solid, geo)
    run_config['wind']['total_wind_seconds'] = float(sum(s['seconds'] for s in wind_metrics['steps']))
    run_config['temperature'].update(run_temperature(geo))
    config_file.write_text(json.dumps(run_config, indent=2) + '\n')
    log('Pipeline complete.')
