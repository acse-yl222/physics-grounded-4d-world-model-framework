"""Solar illumination of the core008 South Kensington domain (1 m) with the NN4PDEs-style shadow / horizon networks
(src/urban_flow/physics/solar_np.py), on the flood terrain (EA LIDAR DTM + core008 buildings).

For each date: sun position every 10 min (NOAA algorithm, domain centre), shadow mask from ShadowNet, clear-sky irradiance
(ASHRAE monthly coefficients) split into direct (unshaded cells, canopy transmittance on tree cells), diffuse (x sky-view
factor) and ground-reflected parts. Sky-view factor and horizon come once from HorizonNet (16 azimuths x 18 altitudes).

Usage: python run_core008_solar.py [--dates 2026-06-21,2026-12-21] [--minutes 10] [--out output/core008/physics/scaled_latent/solar]
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from solar_np import ShadowNet, HorizonNet, sun_position, clear_sky  # noqa: E402

ROOT = repo_root()
TERRAIN = ROOT / "output/core008/physics/scaled_latent/flood/terrain"
LANDCOVER = ROOT / "output/core008/geometry/south_kensington_core008_landcover_4m"
X0, Y0 = 480, 640
REGION_OFFSET = (2116.0, 2124.0)
UTM_ORIGIN = (695238.304719173, 5709236.965026026)
CANOPY_TRANSMITTANCE = 0.3
ALBEDO = 0.2


def log(fh, msg):
    line = time.strftime("%H:%M:%S") + " " + msg
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def domain_centre_latlon(ny, nx):
    from pyproj import Transformer

    tr = Transformer.from_crs("EPSG:32630", "EPSG:4326", always_xy=True)
    cx = X0 + nx / 2 - REGION_OFFSET[0] + UTM_ORIGIN[0]
    cy = Y0 + ny / 2 - REGION_OFFSET[1] + UTM_ORIGIN[1]
    lon, lat = tr.transform(cx, cy)
    return lat, lon


def uk_offset_hours(month, day):
    """British Summer Time (UTC+1) between the last Sundays of March and October; good enough for solstice dates."""
    return 1 if 4 <= month <= 9 or (month == 3 and day >= 29) or (month == 10 and day <= 24) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", default="2026-06-21,2026-12-21")
    ap.add_argument("--minutes", type=float, default=10.0)
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--hourly_1m", type=int, default=1, help="save 1 m irradiance frames on the hour"
    )
    a = ap.parse_args()
    out = Path(a.out) if a.out else ROOT / "output/core008/physics/scaled_latent/solar"
    out.mkdir(parents=True, exist_ok=True)
    fh = open(out / "run.log", "a")
    dev = torch.device("cuda")
    t0 = time.time()

    H = np.load(TERRAIN / "bed_block_1m_yx.npy")
    foot = np.load(TERRAIN / "footprint_1m_yx.npy")
    ny, nx = H.shape
    oy, ox = Y0 // 4, X0 // 4
    canopy4 = np.load(LANDCOVER / "canopy_4m_yx.npy")[oy : oy + ny // 4, ox : ox + nx // 4]
    canopy = np.repeat(np.repeat(canopy4, 4, 0), 4, 1) & ~foot
    trans = torch.as_tensor(
        np.where(canopy, CANOPY_TRANSMITTANCE, 1.0).astype(np.float32), device=dev
    )
    lat, lon = domain_centre_latlon(ny, nx)
    log(
        fh,
        f"grid {ny}x{nx} at 1 m, buildings {foot.mean() * 100:.1f} %, canopy cells {canopy.mean() * 100:.2f} %; centre {lat:.5f} N {lon:.5f} E",
    )
    sn = ShadowNet(H, 1.0, dev)

    # sky-view factor and horizon (geometry only, once)
    svf_path = out / "svf"
    svf_path.mkdir(exist_ok=True)
    if (svf_path / "svf_1m_yx.npy").exists():
        svf = torch.as_tensor(np.load(svf_path / "svf_1m_yx.npy"), device=dev)
        log(fh, "svf loaded")
    else:
        ts = time.time()
        hn = HorizonNet(sn, n_azimuth=16, altitudes_deg=tuple(range(2, 90, 5)))
        svf, horizon = hn()
        np.save(svf_path / "svf_1m_yx.npy", svf.cpu().numpy().astype(np.float32))
        np.save(
            svf_path / "svf_4m_yx.npy",
            svf.reshape(ny // 4, 4, nx // 4, 4).mean(dim=(1, 3)).cpu().numpy().astype(np.float32),
        )
        hz4 = (
            horizon.reshape(16, ny // 4, 4, nx // 4, 4)
            .mean(dim=(2, 4))
            .cpu()
            .numpy()
            .astype(np.float16)
        )
        np.save(svf_path / "horizon_deg_4m_kyx.npy", hz4)
        g = ~torch.as_tensor(foot, device=dev)
        (svf_path / "summary.json").write_text(
            json.dumps(
                {
                    "n_azimuth": 16,
                    "altitudes_deg": list(range(2, 90, 5)),
                    "svf_formula": "mean_k cos^2(horizon_k) (isotropic sky)",
                    "ground_svf_mean": float(svf[g].mean()),
                    "ground_svf_p10": float(torch.quantile(svf[g][::4], 0.1)),
                    "ground_svf_p90": float(torch.quantile(svf[g][::4], 0.9)),
                    "roof_svf_mean": float(svf[~g].mean()),
                    "seconds": time.time() - ts,
                    "horizon_4m_file": "horizon_deg_4m_kyx.npy: k = azimuth index, 0 = N, clockwise 22.5 deg",
                },
                indent=2,
            )
        )
        log(fh, f"svf done in {time.time() - ts:.0f} s: ground mean {float(svf[g].mean()):.3f}")
    svf4 = svf.reshape(ny // 4, 4, nx // 4, 4).mean(dim=(1, 3))
    foot_t = torch.as_tensor(foot, device=dev)

    for date in a.dates.split(","):
        y, m, d = map(int, date.split("-"))
        off = uk_offset_hours(m, d)
        ddir = out / f"{date}"
        (ddir / "shadow_1m_packed").mkdir(parents=True, exist_ok=True)
        (ddir / "ghi_1m_hourly").mkdir(exist_ok=True)
        ts = time.time()
        step_h = a.minutes / 60.0
        hours_utc = np.arange(0, 24, step_h)
        sunlit_s = torch.zeros((ny, nx), device=dev)
        energy = torch.zeros((ny, nx), device=dev)  # J/m^2
        energy_direct = torch.zeros((ny, nx), device=dev)
        frames = []
        ghi4 = []
        shadow_frac = []
        for hu in hours_utc:
            alt, az = sun_position(lat, lon, y, m, d, float(hu))
            if alt <= 0:
                continue
            shadow = sn(alt, az)
            dni, dhi = clear_sky(alt, m)
            direct = (~shadow).float() * trans * dni * math.sin(math.radians(alt))
            ghi_open = dni * math.sin(math.radians(alt)) + dhi
            ghi = direct + dhi * svf + ALBEDO * ghi_open * (1.0 - svf)
            ghi = torch.where(foot_t, direct + dhi * svf, ghi)  # roofs: no ground-reflected term
            dt = a.minutes * 60.0
            sunlit_s += (~shadow).float() * dt
            energy += ghi * dt
            energy_direct += direct * dt
            local = float(hu) + off
            k = len(frames)
            np.save(
                ddir / "shadow_1m_packed" / f"shadow_{k:03d}.npy",
                np.packbits(shadow.cpu().numpy(), axis=1),
            )
            ghi4.append(
                ghi.reshape(ny // 4, 4, nx // 4, 4)
                .mean(dim=(1, 3))
                .cpu()
                .numpy()
                .astype(np.float16)
            )
            if a.hourly_1m and abs(local - round(local)) < 1e-6:
                np.save(
                    ddir / "ghi_1m_hourly" / f"ghi_{int(round(local)):02d}00_float16.npy",
                    ghi.cpu().numpy().astype(np.float16),
                )
            g = ~foot_t
            sf = float(shadow[g].float().mean())
            frames.append(
                {
                    "index": k,
                    "hour_utc": round(float(hu), 4),
                    "local_time": f"{int(local):02d}:{int(round((local % 1) * 60)):02d}",
                    "altitude_deg": alt,
                    "azimuth_deg": az,
                    "dni_w_m2": dni,
                    "dhi_w_m2": dhi,
                    "ground_shaded_fraction": sf,
                    "ground_mean_ghi_w_m2": float(ghi[g].mean()),
                    "roof_mean_ghi_w_m2": float(ghi[~g].mean()),
                }
            )
            if k % 12 == 0:
                log(
                    fh,
                    f"{date} {frames[-1]['local_time']} local | alt {alt:5.1f} az {az:5.1f} | DNI {dni:4.0f} | ground shaded {sf * 100:4.1f} % | ground GHI {frames[-1]['ground_mean_ghi_w_m2']:4.0f} W/m2 | {time.time() - ts:.0f} s",
                )
        np.save(ddir / "ghi_4m_tyx_float16.npy", np.stack(ghi4))
        np.save(ddir / "sunlit_hours_1m_yx.npy", (sunlit_s / 3600).cpu().numpy().astype(np.float32))
        np.save(
            ddir / "daily_irradiation_kwh_m2_1m_yx.npy",
            (energy / 3.6e6).cpu().numpy().astype(np.float32),
        )
        np.save(
            ddir / "daily_direct_kwh_m2_1m_yx.npy",
            (energy_direct / 3.6e6).cpu().numpy().astype(np.float32),
        )
        (ddir / "frames.json").write_text(json.dumps(frames, indent=1))
        g = ~foot_t
        day_h = len(frames) * step_h
        summ = {
            "date": date,
            "utc_offset_h": off,
            "minutes_per_frame": a.minutes,
            "frames": len(frames),
            "daylight_hours": day_h,
            "sunrise_local": frames[0]["local_time"],
            "sunset_local": frames[-1]["local_time"],
            "max_altitude_deg": max(f["altitude_deg"] for f in frames),
            "ground_sunlit_hours_mean": float((sunlit_s[g] / 3600).mean()),
            "ground_sunlit_hours_p10": float(torch.quantile(sunlit_s[g][::4] / 3600, 0.1)),
            "ground_sunlit_hours_p90": float(torch.quantile(sunlit_s[g][::4] / 3600, 0.9)),
            "ground_fraction_lt_1h_sun": float(((sunlit_s[g] / 3600) < 1).float().mean()),
            "ground_daily_kwh_m2_mean": float((energy[g] / 3.6e6).mean()),
            "roof_daily_kwh_m2_mean": float((energy[~g] / 3.6e6).mean()),
            "open_sky_daily_kwh_m2": float(
                sum(
                    (f["dni_w_m2"] * math.sin(math.radians(f["altitude_deg"])) + f["dhi_w_m2"])
                    for f in frames
                )
                * a.minutes
                * 60
                / 3.6e6
            ),
            "seconds": time.time() - ts,
        }
        (ddir / "summary.json").write_text(json.dumps(summ, indent=2))
        log(fh, f"{date}: {json.dumps(summ)}")

    cfg = {
        "date_run": time.strftime("%Y-%m-%d %H:%M:%S"),
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0),
        "model": "src/urban_flow/physics/solar_np.py: ShadowNet (running-maximum network along integer ray vectors, |p| 16-32 cells, angle error < 1 deg), HorizonNet (16 azimuths x 18 altitudes), ASHRAE clear-sky, NOAA sun position",
        "style": "NN4PDEs: fixed-weight tensor layers, no training, PyTorch on GPU",
        "terrain": "flood/terrain/bed_block_1m_yx.npy = EA 2022 LIDAR DTM + core008 roof heights (buildings cast shadows and receive light on roofs)",
        "canopy": f"tree canopy cells (core008.glb materials, 4 m mask) attenuate the direct beam by transmittance {CANOPY_TRANSMITTANCE}; trees cast no shadows on neighbours",
        "albedo_ground_reflected": ALBEDO,
        "grid": {
            "cell_m": 1,
            "shape_yx": [ny, nx],
            "domain_lower_xy_m": [X0, Y0],
            "row0": "south",
            "col0": "west",
        },
        "centre_lat_lon": [lat, lon],
        "dates": a.dates.split(","),
        "minutes_per_frame": a.minutes,
        "outputs": {
            "svf/": "svf_1m_yx, svf_4m_yx, horizon_deg_4m_kyx",
            "<date>/": "shadow_1m_packed/shadow_NNN.npy (np.packbits along x), ghi_4m_tyx_float16.npy [T,704,768] W/m2, ghi_1m_hourly/, sunlit_hours_1m_yx, daily_irradiation_kwh_m2_1m_yx, daily_direct_kwh_m2_1m_yx, frames.json, summary.json",
        },
        "limits": [
            "clear sky only (no clouds); ASHRAE monthly coefficients",
            "2.5-D building columns: overhangs and arcades filled",
            "no facade irradiance (2-D height field)",
            "single ground-reflected bounce as albedo x open-sky GHI x (1 - SVF); no inter-reflections",
            "integer ray direction error < 1 deg -> shadow tip lateral error < 2 % of shadow length",
        ],
        "seconds": time.time() - t0,
    }
    (out / "run_config.json").write_text(json.dumps(cfg, indent=2))
    log(fh, f"done in {time.time() - t0:.0f} s")
    fh.close()


if __name__ == "__main__":
    main()
