"""Figures for temperature3d_solar (PIL only): native vs solar-coupled shade, ground surface temperature, air temperature."""

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
OUT = (
    Path(sys.argv[sys.argv.index("--out") + 1])
    if "--out" in sys.argv
    else ROOT / "output/core008/physics/scaled_latent/temperature3d_solar"
)
CMP = OUT / "compare"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
BG = "#101b29"
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
FONT_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
foot = np.load(ROOT / "output/core008/physics/scaled_latent/flood/terrain/footprint_4m_yx.npy")
stats = json.loads((CMP / "comparison.json").read_text())
# study area (domain orientation) from the shade arrays' definition region
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


def ramp(t, stops):
    t = np.clip(t, 0, 1)
    pos = np.linspace(0, 1, len(stops))
    cm = np.array(stops, float)
    return np.stack([np.interp(t, pos, cm[:, k]) for k in range(3)], -1)


HEAT = [
    (49, 54, 149),
    (69, 117, 180),
    (171, 217, 233),
    (255, 255, 191),
    (253, 174, 97),
    (215, 48, 39),
    (165, 0, 38),
]
DIV = [(33, 102, 172), (146, 197, 222), (247, 247, 247), (244, 165, 130), (178, 24, 43)]
GREY = [(40, 40, 45), (245, 235, 200)]


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


def render(a, stops, lo, hi, mask_out=None, shade=(40, 40, 45)):
    rgb = ramp((a - lo) / (hi - lo), stops)
    if mask_out is not None:
        rgb[mask_out] = shade
    return rgb


def main():
    sh_n = np.load(CMP / "shade_native_yx.npy")
    sh_s = np.load(CMP / "shade_solar_yx.npy")
    gs_n = np.load(CMP / "ground_surface_native_c_yx.npy")
    gs_s = np.load(CMP / "ground_surface_solar_c_yx.npy")
    air_n = np.load(CMP / "air_layer0_final_native_c_yx.npy")
    air_s = np.load(CMP / "air_layer0_final_solar_c_yx.npy")
    outside = ~study
    W = 420
    # row 1: shade native / solar radiation deficit / SVF-based ratio; row 2: ground surface native / solar / diff; row 3: air native / solar / diff
    panels = [
        (
            "model shade (per-building loop, smoothed)",
            render(sh_n[CORE], [(255, 245, 200), (40, 60, 110)], 0, 1, (foot | outside)[CORE]),
        ),
        (
            "solar-coupled: 1 - GHI_cell / GHI_open",
            render(sh_s[CORE], [(255, 245, 200), (40, 60, 110)], 0, 1, (foot | outside)[CORE]),
        ),
        (
            "difference (solar - native)",
            render((sh_s - sh_n)[CORE], DIV, -0.6, 0.6, (foot | outside)[CORE]),
        ),
        ("ground surface T, native (C)", render(gs_n[CORE], HEAT, 18, 36, outside[CORE])),
        ("ground surface T, solar-coupled (C)", render(gs_s[CORE], HEAT, 18, 36, outside[CORE])),
        ("surface difference (C)", render((gs_s - gs_n)[CORE], DIV, -3, 3, outside[CORE])),
        (
            "air T 0-4 m after 30 min, native (C)",
            render(air_n[CORE], HEAT, 24, 30, (foot | outside)[CORE]),
        ),
        (
            "air T 0-4 m, solar-coupled (C)",
            render(air_s[CORE], HEAT, 24, 30, (foot | outside)[CORE]),
        ),
        (
            "air difference (C)",
            render((air_s - air_n)[CORE], DIV, -1.5, 1.5, (foot | outside)[CORE]),
        ),
    ]
    _, hp = img(panels[0][1], W)
    canvas = Image.new("RGB", (3 * (W + 20) + 20, 3 * (hp + 34) + 90), BG)
    d = ImageDraw.Draw(canvas)
    d.text(
        (20, 8),
        f"Yi Qi 3-D temperature model on SCALED wind, {stats['scenario_time_utc']} (sun alt {stats['sun_model_alt_az'][0]:.0f}°, az {stats['sun_model_alt_az'][1]:.0f}°, GHI {stats['ghi_model_w_m2']:.0f} W/m², cloud 0.47) | Imperial core, 4 m, north up",
        fill="white",
        font=FONT,
    )
    d.text(
        (20, 26),
        f"solar coupling: ShadowNet 1 m sunlit fraction x direct {stats['solar_split']['direct_h_w_m2']:.0f} W/m² + diffuse {stats['solar_split']['diffuse_w_m2']:.0f} W/m² x SVF + reflected; longwave x SVF. "
        f"Ground surface diff mean {stats['ground_surface_c']['diff_mean']:+.2f} C (p5 {stats['ground_surface_c']['diff_p5']:+.2f}, p95 {stats['ground_surface_c']['diff_p95']:+.2f}); air 0-4 m diff mean {stats['air_layer0_final_c']['diff_mean']:+.2f} C, corr {stats['air_layer0_final_c']['corr']:.3f}",
        fill="#becbd9",
        font=FONT_S,
    )
    bars = [
        ([(255, 245, 200), (40, 60, 110)], 0, 1, "shade"),
        ([(255, 245, 200), (40, 60, 110)], 0, 1, "radiation deficit"),
        (DIV, -0.6, 0.6, "diff"),
        (HEAT, 18, 36, "C"),
        (HEAT, 18, 36, "C"),
        (DIV, -3, 3, "C"),
        (HEAT, 24, 30, "C"),
        (HEAT, 24, 30, "C"),
        (DIV, -1.5, 1.5, "C"),
    ]
    for i, (title, rgb) in enumerate(panels):
        x = 20 + (i % 3) * (W + 20)
        y = 50 + (i // 3) * (hp + 34)
        d.text((x, y), title, fill="white", font=FONT_S)
        im, _ = img(rgb, W)
        canvas.paste(im, (x, y + 16))
    for i, (st, lo, hi, lab) in enumerate(bars[:3]):
        colorbar(d, 20 + i * (W + 20), canvas.height - 32, st, lo, hi, lab + " (row 1)")
    canvas.save(FIG / "native_vs_solar_core.png")

    # whole-domain surface difference
    rgb = render(gs_s - gs_n, DIV, -3, 3, outside)
    im, hp = img(rgb, 1000)
    canvas = Image.new("RGB", (1040, hp + 90), BG)
    d = ImageDraw.Draw(canvas)
    d.text(
        (20, 8),
        "Ground surface temperature difference, solar-coupled minus native (C), whole study area, 4 m, north up",
        fill="white",
        font=FONT,
    )
    canvas.paste(im, (20, 30))
    colorbar(d, 20, hp + 44, DIV, -3, 3, "C")
    canvas.save(FIG / "surface_difference_whole.png")

    # time series of domain mean air temperature
    fm = stats["frame_means_c"]
    W2, H2 = 640, 300
    canvas = Image.new("RGB", (W2, H2), BG)
    d = ImageDraw.Draw(canvas)
    d.text(
        (20, 8),
        "fluid-cell mean air temperature over the 30 min run (90 s frames)",
        fill="white",
        font=FONT,
    )
    x0_, y0_, w, h = 60, 40, 540, 200
    allv = np.array(fm["native"] + fm["solar"])
    lo, hi = allv.min() - 0.1, allv.max() + 0.1
    d.rectangle([x0_, y0_, x0_ + w, y0_ + h], outline="#3a4a5e")
    for k in range(5):
        yy = y0_ + h - k * h / 4
        d.line([x0_, yy, x0_ + w, yy], fill="#1e2a3a")
        d.text((x0_ - 45, yy - 6), f"{lo + (hi - lo) * k / 4:.2f}", fill="#becbd9", font=FONT_S)
    for name, c in (("native", "#fd8d3c"), ("solar", "#6baed6")):
        v = fm[name]
        pts = [
            (x0_ + i / (len(v) - 1) * w, y0_ + h - (val - lo) / (hi - lo) * h)
            for i, val in enumerate(v)
        ]
        d.line(pts, fill=c, width=2)
        d.text(
            (x0_ + w - 120, y0_ + 8 + (0 if name == "native" else 14)), name, fill=c, font=FONT_S
        )
    for i in range(0, len(fm["native"]), 5):
        d.text(
            (x0_ + i / (len(fm["native"]) - 1) * w - 8, y0_ + h + 4),
            f"{i * 1.5:.0f}m",
            fill="#becbd9",
            font=FONT_S,
        )
    canvas.save(FIG / "air_mean_time_series.png")
    print("figures ->", FIG)


if __name__ == "__main__":
    main()
