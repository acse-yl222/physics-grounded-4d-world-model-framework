"""Figures for output/core008/physics (PIL only; matplotlib is not installed in the trellis2 env)."""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = repo_root()
OUT = ROOT / "output/core008/physics/digit"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)

VIRIDIS = np.array(
    [[16, 35, 74], [29, 105, 158], [68, 189, 168], [231, 217, 108], [229, 98, 58]], float
)
INFERNO = np.array([[0, 0, 4], [87, 16, 110], [188, 55, 84], [249, 142, 9], [252, 255, 164]], float)
DIVERGING = np.array(
    [[33, 102, 172], [146, 197, 222], [247, 247, 247], [244, 165, 130], [178, 24, 43]], float
)
SOLID_GREY = np.array([108, 113, 121], np.uint8)
BG = "#101b29"


def colormap(values, vmin, vmax, palette, mask=None):
    val = np.clip((values - vmin) / (vmax - vmin), 0, 1) * (len(palette) - 1)
    idx = np.minimum(val.astype(int), len(palette) - 2)
    t = (val - idx)[..., None]
    rgb = (palette[idx] * (1 - t) + palette[idx + 1] * t).astype(np.uint8)
    if mask is not None:
        rgb[mask] = SOLID_GREY
    return rgb


def colorbar(draw, x, y, w, h, vmin, vmax, palette, label):
    bar = colormap(np.linspace(vmax, vmin, h)[:, None].repeat(w, 1), vmin, vmax, palette)
    return (
        Image.fromarray(bar),
        (x, y),
        [
            (x + w + 6, y - 6, f"{vmax:g}"),
            (x + w + 6, y + h - 8, f"{vmin:g}"),
            (x, y + h + 8, label),
        ],
    )


def panel(canvas, draw, rgb, x, y, side, title):
    draw.text((x, y), title, fill="white")
    canvas.paste(
        Image.fromarray(rgb[::-1]).resize((side, side), Image.Resampling.NEAREST), (x, y + 16)
    )


def wind_figure():
    v = np.load(OUT / "wind/velocity_final_czyx.npy", mmap_mode="r")
    fluid = np.load(OUT / "wind/solver_fluid_zyx.npy")
    metrics = json.loads((OUT / "wind/metrics.json").read_text())
    spacing = metrics["spacing_m"]
    side = 640
    canvas = Image.new("RGB", (2 * side + 120, 2 * (side + 40) + 90), BG)
    d = ImageDraw.Draw(canvas)
    d.text(
        (20, 12),
        f"DIGIT wind | core008 2 m crop {metrics['shape_zyx']} (z,y,x) | final frame {metrics['frames_predicted']} | north up",
        fill="white",
    )
    d.text(
        (20, 30),
        "Left: speed (source [-4,4] units, shared scale 0-2). Right: horizontal arrows. Grey = solid.",
        fill="#becbd9",
    )
    for row, altitude in enumerate((10, 40)):
        k = altitude // spacing
        speed = np.linalg.norm(v[:, k], axis=0)
        rgb = colormap(speed, 0, 2, VIRIDIS, ~fluid[k])
        y0 = 60 + row * (side + 40)
        panel(canvas, d, rgb, 20, y0, side, f"layer {altitude}-{altitude + spacing} m  speed")
        x1 = 40 + side
        panel(canvas, d, rgb, x1, y0, side, f"layer {altitude}-{altitude + spacing} m  direction")
        n = speed.shape[0]
        stride = max(1, n // 24)
        for iy in range(stride // 2, n, stride):
            for ix in range(stride // 2, n, stride):
                if not fluid[k, iy, ix]:
                    continue
                u, w = float(v[0, k, iy, ix]), float(v[1, k, iy, ix])
                a = x1 + (ix + 0.5) / n * side
                b = y0 + 16 + (1 - (iy + 0.5) / n) * side
                dx, dy = u * 10, -w * 10
                d.line((a, b, a + dx, b + dy), fill="#e0ecf4", width=1)
                length = np.hypot(dx, dy)
                if length > 1:
                    ux, uy = dx / length, dy / length
                    d.line(
                        (
                            a + dx - 3 * ux + 2 * uy,
                            b + dy - 3 * uy - 2 * ux,
                            a + dx,
                            b + dy,
                            a + dx - 3 * ux - 2 * uy,
                            b + dy - 3 * uy + 2 * ux,
                        ),
                        fill="#e0ecf4",
                    )
    bar, pos, texts = colorbar(d, 2 * side + 60, 80, 18, 300, 0, 2, VIRIDIS, "speed")
    canvas.paste(bar, pos)
    for x, y, t in texts:
        d.text((x, y), t, fill="white")
    d.text(
        (20, canvas.height - 22),
        "Local crop inference with synthetic steady inflow; no CFD reference; grid-scale transfer unverified.",
        fill="#becbd9",
    )
    canvas.save(FIG / "wind_final_frame.png")

    # convergence chart
    frames = metrics["frames"]
    W, H = 900, 320
    chart = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(chart)
    changes = [
        f["change_from_previous_rms"] for f in frames if f["change_from_previous_rms"] is not None
    ]
    means = [f["fluid_speed_mean"] for f in frames]
    d.text(
        (20, 10), "DIGIT frame-to-frame RMS change (fluid cells) and mean fluid speed", fill="white"
    )
    ox, oy, pw, ph = 70, 40, W - 100, H - 90
    d.rectangle((ox, oy, ox + pw, oy + ph), outline="#4a5a6e")
    for series, colour, scale, label in (
        (changes, "#e7d96c", max(changes) * 1.1, "RMS change"),
        (means, "#44bda8", max(means) * 1.1, "mean speed"),
    ):
        pts = [
            (ox + (i + 1) / len(frames) * pw, oy + ph - val / scale * ph)
            for i, val in enumerate(series)
        ]
        if label == "RMS change":
            pts = [
                (ox + (i + 2) / len(frames) * pw, oy + ph - val / scale * ph)
                for i, val in enumerate(series)
            ]
        d.line(pts, fill=colour, width=2)
        for p in pts:
            d.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), fill=colour)
    d.text((ox, oy + ph + 8), "frame 1", fill="white")
    d.text((ox + pw - 60, oy + ph + 8), f"frame {len(frames)}", fill="white")
    d.text((ox + pw - 260, oy + 8), f"yellow: RMS change, last = {changes[-1]:.4f}", fill="#e7d96c")
    d.text((ox + pw - 260, oy + 24), f"green: mean speed, last = {means[-1]:.4f}", fill="#44bda8")
    d.text((20, H - 24), "y axes scaled to each series maximum", fill="#becbd9")
    chart.save(FIG / "wind_convergence.png")


def temperature_figure(height_m=10.0):
    solid = np.load(OUT / "temperature/solid_4m_zyx.npy")
    rows = json.loads((OUT / "temperature/metrics.json").read_text())
    steps = max(r["time_seconds"] for r in rows) // 90
    z = int(height_m // 4)
    refs = [np.load(OUT / f"temperature/reference_{k + 2:03d}.npy")[z] for k in range(steps + 1)]
    preds = [refs[0]] + [
        np.load(OUT / f"temperature/recursive_{k:03d}.npy")[z] for k in range(1, steps + 1)
    ]
    m = solid[z]
    vmin = min(float(a[~m].min()) for a in refs + preds)
    vmax = max(float(a[~m].max()) for a in refs + preds)
    limit = max(1e-6, max(float(np.abs((p - r)[~m]).max()) for p, r in zip(preds, refs)))
    side = 300
    cols = steps + 1
    canvas = Image.new("RGB", (cols * (side + 12) + 140, 3 * (side + 30) + 100), BG)
    d = ImageDraw.Draw(canvas)
    d.text(
        (20, 12),
        f"Temperature | 4 m grid | height cell {z}: [{z * 4},{z * 4 + 4}) m | same steady DIGIT wind",
        fill="white",
    )
    d.text(
        (20, 30),
        f"Rows: controlled solver / coupled recursive U-Net / prediction - solver. Colour {vmin:.2f}-{vmax:.2f} C; difference +-{limit:.2f} C.",
        fill="#becbd9",
    )
    for k, (ref, pred) in enumerate(zip(refs, preds)):
        x = 20 + k * (side + 12)
        for row, (a, pal, lo, hi) in enumerate(
            (
                (ref, INFERNO, vmin, vmax),
                (pred, INFERNO, vmin, vmax),
                (pred - ref, DIVERGING, -limit, limit),
            )
        ):
            y = 60 + row * (side + 30)
            title = ["solver", "recursive", "pred - solver"][row] + f"  +{90 * k} s"
            panel(canvas, d, colormap(a, lo, hi, pal, m), x, y, side, title)
    bx = cols * (side + 12) + 50
    for lo, hi, pal, label, y in (
        (vmin, vmax, INFERNO, "C", 80),
        (-limit, limit, DIVERGING, "dC", 60 + 2 * (side + 30) + 20),
    ):
        bar, pos, texts = colorbar(d, bx, y, 18, 220, lo, hi, pal, label)
        canvas.paste(bar, pos)
        for tx, ty, t in texts:
            d.text((tx, ty), t, fill="white")
    d.text(
        (20, canvas.height - 22),
        "Controlled solver is the adapted reference, not CFD; thermal scenario values are chosen settings.",
        fill="#becbd9",
    )
    canvas.save(FIG / "temperature_comparison_10m.png")

    W, H = 900, 340
    chart = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(chart)
    d.text((20, 10), "Fluid-only temperature MAE vs controlled solver (C)", fill="white")
    ox, oy, pw, ph = 70, 40, W - 100, H - 100
    d.rectangle((ox, oy, ox + pw, oy + ph), outline="#4a5a6e")
    top = max(r["mae_c"] for r in rows) * 1.15
    for mode, colour in (
        ("recursive", "#e7d96c"),
        ("one_step", "#44bda8"),
        ("persistence", "#e5623a"),
    ):
        series = [r for r in rows if r["mode"] == mode]
        pts = [
            (ox + r["time_seconds"] / (steps * 90) * pw, oy + ph - r["mae_c"] / top * ph)
            for r in series
        ]
        d.line(pts, fill=colour, width=2)
        for p in pts:
            d.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), fill=colour)
        d.text(
            (ox + 10, oy + 8 + 16 * ["recursive", "one_step", "persistence"].index(mode)),
            f"{mode}: " + ", ".join(f"{r['mae_c']:.3f}" for r in series),
            fill=colour,
        )
    d.text((ox, oy + ph + 8), "+90 s", fill="white")
    d.text((ox + pw - 40, oy + ph + 8), f"+{steps * 90} s", fill="white")
    d.text((ox - 60, oy - 6), f"{top:.2f}", fill="white")
    d.text((ox - 30, oy + ph - 8), "0", fill="white")
    chart.save(FIG / "temperature_mae.png")


if __name__ == "__main__":
    wind_figure()
    temperature_figure()
    print("figures written to", FIG)
