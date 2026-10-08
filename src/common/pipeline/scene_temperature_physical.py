"""Scene 3-D physical temperature: the existing Yi Qi equation solver driven by the stored SCALED wind frames.

    python src/common/pipeline/scene_temperature_physical.py --config output/<scene>/configs/scaled_latent.json \
        --out output/<scene>/physics/temperature3d_physical [--frames 20]

Uses controlled surface temperatures (thermal.ambient_c / ground_c from the legacy wind config), requiring no
assumed solar location. No learned temperature network or temperature checkpoint is loaded. Runs on the
coarse wind grid (cell_m x coarse_factor) over the last --frames wind steps.
"""

# Compatibility for direct source-script execution.
if __name__ == '__main__' and not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.locations import code_path
from common.layout import repo_root
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import torch

ROOT = repo_root()
from common.pipeline.paths import project_path
from common.pipeline.scene_scaled_latent import digest, save_json, log


def load_solver():
    models = code_path('src/urban_flow/physics/environment-integration/members/yiqi_temperature/models')
    sys.path.insert(0, str(models / 'velocity_calculation'))
    sys.path.insert(0, str(models / 'physical_model'))
    import south_kensington_jupyter as velocity
    # The upstream temperature module imports this helper for geometry processing;
    # this adapter supplies already prepared fields and never calls it.
    if not hasattr(velocity, 'rotate_2d_field'):
        def unused_rotation(*args, **kwargs):
            raise RuntimeError('Geometry extraction is bypassed in this scene adapter')
        velocity.rotate_2d_field = unused_rotation
    path = models / 'physical_model/south_kensington_temperature_3d.py'
    spec = importlib.util.spec_from_file_location('scene_physical_temperature', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, path


def fields_and_boundary(solid, wind, ambient_c, excess_c, exchange_per_s):
    roof = solid.copy()
    roof[:-1] &= ~solid[1:]
    fields = {'u': wind[:, 0], 'v': wind[:, 1], 'w': wind[:, 2],
              'solid_mask_3d': solid, 'roof_mask_3d': roof, 'study_area_mask_2d': np.ones(solid.shape[1:], bool)}
    boundary = {'surface_exchange_coeff_per_s': np.full(solid.shape[1:], exchange_per_s, np.float32),
                'ground_surface_temperature_excess_c': np.full(solid.shape[1:], excess_c, np.float32),
                'roof_surface_temperature_excess_3d': roof.astype(np.float32) * excess_c,
                'ambient_temp_series_c': np.full(wind.shape[0] + 1, ambient_c, np.float32),
                'inflow_temp_series_c': np.full(wind.shape[0] + 1, ambient_c, np.float32),
                'surface_forcing_layer_count': np.array([1], np.int32)}
    return fields, boundary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', default='configs/white_city/scaled_latent.json', help='legacy wind config (scaled_latent.json)')
    ap.add_argument('--out', default=None, help='output directory (default: <physics>/temperature3d_physical)')
    ap.add_argument('--frames', type=int, default=20, help='number of trailing wind frames to drive the solver')
    args = ap.parse_args()
    cfg = json.loads(project_path(args.config).read_text())
    run = project_path(cfg['output'])
    geometry = project_path(cfg['geometry'])
    out = project_path(args.out) if args.out else run.parent / 'temperature3d_physical'
    out.mkdir(parents=True, exist_ok=True)
    cell, factor = cfg['cell_m'], cfg['coarse_factor']
    coarse = cell * factor
    steps, step_s = cfg['wind_steps'], float(cfg['step_seconds'])
    thermal = cfg['thermal']
    ambient, excess, exchange = float(thermal['ambient_c']), float(thermal['ground_c']) - float(thermal['ambient_c']), float(thermal['surface_exchange_per_s'])
    n = max(1, min(args.frames, steps))
    first = steps - n

    torch.set_num_threads(8)
    m, source = load_solver()
    # Verify the existing GPU solver against its NumPy counterpart on a small case.
    s = np.zeros((4, 8, 8), bool); s[:2, 3:5, 3:5] = True
    w = np.zeros((2, 3, *s.shape), np.float32); w[:, 0] = .2
    f, b = fields_and_boundary(s, w, 26., 4., .001)
    v = SimpleNamespace(model_resolution_m=float(coarse), height_scale_m=float(coarse))
    t = m.Temperature3DScenarioConfig(frame_duration_s=10., ambient_temp_c=26., inflow_temp_c=26., temperature_solver_device='cuda')
    cpu = m.solve_temperature_fields_3d_numpy(f, b, v, t)['temperature_fields_c']
    gpu = m.solve_temperature_fields_3d_torch(f, b, v, t)['temperature_fields_c']
    error = float(np.max(np.abs(cpu - gpu))); assert np.allclose(cpu, gpu, atol=1e-4, rtol=0)
    save_json(out / 'solver_check.json', {'numpy_cuda_max_abs_error_c': error, 'passed': True})

    fine = np.load(geometry / 'solid.npy', mmap_mode='r')[:cfg['wind_layers']]
    # Physical ground is a boundary, not the SCALED artificial occupied bottom layer.
    z, y, x = fine.shape
    solid = np.asarray(fine).reshape(z // factor, factor, y // factor, factor, x // factor, factor).max(axis=(1, 3, 5))[:, ::-1, :].copy()
    del fine
    frames = []
    for k in range(first, steps):
        with np.load(run / f'wind/wind{coarse}m_{k:03d}.npz') as data:
            uvw = data['uvw'][:, :, ::-1, :].copy(); uvw[1] *= -1; frames.append(uvw)
    wind = np.stack(frames); del frames
    fields, boundary = fields_and_boundary(solid, wind, ambient, excess, exchange)
    config = m.Temperature3DScenarioConfig(frame_duration_s=step_s, ambient_temp_c=ambient, inflow_temp_c=ambient, temperature_solver_device='cuda')
    duration = n * step_s
    save_json(out / 'run_config.json', {'solver': str(source), 'solver_sha256': digest(source), 'wind_config': str(project_path(args.config)),
        'implementation': 'Existing solve_temperature_fields_3d_torch, unchanged finite-difference equations; no trained temperature network.',
        'wind_frames': list(range(first, steps)), 'wind_step_seconds': step_s, 'duration_seconds': duration, 'cell_m': coarse,
        'shape_zyx': list(solid.shape), 'ambient_c': ambient, 'surface_c': ambient + excess, 'exchange_per_s': exchange,
        'forcing_layers': 1, 'diffusivity_m2_s': config.diffusion_coeff_m2_s,
        'orientation': 'Inputs flipped north-up and v negated for original solver; saved arrays restored to local +y row order.',
        'limitations': ['Controlled thermal scenario, not observed temperatures.',
                        'Stored coarse wind has zero bottom-layer velocities due to SCALED conservative ground masking.',
                        'Native solver imposes a fixed left inflow and zero-gradient lateral/outflow boundaries.',
                        f'No solar energy-balance forcing in this run; controlled surfaces remain {ambient + excess:g} C.']})
    log(f'Running original 3-D physical temperature solver, {n} intervals of {step_s:g} seconds on the {coarse} m grid')
    result = m.solve_temperature_fields_3d_torch(fields, boundary, v, config)
    values = result['temperature_fields_c'][:, :, ::-1, :].copy()
    assert values.shape == (n + 1, *solid.shape) and np.isfinite(values).all()
    np.save(out / 'temperature_c_tzyx.npy', values)
    np.save(out / f'solid_{coarse}m_zyx.npy', solid[:, ::-1, :])
    fluid = ~solid[:, ::-1, :]; final = values[-1][fluid]
    save_json(out / 'summary.json', {'complete': True, 'frames': n + 1, 'duration_seconds': duration, 'cell_m': coarse,
        'dt_seconds': result['dt_seconds'], 'substeps_per_frame': result['substeps_per_frame'],
        'final_fluid_mean_c': float(final.mean()), 'final_fluid_min_c': float(final.min()), 'final_fluid_max_c': float(final.max()),
        'all_finite': True, 'numpy_cuda_check_passed': True})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for ax, layer in zip(axes, [0, 1]):
        im = ax.imshow(np.ma.masked_where(~fluid[layer], values[-1, layer]), origin='lower', vmin=ambient, vmax=ambient + excess, cmap='inferno')
        ax.set_title(f'Physical temperature at {duration:g} s; z=[{layer * coarse},{(layer + 1) * coarse}) m'); fig.colorbar(im, ax=ax, label='C')
    fig.savefig(out / 'temperature_final.png', dpi=150); plt.close(fig)
    log('Physical temperature complete')


if __name__ == '__main__':
    main()
