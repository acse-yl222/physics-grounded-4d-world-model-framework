"""Add the solar results to the 2-D web package (output/core008/physics/web2d) as a `solar/` sub-folder and mirror-ready manifest.

Usage: python export_web2d_solar.py [--src output/core008/physics/scaled_latent/solar] [--out output/core008/physics/web2d]
Convention as the rest of the package: row 0 = south, col 0 = west, float16 / uint8; 1 m arrays are [2816, 3072], 4 m [704, 768].
"""
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
SRC = ROOT / (args[args.index('--src') + 1] if '--src' in args else 'output/core008/physics/scaled_latent/solar')
OUT = ROOT / (args[args.index('--out') + 1] if '--out' in args else 'output/core008/physics/web2d')
(OUT / 'solar').mkdir(parents=True, exist_ok=True)
manifest = json.loads((OUT / 'manifest.json').read_text())
cfg = json.loads((SRC / 'run_config.json').read_text())
ny, nx = cfg['grid']['shape_yx']


def put(name, arr, **meta):
    arr = np.asarray(arr); np.save(OUT / 'solar' / f'{name}.npy', arr)
    manifest['arrays'][f'solar/{name}.npy'] = {'shape': list(arr.shape), 'dtype': str(arr.dtype), **meta}
    print(f'solar/{name}.npy', arr.shape, arr.dtype, f'{arr.nbytes / 1e6:.1f} MB')


put('svf_1m_yx', np.load(SRC / 'svf/svf_1m_yx.npy').astype(np.float16), cell_m=1, unit='-', meaning='sky-view factor (isotropic sky), roofs included')
put('svf_4m_yx', np.load(SRC / 'svf/svf_4m_yx.npy').astype(np.float16), cell_m=4, unit='-', meaning='4x4 block mean of svf_1m_yx')
put('horizon_deg_4m_kyx', np.load(SRC / 'svf/horizon_deg_4m_kyx.npy'), cell_m=4, unit='deg', meaning='horizon angle per azimuth k (0 = N, clockwise 22.5 deg steps), 4 m block mean')
dates = {}
for date in cfg['dates']:
    d = SRC / date; frames = json.loads((d / 'frames.json').read_text()); summ = json.loads((d / 'summary.json').read_text())
    tag = date.replace('-', '')
    put(f'sunlit_hours_1m_{tag}_yx', np.load(d / 'sunlit_hours_1m_yx.npy').astype(np.float16), cell_m=1, unit='h', date=date, meaning='hours of direct sun (10-min frames)')
    put(f'daily_irradiation_kwh_m2_1m_{tag}_yx', np.load(d / 'daily_irradiation_kwh_m2_1m_yx.npy').astype(np.float16), cell_m=1, unit='kWh/m2/day', date=date, meaning='clear-sky global irradiation, roofs included')
    ghi4 = np.load(d / 'ghi_4m_tyx_float16.npy')
    put(f'ghi_4m_{tag}_tyx', ghi4, cell_m=4, unit='W/m2', date=date, time_local=[f['local_time'] for f in frames], hour_utc=[f['hour_utc'] for f in frames],
        altitude_deg=[round(f['altitude_deg'], 2) for f in frames], azimuth_deg=[round(f['azimuth_deg'], 2) for f in frames], meaning='global horizontal irradiance every 10 min, 4 m block mean of the 1 m field')
    hourly = [f for f in frames if f['local_time'].endswith(':00')]
    sh = np.empty((len(hourly), ny, nx), np.uint8)
    for k, f in enumerate(hourly):
        sh[k] = np.unpackbits(np.load(d / 'shadow_1m_packed' / f'shadow_{f["index"]:03d}.npy'), axis=1)[:, :nx]
    put(f'shadow_1m_{tag}_tyx', sh, cell_m=1, unit='1 = shaded', date=date, time_local=[f['local_time'] for f in hourly],
        altitude_deg=[round(f['altitude_deg'], 2) for f in hourly], azimuth_deg=[round(f['azimuth_deg'], 2) for f in hourly], meaning='direct-beam shadow mask on the hour (buildings count as shaded ground = 1 only where roofs are shaded)')
    shutil.copy(d / 'frames.json', OUT / 'metadata' / f'solar_frames_{tag}.json'); shutil.copy(d / 'summary.json', OUT / 'metadata' / f'solar_summary_{tag}.json')
    dates[date] = summ
for p in (SRC / 'figures').iterdir():
    shutil.copy(p, OUT / 'figures' / f'solar_{p.name}')
shutil.copy(SRC / 'run_config.json', OUT / 'metadata' / 'solar_run_config.json'); shutil.copy(SRC / 'verification.json', OUT / 'metadata' / 'solar_verification.json')
shutil.copy(SRC / 'svf/summary.json', OUT / 'metadata' / 'solar_svf_summary.json')
manifest['solar'] = {'run': str(SRC.relative_to(ROOT)), 'model': cfg['model'], 'style': cfg['style'], 'dates': dates, 'centre_lat_lon': cfg['centre_lat_lon'],
                     'grid_1m': {'shape_yx': [ny, nx], 'domain_origin_xy_m': cfg['grid']['domain_lower_xy_m'], 'orientation': manifest['orientation']},
                     'display_hint': 'shadow: 1 = shaded (dark), 0 = sunlit; ghi colour 0-1000 W/m2; sunlit hours colour 0-daylight_hours', 'limits': cfg['limits']}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1))
readme = OUT / 'README_source_run.md'; text = readme.read_text()
marker = '\n\n---\n\n# 光照结果（solar/）— 来源 output/core008/physics/scaled_latent/solar/README.md\n\n'
if marker.strip() not in text and (SRC / 'README.md').exists():
    readme.write_text(text.rstrip() + marker + (SRC / 'README.md').read_text())
print('manifest arrays:', len(manifest['arrays']))
