"""Controlled wind-to-temperature transfer experiment, not original-case reproduction."""
from __future__ import annotations

import gc
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import sys

import h5py
import numpy as np
import torch
from tqdm.auto import tqdm

ROOT = Path(__file__).resolve().parent
GEOMETRY_HASH = 'fe6d1a16c75276a7b780b232e9091c3e0f9386ed3638238f81b75cae15b22765'


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_suffix('.partial')
    tmp.write_text(json.dumps(value, indent=2))
    os.replace(tmp, path)


def save_array(path, array):
    path = Path(path)
    with path.with_suffix('.partial').open('wb') as f:
        np.save(f, array, allow_pickle=False)
    os.replace(path.with_suffix('.partial'), path)


def save_torch(path, value):
    path = Path(path)
    torch.save(value, path.with_suffix('.partial'))
    os.replace(path.with_suffix('.partial'), path)


def geometry(path):
    a = np.load(path, allow_pickle=False).squeeze()
    if a.shape != (64, 1024, 1024):
        raise ValueError(f'Geometry must be [64,1024,1024], got {a.shape}. Use saved inputs/sigma.npy.')
    if not np.isfinite(a).all():
        raise ValueError('Non-finite geometry')
    solid = a > .5
    if hashlib.sha256(solid.astype(np.float32).tobytes()).hexdigest() != GEOMETRY_HASH:
        raise ValueError('Geometry does not match Zhongkai regression1024.')
    return solid


def initial_wind(path):
    if Path(path).suffix == '.npy':
        a = np.load(path, allow_pickle=False)
    else:
        with h5py.File(path) as f:
            if 'uvw' not in f:
                raise KeyError('Use physical/W_005000.h5 with physical-unit uvw, not a preview or wind latent.')
            a = f['uvw'][:]
    a = np.asarray(a, dtype=np.float32).squeeze()
    if a.shape != (3, 64, 1024, 1024) or not np.isfinite(a).all():
        raise ValueError('Initial wind must be finite physical uvw [3,64,1024,1024].')
    return a


def block_reduce(a, factor, mode='mean'):
    z, y, x = a.shape[-3:]
    if any(n % factor for n in (z, y, x)):
        raise ValueError('Grid dimensions must be divisible by the coarsening factor.')
    b = a.reshape(*a.shape[:-3], z//factor, factor, y//factor, factor, x//factor, factor)
    axes = (-1, -3, -5)
    return b.max(axis=axes) if mode == 'max' else b.mean(axis=axes)


def coarse_geometry(solid, factor=4, spacing=4.):
    # Conservative voxel occupancy: any solid fine cell blocks the coarse cell.
    coarse = block_reduce(solid, factor, 'max').astype(bool)
    above = np.zeros_like(coarse)
    above[:-1] = coarse[1:]
    roof = coarse & ~above
    height = np.max(np.where(coarse, (np.arange(coarse.shape[0])+1)[:,None,None]*spacing, 0), axis=0)
    return {'solid': coarse, 'roof': roof, 'height': height.astype(np.float32)}


def coarse_wind(uvw, solid, factor):
    # NN4PDEs xadv differentiates along DECREASING x index (w2=-p_div_x/2).
    # Its yadv/zadv differentiate along INCREASING indices. Convert only at
    # the scalar-temperature interface; retain raw convention in the wind model.
    out = block_reduce(uvw, factor).astype(np.float32)
    out[0] *= -1
    out[:, solid] = 0
    if not np.isfinite(out).all():
        raise ValueError('Non-finite mapped wind')
    return out


def validate_config(cfg):
    for key in ('ambient_c','ground_c','roof_c','surface_exchange_per_s','diffusivity_m2_s','cfl_safety'):
        if not np.isfinite(cfg[key]):
            raise ValueError(f'Non-finite scenario setting: {key}')
    if cfg['factor'] != 4 or cfg['fine_spacing_m'] != 1.:
        raise ValueError('This first experiment is fixed to 1 m wind -> 4 m temperature.')
    if cfg['wind_step_seconds'] != 25. or cfg['temperature_step_seconds'] != 90.:
        raise ValueError('This version uses the explicit 50 * 0.5 = 25 s mapping and 90 s temperature steps.')
    if not 1 <= cfg['temperature_steps'] <= 5:
        raise ValueError('First experiment supports 1..5 temperature steps (at most 450 s).')
    if cfg['surface_exchange_per_s'] < 0 or cfg['diffusivity_m2_s'] <= 0:
        raise ValueError('Invalid physical coefficients')
    if not 0 < cfg['cfl_safety'] < 1:
        raise ValueError('CFL safety must lie between zero and one.')
    if not 1 <= cfg['forcing_layers'] <= 16:
        raise ValueError('Invalid thermal forcing depth')


def prepare_run(paths, cfg, output):
    validate_config(cfg)
    for key, path in paths.items():
        if not Path(path).is_file():
            raise FileNotFoundError(f'Missing {key}: {path}')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    record = {
        'experiment': 'new controlled scenario; frozen Yi Qi one-step transfer',
        'config': cfg, 'assets': {k: digest(v) for k,v in paths.items()},
        'runtime': digest(ROOT/'SOURCE_INFO.json'),
        'environment': {'python': platform.python_version(), 'torch': str(torch.__version__),
                        'numpy': np.__version__, 'cuda': torch.version.cuda,
                        'gpu': torch.cuda.get_device_name() if torch.cuda.is_available() else 'CPU'},
        'time_note': 'Experimental SI interpretation of wind dt=0.5; not verified against Yi Qi original-case clocks.',
        'warmup': '180 seconds using fixed initial wind; generated history, not historical CFD temperatures',
        'reference': 'adapted explicit upwind/diffusion heat solver using SAME forecast wind; not ground truth',
        'wind_components': 'temperature (u,v,w)=(-raw_u,raw_v,raw_w) in increasing array-index coordinates; NN4PDEs stencil sign verified',
    }
    meta = output/'manifest.json'
    if meta.exists() and json.loads(meta.read_text()) != record:
        raise ValueError('Configuration, data, code or environment changed. Choose a NEW RUN_DIR.')
    atomic_json(meta, record)
    for folder in ('wind', 'temperature', 'figures'):
        (output/folder).mkdir(exist_ok=True)
    return record


def load_wind_models(paths, device):
    sys.path.insert(0, str(ROOT/'vendor/scaled'))
    from scaled.model.autoencoders.autoencoder3dv1 import AutoencoderKL
    from scaled.model.unets.unet_3ds import UNet3DsModel
    encoder = AutoencoderKL(in_channels=3, out_channels=3,
        down_block_types=['DownEncoderBlock3D']*3, up_block_types=['UpDecoderBlock3D']*3,
        block_out_channels=[128,256,384], latent_channels=4)
    payload = torch.load(paths['wind_vae'], map_location='cpu', weights_only=True)
    state = payload.get('state_dict', payload)
    encoder.load_state_dict({k.removeprefix('module.'):v for k,v in state.items() if torch.is_tensor(v)}, strict=True)
    del payload, state
    wind = UNet3DsModel(in_channels=8, out_channels=4,
        down_block_types=('DownBlock3D',)*4, up_block_types=('UpBlock3D',)*4,
        block_out_channels=(128,256,384,512), add_attention=False)
    # Original author checkpoint can contain Python metadata. Only use your trusted checkpoint.
    payload = torch.load(paths['wind'], map_location='cpu', weights_only=False)
    if payload.get('geometry_hash') not in (None, GEOMETRY_HASH):
        raise ValueError('Wind checkpoint geometry differs')
    for k,v in {'domain_size':1024, 'patch_size':256, 'halo':32, 'delta_t':50, 'bc_mode':'geometry'}.items():
        if k in payload.get('config', {}) and payload['config'][k] != v:
            raise ValueError(f'Wrong wind checkpoint config: {k}')
    wind.load_state_dict(payload['model_state'], strict=True)
    return wind.eval().requires_grad_(False).to(device), encoder.eval().requires_grad_(False).to(device)


def generate_wind(paths, cfg, output, solid, geo, device='cuda'):
    from wind_core import wind_step
    if not str(device).startswith('cuda') or not torch.cuda.is_available():
        raise RuntimeError('Full regression1024 inference requires a CUDA GPU; no synthetic fallback.')
    output = Path(output)
    folder = output/'wind'
    intervals = math.ceil(cfg['temperature_steps']*90/25)
    if (folder/'complete.json').exists():
        for k in range(intervals+1):
            a = np.load(folder/f'wind_{k:03d}.npy', mmap_mode='r')
            if a.shape != (3,*geo['solid'].shape) or not np.isfinite(a).all():
                raise ValueError('Invalid cached wind')
        print('Reusing complete predicted wind cache.')
        return
    state_file = folder/'resume.pt'
    if state_file.exists():
        state = torch.load(state_file, map_location='cpu', weights_only=True)
        x, start = state['x'].numpy(), state['index']
    else:
        x, start = initial_wind(paths['initial_wind'])/3., 0
        state = None
    wind, encoder = load_wind_models(paths, device)
    # Model construction consumes RNG; restore only after loading the models.
    if state is not None:
        torch.set_rng_state(state['cpu_rng'])
        torch.cuda.set_rng_state(state['cuda_rng'])
        del state
    else:
        torch.manual_seed(cfg['seed'])
    save_array(folder/f'wind_{start:03d}.npy', coarse_wind(x*3, geo['solid'], cfg['factor']))
    try:
        for k in range(start+1, intervals+1):
            x = wind_step(x, solid, wind, encoder, device)
            if not np.isfinite(x).all():
                raise RuntimeError('Non-finite wind forecast; stopping before temperature inference.')
            save_array(folder/f'wind_{k:03d}.npy', coarse_wind(x*3, geo['solid'], cfg['factor']))
            save_torch(state_file, {'x':torch.from_numpy(x), 'index':k,
                'cpu_rng':torch.get_rng_state(), 'cuda_rng':torch.cuda.get_rng_state()})
            print(f'Saved predicted wind: index={5000+50*k}, elapsed={25*k} s', flush=True)
        atomic_json(folder/'complete.json', {'intervals':intervals, 'step_seconds':25})
    finally:
        del wind, encoder
        gc.collect()
        torch.cuda.empty_cache()


def wind_at(folder, seconds, step=25.):
    # Only the declared initialization warmup uses fixed initial wind.
    seconds = max(float(seconds), 0.)
    lo = int(math.floor(seconds/step))
    fraction = seconds/step-lo
    a = np.load(Path(folder)/f'wind_{lo:03d}.npy', allow_pickle=False)
    if fraction < 1e-10:
        return a
    b = np.load(Path(folder)/f'wind_{lo+1:03d}.npy', allow_pickle=False)
    return ((1-fraction)*a + fraction*b).astype(np.float32)


def shift_edge(t, axis, shift):
    out = torch.roll(t, shift, axis)
    dst, src = [slice(None)]*3, [slice(None)]*3
    dst[axis], src[axis] = (0,0) if shift == 1 else (-1,-1)
    out[tuple(dst)] = t[tuple(src)]
    return out


def impose(t, wind, solid, roof, cfg):
    # Unlike original Yi Qi fixed-left inflow, handle the actual local wind sign.
    for axis, component in ((2,0), (1,1)):
        for edge, neighbour, sign in ((0,1,1),(-1,-2,-1)):
            dst, src = [slice(None)]*3, [slice(None)]*3
            dst[axis], src[axis] = edge, neighbour
            dst, src = tuple(dst), tuple(src)
            incoming = wind[component][dst]*sign > 0
            t[dst] = torch.where(incoming, cfg['ambient_c'], t[src])
    t[-1] = cfg['ambient_c']
    t[solid] = cfg['ambient_c']
    t[roof] = cfg['roof_c']


@torch.inference_mode()
def physical_step(temperature, uvw, geo, cfg, device='cpu'):
    """Adapted Yi Qi-style heat equation; joint advection/diffusion/reaction CFL."""
    t = torch.as_tensor(temperature.copy(), dtype=torch.float32, device=device)
    wind = torch.as_tensor(uvw, dtype=torch.float32, device=device)
    solid = torch.as_tensor(geo['solid'], device=device)
    roof = torch.as_tensor(geo['roof'], device=device)
    fluid = ~solid
    wind = wind.masked_fill(solid[None], 0)
    dx = cfg['fine_spacing_m']*cfg['factor']
    diffusivity = cfg['diffusivity_m2_s']
    exchange = cfg['surface_exchange_per_s']
    rate = float(wind.abs().sum(0).max().item())/dx + 6*diffusivity/dx**2 + exchange
    n = max(1, math.ceil(90*rate/cfg['cfl_safety']))
    dt = 90/n
    heating = torch.zeros_like(fluid)
    heating[:cfg['forcing_layers']] = fluid[:cfg['forcing_layers']] & fluid[0]
    impose(t, wind, solid, roof, cfg)
    for _ in range(n):
        tendency = torch.zeros_like(t)
        for axis, component in ((2,0), (1,1), (0,2)):
            left, right = shift_edge(t, axis, 1), shift_edge(t, axis, -1)
            vel = wind[component]
            tendency -= torch.where(vel >= 0, vel*(t-left)/dx, vel*(right-t)/dx)
            tendency += diffusivity*(left-2*t+right)/dx**2
        tendency += heating * exchange * (cfg['ground_c']-t)
        t[fluid] += dt*tendency[fluid]
        impose(t, wind, solid, roof, cfg)
    if not torch.isfinite(t).all():
        raise RuntimeError('Non-finite physical temperature')
    return t.cpu().numpy(), {'substeps':n, 'dt_seconds':dt}


def physical_reference(cfg, output, geo, device='cpu'):
    output = Path(output)
    folder = output/'temperature'
    times = [-180,-90,0] + [90*k for k in range(1, cfg['temperature_steps']+1)]
    files = [folder/f'reference_{k:03d}.npy' for k in range(len(times))]
    # Reuse only a contiguous prefix. A completed frame is the checkpoint.
    t = np.full(geo['solid'].shape, cfg['ambient_c'], np.float32)
    t[geo['roof']] = cfg['roof_c']
    if not files[0].exists():
        save_array(files[0], t)
    previous = np.load(files[0])
    logs = []
    for k in tqdm(range(len(times)-1), desc='Controlled physical temperature'):
        uvw = wind_at(output/'wind', times[k])
        if files[k+1].exists():
            previous = np.load(files[k+1])
            logs.append({'time_seconds':times[k+1], 'reused':True})
            continue
        previous, stats = physical_step(previous, uvw, geo, cfg, device)
        save_array(files[k+1], previous)
        logs.append({'time_seconds':times[k+1], **stats})
    atomic_json(folder/'physical_solver.json', {'times_seconds':times, 'frames':logs,
        'wind_hold':'start-of-90s-frame wind held constant during its physical substeps',
        'initialization':'warmup from -180 s to 0 s with fixed initial wind'})
    return times


def load_temperature(path, device='cpu'):
    from temperature_model import UNet3D
    p = torch.load(path, map_location='cpu', weights_only=True)
    config, stats = p['config'], p['stats']
    if config['in_channels'] != 15 or config['history_steps'] != 3:
        raise ValueError('This notebook requires the 15-channel one-step temperature checkpoint.')
    for key in ('temp_std','velocity_scale','surface_temp_std','surface_exchange_scale','height_scale'):
        if not np.isfinite(stats[key]) or stats[key] <= 0:
            raise ValueError(f'Invalid checkpoint statistics: {key}')
    m = UNet3D(in_channels=15, base_channels=config['base_channels'], depth=config['depth'])
    m.load_state_dict(p['model_state_dict'], strict=True)
    return m.eval().requires_grad_(False).to(device), stats, tuple(config['patch_size'])


def make_input(history, uvw, geo, cfg, stats):
    shape = geo['solid'].shape
    if history.shape != (3,*shape) or uvw.shape != (3,*shape):
        raise ValueError('History/wind/geometry shape mismatch')
    full = lambda v: np.broadcast_to(np.asarray(v, np.float32), shape)
    channels = list((history-stats['temp_mean'])/stats['temp_std'])
    channels += list(uvw/stats['velocity_scale'])
    channels += [np.linalg.norm(uvw, axis=0)/stats['velocity_scale']]
    channels += [geo['solid'], ~geo['solid'], geo['roof'],
        full(geo['height']/stats['height_scale']), full(1),
        full(cfg['surface_exchange_per_s']/stats['surface_exchange_scale']),
        full((cfg['ground_c']-stats['surface_temp_mean'])/stats['surface_temp_std']),
        full((cfg['ambient_c']-stats['temp_mean'])/stats['temp_std'])]
    a = np.stack(channels).astype(np.float32)
    if a.shape != (15,*shape) or not np.isfinite(a).all():
        raise ValueError('Invalid 15-channel model input')
    return a


def tile_starts(n, p, overlap):
    if not 0 <= overlap < p or n < p:
        raise ValueError('Invalid temperature patch/overlap')
    starts = list(range(0, n-p+1, p-overlap))
    return sorted(set(starts+[n-p]))


@torch.inference_mode()
def predict(model, inputs, stats, patch, overlap, device):
    shape = inputs.shape[1:]
    out, count = np.zeros(shape, np.float32), np.zeros(shape, np.uint16)
    grid = list(itertools.product(*(tile_starts(n,p,o) for n,p,o in zip(shape,patch,overlap))))
    for origin in tqdm(grid, desc='Temperature patches', leave=False):
        sl = tuple(slice(a,a+p) for a,p in zip(origin,patch))
        x = torch.from_numpy(np.ascontiguousarray(inputs[(slice(None),*sl)]))[None].to(device)
        y = model(x)[0,0].float().cpu().numpy()
        out[sl] += y*stats['temp_std'] + stats['temp_mean']
        count[sl] += 1
    if np.any(count == 0):
        raise RuntimeError('Uncovered temperature cells')
    out /= count
    if not np.isfinite(out).all():
        raise RuntimeError('Temperature surrogate produced non-finite values. No clipping/fallback applied.')
    return out


def metrics(pred, reference, mask):
    error = (pred[mask]-reference[mask]).astype(np.float64)
    return {'mae_c':float(np.mean(abs(error))), 'rmse_c':float(np.sqrt(np.mean(error**2))),
            'bias_c':float(error.mean()), 'mean_c':float(pred[mask].mean()),
            'min_c':float(pred[mask].min()), 'max_c':float(pred[mask].max())}


def run_temperature(paths, cfg, output, geo, device='cpu'):
    output = Path(output)
    folder = output/'temperature'
    model, stats, patch = load_temperature(paths['temperature'], device)
    mask = ~geo['solid']
    history = np.stack([np.load(folder/f'reference_{i:03d}.npy') for i in range(3)])
    persistence = history[-1].copy()
    rows = []
    for k in range(cfg['temperature_steps']):
        uvw = wind_at(output/'wind', k*90)
        target = np.load(folder/f'reference_{k+3:03d}.npy')
        outputs = {}
        for mode in ('recursive','one_step'):
            file = folder/f'{mode}_{k+1:03d}.npy'
            # One-step diagnostic uses physical history; recursive forecast never does.
            h = history if mode == 'recursive' else np.stack([
                np.load(folder/f'reference_{i:03d}.npy') for i in range(k,k+3)])
            if file.exists():
                pred = np.load(file)
            else:
                pred = predict(model, make_input(h,uvw,geo,cfg,stats), stats, patch,
                               tuple(cfg['temperature_overlap']), device)
                save_array(file, pred)
            outputs[mode] = pred
            rows.append({'time_seconds':(k+1)*90, 'mode':mode, **metrics(pred,target,mask)})
        rows.append({'time_seconds':(k+1)*90, 'mode':'persistence', **metrics(persistence,target,mask)})
        # No temperature truth beyond the common initial history enters this branch.
        history = np.concatenate([history[1:], outputs['recursive'][None]], axis=0)
        atomic_json(folder/'metrics.json', rows)
        print(f'Temperature +{(k+1)*90}s: {rows[-3]}', flush=True)
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return rows


def plot_results(cfg, output, geo, height_m=10.):
    import matplotlib.pyplot as plt
    output = Path(output)
    spacing = cfg['factor']*cfg['fine_spacing_m']
    z = int(height_m//spacing)
    if not 0 <= z < geo['solid'].shape[0]:
        raise ValueError('Requested plot height is outside the new temperature domain')
    count = cfg['temperature_steps']+1
    folder = output/'temperature'
    refs = [np.load(folder/f'reference_{k+2:03d}.npy')[z] for k in range(count)]
    preds = [refs[0]] + [np.load(folder/f'recursive_{k:03d}.npy')[z] for k in range(1,count)]
    masked = lambda a: np.ma.masked_where(geo['solid'][z], a)
    vmin = min(float(masked(a).min()) for a in refs+preds)
    vmax = max(float(masked(a).max()) for a in refs+preds)
    limit = max(1e-6, max(float(abs(masked(p-r)).max()) for p,r in zip(preds,refs)))
    fig, axes = plt.subplots(3,count, figsize=(4*count,10), squeeze=False, layout='constrained')
    cm = plt.get_cmap('inferno').copy(); cm.set_bad('lightgray')
    diff = plt.get_cmap('RdBu_r').copy(); diff.set_bad('lightgray')
    for k,(ref,pred) in enumerate(zip(refs,preds)):
        for row,a in enumerate((ref,pred,pred-ref)):
            kw = dict(cmap=cm,vmin=vmin,vmax=vmax) if row<2 else dict(cmap=diff,vmin=-limit,vmax=limit)
            im = axes[row,k].imshow(masked(a), origin='lower', **kw)
            axes[row,k].set_title(f'{["Controlled solver", "Coupled recursive", "Prediction − solver"][row]}\n+{90*k} s')
            axes[row,k].set_xticks([]); axes[row,k].set_yticks([])
            if k == count-1:
                fig.colorbar(im, ax=axes[row,:], label='°C' if row<2 else 'Δ°C', shrink=.75)
    fig.suptitle(f'New scenario transfer | height cell {z}: [{z*spacing:g},{(z+1)*spacing:g}) m | same predicted wind')
    fig.savefig(output/'figures/temperature_comparison.png', dpi=140)
    plt.show()
    rows = json.loads((folder/'metrics.json').read_text())
    fig, ax = plt.subplots(figsize=(7,4), layout='constrained')
    for mode in ('recursive','one_step','persistence'):
        a = [r for r in rows if r['mode']==mode]
        ax.plot([r['time_seconds'] for r in a], [r['mae_c'] for r in a], marker='o', label=mode)
    ax.set(xlabel='Elapsed forecast time (s)', ylabel='Fluid-only temperature MAE (°C)')
    ax.legend(); ax.grid(alpha=.3)
    fig.savefig(output/'figures/temperature_mae.png', dpi=160)
    plt.show()
