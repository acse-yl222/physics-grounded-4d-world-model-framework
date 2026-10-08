"""Figures for a diurnal solar-coupled 3-D temperature run (PIL only).
Usage: python plot_core008_temperature3d_diurnal.py [--dir output/core008/physics/scaled_latent/temperature3d_solar/diurnal_2026-06-21]"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = repo_root()
D = (
    Path(sys.argv[sys.argv.index("--dir") + 1])
    if "--dir" in sys.argv
    else ROOT / "output/core008/physics/scaled_latent/temperature3d_solar/diurnal_2026-06-21"
)
FIG = D / "figures"
FIG.mkdir(exist_ok=True)
BG = "#101b29"
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
FONT_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
foot = np.load(ROOT / "output/core008/physics/scaled_latent/flood/terrain/footprint_4m_yx.npy")
X0, Y0, CELL = 480, 640, 4
(x0, x1), (y0, y1) = (625, 3474), (754, 3348)
study = np.zeros_like(foot)
study[
    int((y0 - Y0) // CELL) : int(np.ceil((y1 - Y0) / CELL)),
    int((x0 - X0) // CELL) : int(np.ceil((x1 - X0) / CELL)),
] = True
CORE = (
    slice((-581 + 2124 - Y0) // CELL - 30, (188 + 2124 - Y0) // CELL + 30),
    slice((389 + 2116 - X0) // CELL - 30, (967 + 2116 - X0) // CELL + 30),
)
HEAT = [
    (49, 54, 149),
    (69, 117, 180),
    (171, 217, 233),
    (255, 255, 191),
    (253, 174, 97),
    (215, 48, 39),
    (165, 0, 38),
]


def ramp(t, stops):
    t = np.clip(t, 0, 1)
    pos = np.linspace(0, 1, len(stops))
    cm = np.array(stops, float)
    return np.stack([np.interp(t, pos, cm[:, k]) for k in range(3)], -1)


def img(rgb, w):
    h = int(round(w * rgb.shape[0] / rgb.shape[1]))
    return Image.fromarray(rgb[::-1].astype(np.uint8)).resize((w, h), Image.Resampling.NEAREST), h


def colorbar(d, x, y, stops, lo, hi, label):
    for i in range(200):
        d.line(
            [x + i, y, x + i, y + 10],
            fill=tuple(int(v) for v in ramp(np.array([i / 199]), stops)[0]),
        )
    for k in range(5):
        d.text((x + k * 50 - 8, y + 12), f"{lo + (hi - lo) * k / 4:g}", fill="#becbd9", font=FONT_S)
    d.text((x + 210, y - 1), label, fill="#becbd9", font=FONT_S)


def main():
    cfg = json.loads((D / "run_config.json").read_text())
    series = json.loads((D / "series.json").read_text())
    surf = np.load(D / "hourly_ground_surface_c_tyx.npy").astype(np.float32)
    air0 = np.load(D / "hourly_air_0_4m_c_tyx.npy").astype(np.float32)
    hours = [r["hour_local"] for r in series]
    # 1. time series
    W, H = 1000, 420
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    d.text(
        (20, 8),
        f"{cfg['date']} clear-sky diurnal cycle | Yi Qi 3-D temperature model + NN4PDEs solar (hourly sun, ShadowNet + SVF) + SCALED wind | study-area means",
        fill="white",
        font=FONT,
    )
    x0_, y0_, w, h = 70, 50, 560, 320
    curves = [
        ("ambient air (prescribed)", [r["ambient_c_end"] for r in series], "#becbd9"),
        ("air 0-4 m mean", [r["air0_mean_c"] for r in series], "#6baed6"),
        ("air 0-4 m over urban ground", [r["air0_urban_mean_c"] for r in series], "#fd8d3c"),
        ("air 0-4 m over vegetation", [r["air0_vegetation_mean_c"] for r in series], "#74c476"),
        ("ground surface, urban", [r["surface_mean_urban_c"] for r in series], "#d62728"),
        ("ground surface, vegetation", [r["surface_mean_vegetation_c"] for r in series], "#2ca02c"),
    ]
    allv = np.concatenate([np.array(c[1]) for c in curves])
    lo, hi = np.floor(allv.min()) - 1, np.ceil(allv.max()) + 1
    d.rectangle([x0_, y0_, x0_ + w, y0_ + h], outline="#3a4a5e")
    for k in range(7):
        yy = y0_ + h - k * h / 6
        d.line([x0_, yy, x0_ + w, yy], fill="#1e2a3a")
        d.text((x0_ - 40, yy - 6), f"{lo + (hi - lo) * k / 6:.0f}", fill="#becbd9", font=FONT_S)
    for i, hh in enumerate(hours):
        xx = x0_ + i / (len(hours) - 1) * w
        if hh % 2 == 0:
            d.text((xx - 10, y0_ + h + 4), f"{hh:02d}:00", fill="#becbd9", font=FONT_S)
    for name, v, c in curves:
        pts = [
            (x0_ + i / (len(v) - 1) * w, y0_ + h - (val - lo) / (hi - lo) * h)
            for i, val in enumerate(v)
        ]
        d.line(pts, fill=c, width=2)
    for i, (name, v, c) in enumerate(curves):
        d.rectangle([660, 60 + i * 16, 670, 70 + i * 16], fill=c)
        d.text((676, 57 + i * 16), name, fill="#becbd9", font=FONT_S)
    d.text((x0_ - 40, y0_ - 18), "°C", fill="#becbd9", font=FONT_S)
    # GHI on the right
    gx, gy, gw, gh = 660, 200, 320, 150
    ghi = [r["ghi_open_w_m2"] for r in series]
    gmax = max(1.0, max(ghi))
    d.rectangle([gx, gy, gx + gw, gy + gh], outline="#3a4a5e")
    d.text(
        (gx, gy - 16), "open-sky GHI (W/m²) and ground sunlit fraction", fill="#becbd9", font=FONT_S
    )
    d.line(
        [(gx + i / (len(ghi) - 1) * gw, gy + gh - v / gmax * gh) for i, v in enumerate(ghi)],
        fill="#ffd92f",
        width=2,
    )
    d.line(
        [
            (gx + i / (len(ghi) - 1) * gw, gy + gh - r["sunlit_fraction_ground"] * gh)
            for i, r in enumerate(series)
        ],
        fill="#9e9ac8",
        width=2,
    )
    d.text(
        (gx, gy + gh + 4),
        f"GHI max {gmax:.0f} W/m² (yellow); sunlit fraction 0-1 (purple)",
        fill="#becbd9",
        font=FONT_S,
    )
    exc = [r["air_excess_over_ambient_c"] for r in series]
    d.text(
        (20, H - 22),
        f"air 0-4 m excess over ambient: min {min(exc):+.2f} C at {hours[int(np.argmin(exc))]:02d}:00, max {max(exc):+.2f} C at {hours[int(np.argmax(exc))]:02d}:00; run {cfg['seconds'] / 60:.1f} min",
        fill="#becbd9",
        font=FONT_S,
    )
    canvas.save(FIG / "diurnal_time_series.png")

    # 2. maps at selected hours: ground surface and air 0-4 m, core
    picks = [h for h in (6, 9, 12, 15, 18, 21) if h in hours]
    Wp = 300
    rows = []
    lo_s, hi_s = (
        float(np.floor(np.percentile(surf[:, study], 1))),
        float(np.ceil(np.percentile(surf[:, study], 99))),
    )
    lo_a, hi_a = (
        float(np.floor(np.percentile(air0[:, study & ~foot], 1))),
        float(np.ceil(np.percentile(air0[:, study & ~foot], 99))),
    )
    _, hp = img(np.zeros(surf[0][CORE].shape + (3,)), Wp)
    canvas = Image.new("RGB", (len(picks) * (Wp + 14) + 20, 2 * (hp + 30) + 100), BG)
    d = ImageDraw.Draw(canvas)
    d.text(
        (20, 8),
        f"{cfg['date']} | top: ground surface temperature (C, {lo_s:g}-{hi_s:g}) | bottom: air 0-4 m (C, {lo_a:g}-{hi_a:g}) | Imperial core, 4 m, north up, local time",
        fill="white",
        font=FONT,
    )
    for j, hh in enumerate(picks):
        k = hours.index(hh)
        x = 20 + j * (Wp + 14)
        rgb = ramp((surf[k][CORE] - lo_s) / (hi_s - lo_s), HEAT)
        rgb[~study[CORE]] = (40, 40, 45)
        im, _ = img(rgb, Wp)
        d.text(
            (x, 34),
            f"{hh:02d}:00  surface  (ambient {series[k]['ambient_c_end']:.1f} C)",
            fill="white",
            font=FONT_S,
        )
        canvas.paste(im, (x, 50))
        rgb = ramp((air0[k][CORE] - lo_a) / (hi_a - lo_a), HEAT)
        rgb[(foot | ~study)[CORE]] = (40, 40, 45)
        im, _ = img(rgb, Wp)
        d.text(
            (x, 50 + hp + 14),
            f"{hh:02d}:00  air 0-4 m  (mean {series[k]['air0_mean_c']:.1f} C)",
            fill="white",
            font=FONT_S,
        )
        canvas.paste(im, (x, 50 + hp + 30))
    colorbar(d, 20, canvas.height - 40, HEAT, lo_s, hi_s, "surface C")
    colorbar(d, 400, canvas.height - 40, HEAT, lo_a, hi_a, "air C")
    canvas.save(FIG / "diurnal_maps_core.png")

    # 3. gif of air 0-4 m whole study area
    frames = []
    for k, hh in enumerate(hours):
        rgb = ramp((air0[k] - lo_a) / (hi_a - lo_a), HEAT)
        rgb[foot | ~study] = (40, 40, 45)
        im, hp2 = img(rgb, 700)
        fr = Image.new("RGB", (740, hp2 + 50), BG)
        dd = ImageDraw.Draw(fr)
        dd.text(
            (20, 8),
            f"{cfg['date']} {hh:02d}:00 | air 0-4 m (C, {lo_a:g}-{hi_a:g}) | ambient {series[k]['ambient_c_end']:.1f} | GHI {series[k]['ghi_open_w_m2']:.0f} W/m²",
            fill="white",
            font=FONT,
        )
        fr.paste(im, (20, 30))
        frames.append(fr)
    frames[0].save(
        FIG / "diurnal_air_0_4m.gif", save_all=True, append_images=frames[1:], duration=400, loop=0
    )
    print("figures ->", FIG)


if __name__ == "__main__":
    main()
