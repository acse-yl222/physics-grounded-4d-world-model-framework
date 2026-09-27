"""Figures for a pollution folder (PIL only). Usage: python plot_core008_pollution_1024.py [--dir output/core008/physics/scaled_latent]"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = repo_root()
RUN = ROOT / (sys.argv[sys.argv.index('--dir') + 1] if '--dir' in sys.argv else 'output/core008/physics/scaled_latent_1024')
OUT = RUN / 'pollution'
FIG = OUT / 'figures'
FIG.mkdir(exist_ok=True)
BG = '#101b29'
MAGMA = np.array([[0, 0, 4], [59, 15, 112], [140, 41, 129], [222, 73, 104], [254, 159, 109], [252, 253, 191]], float)
GREY = np.array([108, 113, 121], np.uint8)


def colormap(values, vmax, mask, log=True):
    v = np.log10(np.clip(values, 0, None) + 1e-3) if log else values
    lo, hi = (np.log10(1e-3), np.log10(vmax)) if log else (0, vmax)
    t = np.clip((v - lo) / (hi - lo), 0, 1) * (len(MAGMA) - 1)
    i = np.minimum(t.astype(int), len(MAGMA) - 2); f = (t - i)[..., None]
    rgb = (MAGMA[i] * (1 - f) + MAGMA[i + 1] * f).astype(np.uint8)
    rgb[mask] = GREY
    return rgb


def main():
    solid = np.load(RUN / 'wind/solid_4m_full_zyx.npy') if (RUN / 'wind/solid_4m_full_zyx.npy').exists() else np.load(RUN / 'temperature/solid_4m_zyx.npy')
    mass = json.loads((OUT / 'mass.json').read_text())
    manifest = json.loads((OUT / 'manifest.json').read_text())
    last = mass[-1]['wind_step']
    c = np.load(OUT / f'concentration_{last:03d}_float16.npy').astype(np.float32)
    vmax = float(np.percentile(c[c > 0], 99.5)) if (c > 0).any() else 1.0
    width = 620
    layers = (1, 3, 6, 12) if c.shape[0] > 12 else (1, 3, 6, 10)
    h_px = int(round(width * c.shape[1] / c.shape[2]))
    canvas = Image.new('RGB', (2 * width + 60, 2 * (h_px + 40) + 80), BG); d = ImageDraw.Draw(canvas)
    d.text((20, 12), f'Pollutant concentration | {RUN.name} | upwind transport on SCALED wind | wind step {last} = solver t {mass[-1]["solver_time"]:g} | 4 m grid, north up', fill='white')
    d.text((20, 30), f'log colour 1e-3 .. {vmax:.2g} (99.5th percentile); source: x {manifest["source_domain_m"]["x"]} m, y {manifest["source_domain_m"]["y"]} m, z {manifest["source_domain_m"]["z"]} m, rate {manifest.get("source_rate", manifest.get("source_rate_per_cell_per_s"))}', fill='#becbd9')
    for n, k in enumerate(layers):
        x = 20 + (n % 2) * (width + 20); y = 60 + (n // 2) * (h_px + 40)
        d.text((x, y), f'z = {k * 4}-{k * 4 + 4} m', fill='white')
        canvas.paste(Image.fromarray(colormap(c[k], vmax, solid[k])[::-1]).resize((width, h_px), Image.Resampling.NEAREST), (x, y + 16))
    d.text((20, canvas.height - 22), 'Numerical transport (Yuhang physical_transport.py), not the pollution surrogate; SCALED wind has no CFD reference.', fill='#becbd9')
    canvas.save(FIG / f'concentration_step{last:03d}.png')

    slices = np.load(OUT / 'slices_z12m_tyx_float16.npy').astype(np.float32) if (OUT / 'slices_z12m_tyx_float16.npy').exists() else None
    if slices is None:
        slices = np.stack([np.load(OUT / f'concentration_{m["wind_step"]:03d}_float16.npy', mmap_mode='r')[3].astype(np.float32) for m in mass])
    frames = []
    for m, s in zip(mass, slices):
        img = Image.new('RGB', (width + 40, h_px + 70), BG); dd = ImageDraw.Draw(img)
        dd.text((20, 10), f"pollutant | z 12-16 m | wind step {m['wind_step']} | t {m['solver_time']:g} | mass {m['mass']:.0f}", fill='white')
        img.paste(Image.fromarray(colormap(s, vmax, solid[3])[::-1]).resize((width, h_px), Image.Resampling.NEAREST), (20, 30))
        dd.text((20, h_px + 40), f'log colour 1e-3 .. {vmax:.2g}; grey = building', fill='#becbd9')
        frames.append(img)
    frames[0].save(FIG / 'concentration_z12m.gif', save_all=True, append_images=frames[1:], duration=200, loop=0)

    W, H = 900, 320
    chart = Image.new('RGB', (W, H), BG); dd = ImageDraw.Draw(chart)
    dd.text((20, 10), 'Total pollutant mass in the domain vs wind step (source on from step 1)', fill='white')
    ox, oy, pw, ph = 70, 40, W - 100, H - 90
    dd.rectangle((ox, oy, ox + pw, oy + ph), outline='#4a5a6e')
    ms = [m['mass'] for m in mass]; top = max(ms) * 1.1
    pts = [(ox + i / max(1, len(ms) - 1) * pw, oy + ph - v / top * ph) for i, v in enumerate(ms)]
    dd.line(pts, fill='#e7d96c', width=2)
    dd.text((ox, oy + ph + 8), 'step 1', fill='white'); dd.text((ox + pw - 60, oy + ph + 8), f'step {last}', fill='white')
    dd.text((ox - 60, oy - 6), f'{top:.0f}', fill='white'); dd.text((ox - 30, oy + ph - 8), '0', fill='white')
    dd.text((ox + 10, oy + 8), f'last mass {ms[-1]:.0f}; mean Jacobi iterations {np.mean([m["mean_iterations"] for m in mass]):.1f}', fill='#e7d96c')
    chart.save(FIG / 'mass.png')
    print('figures written to', FIG)


if __name__ == '__main__':
    main()
