"""Figures for the solar run (PIL only). Usage: python plot_core008_solar.py [--out output/core008/physics/scaled_latent/solar]"""
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
OUT = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else ROOT / 'output/core008/physics/scaled_latent/solar'
FIG = OUT / 'figures'; FIG.mkdir(exist_ok=True)
TERRAIN = ROOT / 'output/core008/physics/scaled_latent/flood/terrain'
BG = '#101b29'
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
FONT_S = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
foot1 = np.load(TERRAIN / 'footprint_1m_yx.npy'); ny, nx = foot1.shape
foot4 = np.load(TERRAIN / 'footprint_4m_yx.npy')
cfg = json.loads((OUT / 'run_config.json').read_text())
CORE = (slice(int((-581 + 2124 - 640) - 120), int((188 + 2124 - 640) + 120)), slice(int((389 + 2116 - 480) - 120), int((967 + 2116 - 480) + 120)))   # 1 m core zoom


def ramp(t, stops):
    t = np.clip(t, 0, 1); pos = np.linspace(0, 1, len(stops)); cm = np.array(stops, float)
    return np.stack([np.interp(t, pos, cm[:, k]) for k in range(3)], -1)


SUN = [(20, 30, 70), (70, 60, 120), (200, 110, 60), (250, 200, 90), (255, 250, 220)]
VIR = [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]


def panel(rgb, width):
    h_px = int(round(width * rgb.shape[0] / rgb.shape[1]))
    return Image.fromarray(rgb[::-1].astype(np.uint8)).resize((width, h_px), Image.Resampling.BOX if rgb.shape[1] > width else Image.Resampling.NEAREST), h_px


def colorbar(d, x, y, stops, lo, hi, label, n=6):
    for i in range(240):
        c = tuple(int(v) for v in ramp(np.array([i / 239]), stops)[0]); d.line([x + i, y, x + i, y + 12], fill=c)
    for k in range(n):
        d.text((x + k * 240 / (n - 1) - 8, y + 14), f'{lo + (hi - lo) * k / (n - 1):g}', fill='#becbd9', font=FONT_S)
    d.text((x + 250, y), label, fill='#becbd9', font=FONT_S)


def with_buildings(rgb, foot, shade=(60, 60, 65)):
    rgb = rgb.copy(); rgb[foot] = shade; return rgb


def main():
    dates = cfg['dates']
    # 1. SVF (1 m core + 4 m whole)
    svf1 = np.load(OUT / 'svf/svf_1m_yx.npy'); svf4 = np.load(OUT / 'svf/svf_4m_yx.npy')
    W = 620
    im1, hp1 = panel(with_buildings(ramp(svf4, VIR), foot4), W); im2, hp2 = panel(with_buildings(ramp(svf1[CORE], VIR), foot1[CORE]), W)
    hp = max(hp1, hp2); canvas = Image.new('RGB', (2 * W + 60, hp + 110), BG); d = ImageDraw.Draw(canvas)
    d.text((20, 10), 'Sky-view factor (isotropic sky, 16 azimuths x 18 altitudes, HorizonNet) | left: whole domain 4 m | right: Imperial core 1 m | buildings grey (roofs included in the field, shown grey)', fill='white', font=FONT)
    canvas.paste(im1, (20, 36)); canvas.paste(im2, (W + 40, 36)); colorbar(d, 20, hp + 50, VIR, 0, 1, 'SVF'); canvas.save(FIG / 'svf.png')

    for date in dates:
        ddir = OUT / date; frames = json.loads((ddir / 'frames.json').read_text()); summ = json.loads((ddir / 'summary.json').read_text())
        sun_h = np.load(ddir / 'sunlit_hours_1m_yx.npy'); kwh = np.load(ddir / 'daily_irradiation_kwh_m2_1m_yx.npy')
        # 2. sunlit hours + daily irradiation, core 1 m
        hmax = summ['daylight_hours']
        im1, hp1 = panel(with_buildings(ramp(sun_h[CORE] / hmax, SUN), foot1[CORE], (40, 40, 45)), W)
        im2, hp2 = panel(ramp(kwh[CORE] / max(1e-6, np.percentile(kwh, 99.5)), VIR), W)   # roofs keep their values
        hp = max(hp1, hp2); canvas = Image.new('RGB', (2 * W + 60, hp + 110), BG); d = ImageDraw.Draw(canvas)
        d.text((20, 10), f'{date} | left: ground sunlit hours (of {hmax:.1f} h daylight), buildings grey | right: daily global irradiation incl. roofs (kWh/m2) | 1 m, Imperial core, north up', fill='white', font=FONT)
        canvas.paste(im1, (20, 36)); canvas.paste(im2, (W + 40, 36))
        colorbar(d, 20, hp + 50, SUN, 0, round(hmax, 1), 'sunlit hours'); colorbar(d, W + 40, hp + 50, VIR, 0, round(float(np.percentile(kwh, 99.5)), 2), 'kWh/m2/day')
        d.text((20, hp + 86), f"ground mean sunlit {summ['ground_sunlit_hours_mean']:.2f} h, {summ['ground_fraction_lt_1h_sun'] * 100:.1f} % of ground gets < 1 h sun; ground {summ['ground_daily_kwh_m2_mean']:.2f}, roofs {summ['roof_daily_kwh_m2_mean']:.2f}, open sky {summ['open_sky_daily_kwh_m2']:.2f} kWh/m2/day (clear sky)", fill='#becbd9', font=FONT_S)
        canvas.save(FIG / f'{date}_sunlit_hours_irradiation_core.png')
        # whole domain sunlit hours at 4 m
        sh4 = sun_h.reshape(ny // 4, 4, nx // 4, 4).mean(axis=(1, 3))
        im, hp = panel(with_buildings(ramp(sh4 / hmax, SUN), foot4, (40, 40, 45)), 1100)
        canvas = Image.new('RGB', (1140, hp + 100), BG); d = ImageDraw.Draw(canvas)
        d.text((20, 10), f'{date} | ground sunlit hours over the whole core008 domain (4 m block mean of the 1 m result), buildings grey, north up', fill='white', font=FONT)
        canvas.paste(im, (20, 36)); colorbar(d, 20, hp + 50, SUN, 0, round(hmax, 1), 'sunlit hours'); canvas.save(FIG / f'{date}_sunlit_hours_whole.png')
        # 3. shadow snapshots (core, 1 m) at 4 local times
        picks = []
        for target in ('08:00', '10:00', '12:00', '14:00', '16:00', '18:00'):
            c = [f for f in frames if f['local_time'] == target]
            if c: picks.append(c[0])
        picks = picks[:6]
        w3 = 400; ims = []
        for f in picks:
            packed = np.load(ddir / 'shadow_1m_packed' / f'shadow_{f["index"]:03d}.npy'); sh = np.unpackbits(packed, axis=1)[:, :nx].astype(bool)
            rgb = np.where(sh[CORE][..., None], np.array([70, 80, 110]), np.array([255, 240, 190])).astype(np.uint8); rgb = with_buildings(rgb, foot1[CORE], (45, 45, 50))
            ims.append((panel(rgb, w3), f))
        if ims:
            hp = ims[0][0][1]; cols = min(3, len(ims)); rows = (len(ims) + cols - 1) // cols
            canvas = Image.new('RGB', (cols * (w3 + 20) + 20, rows * (hp + 40) + 60), BG); d = ImageDraw.Draw(canvas)
            d.text((20, 10), f'{date} | direct-beam shadows (ShadowNet, 1 m), Imperial core, local time; dark blue = shaded ground, grey = buildings', fill='white', font=FONT)
            for i, ((im, _), f) in enumerate(ims):
                x = 20 + (i % cols) * (w3 + 20); y = 40 + (i // cols) * (hp + 40)
                d.text((x, y), f"{f['local_time']}  alt {f['altitude_deg']:.0f}°  az {f['azimuth_deg']:.0f}°  ground shaded {f['ground_shaded_fraction'] * 100:.0f} %", fill='white', font=FONT_S)
                canvas.paste(im, (x, y + 16))
            canvas.save(FIG / f'{date}_shadows_core.png')
        # 4. time series
        Wt, Ht = 900, 330; canvas = Image.new('RGB', (Wt, Ht), BG); d = ImageDraw.Draw(canvas)
        t = np.array([f['hour_utc'] + summ['utc_offset_h'] for f in frames])
        def axes(x, y, w, h, ys, label, colors, names, ymax):
            d.rectangle([x, y, x + w, y + h], outline='#3a4a5e'); d.text((x, y - 16), label, fill='white', font=FONT_S)
            for k in range(5):
                yy = y + h - k * h / 4; d.line([x, yy, x + w, yy], fill='#1e2a3a'); d.text((x - 40, yy - 6), f'{ymax * k / 4:.3g}', fill='#becbd9', font=FONT_S)
            for hh in range(int(t.min()), int(t.max()) + 2, 2):
                xx = x + (hh - t.min()) / (t.max() - t.min()) * w; d.text((xx - 8, y + h + 4), f'{hh:02d}h', fill='#becbd9', font=FONT_S)
            for v, c, nm in zip(ys, colors, names):
                d.line([(x + (tt - t.min()) / (t.max() - t.min()) * w, y + h - min(1, val / ymax) * h) for tt, val in zip(t, v)], fill=c, width=2)
            for i, (c, nm) in enumerate(zip(colors, names)):
                d.rectangle([x + 8, y + 6 + i * 14, x + 18, y + 14 + i * 14], fill=c); d.text((x + 22, y + 3 + i * 14), nm, fill='#becbd9', font=FONT_S)
        d.text((20, 8), f'{date} | clear-sky irradiance and shading through the day (local time)', fill='white', font=FONT)
        axes(60, 50, 360, 220, [np.array([f['dni_w_m2'] * np.sin(np.radians(f['altitude_deg'])) + f['dhi_w_m2'] for f in frames]), np.array([f['ground_mean_ghi_w_m2'] for f in frames]), np.array([f['roof_mean_ghi_w_m2'] for f in frames])],
             'W/m2', ['#ffd92f', '#6baed6', '#fd8d3c'], ['open-sky GHI', 'ground mean GHI', 'roof mean GHI'], 1000)
        axes(520, 50, 360, 220, [np.array([f['ground_shaded_fraction'] * 100 for f in frames]), np.array([f['altitude_deg'] for f in frames])],
             '% / degrees', ['#9e9ac8', '#ffd92f'], ['ground shaded %', 'sun altitude (deg)'], 100)
        canvas.save(FIG / f'{date}_time_series.png')
        # 5. gif of 4 m irradiance
        ghi4 = np.load(ddir / 'ghi_4m_tyx_float16.npy').astype(np.float32); gif = []
        for k, f in enumerate(frames):
            if k % 3: continue
            rgb = with_buildings(ramp(ghi4[k] / 1000, SUN), foot4 & (ghi4[k] < 0), (40, 40, 45))   # roofs keep value
            im, hp = panel(rgb, 720); fr = Image.new('RGB', (760, hp + 50), BG); dd = ImageDraw.Draw(fr)
            dd.text((20, 8), f"{date} {f['local_time']} | alt {f['altitude_deg']:.0f}° az {f['azimuth_deg']:.0f}° | GHI 0-1000 W/m2 (4 m mean) | ground shaded {f['ground_shaded_fraction'] * 100:.0f} %", fill='white', font=FONT)
            fr.paste(im, (20, 30)); gif.append(fr)
        gif[0].save(FIG / f'{date}_ghi_day.gif', save_all=True, append_images=gif[1:], duration=200, loop=0)
    print('figures ->', FIG)


if __name__ == '__main__':
    main()
