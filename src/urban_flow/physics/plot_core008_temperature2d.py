"""Figures for the 2-D temperature label model run (PIL only). Arrays are model orientation (row 0 = north)."""

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
from PIL import Image, ImageDraw

ROOT = repo_root()
RUN = ROOT / (
    sys.argv[sys.argv.index("--dir") + 1]
    if "--dir" in sys.argv
    else "output/core008/physics/scaled_latent_1024"
)
OUT = RUN / "temperature2d"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
BG = "#101b29"
INFERNO = np.array([[0, 0, 4], [87, 16, 110], [188, 55, 84], [249, 142, 9], [252, 255, 164]], float)
DIVERGING = np.array(
    [[33, 102, 172], [146, 197, 222], [247, 247, 247], [244, 165, 130], [178, 24, 43]], float
)
GREY = np.array([108, 113, 121], np.uint8)
DARK = np.array([30, 36, 48], np.uint8)


def colormap(values, vmin, vmax, palette, building, outside=None):
    t = np.clip((np.nan_to_num(values, nan=vmin) - vmin) / (vmax - vmin), 0, 1) * (len(palette) - 1)
    i = np.minimum(t.astype(int), len(palette) - 2)
    f = (t - i)[..., None]
    rgb = (palette[i] * (1 - f) + palette[i + 1] * f).astype(np.uint8)
    if outside is not None:
        rgb[outside] = DARK
    rgb[building] = GREY
    return rgb


def colorbar(canvas, d, x, y, w, h, vmin, vmax, palette, label):
    bar = colormap(
        np.linspace(vmax, vmin, h)[:, None].repeat(w, 1),
        vmin,
        vmax,
        palette,
        np.zeros((h, w), bool),
    )
    canvas.paste(Image.fromarray(bar), (x, y))
    d.text((x + w + 6, y - 6), f"{vmax:.2f}", fill="white")
    d.text((x + w + 6, y + h - 8), f"{vmin:.2f}", fill="white")
    d.text((x, y + h + 8), label, fill="white")


def crop(a, study):
    rows = np.where(study.any(1))[0]
    cols = np.where(study.any(0))[0]
    return a[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def main():
    summary = json.loads((OUT / "temperature_run_summary.json").read_text())
    T = np.load(OUT / "temperature_fields_masked_c.npy", mmap_mode="r")
    building = np.load(OUT / "building_mask.npy")
    study = np.load(OUT / "study_area_mask.npy")
    veg = np.load(OUT / "vegetation_mask.npy")
    source = np.load(OUT / "source_c_per_hour.npy")
    speed = np.load(OUT / "velocity_speed_slice.npy", mmap_mode="r")
    n = T.shape[0]
    frame_s = summary["temperature_config"]["frame_duration_s"]
    c = lambda a: crop(a, study)
    b, s, v = c(building), c(study), c(veg)
    outside = ~s
    fields = [np.asarray(c(T[k]), np.float32) for k in (0, n // 2, n - 1)]
    vals = np.concatenate([f[s & ~b] for f in fields])
    vmin, vmax = float(np.nanpercentile(vals, 1)), float(np.nanpercentile(vals, 99))
    width = 560
    h_px = int(round(width * fields[0].shape[0] / fields[0].shape[1]))
    canvas = Image.new("RGB", (3 * (width + 16) + 120, 2 * (h_px + 40) + 90), BG)
    d = ImageDraw.Draw(canvas)
    d.text(
        (20, 12),
        f"2-D temperature label model (Yi Qi) on SCALED wind | {RUN.name} | 12-16 m slice | 4 m grid | north up | "
        f"solar elev {summary['solar_elevation_deg']:.1f} deg, az {summary['solar_azimuth_deg']:.1f} deg",
        fill="white",
    )
    d.text(
        (20, 30),
        f"top: temperature at t = 0, {frame_s * (n // 2):g}, {frame_s * (n - 1):g} s (colour {vmin:.2f}-{vmax:.2f} C); "
        f"bottom: heat source (C/h), final minus initial, wind speed of first frame. Grey = building, dark = outside study area.",
        fill="#becbd9",
    )
    for k, (f, t) in enumerate(zip(fields, (0, n // 2, n - 1))):
        x = 20 + k * (width + 16)
        d.text((x, 60), f"T  t = {frame_s * t:g} s", fill="white")
        canvas.paste(
            Image.fromarray(colormap(f, vmin, vmax, INFERNO, b, outside)).resize(
                (width, h_px), Image.Resampling.NEAREST
            ),
            (x, 76),
        )
    src = c(source)
    smin, smax = float(src[s & ~b].min()), float(src[s & ~b].max())
    diff = fields[-1] - fields[0]
    lim = float(np.nanpercentile(np.abs(diff[s & ~b]), 99))
    spd = np.asarray(c(speed[0]), np.float32)
    y2 = 76 + h_px + 40
    for k, (a, pal, lo, hi, title) in enumerate(
        (
            (
                src,
                DIVERGING,
                -max(abs(smin), abs(smax)),
                max(abs(smin), abs(smax)),
                "heat source C/h (urban +, vegetation/shade -)",
            ),
            (diff, DIVERGING, -lim, lim, f"T(final) - T(initial), +-{lim:.2f} C"),
            (spd, INFERNO, 0, float(np.percentile(spd[s & ~b], 99)), "wind speed m/s, first frame"),
        )
    ):
        x = 20 + k * (width + 16)
        d.text((x, y2 - 16), title, fill="white")
        canvas.paste(
            Image.fromarray(colormap(a, lo, hi, pal, b, outside)).resize(
                (width, h_px), Image.Resampling.NEAREST
            ),
            (x, y2),
        )
    colorbar(canvas, d, 3 * (width + 16) + 40, 90, 18, 260, vmin, vmax, INFERNO, "C")
    d.text(
        (20, canvas.height - 22),
        "Scenario values are the model's defaults (summer afternoon, 2025-07-25 13:00 UTC); vegetation from core008 grass/canopy meshes; no observations.",
        fill="#becbd9",
    )
    canvas.save(FIG / "temperature2d_overview.png")

    frames = []
    step = max(1, n // 30)
    for k in range(0, n, step):
        f = np.asarray(c(T[k]), np.float32)
        img = Image.new("RGB", (width + 40, h_px + 70), BG)
        dd = ImageDraw.Draw(img)
        dd.text(
            (20, 10),
            f"2-D temperature | t = {frame_s * k:g} s | fluid mean {np.nanmean(f[s & ~b]):.2f} C",
            fill="white",
        )
        img.paste(
            Image.fromarray(colormap(f, vmin, vmax, INFERNO, b, outside)).resize(
                (width, h_px), Image.Resampling.NEAREST
            ),
            (20, 30),
        )
        dd.text((20, h_px + 40), f"colour {vmin:.2f}-{vmax:.2f} C; grey = building", fill="#becbd9")
        frames.append(img)
    frames[0].save(
        FIG / "temperature2d.gif", save_all=True, append_images=frames[1:], duration=250, loop=0
    )
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
