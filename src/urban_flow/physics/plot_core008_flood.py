"""Figures for a flood run folder (PIL only). Usage: python plot_core008_flood.py --run output/core008/physics/scaled_latent/flood/run_4m"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = repo_root()
RUN = Path(sys.argv[sys.argv.index('--run') + 1]) if '--run' in sys.argv else ROOT / 'output/core008/physics/scaled_latent/flood/run_4m'
FIG = RUN / 'figures'; FIG.mkdir(exist_ok=True)
TERRAIN = ROOT / 'output/core008/physics/scaled_latent/flood/terrain'
BG = '#101b29'
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
FONT_S = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
# depth colour: dry ground light, then light blue -> blue -> dark blue -> purple (m)
DEPTH_STOPS = [(0.02, (198, 219, 239)), (0.1, (107, 174, 214)), (0.3, (33, 113, 181)), (0.6, (8, 48, 107)), (1.0, (84, 39, 143)), (1.5, (63, 0, 125))]
GROUND = np.array([232, 228, 218], np.uint8); BUILDING = np.array([90, 90, 95], np.uint8); GREEN = np.array([205, 222, 190], np.uint8)


def load_terrain(shape):
    cell = 2816 // shape[0]
    if cell == 4:
        foot = np.load(TERRAIN / 'footprint_4m_yx.npy'); green = np.load(TERRAIN / 'grass_4m_yx.npy') | np.load(TERRAIN / 'vegetation_4m_yx.npy')
    else:
        foot1 = np.load(TERRAIN / 'footprint_1m_yx.npy'); g1 = np.load(TERRAIN / 'grass_1m_yx.npy') | np.load(TERRAIN / 'vegetation_1m_yx.npy')
        if cell == 1:
            foot, green = foot1, g1
        else:
            ny, nx = shape
            foot = foot1.reshape(ny, cell, nx, cell).mean(axis=(1, 3)) >= 0.5
            green = g1.reshape(ny, cell, nx, cell).mean(axis=(1, 3)) >= 0.5
    return foot, green & ~foot, cell


def depth_rgb(h, foot, green, vmax=None):
    rgb = np.empty(h.shape + (3,), np.uint8); rgb[:] = GROUND; rgb[green] = GREEN
    stops = DEPTH_STOPS if vmax is None else [(v * vmax / 1.5, c) for v, c in DEPTH_STOPS]
    lv = np.array([s[0] for s in stops]); cols = np.array([s[1] for s in stops], float)
    wet = h >= lv[0]
    if wet.any():
        hv = np.clip(h[wet], lv[0], lv[-1])
        c = np.stack([np.interp(hv, lv, cols[:, k]) for k in range(3)], -1)
        rgb[wet] = c.astype(np.uint8)
    rgb[foot] = BUILDING
    return rgb


def legend(d, x, y, stops, title):
    d.text((x, y), title, fill='white', font=FONT_S)
    for i, (v, c) in enumerate(stops):
        d.rectangle([x + i * 58, y + 16, x + i * 58 + 54, y + 30], fill=tuple(c))
        d.text((x + i * 58, y + 32), f'{"≥" if i == len(stops) - 1 else ""}{v:g} m', fill='#becbd9', font=FONT_S)


def panel(arr_rgb, width):
    h_px = int(round(width * arr_rgb.shape[0] / arr_rgb.shape[1]))
    return Image.fromarray(arr_rgb[::-1]).resize((width, h_px), Image.Resampling.NEAREST), h_px


def main():
    cfg = json.loads((RUN / 'run_config.json').read_text()); summ = json.loads((RUN / 'summary.json').read_text())
    series = json.loads((RUN / 'series.json').read_text()); frames = json.loads((RUN / 'frames/manifest.json').read_text())
    hmax = np.load(RUN / 'max_depth_m.npy'); smax = np.load(RUN / 'max_speed_m_s.npy'); haz = np.load(RUN / 'max_hazard_hv_m2_s.npy')
    foot, green, cell = load_terrain(hmax.shape)
    ny, nx = hmax.shape
    x0, y0 = cfg['grid']['domain_lower_xy_m']
    pois = cfg['pois_index_yx']
    title = f"{cfg['scenario']['total_rain_mm']:.0f} mm / 90 min cloudburst | {cell} m grid | sewer {cfg['scenario']['sewer_capacity_mm_h']:g} mm/h"

    # 1. maximum depth, whole domain
    width = 1100
    img, h_px = panel(depth_rgb(hmax, foot, green), width)
    canvas = Image.new('RGB', (width + 40, h_px + 130), BG); d = ImageDraw.Draw(canvas)
    d.text((20, 10), f'Maximum water depth over {cfg["scenario"]["duration_h"]:g} h | core008 South Kensington | {title} | north up', fill='white', font=FONT)
    d.text((20, 28), f'shallow-water solver (NN4PDEs style, semi-implicit) on EA 1 m LIDAR DTM + core008 buildings (grey). Area with max depth > 10 cm: {summ["area_max_depth_gt_10cm_m2"] / 1e4:.1f} ha, > 30 cm: {summ["area_max_depth_gt_30cm_m2"] / 1e4:.2f} ha, peak {summ["max_depth_m"]:.2f} m', fill='#becbd9', font=FONT_S)
    canvas.paste(img, (20, 50))
    sc = width / nx
    for name, (iy, ix) in pois.items():
        px, py = 20 + ix * sc, 50 + (ny - 1 - iy) * sc
        d.ellipse([px - 4, py - 4, px + 4, py + 4], outline='#ff5a36', width=2)
        d.text((px + 6, py - 7), name.split(' (')[0].split(' / ')[0], fill='#ff5a36', font=FONT_S)
    legend(d, 20, h_px + 60, DEPTH_STOPS, 'max depth')
    d.text((width - 420, h_px + 100), 'No observations for this event on this geometry; scenario and drainage rates are assumptions (see README).', fill='#becbd9', font=FONT_S)
    canvas.save(FIG / 'max_depth_whole.png')

    # 2. core008 detailed core zoom (region x 389..967, y -581..188 -> domain +2116/+2124)
    cx0, cx1 = int((389 + 2116 - x0) // cell), int((967 + 2116 - x0) // cell); cy0, cy1 = int((-581 + 2124 - y0) // cell), int((188 + 2124 - y0) // cell)
    pad = int(120 // cell)
    sl = (slice(max(0, cy0 - pad), min(ny, cy1 + pad)), slice(max(0, cx0 - pad), min(nx, cx1 + pad)))
    img, h_px = panel(depth_rgb(hmax[sl], foot[sl], green[sl]), 1000)
    canvas = Image.new('RGB', (1040, h_px + 120), BG); d = ImageDraw.Draw(canvas)
    d.text((20, 10), f'Maximum water depth, Imperial / Albertopolis core ({cell} m grid) | {title}', fill='white', font=FONT)
    canvas.paste(img, (20, 34)); legend(d, 20, h_px + 44, DEPTH_STOPS, 'max depth'); canvas.save(FIG / 'max_depth_core.png')

    # 3. max speed and hazard
    def scalar_rgb(a, vmax, cmap):
        t = np.clip(a / vmax, 0, 1); pos = np.linspace(0, 1, len(cmap)); cm = np.array(cmap, float)
        rgb = np.stack([np.interp(t, pos, cm[:, k]) for k in range(3)], -1).astype(np.uint8)
        rgb[a < 0.02 * vmax] = GROUND; rgb[(a < 0.02 * vmax) & green] = GREEN; rgb[foot] = BUILDING
        return rgb
    HOT = [(255, 245, 200), (254, 196, 79), (236, 112, 20), (153, 52, 4), (60, 10, 0)]
    w2 = 640
    im1, hp = panel(scalar_rgb(smax, 1.5, HOT), w2); im2, _ = panel(scalar_rgb(haz, 0.5, HOT), w2)
    canvas = Image.new('RGB', (2 * w2 + 60, hp + 110), BG); d = ImageDraw.Draw(canvas)
    d.text((20, 10), f'Maximum speed (left, 0-1.5 m/s) and maximum depth x speed hazard (right, 0-0.5 m²/s) | {title}', fill='white', font=FONT)
    canvas.paste(im1, (20, 40)); canvas.paste(im2, (w2 + 40, 40))
    d.text((20, hp + 50), f'max speed {summ["max_speed_m_s"]:.2f} m/s; hazard classes (UK FD2320): h·v < 0.5 low, 0.5-1 moderate, > 1 significant', fill='#becbd9', font=FONT_S)
    canvas.save(FIG / 'max_speed_hazard.png')

    # 4. time series: rain, stored volume, wet area, POI depths
    W, H = 1000, 640
    canvas = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(canvas)
    tmin = np.array([r['t_s'] for r in series]) / 60
    def axes(x, y, w, h, ys, label, ylab, colors, names, ymax=None):
        ymax = ymax or max(1e-9, max(float(np.max(v)) for v in ys) * 1.05)
        d.rectangle([x, y, x + w, y + h], outline='#3a4a5e')
        d.text((x, y - 16), label, fill='white', font=FONT_S)
        for k in range(5):
            yy = y + h - k * h / 4; d.line([x, yy, x + w, yy], fill='#1e2a3a'); d.text((x - 46, yy - 6), f'{ymax * k / 4:.3g}', fill='#becbd9', font=FONT_S)
        for k in range(7):
            xx = x + k * w / 6; d.text((xx - 8, y + h + 4), f'{tmin.max() * k / 6:.0f}', fill='#becbd9', font=FONT_S)
        d.text((x + w - 40, y + h + 16), 'min', fill='#becbd9', font=FONT_S); d.text((x - 46, y - 16), ylab, fill='#becbd9', font=FONT_S)
        for v, c, nm in zip(ys, colors, names):
            pts = [(x + tt / tmin.max() * w, y + h - min(1, val / ymax) * h) for tt, val in zip(tmin, v)]
            d.line(pts, fill=c, width=2)
        for i, (c, nm) in enumerate(zip(colors, names)):
            d.rectangle([x + w - 250, y + 6 + i * 14, x + w - 240, y + 14 + i * 14], fill=c); d.text((x + w - 235, y + 3 + i * 14), nm, fill='#becbd9', font=FONT_S)
    d.text((20, 8), f'Flood time series | {title}', fill='white', font=FONT)
    axes(70, 50, 400, 130, [np.array([r['rain_mm_h'] for r in series])], 'rainfall intensity', 'mm/h', ['#6baed6'], ['rain'])
    axes(560, 50, 400, 130, [np.array([r['stored_m3'] for r in series]) / 1e3, np.array([r['drained'] for r in series]) / 1e3, np.array([r['outflow'] for r in series]) / 1e3],
         'volumes', '10³ m³', ['#6baed6', '#74c476', '#fd8d3c'], ['stored on surface', 'drained (cumulative)', 'left domain (cumulative)'])
    axes(70, 230, 400, 130, [np.array([r['area_gt_10cm_m2'] for r in series]) / 1e4, np.array([r['area_gt_30cm_m2'] for r in series]) / 1e4],
         'flooded area', 'ha', ['#6baed6', '#9e9ac8'], ['depth > 10 cm', 'depth > 30 cm'])
    axes(560, 230, 400, 130, [np.array([r['max_depth_m'] for r in series]), np.array([r['mean_depth_wet_m'] for r in series])],
         'depth', 'm', ['#9e9ac8', '#6baed6'], ['max depth', 'mean depth (wet cells)'])
    poi = json.loads((RUN / 'poi_depth_series.json').read_text())
    cols = ['#6baed6', '#fd8d3c', '#74c476', '#9e9ac8', '#e377c2', '#ffd92f', '#8c564b', '#17becf']
    names = list(poi['depth_m'].keys())
    axes(70, 420, 890, 160, [np.array(poi['depth_m'][k]) for k in names], 'water depth at points of interest', 'm', cols[:len(names)], names)
    d.text((20, H - 22), f'balance error {summ["volumes_m3"]["balance_error"]:.2f} m³ of {summ["volumes_m3"]["rain_on_ground"] + summ["volumes_m3"]["roof_routed"]:.0f} m³ rain; {summ["steps"]} steps, {summ["wall_seconds"]:.0f} s wall', fill='#becbd9', font=FONT_S)
    canvas.save(FIG / 'time_series.png')

    # 5. gif of depth frames (whole domain, down-sampled)
    gif = []
    for f in frames:
        h = np.load(RUN / 'frames' / f'depth_{f["index"]:03d}_float16.npy').astype(np.float32)
        img, hp = panel(depth_rgb(h, foot, green), 720)
        fr = Image.new('RGB', (760, hp + 60), BG); dd = ImageDraw.Draw(fr)
        dd.text((20, 8), f't = {f["t_s"] / 60:5.0f} min | rain {f["rain_mm_h"]:5.1f} mm/h | depth colour 0.02-1.5 m | {cell} m grid', fill='white', font=FONT)
        fr.paste(img, (20, 30)); gif.append(fr)
    if gif:
        gif[0].save(FIG / 'depth_evolution.gif', save_all=True, append_images=gif[1:], duration=250, loop=0)
    print('figures ->', FIG)


if __name__ == '__main__':
    main()
