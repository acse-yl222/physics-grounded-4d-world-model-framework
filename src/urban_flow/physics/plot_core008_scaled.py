"""Figures for a SCALED result folder (PIL only).
Usage: python plot_core008_scaled.py [--dir output/core008/physics/scaled_latent] [step]"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = repo_root()
_args = sys.argv[1:]
RESULT_DIR = 'output/core008/physics/scaled'
if '--dir' in _args:
    RESULT_DIR = _args[_args.index('--dir') + 1]; del _args[_args.index('--dir'):_args.index('--dir') + 2]
OUT = ROOT / RESULT_DIR
_cfg = json.loads((OUT / 'run_config.json').read_text())
FIG = OUT / 'figures'
FIG.mkdir(exist_ok=True)

VIRIDIS = np.array([[16, 35, 74], [29, 105, 158], [68, 189, 168], [231, 217, 108], [229, 98, 58]], float)
INFERNO = np.array([[0, 0, 4], [87, 16, 110], [188, 55, 84], [249, 142, 9], [252, 255, 164]], float)
DIVERGING = np.array([[33, 102, 172], [146, 197, 222], [247, 247, 247], [244, 165, 130], [178, 24, 43]], float)
SOLID_GREY = np.array([108, 113, 121], np.uint8)
BG = '#101b29'


def colormap(values, vmin, vmax, palette, mask=None):
    val = np.clip((values - vmin) / (vmax - vmin), 0, 1) * (len(palette) - 1)
    idx = np.minimum(val.astype(int), len(palette) - 2)
    t = (val - idx)[..., None]
    rgb = (palette[idx] * (1 - t) + palette[idx + 1] * t).astype(np.uint8)
    if mask is not None:
        rgb[mask] = SOLID_GREY
    return rgb


def colorbar(canvas, draw, x, y, w, h, vmin, vmax, palette, label):
    bar = colormap(np.linspace(vmax, vmin, h)[:, None].repeat(w, 1), vmin, vmax, palette)
    canvas.paste(Image.fromarray(bar), (x, y))
    for tx, ty, t in ((x + w + 6, y - 6, f'{vmax:.2f}'), (x + w + 6, y + h - 8, f'{vmin:.2f}'), (x, y + h + 8, label)):
        draw.text((tx, ty), t, fill='white')


def panel(canvas, draw, rgb, x, y, width, title):
    """Paste north-up with preserved aspect ratio; returns pasted height."""
    h, w = rgb.shape[:2]
    height = int(round(width * h / w))
    draw.text((x, y), title, fill='white')
    canvas.paste(Image.fromarray(rgb[::-1]).resize((width, height), Image.Resampling.NEAREST), (x, y + 16))
    return height + 16


def line_chart(path, title, series, xlabels, note):
    W, H = 960, 340
    chart = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(chart)
    d.text((20, 10), title, fill='white')
    ox, oy, pw, ph = 70, 40, W - 100, H - 100
    d.rectangle((ox, oy, ox + pw, oy + ph), outline='#4a5a6e')
    for i, (label, colour, xs, ys) in enumerate(series):
        top = max(ys) * 1.15 if max(ys) > 0 else 1
        pts = [(ox + (x - xs[0]) / max(1e-9, xs[-1] - xs[0]) * pw, oy + ph - v / top * ph) for x, v in zip(xs, ys)]
        d.line(pts, fill=colour, width=2)
        for p in pts:
            d.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), fill=colour)
        d.text((ox + 10, oy + 8 + 16 * i), f'{label}: first {ys[0]:.4f}, last {ys[-1]:.4f} (axis max {top:.3f})', fill=colour)
    d.text((ox, oy + ph + 8), xlabels[0], fill='white'); d.text((ox + pw - 80, oy + ph + 8), xlabels[1], fill='white')
    d.text((20, H - 24), note, fill='#becbd9')
    chart.save(path)


def _solid_4m_fallback():
    if (OUT / 'wind/solid_4m_full_zyx.npy').exists():
        return np.load(OUT / 'wind/solid_4m_full_zyx.npy')[:16]
    s1 = np.load(OUT / 'wind/solid_1m_zyx.npy', mmap_mode='r')
    return np.asarray(s1).reshape(16, 4, s1.shape[1] // 4, 4, s1.shape[2] // 4, 4).max(axis=(1, 3, 5))


def wind_figure(step):
    metrics = json.loads((OUT / 'wind/metrics.json').read_text())
    steps = metrics['steps']
    step = step or steps[-1]['step']
    v = np.load(OUT / f'wind/wind4m_{step:03d}.npy')          # [3,16,H,W] at 4 m, physical units, +x/+y/+z
    solid = np.load(OUT / 'temperature/solid_4m_zyx.npy') if (OUT / 'temperature/solid_4m_zyx.npy').exists() else None
    if solid is None:
        solid = _solid_4m_fallback()
    width = 900
    h_px = int(round(width * v.shape[2] / v.shape[3]))
    canvas = Image.new('RGB', (2 * width + 140, 2 * (h_px + 46) + 90), BG)
    d = ImageDraw.Draw(canvas)
    d.text((20, 12), f"SCALED wind | {OUT.name} | core008 building extent {list(v.shape[1:])} (z,y,x) at 4 m | step {step} = {step * 25:g} s from rest | north up", fill='white')
    d.text((20, 30), 'Left: speed (m/s, shared scale 0-3). Right: horizontal arrows (sub-sampled). Grey = solid (conservative 4 m).', fill='#becbd9')
    vmax = 3.0
    for row, altitude in enumerate((10, 40)):
        k = altitude // 4
        speed = np.linalg.norm(v[:, k], axis=0)
        rgb = colormap(speed, 0, vmax, VIRIDIS, solid[k])
        y0 = 60 + row * (h_px + 46)
        panel(canvas, d, rgb, 20, y0, width, f'layer {k * 4}-{k * 4 + 4} m  speed')
        x1 = 40 + width
        panel(canvas, d, rgb, x1, y0, width, f'layer {k * 4}-{k * 4 + 4} m  direction')
        ny, nx = speed.shape; stride = max(1, nx // 36)
        for iy in range(stride // 2, ny, stride):
            for ix in range(stride // 2, nx, stride):
                if solid[k, iy, ix]:
                    continue
                u, w = float(v[0, k, iy, ix]), float(v[1, k, iy, ix])
                a = x1 + (ix + .5) / nx * width; b = y0 + 16 + (1 - (iy + .5) / ny) * h_px
                dx, dy = u * 8, -w * 8
                d.line((a, b, a + dx, b + dy), fill='#e0ecf4', width=1)
                length = np.hypot(dx, dy)
                if length > 1:
                    ux, uy = dx / length, dy / length
                    d.line((a + dx - 3 * ux + 2 * uy, b + dy - 3 * uy - 2 * ux, a + dx,
                            b + dy, a + dx - 3 * ux - 2 * uy, b + dy - 3 * uy + 2 * ux), fill='#e0ecf4')
    colorbar(canvas, d, 2 * width + 70, 80, 18, 300, 0, vmax, VIRIDIS, 'm/s')
    dd = _cfg['wind'].get('domain_decomposition')
    dd_text = dd if isinstance(dd, str) else f"latent-space DD: {dd['latent_inference']}" if isinstance(dd, dict) else ''
    d.text((20, canvas.height - 22), f'SCALED inference on new geometry; {dd_text}; no CFD reference.', fill='#becbd9')
    canvas.save(FIG / f'wind_step{step:03d}.png')

    xs = [s['step'] for s in steps]
    line_chart(FIG / 'wind_convergence.png', 'SCALED step-to-step RMS change (4 m fluid cells, m/s) and mean fluid speed (m/s)',
               [('RMS change', '#e7d96c', xs, [s['change_from_previous_rms_4m'] for s in steps]),
                ('mean speed', '#44bda8', xs, [s['fluid_speed_mean'] for s in steps]),
                ('mean u (+x)', '#e5623a', xs, [abs(s['mean_u_fluid']) for s in steps])],
               (f'step {xs[0]}', f'step {xs[-1]}'), 'Each series scaled to its own axis maximum; mean u shown as absolute value.')


def temperature_figure(height_m=10.0):
    solid = np.load(OUT / 'temperature/solid_4m_zyx.npy')
    rows = json.loads((OUT / 'temperature/metrics.json').read_text())
    steps = max(r['time_seconds'] for r in rows) // 90
    z = int(height_m // 4)
    refs = [np.load(OUT / f'temperature/reference_{k + 2:03d}.npy')[z] for k in range(steps + 1)]
    preds = [refs[0]] + [np.load(OUT / f'temperature/recursive_{k:03d}.npy')[z] for k in range(1, steps + 1)]
    m = solid[z]
    vmin = min(float(a[~m].min()) for a in refs + preds); vmax = max(float(a[~m].max()) for a in refs + preds)
    limit = max(1e-6, max(float(np.abs((p - r)[~m]).max()) for p, r in zip(preds, refs)))
    width = 330
    h_px = int(round(width * m.shape[0] / m.shape[1]))
    cols = steps + 1
    canvas = Image.new('RGB', (cols * (width + 12) + 140, 3 * (h_px + 36) + 100), BG)
    d = ImageDraw.Draw(canvas)
    d.text((20, 12), f'Temperature | 4 m grid | height cell {z}: [{z * 4},{z * 4 + 4}) m | SCALED wind, whole building extent', fill='white')
    d.text((20, 30), f'Rows: controlled solver / coupled recursive U-Net / prediction - solver. Colour {vmin:.2f}-{vmax:.2f} C; difference +-{limit:.2f} C.', fill='#becbd9')
    for k, (ref, pred) in enumerate(zip(refs, preds)):
        x = 20 + k * (width + 12)
        for row, (a, pal, lo, hi) in enumerate(((ref, INFERNO, vmin, vmax), (pred, INFERNO, vmin, vmax),
                                                (pred - ref, DIVERGING, -limit, limit))):
            y = 60 + row * (h_px + 36)
            panel(canvas, d, colormap(a, lo, hi, pal, m), x, y, width, ['solver', 'recursive', 'pred - solver'][row] + f'  +{90 * k} s')
    bx = cols * (width + 12) + 50
    colorbar(canvas, d, bx, 80, 18, 220, vmin, vmax, INFERNO, 'C')
    colorbar(canvas, d, bx, 60 + 2 * (h_px + 36) + 20, 18, 220, -limit, limit, DIVERGING, 'dC')
    d.text((20, canvas.height - 22), 'Controlled solver is the adapted reference, not CFD; thermal scenario values are chosen settings.', fill='#becbd9')
    canvas.save(FIG / 'temperature_comparison_10m.png')
    series = []
    for mode, colour in (('recursive', '#e7d96c'), ('one_step', '#44bda8'), ('persistence', '#e5623a')):
        rs = [r for r in rows if r['mode'] == mode]
        series.append((mode, colour, [r['time_seconds'] for r in rs], [r['mae_c'] for r in rs]))
    line_chart(FIG / 'temperature_mae.png', 'Fluid-only temperature MAE vs controlled solver (C)', series,
               ('+90 s', f'+{steps * 90} s'), 'Each series scaled to its own axis maximum.')


CORE_DOMAIN_XY = ((2505, 3083), (1543, 2312))   # detailed 008 core in padded-domain metres
DOMAIN_LOWER = tuple(_cfg['domain_lower_xyz_m'][:2])
CELL_M = int(_cfg.get('cell_m', 1))


def _slice_panel_pair(canvas, d, speed, u, v, mask, x, y, width, title, stride_px, vmax):
    rgb = colormap(speed, 0, vmax, VIRIDIS, mask)
    panel(canvas, d, rgb, x, y, width, title + '  speed')
    ny, nx = speed.shape
    h_px = int(round(width * ny / nx))
    x1 = x + width + 20
    panel(canvas, d, rgb, x1, y, width, title + '  direction')
    stride = max(1, nx // stride_px)
    for iy in range(stride // 2, ny, stride):
        for ix in range(stride // 2, nx, stride):
            if mask[iy, ix]:
                continue
            a = x1 + (ix + .5) / nx * width; b = y + 16 + (1 - (iy + .5) / ny) * h_px
            dx, dy = float(u[iy, ix]) * 8, -float(v[iy, ix]) * 8
            d.line((a, b, a + dx, b + dy), fill='#e0ecf4', width=1)
            length = np.hypot(dx, dy)
            if length > 1:
                ux, uy = dx / length, dy / length
                d.line((a + dx - 3 * ux + 2 * uy, b + dy - 3 * uy - 2 * ux, a + dx, b + dy,
                        a + dx - 3 * ux - 2 * uy, b + dy - 3 * uy + 2 * ux), fill='#e0ecf4')
    return h_px + 16


def wind_fullres_figures(vmax=3.0):
    """Final 1 m field: whole-extent slices and a zoom on the detailed 008 campus core."""
    raw = np.load(OUT / f'wind/velocity_final_{CELL_M}m_raw_czyx_float16.npy', mmap_mode='r')   # raw: u along decreasing x
    solid = np.load(OUT / ('wind/solid_1m_zyx.npy' if CELL_M == 1 else f'wind/solid_{CELL_M}m_full_zyx.npy'), mmap_mode='r')
    (x0, x1), (y0, y1) = CORE_DOMAIN_XY
    zx = slice((x0 - DOMAIN_LOWER[0]) // CELL_M, (x1 - DOMAIN_LOWER[0]) // CELL_M)
    zy = slice((y0 - DOMAIN_LOWER[1]) // CELL_M, (y1 - DOMAIN_LOWER[1]) // CELL_M)
    for name, sy, sx, width, stride_px in (('whole', slice(None), slice(None), 900, 40), ('core', zy, zx, 900, 40)):
        layers = (10, 40) if name == 'whole' else ((2, 10, 30) if CELL_M == 1 else (4, 12, 32))
        first = np.asarray(raw[0, 0][sy, sx]); ny, nx = first.shape
        h_px = int(round(width * ny / nx))
        canvas = Image.new('RGB', (2 * width + 160, len(layers) * (h_px + 46) + 90), BG)
        d = ImageDraw.Draw(canvas)
        label = 'whole building extent' if name == 'whole' else f'008 campus core x {x0}..{x1}, y {y0}..{y1} (domain m)'
        d.text((20, 12), f'SCALED wind | {OUT.name} | {CELL_M} m grid | final step | {label} | north up', fill='white')
        d.text((20, 30), f'Speed m/s (0-{vmax:g}); arrows = horizontal flow; grey = building. Raw u sign flipped to +x east.', fill='#becbd9')
        for row, altitude in enumerate(layers):
            k = altitude // CELL_M
            u = -np.asarray(raw[0, k][sy, sx], np.float32); v = np.asarray(raw[1, k][sy, sx], np.float32)
            w = np.asarray(raw[2, k][sy, sx], np.float32)
            speed = np.sqrt(u * u + v * v + w * w)
            _slice_panel_pair(canvas, d, speed, u, v, np.asarray(solid[k][sy, sx]), 20, 60 + row * (h_px + 46), width,
                              f'z = {altitude}-{altitude + CELL_M} m', stride_px, vmax)
        colorbar(canvas, d, 2 * width + 80, 80, 18, 300, 0, vmax, VIRIDIS, 'm/s')
        d.text((20, canvas.height - 22), 'Domain-decomposed SCALED inference on new geometry; no CFD reference.', fill='#becbd9')
        canvas.save(FIG / f'wind_final_1m_{name}.png')


def spinup_gif(altitude_m=10, vmax=3.0, width=700):
    metrics = json.loads((OUT / 'wind/metrics.json').read_text())
    solid = np.load(OUT / 'temperature/solid_4m_zyx.npy') if (OUT / 'temperature/solid_4m_zyx.npy').exists() else None
    if solid is None:
        solid = _solid_4m_fallback()
    k = altitude_m // 4
    frames = []
    for s in metrics['steps']:
        v = np.load(OUT / f"wind/wind4m_{s['step']:03d}.npy", mmap_mode='r')[:, k]
        speed = np.linalg.norm(np.asarray(v, np.float32), axis=0)
        rgb = colormap(speed, 0, vmax, VIRIDIS, solid[k])
        ny, nx = speed.shape; h_px = int(round(width * ny / nx))
        img = Image.new('RGB', (width + 40, h_px + 70), BG); d = ImageDraw.Draw(img)
        d.text((20, 10), f"SCALED spin-up | {OUT.name} | z {k * 4}-{k * 4 + 4} m | step {s['step']} = {s['time_seconds']:g} s | mean {s['fluid_speed_mean']:.2f} m/s", fill='white')
        img.paste(Image.fromarray(rgb[::-1]).resize((width, h_px), Image.Resampling.NEAREST), (20, 30))
        d.text((20, h_px + 40), f'layer {k * 4}-{k * 4 + 4} m; speed 0-{vmax:g} m/s; grey = building', fill='#becbd9')
        frames.append(img)
    frames[0].save(FIG / f'wind_spinup_{altitude_m}m.gif', save_all=True, append_images=frames[1:], duration=250, loop=0)


if __name__ == '__main__':
    step = int(_args[0]) if _args else None
    wind_figure(step)
    if (OUT / f'wind/velocity_final_{CELL_M}m_raw_czyx_float16.npy').exists():
        wind_fullres_figures()
        spinup_gif()
    if (OUT / 'temperature/metrics.json').exists():
        temperature_figure()
    print('figures written to', FIG)
