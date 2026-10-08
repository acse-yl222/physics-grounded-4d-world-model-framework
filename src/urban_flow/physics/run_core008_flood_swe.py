"""Pluvial (rainfall) flood simulation of the core008 South Kensington domain with the NN4PDEs-style shallow-water solver
(src/urban_flow/physics/flood_swe.py), on the terrain built by build_core008_flood_terrain.py.

Scenario (default): a 12 July 2021-type Kensington cloudburst, 50 mm in 90 minutes (15-minute blocks, peak 74 mm/h),
then 90 minutes of recession, 3 hours in total. Sewer drainage 12 mm/h on all sealed cells and roofs (the EA surface-water
mapping allowance), infiltration 20 mm/h on grass/vegetation. Roof rainfall in excess of the drainage rate is routed to the
nearest ground cell (downpipes / surcharged gullies). Buildings are raised blocks (solid). Domain edges absorb outflow.

Usage: python run_core008_flood_swe.py --cell 4 [--hours 3] [--frame_seconds 300] [--out output/core008/physics/scaled_latent/flood/run_4m]
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flood_swe import ShallowWater  # noqa: E402

ROOT = repo_root()
RUN = ROOT / "output/core008/physics/scaled_latent"
TERRAIN = RUN / "flood/terrain"
X0, Y0 = 480, 640  # domain metres of grid origin (row 0 = south, col 0 = west)
REGION_OFFSET = (2116.0, 2124.0)
UTM_ORIGIN = (695238.304719173, 5709236.965026026)
MM_H = 1e-3 / 3600.0

# 15-minute rainfall blocks, mm/h. 50 mm total in 90 min; the 12 July 2021 London event gave 40-50 mm in about 90 min.
HYETOGRAPH_MM_H = [14.8, 29.6, 74.0, 44.4, 22.2, 14.8]
BLOCK_S = 900.0

POIS = {  # lon, lat (WGS84)
    "South Kensington station": (-0.17401, 51.49415),
    "Imperial College, Exhibition Rd entrance": (-0.17411, 51.49874),
    "Natural History Museum (Cromwell Rd)": (-0.17636, 51.49671),
    "Gloucester Road station": (-0.18337, 51.49437),
    "Royal Albert Hall": (-0.17740, 51.50097),
    "Kensington High St / Church St": (-0.19198, 51.50153),
    "Earls Court station": (-0.19410, 51.49180),
    "Queen's Gate / Old Brompton Rd": (-0.18111, 51.49227),
}


def log(fh, msg):
    line = time.strftime("%H:%M:%S") + " " + msg
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def rain_rate(t):
    k = int(t // BLOCK_S)
    return HYETOGRAPH_MM_H[k] * MM_H if k < len(HYETOGRAPH_MM_H) else 0.0


def load_terrain(cell):
    if cell == 4:
        bed = np.load(TERRAIN / "bed_block_4m_yx.npy")
        foot = np.load(TERRAIN / "footprint_4m_yx.npy")
        grass = np.load(TERRAIN / "grass_4m_yx.npy")
        veg = np.load(TERRAIN / "vegetation_4m_yx.npy")
        dtm = np.load(TERRAIN / "dtm_4m_yx.npy")
    else:
        dtm1 = np.load(TERRAIN / "dtm_1m_yx.npy")
        foot1 = np.load(TERRAIN / "footprint_1m_yx.npy")
        bed1 = np.load(TERRAIN / "bed_block_1m_yx.npy")
        grass1 = np.load(TERRAIN / "grass_1m_yx.npy")
        veg1 = np.load(TERRAIN / "vegetation_1m_yx.npy")
        if cell == 1:
            dtm, bed, foot, grass, veg = dtm1, bed1, foot1, grass1, veg1
        else:
            ny, nx = dtm1.shape[0] // cell, dtm1.shape[1] // cell
            pool = lambda a: a.reshape(ny, cell, nx, cell).mean(axis=(1, 3))
            dtm = pool(dtm1).astype(np.float32)
            foot = pool(foot1.astype(np.float32)) >= 0.5
            hb = np.where(foot1, bed1 - dtm1, np.nan).reshape(ny, cell, nx, cell)
            with np.errstate(all="ignore"):
                hb = np.nan_to_num(np.nanmean(hb, axis=(1, 3)), nan=0.0)
            bed = (dtm + np.where(foot, np.maximum(hb, 3.0), 0.0)).astype(np.float32)
            grass = (pool(grass1.astype(np.float32)) >= 0.5) & ~foot
            veg = (pool(veg1.astype(np.float32)) >= 0.5) & ~foot
    return dtm, bed, foot, grass | veg


def poi_indices(cell):
    from pyproj import Transformer

    tr = Transformer.from_crs("EPSG:4326", "EPSG:32630", always_xy=True)
    out = {}
    for name, (lon, lat) in POIS.items():
        e, n = tr.transform(lon, lat)
        dx_, dy_ = (
            e - UTM_ORIGIN[0] + REGION_OFFSET[0] - X0,
            n - UTM_ORIGIN[1] + REGION_OFFSET[1] - Y0,
        )
        out[name] = (int(dy_ // cell), int(dx_ // cell))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", type=int, default=4)
    ap.add_argument("--hours", type=float, default=3.0)
    ap.add_argument("--frame_seconds", type=float, default=300.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dt_max", type=float, default=None)
    ap.add_argument("--sewer_mm_h", type=float, default=12.0)
    ap.add_argument("--infiltration_mm_h", type=float, default=20.0)
    ap.add_argument("--rain_scale", type=float, default=1.0)
    ap.add_argument("--n_paved", type=float, default=0.02)
    ap.add_argument("--n_green", type=float, default=0.05)
    ap.add_argument(
        "--roof_to_ground",
        type=int,
        default=1,
        help="route roof rain excess to nearest ground cell (1) or discard (0)",
    )
    ap.add_argument("--save_speed", type=int, default=1)
    a = ap.parse_args()
    cell = a.cell
    out = Path(a.out) if a.out else RUN / f"flood/run_{cell}m"
    out.mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir(exist_ok=True)
    fh = open(out / "run.log", "a")
    dev = torch.device("cuda")
    dt_max = a.dt_max or {4: 0.5, 2: 0.3, 1: 0.15}[cell]
    t_start = time.time()

    dtm, bed, foot, green = load_terrain(cell)
    ny, nx = bed.shape
    manning = np.where(green, a.n_green, a.n_paved).astype(np.float32)
    log(
        fh,
        f"grid {ny}x{nx} at {cell} m; buildings {foot.mean() * 100:.1f} %, green {green.mean() * 100:.1f} %; dt_max {dt_max} s",
    )
    sw = ShallowWater(bed, foot, cell, manning, dev)

    ground = ~foot
    # sources: rain on ground cells (+ roof excess routed to nearest ground cell); sinks: sewer / infiltration
    roof_weight = np.zeros((ny, nx), np.float32)
    if a.roof_to_ground and foot.any():
        idx = ndimage.distance_transform_edt(foot, return_distances=False, return_indices=True)
        tgt_r, tgt_c = idx[0][foot], idx[1][foot]
        np.add.at(roof_weight, (tgt_r, tgt_c), 1.0)
    sewer, infil = a.sewer_mm_h * MM_H, a.infiltration_mm_h * MM_H
    sink = np.where(green, infil, sewer).astype(np.float32)
    sink[foot] = 0
    ground_t = torch.as_tensor(ground.astype(np.float32), device=dev)
    roof_t = torch.as_tensor(roof_weight, device=dev)
    sink_t = torch.as_tensor(sink, device=dev)
    absorb = np.zeros((ny, nx), bool)
    absorb[:2] = absorb[-2:] = absorb[:, :2] = absorb[:, -2:] = True
    absorb_t = torch.as_tensor(absorb, device=dev)
    pois = poi_indices(cell)
    POI_R = 25.0
    yy, xx = np.mgrid[0:ny, 0:nx]
    poi_masks = {}
    for k, (iy, ix) in pois.items():
        m = ((yy - iy) ** 2 + (xx - ix) ** 2) * cell * cell <= POI_R**2
        poi_masks[k] = torch.as_tensor(m & ground, device=dev)
    log(
        fh,
        f"roof cells routed to ground: {int(foot.sum())} -> receiving cells {int((roof_weight > 0).sum())}, max weight {roof_weight.max():.0f}",
    )

    cfg = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0),
        "solver": "src/urban_flow/physics/flood_swe.py ShallowWater (semi-implicit free surface, C grid, upwind advection, implicit Manning, CG tol 1e-7)",
        "paper": "Chen, Nadimy, Heaney, Sharifian, Via Estrem, Nicotina, Hilberts, Pain (2025) Solving the discretised shallow water equations using neural networks, Advances in Water Resources 2025 (PII S030917082500017X); code github.com/Amin-Nadimy/Shallow_Water_Equations_NN4PDEs",
        "terrain": json.loads((TERRAIN / "metadata.json").read_text()),
        "grid": {
            "cell_m": cell,
            "shape_yx": [ny, nx],
            "domain_lower_xy_m": [X0, Y0],
            "row0": "south",
            "col0": "west",
            "index_to_domain_m": f"x = {X0} + {cell} * ix, y = {Y0} + {cell} * iy (cell lower corner)",
        },
        "scenario": {
            "hyetograph_mm_h_15min_blocks": [v * a.rain_scale for v in HYETOGRAPH_MM_H],
            "total_rain_mm": sum(HYETOGRAPH_MM_H) * a.rain_scale * BLOCK_S / 3600,
            "reference_event": "12 July 2021 London / Kensington & Chelsea cloudburst (about 40-50 mm in 90 min)",
            "duration_h": a.hours,
            "sewer_capacity_mm_h": a.sewer_mm_h,
            "infiltration_green_mm_h": a.infiltration_mm_h,
            "roof_runoff": "excess over sewer capacity routed to nearest ground cell"
            if a.roof_to_ground
            else "discarded",
            "manning_n": {"paved": a.n_paved, "green": a.n_green},
            "buildings": "solid raised blocks (no flow through)",
            "boundary": "outer 2 cells absorb (open outflow)",
            "initial_state": "dry",
        },
        "time_stepping": {
            "dt_max_s": dt_max,
            "cfl_advective": 0.7,
            "frame_seconds": a.frame_seconds,
        },
        "pois_index_yx": pois,
        "poi_radius_m": 25.0,
    }
    (out / "run_config.json").write_text(json.dumps(cfg, indent=2))

    T_end = a.hours * 3600.0
    t = 0.0
    step = 0
    tot = {
        "rain_on_ground": 0.0,
        "roof_routed": 0.0,
        "drained": 0.0,
        "outflow": 0.0,
        "neg_clamped": 0.0,
    }
    hmax = torch.zeros((ny, nx), device=dev)
    smax = torch.zeros_like(hmax)
    hazmax = torch.zeros_like(hmax)
    arrival = torch.full((ny, nx), float("nan"), device=dev)
    series = []
    frames_meta = []
    next_frame = 0.0
    next_series = 0.0
    poi_series = {k: [] for k in pois}
    cg_hist = []
    while t < T_end - 1e-6:
        dt = min(sw.stable_dt(dt_max), T_end - t)
        R = rain_rate(t) * a.rain_scale
        roof_excess = max(0.0, R - sewer)
        source = R * ground_t + roof_excess * roof_t if R > 0 else None
        o = sw.step(dt, source=source, sink_rate=sink_t, absorb=absorb_t)
        t += dt
        step += 1
        if source is not None:
            tot["rain_on_ground"] += R * dt * cell * cell * float(ground_t.sum().item())
            tot["roof_routed"] += roof_excess * dt * cell * cell * float(roof_t.sum().item())
        tot["drained"] += o["drained"]
        tot["outflow"] += o["outflow"]
        tot["neg_clamped"] += o["neg_clamped"]
        cg_hist.append(o["cg_iters"])
        speed, _, _ = sw.cell_speed()
        hmax = torch.maximum(hmax, sw.h)
        smax = torch.maximum(smax, speed)
        hazmax = torch.maximum(hazmax, sw.h * speed)
        arrival = torch.where(
            torch.isnan(arrival) & (sw.h > 0.1), torch.full_like(arrival, t), arrival
        )
        if t >= next_series - 1e-6:
            h = sw.h
            wet = h > 0.02
            rec = {
                "t_s": round(t, 3),
                "rain_mm_h": R / MM_H,
                "dt_s": dt,
                "step": step,
                "stored_m3": sw.volume(),
                **{k: v for k, v in tot.items()},
                "max_depth_m": float(h.max().item()),
                "p99_depth_ground_m": float(
                    torch.quantile(
                        h[ground_t > 0][:: max(1, int((ground_t > 0).sum().item()) // 2_000_000)],
                        0.99,
                    ).item()
                ),
                "mean_depth_wet_m": float(h[wet].mean().item()) if wet.any() else 0.0,
                "area_gt_2cm_m2": float(wet.sum().item()) * cell * cell,
                "area_gt_10cm_m2": float((h > 0.1).sum().item()) * cell * cell,
                "area_gt_30cm_m2": float((h > 0.3).sum().item()) * cell * cell,
                "max_speed_m_s": sw.max_speed(),
                "cg_iters_mean": float(np.mean(cg_hist)),
                "wall_s": time.time() - t_start,
            }
            rec["balance_error_m3"] = rec["stored_m3"] - (
                tot["rain_on_ground"]
                + tot["roof_routed"]
                - tot["drained"]
                - tot["outflow"]
                - tot["neg_clamped"]
            )
            series.append(rec)
            cg_hist = []
            for k, m in poi_masks.items():
                poi_series[k].append(float(h[m].max().item()) if m.any() else 0.0)
            if int(round(t)) % 600 == 0 or t >= T_end - 1e-6:
                log(
                    fh,
                    f"t {t / 60:6.1f} min | rain {rec['rain_mm_h']:5.1f} mm/h | dt {dt:.3f} | max h {rec['max_depth_m']:.2f} m | area>10cm {rec['area_gt_10cm_m2'] / 1e4:.1f} ha | "
                    f">30cm {rec['area_gt_30cm_m2'] / 1e4:.2f} ha | stored {rec['stored_m3']:.0f} m3 | drained {tot['drained']:.0f} | out {tot['outflow']:.0f} | "
                    f"clamp {tot['neg_clamped']:.1f} | cg {rec['cg_iters_mean']:.1f} | {rec['wall_s']:.0f} s",
                )
            next_series += 60.0
        if t >= next_frame - 1e-6:
            k = len(frames_meta)
            np.save(
                out / "frames" / f"depth_{k:03d}_float16.npy", sw.h.cpu().numpy().astype(np.float16)
            )
            if a.save_speed:
                np.save(
                    out / "frames" / f"speed_{k:03d}_float16.npy",
                    speed.cpu().numpy().astype(np.float16),
                )
            frames_meta.append({"index": k, "t_s": round(t, 3), "rain_mm_h": R / MM_H})
            next_frame += a.frame_seconds

    np.save(out / "max_depth_m.npy", hmax.cpu().numpy())
    np.save(out / "max_speed_m_s.npy", smax.cpu().numpy())
    np.save(out / "max_hazard_hv_m2_s.npy", hazmax.cpu().numpy())
    np.save(out / "arrival_time_gt10cm_s.npy", arrival.cpu().numpy())
    np.save(out / "final_depth_m.npy", sw.h.cpu().numpy())
    (out / "series.json").write_text(json.dumps(series, indent=1))
    (out / "frames/manifest.json").write_text(json.dumps(frames_meta, indent=1))
    (out / "poi_depth_series.json").write_text(
        json.dumps(
            {
                "t_s": [r["t_s"] for r in series],
                "depth_m": poi_series,
                "index_yx": pois,
                "definition": f"max depth over ground cells within {POI_R:g} m of the point",
            },
            indent=1,
        )
    )
    hm = hmax.cpu().numpy()
    street = ground & ~absorb
    summary = {
        "steps": step,
        "wall_seconds": time.time() - t_start,
        "seconds_per_step": (time.time() - t_start) / step,
        "volumes_m3": {
            **tot,
            "stored_final": sw.volume(),
            "balance_error": series[-1]["balance_error_m3"],
        },
        "max_depth_m": float(hm.max()),
        "max_depth_p99_ground_m": float(np.percentile(hm[street], 99)),
        "area_max_depth_gt_10cm_m2": float(((hm > 0.1) & street).sum()) * cell * cell,
        "area_max_depth_gt_30cm_m2": float(((hm > 0.3) & street).sum()) * cell * cell,
        "area_max_depth_gt_50cm_m2": float(((hm > 0.5) & street).sum()) * cell * cell,
        "max_speed_m_s": float(smax.max().item()),
        "peak_stored_m3": max(r["stored_m3"] for r in series),
        "peak_stored_t_min": max(series, key=lambda r: r["stored_m3"])["t_s"] / 60,
        "poi_max_depth_m": {k: max(v) for k, v in poi_series.items()},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    log(fh, "summary: " + json.dumps(summary))
    fh.close()


if __name__ == "__main__":
    main()
