"""Add the solar-coupled 3-D temperature results to the 2-D web package (output/core008/physics/web2d) as `temperature3d_solar/`.
Usage: python export_web2d_temperature3d_solar.py [--out output/core008/physics/web2d]
All arrays 4 m [704, 768], row 0 = south, col 0 = west, float16."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = repo_root()
args = sys.argv[1:]
SRC = ROOT / 'output/core008/physics/scaled_latent/temperature3d_solar'
OUT = ROOT / (args[args.index('--out') + 1] if '--out' in args else 'output/core008/physics/web2d')
sub = 'temperature3d_solar'; (OUT / sub).mkdir(parents=True, exist_ok=True)
manifest = json.loads((OUT / 'manifest.json').read_text())


def put(name, arr, **meta):
    arr = np.asarray(arr); np.save(OUT / sub / f'{name}.npy', arr)
    manifest['arrays'][f'{sub}/{name}.npy'] = {'shape': list(arr.shape), 'dtype': str(arr.dtype), 'cell_m': 4, **meta}
    print(f'{sub}/{name}.npy', arr.shape, arr.dtype, f'{arr.nbytes / 1e6:.1f} MB')


cmp = SRC / 'compare'; stats = json.loads((cmp / 'comparison.json').read_text())
t = stats['scenario_time_utc']
for name, src, meta in [('ground_surface_native_c_yx', 'ground_surface_native_c_yx.npy', 'model own shadow loop, uniform GHI/longwave'),
                        ('ground_surface_solar_c_yx', 'ground_surface_solar_c_yx.npy', 'ShadowNet sunlit fraction + SVF diffuse/longwave'),
                        ('air_0_4m_final_native_c_yx', 'air_layer0_final_native_c_yx.npy', 'air 0-4 m after 30 min, native'),
                        ('air_0_4m_final_solar_c_yx', 'air_layer0_final_solar_c_yx.npy', 'air 0-4 m after 30 min, solar-coupled'),
                        ('shade_native_yx', 'shade_native_yx.npy', 'model shade 0-1'), ('radiation_deficit_solar_yx', 'shade_solar_yx.npy', '1 - GHI_cell/GHI_open')]:
    put(name, np.load(cmp / src).astype(np.float16), unit='C' if '_c_' in name else '-', scenario_time_utc=t, meaning=meta)
put('air_0_4m_frames_solar_c_tyx', np.load(cmp / 'air_layer0_frames_solar_c_tyx.npy'), unit='C', time_s=[90 * k for k in range(21)], scenario_time_utc=t, meaning='air 0-4 m every 90 s, solar-coupled run')
shutil.copy(cmp / 'comparison.json', OUT / 'metadata' / 'temperature3d_solar_comparison.json'); shutil.copy(SRC / 'run_summary.json', OUT / 'metadata' / 'temperature3d_solar_run_summary.json')
diurnal = {}
for d in sorted(SRC.glob('diurnal_*')):
    tag = d.name.replace('diurnal_', '').replace('-', '')
    series = json.loads((d / 'series.json').read_text()); hours = [r['hour_local'] for r in series]
    put(f'diurnal_{tag}_ground_surface_c_tyx', np.load(d / 'hourly_ground_surface_c_tyx.npy'), unit='C', hour_local=hours, meaning='ground surface temperature at the end of each hour')
    put(f'diurnal_{tag}_air_0_4m_c_tyx', np.load(d / 'hourly_air_0_4m_c_tyx.npy'), unit='C', hour_local=hours, meaning='air 0-4 m at the end of each hour')
    put(f'diurnal_{tag}_air_12_16m_c_tyx', np.load(d / 'hourly_air_12_16m_c_tyx.npy'), unit='C', hour_local=hours, meaning='air 12-16 m at the end of each hour')
    shutil.copy(d / 'series.json', OUT / 'metadata' / f'temperature3d_solar_diurnal_{tag}_series.json'); shutil.copy(d / 'run_config.json', OUT / 'metadata' / f'temperature3d_solar_diurnal_{tag}_config.json')
    diurnal[d.name] = {'hours_local': hours, 'ambient_c': [r['ambient_c_end'] for r in series], 'air0_mean_c': [r['air0_mean_c'] for r in series], 'surface_mean_ground_c': [r['surface_mean_ground_c'] for r in series]}
    for p in (d / 'figures').glob('*'):
        shutil.copy(p, OUT / 'figures' / f'temperature3d_solar_{d.name}_{p.name}')
for p in (SRC / 'figures').glob('*'):
    shutil.copy(p, OUT / 'figures' / f'temperature3d_solar_{p.name}')
manifest['temperature3d_solar'] = {'run': str(SRC.relative_to(ROOT)), 'model': 'Yi Qi south_kensington_temperature_3d.py (unchanged) on SCALED wind; shadow + longwave replaced by the NN4PDEs solar model',
                                   'single_time_comparison': {k: stats[k] for k in ('scenario_time_utc', 'ground_surface_c', 'air_layer0_final_c')}, 'diurnal': diurnal,
                                   'orientation': manifest['orientation'], 'grid': {'cell_m': 4, 'shape_yx': [704, 768], 'domain_origin_xy_m': [480, 640]}}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1))
readme = OUT / 'README_source_run.md'; text = readme.read_text()
marker = '\n\n---\n\n# 光照-温度耦合（temperature3d_solar/）— 来源 output/core008/physics/scaled_latent/temperature3d_solar/README.md\n\n'
if marker.strip() not in text and (SRC / 'README.md').exists():
    readme.write_text(text.rstrip() + marker + (SRC / 'README.md').read_text())
print('manifest arrays:', len(manifest['arrays']))
