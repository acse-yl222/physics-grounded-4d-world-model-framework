"""10 m/s uniform-grid rotor pilot with explicit paper/reproduction boundaries.

Run as python -m urban_flow.paper_rotor.wind_tunnel with src on PYTHONPATH.
Retains the old pilots; emits a unique, self-contained protocol run in cache.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

import numpy as np
import torch

from common.contract import validate
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runtime import trial_root
from common.storage import Storage
from .rotor import WeightedRotor


def axial_centres(mac):
    west = torch.cat((mac.inlet[..., None], mac.vel[0][..., :-1]), -1)
    return (mac.vel[0] + west) * .5


def axial_faces(acceleration):
    """Cell-to-face force transfer; support must be clear of outer boundaries."""
    return .5 * (acceleration + torch.cat(
        (acceleration[..., 1:], torch.zeros_like(acceleration[..., :1])), -1))


def check_config(config):
    positive = ('inlet_m_s', 'rotor_diameter_m', 'rotor_thickness_m',
                'rho_kg_m3', 'sigma_m', 'cutoff_sigma', 'cell_m', 'end_s',
                'save_interval_s', 'ramp_s', 'cfl', 'pressure_rtol')
    if any(not math.isfinite(config[k]) or config[k] <= 0 for k in positive):
        raise ValueError('Physical and numerical scales must be finite and positive')
    if not 0 < config['ct'] < 1 or not 0 <= config['inner_diameter_m'] < config['rotor_diameter_m']:
        raise ValueError('Invalid rotor geometry or thrust coefficient')
    if config['cfl'] > .5:
        raise ValueError('This pilot limits CFL to 0.5')
    h = config['cell_m']
    shape = tuple(round(v / h) for v in config['domain_xyz_m'][::-1])
    if any(n <= 0 or not math.isclose(n*h, length) for n, length in
           zip(shape, config['domain_xyz_m'][::-1])):
        raise ValueError('Domain must be exactly divisible by uniform cell size')
    level = shape
    while min(level) > 4:
        if any(n % 2 for n in level):
            raise ValueError('Grid dimensions are incompatible with multigrid')
        level = tuple(n // 2 for n in level)
    if not math.isclose(2*config['cutoff_sigma']*config['sigma_m'], config['rotor_thickness_m']):
        raise ValueError('Gaussian support must equal the specified rotor thickness')
    half = [config['rotor_thickness_m']/2] + [config['rotor_diameter_m']/2]*2
    if any(not math.isfinite(p) or p-r <= h or p+r >= length-h
           for p, r, length in zip(config['hub_xyz_m'], half, config['domain_xyz_m'])):
        raise ValueError('Rotor must remain inside the domain, clear of boundary faces')
    return shape


def run(config, backend='triton'):
    shape = check_config(config)
    torch.set_num_threads(4)
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    if backend == 'triton':
        if not torch.cuda.is_available():
            raise RuntimeError('Triton backend requires CUDA; select --backend torch for CPU')
        from urban_flow.solvers.mac_triton import MAC
    else:
        from urban_flow.solvers.mac_torch import MAC
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    storage = Storage.load()
    out = trial_root('actuator_lab', 'paper_rotor_10ms')
    out.mkdir(parents=True, exist_ok=False)
    print('Run directory:', out, flush=True)
    write(out/'config.json', config)
    revision = snapshot_sources(storage.root, out/'source_snapshot.tar.gz')
    created = datetime.now(timezone.utc).isoformat()
    spatial = json.loads((storage.metadata('actuator_lab')/'project.json').read_text())['spatial']
    spatial['bounds_m'] = {'min': [0, 0, 0], 'max': config['domain_xyz_m']}
    manifest = dict(schema_version='1.1.0', scene_id='actuator_lab',
                    simulation='paper_rotor_10ms', run_id=out.name, status='running',
                    created_at=created, spatial=spatial,
                    provenance=dict(code_revision=revision, dirty=True,
                                    parameters={**config, 'backend': backend, 'device': device,
                                                'torch_version': torch.__version__, 'cuda_version': torch.version.cuda},
                                    inputs=[dict(id='configuration', sha256=digest(out/'config.json'))]),
                    time={'unit': 's', 'samples': []}, layers=[])
    write(out/'manifest.json', manifest)
    try:
        h = config['cell_m']; U = config['inlet_m_s']; rho = config['rho_kg_m3']
        nz, ny, nx = shape
        fluid = torch.ones(shape, dtype=torch.bool, device=device)
        inlet = torch.full((nz, ny), U, device=device)
        mac = MAC(fluid, h, inlet)
        mac.vel[0].fill_(U)
        hub = config['hub_xyz_m']
        rotor = WeightedRotor(config['rotor_diameter_m']/2, config['sigma_m'],
                              ct=config['ct'], inner_radius=config['inner_diameter_m']/2,
                              cutoff=config['cutoff_sigma'], rho=rho)
        # Only the rotor bounding box needs coordinates and load-law evaluation.
        half = [config['rotor_thickness_m']/2] + [config['rotor_diameter_m']/2]*2
        indices = [torch.arange(max(0, math.floor((p-r)/h)-1),
                               min(n, math.ceil((p+r)/h)+1), device=device)
                   for p, r, n in zip(hub, half, (nx, ny, nz))]
        iz, iy, ix = torch.meshgrid(*indices[::-1], indexing='ij')
        xyz = (torch.stack((ix, iy, iz), -1).to(torch.float32)+.5)*h
        velocity = torch.zeros_like(xyz)
        acceleration = torch.zeros(shape, device=device)
        def load():
            velocity[..., 0] = .5*(mac.vel[0][iz, iy, ix] + mac.vel[0][iz, iy, ix-1])
            return rotor(xyz, velocity, h**3, hub, [1, 0, 0])
        times = []; histories = []; frames = []; max_balance = 0.; max_divergence = 0.
        # Interpolate the horizontal slice to the exact hub height.
        qz = hub[2]/h-.5; z0 = math.floor(qz); zmix = qz-z0
        def save(t, diag, ramp):
            state = load()
            times.append(t)
            histories.append([float(state['disc_speed']), float(state['thrust'])*ramp,
                              diag['divergence_rms']])
            centred = axial_centres(mac)
            frames.append(((1-zmix)*centred[z0]+zmix*centred[z0+1]).cpu().numpy().copy())
            write(out/'status.json', dict(state='running', time_s=t, steps=step,
                                         disc_speed_m_s=histories[-1][0], thrust_N=histories[-1][1]))
        t = 0.; step = 0; start = time.perf_counter()
        save(0., {'divergence_rms': 0.}, 0.)
        next_save = config['save_interval_s']
        while t < config['end_s']-1e-10:
            state = load()
            ramp = min(1., (t+1e-12)/config['ramp_s'])
            acceleration.zero_()
            acceleration[iz, iy, ix] = state['acceleration'][..., 0]*ramp
            faces = axial_faces(acceleration)
            thrust = float(state['thrust'])*ramp
            balance = abs(float(faces.sum())*rho*h**3+thrust)
            max_balance = max(max_balance, balance)
            if balance > 2e-5*max(thrust, 1.):
                raise RuntimeError('Cell-to-face transfer violates total-force conservation')
            speed = max(U, mac.maxsum())
            if not math.isfinite(speed):
                raise RuntimeError('Nonfinite velocity')
            # Bound both advective transport and the explicit rotor acceleration.
            force_bound = math.sqrt(config['cfl']*h/max(float(faces.abs().max()), 1e-12))
            dt = min(config['cfl']*h/speed, force_bound, config['end_s']-t, next_save-t)
            mac.advect(dt)
            mac.vel[0].add_(faces, alpha=dt)
            diag = mac.project(rtol=config['pressure_rtol'], maxiter=200)
            if not math.isfinite(diag['divergence_rms']):
                raise RuntimeError('Nonfinite divergence')
            max_divergence = max(max_divergence, diag['divergence_rms'])
            t += dt; step += 1
            if t >= next_save-1e-10 or t >= config['end_s']-1e-10:
                save(t, diag, min(1., t/config['ramp_s']))
                next_save += config['save_interval_s']
            if step % 250 == 0:
                print(f'{step} steps, t={t:.3f}s, thrust={thrust:.4f} N', flush=True)
        fields = np.asarray(frames, dtype='<f4')
        (out/'data').mkdir()
        np.save(out/'data/axial_velocity.npy', fields)
        write(out/'data/thrust.json', {'labels': ['rotor'], 'values': [[r[1]] for r in histories]})
        # Exact requested x stations via linear interpolation of cell-centred data.
        profiles = {}
        for station in (1, 3, 5):
            x = hub[0]+station*config['rotor_diameter_m']; q = x/h-.5
            left = math.floor(q); mix = q-left
            if not 0 <= left < nx-1:
                raise ValueError('Requested wake station lies outside domain')
            profiles[f'{station}D'] = (1-((1-mix)*fields[-1, :, left]+mix*fields[-1, :, left+1])/U).tolist()
        summary = dict(status='completed_numerical_pilot_not_paper_validation', steps=step,
                       time_s=t, wall_seconds=time.perf_counter()-start,
                       final_disc_speed_m_s=histories[-1][0], final_thrust_N=histories[-1][1],
                       max_force_balance_error_N=max_balance, max_divergence_rms_s_inv=max_divergence,
                       cells_across_diameter=config['rotor_diameter_m']/h,
                       cells_across_thickness=config['rotor_thickness_m']/h,
                       analytical_ideal_disc_speed_m_s=U*(1-rotor.a),
                       analytical_ideal_thrust_N=.5*rho*rotor.area*config['ct']*U**2,
                       steady_state_verified=False, experimental_accuracy_validated=False)
        write(out/'summary.json', summary)
        write(out/'profiles.json', {'cross_stream_over_D': (((np.arange(ny)+.5)*h-hub[1])/config['rotor_diameter_m']).tolist(),
                                    'velocity_deficit': profiles, 'time_s': t})
        np.savetxt(out/'history.csv', np.column_stack((times, histories)), delimiter=',',
                   header='time_s,disc_speed_m_s,thrust_N,divergence_rms_s_inv', comments='')
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 3, figsize=(15, 4), layout='constrained')
        im = axes[0].imshow(fields[-1], origin='lower', extent=[0, nx*h, 0, ny*h], vmin=0, vmax=U*1.2)
        axes[0].set(title=f'10 m/s rotor pilot, t={t:g} s', xlabel='x (m)', ylabel='y (m)')
        fig.colorbar(im, ax=axes[0], label='Axial velocity (m/s)')
        for name, values in profiles.items():
            axes[1].plot(((np.arange(ny)+.5)*h-hub[1])/config['rotor_diameter_m'], values, label=name)
        axes[1].set(xlabel='(y - hub y) / D', ylabel='1 - u / inlet', xlim=(-2, 2), title='Numerical wake; no experimental reference')
        axes[1].legend()
        axes[2].plot(times, [r[1] for r in histories], label='Computed')
        axes[2].axhline(summary['analytical_ideal_thrust_N'], color='gray', linestyle='--', label='Ideal unbounded actuator theory')
        axes[2].set(xlabel='Time (s)', ylabel='Thrust (N)', title='Slip walls; no turbulence closure')
        axes[2].legend()
        fig.savefig(out/'overview.png', dpi=150); plt.close(fig)
        manifest['time']['samples'] = times
        manifest['layers'] = [dict(id='axial_velocity', kind='scalar_field', format='npy', asset='data/axial_velocity.npy', sampling='linear',
             field={'name': 'axial_velocity', 'unit': 'm/s'},
             encoding=dict(coordinate_frame='ENU', dtype='<f4', shape=list(fields.shape), axes='TYX',
                           origin_m=[0, 0, hub[2]], spacing_m=[h, h], sample_location='cell_center', byte_order='little', compression='none'),
             display={'widget': 'scalar_field', 'capabilities': ['pick', 'legend', 'opacity'], 'range': [0, U*1.2]}),
             dict(id='thrust', kind='time_series', format='json', asset='data/thrust.json', sampling='linear',
                  field={'name': 'thrust', 'unit': 'N'}, display={'widget': 'time_series', 'capabilities': ['pick']})]
        write(out/'status.json', {'state': 'complete', 'time_s': t, 'steps': step})
        assets = [('source_snapshot', 'source_snapshot.tar.gz', 'application/gzip'),
                  ('configuration', 'config.json', 'application/json'), ('summary', 'summary.json', 'application/json'),
                  ('profiles', 'profiles.json', 'application/json'), ('history', 'history.csv', 'text/csv'),
                  ('overview', 'overview.png', 'image/png'), ('status', 'status.json', 'application/json')]
        manifest['artifacts'] = [dict(id=key, asset=name, sha256=digest(out/name), media_type=mime) for key, name, mime in assets]
        manifest['status'] = 'complete'
        write(out/'manifest.json', manifest)
        validate(out/'manifest.json')
        print(json.dumps(summary, indent=2), flush=True)
        return out
    except Exception as exc:
        manifest['status'] = 'failed'
        write(out/'manifest.json', manifest)
        write(out/'status.json', {'state': 'failed', 'error': str(exc)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Storage.load().metadata('actuator_lab')/'configs/paper_rotor_10ms.json')
    parser.add_argument('--cell', type=float)
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--backend', choices=['triton', 'torch'], default='triton')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if args.cell is not None: config['cell_m'] = args.cell
    if args.seconds is not None: config['end_s'] = args.seconds
    with torch.inference_mode():
        run(config, args.backend)


if __name__ == '__main__':
    main()
