"""Core008 padded domain downscaled to 64x1024x1024 (4 m cells): SCALED latent wind -> temperature.

Grid: the whole 4096 m x 4096 m padded domain max-pooled 4x4x4 from the 1 m voxels -> [32,1024,1024],
32 air layers appended -> [64,1024,1024] at 4 m (256 m tall). The model sees it as a 1024-unit domain,
the same scale as its training geometry (INHALE_1280 crop of 1024 cells). One 256-latent tile: no
domain decomposition is needed at inference; encode/decode use 16 tiles each.
Time: with CFL 0.5, ub 1 and 4 m cells, one model step (50 CFD steps) = 100 s.

Derived from run_core008_scaled_latent.py:

Single-GPU port of SCALED-Surrogate-Computational-Physics-Model/inference_inmemory.py
(DataPreprocessDDP.encode_distributed_with_halo, LatentInferenceOnlyGeometryDDP.step_once,
DataPreprocessDDP.decode_single_visualize_distributed), same numerics without torchrun/NCCL:
  1. geometry encoded ONCE: 256 m physical tiles + 8 m halo (replicate pad at edges), latent core
     (halo 2) stitched into one full-domain latent [1,4,16,H/4,W/4]; z=0 layer forced solid.
  2. every step: U-Net on latent tiles of 256 latent cells (1024 m) + 4 latent halo, cores stitched;
     the state never leaves latent space between steps.
  3. decode: reflect-padded latent, 64-latent tiles + 4 halo, 288 -> 256 core trimmed.
Weights: SCALED-Tutorial weight/compression.pth + weight/inference.pth (same architecture as
inference_regression.pth expected by the v3 script).
Temperature: identical to run_core008_scaled_wind_temperature.py (teacher cloud_workflow functions).
Outputs: <project>/output/core008/physics/scaled_latent
"""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root
import hashlib
import importlib.metadata
import json
import math
import sys
import time
import types
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

_orig_version = importlib.metadata.version
importlib.metadata.version = lambda n: "1.24.4" if n == "numpy" else _orig_version(n)

ROOT = repo_root()
SCALED_REPO = Path("/home/yl222/workspace/SCALED-Tutorial")
V3_REPO = Path("/home/yl222/workspace/SCALED-Surrogate-Computational-Physics-Model")
TEACHER_CODE = ROOT / "src/urban_flow/physics/wind_temperature_teacher/code"
TEMPERATURE_WEIGHTS = ROOT / "project/south_ken/input/models/temperature_one_step.pt"
GEOMETRY = ROOT / "output/core008/geometry/south_kensington_core008_voxel_1m_domain4096"
OUT = ROOT / "output/core008/physics/scaled_latent_1024"
WIND_DIR, TEMP_DIR, LAT_DIR = OUT / "wind", OUT / "temperature", OUT / "wind/latent"
for folder in (WIND_DIR, TEMP_DIR, LAT_DIR):
    folder.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SCALED_REPO))
sys.path.insert(0, str(TEACHER_CODE))
sys.modules.setdefault("h5py", types.ModuleType("h5py"))
from scaled.model.autoencoders.autoencoder3dv1 import AutoencoderKL  # noqa: E402
from scaled.model.unets.unet_3ds import UNet3DsModel  # noqa: E402
import cloud_workflow as cw  # noqa: E402

# ----------------------------------------------------------------------------- settings
DOMAIN_LOWER_XYZ = (0, 0, 0)  # whole padded domain
DOMAIN_SIZE_XYZ = (4096, 4096, 256)  # metres; 4 m cells -> [64,1024,1024]
CELL_M = 4  # model cell size in metres (model itself is unit-less)
TEMP_LAYERS = 16  # bottom 16 x 4 m = 64 m for the temperature model
SCALE = 4  # VAE ratio
TILE_PHYS, HALO_PHYS = 256, 8  # encode
TILE_LAT, HALO_LAT = 256, 4  # latent inference (inference_inmemory.py defaults)
DEC_TILE_OUT, DEC_HALO_LAT = 256, 4  # decode
WIND_STEPS = 100
STEP_SECONDS = 25.0 * CELL_M  # 100 s per model step at 4 m cells
SPINUP_STEPS = WIND_STEPS - math.ceil(450 / STEP_SECONDS) - 1  # frames covering 0..450 s
FACTOR = 1  # wind grid already 4 m
THERMAL = {
    "ambient_c": 26.0,
    "ground_c": 30.0,
    "roof_c": 30.0,
    "surface_exchange_per_s": 0.001,
    "diffusivity_m2_s": 1.0,
    "cfl_safety": 0.8,
    "forcing_layers": 2,
    "temperature_steps": 5,
    "temperature_overlap": [4, 8, 8],
    "fine_spacing_m": float(CELL_M),
    "factor": FACTOR,
    "wind_step_seconds": STEP_SECONDS,
    "temperature_step_seconds": 90.0,
    "seed": 0,
}

assert torch.cuda.is_available()
device = torch.device("cuda")
torch.set_num_threads(8)
torch.backends.cudnn.benchmark = True


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def atomic_save(path, array):
    tmp = path.with_suffix(".partial")
    with open(tmp, "wb") as f:
        np.save(f, array)
    tmp.rename(path)


def load_models():
    enc = AutoencoderKL(
        in_channels=3,
        out_channels=3,
        down_block_types=["DownEncoderBlock3D"] * 3,
        up_block_types=["UpDecoderBlock3D"] * 3,
        block_out_channels=[128, 256, 384],
        latent_channels=4,
    )
    enc.load_state_dict(
        torch.load(SCALED_REPO / "weight/compression.pth", map_location="cpu", weights_only=True),
        strict=True,
    )
    net = UNet3DsModel(
        in_channels=8,
        out_channels=4,
        down_block_types=("DownBlock3D",) * 4,
        up_block_types=("UpBlock3D",) * 4,
        block_out_channels=(128, 256, 384, 512),
        add_attention=False,
    )
    net.load_state_dict(
        torch.load(SCALED_REPO / "weight/inference.pth", map_location="cpu", weights_only=True),
        strict=True,
    )
    return enc.eval().requires_grad_(False).to(device), net.eval().requires_grad_(False).to(device)


# ----------------------------------------------------------------------------- 1. encode once
@torch.inference_mode()
def encode_domain(solid, enc):
    """DataPreprocessDDP.preprocess_geometry_into_tiles + encode_distributed_with_halo, single process."""
    D, H, W = solid.shape
    assert H % TILE_PHYS == 0 and W % TILE_PHYS == 0
    halo_lat = HALO_PHYS // SCALE
    tile_lat = TILE_PHYS // SCALE
    lat0 = torch.zeros((1, 4, D // SCALE, H // SCALE, W // SCALE), dtype=torch.float32)
    latbg = torch.zeros_like(lat0)
    for i in range(H // TILE_PHYS):
        for j in range(W // TILE_PHYS):
            hs, ws = i * TILE_PHYS, j * TILE_PHYS
            he, we = hs + TILE_PHYS, ws + TILE_PHYS
            y0, x0 = max(hs - HALO_PHYS, 0), max(ws - HALO_PHYS, 0)
            y1, x1 = min(he + HALO_PHYS, H), min(we + HALO_PHYS, W)
            geo = torch.from_numpy(solid[:, y0:y1, x0:x1].astype(np.float32)).unsqueeze(
                1
            )  # [D,1,h,w]
            pad = (
                max(0, HALO_PHYS - (ws - x0)),
                max(0, (we + HALO_PHYS) - x1),
                max(0, HALO_PHYS - (hs - y0)),
                max(0, (he + HALO_PHYS) - y1),
            )
            geo = F.pad(geo, pad, mode="replicate").squeeze(1)  # [D,272,272]
            bg = (
                (1.0 - geo)
                .unsqueeze(0)
                .unsqueeze(0)
                .expand(1, 3, *geo.shape)
                .contiguous()
                .to(device)
            )
            zero = torch.zeros_like(bg)
            l0 = enc.encode(zero)
            lbg = enc.encode(bg)
            sl = (
                slice(None),
                slice(None),
                slice(None),
                slice(halo_lat, halo_lat + tile_lat),
                slice(halo_lat, halo_lat + tile_lat),
            )
            lat0[:, :, :, i * tile_lat : (i + 1) * tile_lat, j * tile_lat : (j + 1) * tile_lat] = (
                l0[sl].cpu()
            )
            latbg[:, :, :, i * tile_lat : (i + 1) * tile_lat, j * tile_lat : (j + 1) * tile_lat] = (
                lbg[sl].cpu()
            )
    return lat0, latbg


# ----------------------------------------------------------------------------- 2. latent step
@torch.inference_mode()
def latent_step(latent_t, latent_geo, net):
    """LatentInferenceOnlyGeometryDDP.step_once, single process. latent_t/latent_geo already /10."""
    _, _, D_lat, H_lat, W_lat = latent_geo.shape
    stacked = torch.cat([latent_t, latent_geo], dim=1)
    nxt = torch.zeros_like(latent_t)
    for i in range(math.ceil(H_lat / TILE_LAT)):
        for j in range(math.ceil(W_lat / TILE_LAT)):
            y0, x0 = i * TILE_LAT, j * TILE_LAT
            wy0, wy1 = y0 - HALO_LAT, y0 + TILE_LAT + HALO_LAT
            wx0, wx1 = x0 - HALO_LAT, x0 + TILE_LAT + HALO_LAT
            sub = stacked[
                :, :, :, max(0, wy0) : min(H_lat, wy1), max(0, wx0) : min(W_lat, wx1)
            ].contiguous()
            pad = (max(0, -wx0), max(0, wx1 - W_lat), max(0, -wy0), max(0, wy1 - H_lat), 0, 0)
            if any(pad):
                sub = F.pad(sub, pad, mode="replicate")
            pred = net(sub.to(device)).sample
            core = pred[
                :, :, :, HALO_LAT : HALO_LAT + TILE_LAT, HALO_LAT : HALO_LAT + TILE_LAT
            ].cpu()
            Y1, X1 = min(y0 + TILE_LAT, H_lat), min(x0 + TILE_LAT, W_lat)
            nxt[:, :, :, y0:Y1, x0:X1] = core[:, :, :, : Y1 - y0, : X1 - x0]
    return nxt


# ----------------------------------------------------------------------------- 3. decode
@torch.inference_mode()
def decode_domain(latent_t, enc):
    """decode_single_visualize_distributed with full depth; input latent in /10 units; returns model units (uvw/3)."""
    _, _, D_lat, H_lat, W_lat = latent_t.shape
    tile_lat = DEC_TILE_OUT // SCALE
    expected = SCALE * (tile_lat + 2 * DEC_HALO_LAT)
    trim = (expected - DEC_TILE_OUT) // 2
    lp = F.pad(latent_t * 10, (DEC_HALO_LAT,) * 4 + (0, 0), mode="reflect")
    H, W = H_lat * SCALE, W_lat * SCALE
    out = np.zeros((3, D_lat * SCALE, H, W), np.float32)
    for i in range(math.ceil(H_lat / tile_lat)):
        for j in range(math.ceil(W_lat / tile_lat)):
            y0, x0 = i * tile_lat, j * tile_lat
            sub = lp[
                :,
                :,
                :,
                y0 : y0 + tile_lat + 2 * DEC_HALO_LAT,
                x0 : x0 + tile_lat + 2 * DEC_HALO_LAT,
            ].to(device)
            dec = enc.decode(sub)
            core = (
                dec[0, :, :, trim : expected - trim, trim : expected - trim].float().cpu().numpy()
            )
            Y0, X0 = i * DEC_TILE_OUT, j * DEC_TILE_OUT
            Y1, X1 = min(Y0 + DEC_TILE_OUT, H), min(X0 + DEC_TILE_OUT, W)
            out[:, :, Y0:Y1, X0:X1] = core[:, :, : Y1 - Y0, : X1 - X0]
    return out


def wake_diagnostic(uvw4, solid4, zmax_cells=5):
    fluid = ~solid4
    speed = np.linalg.norm(uvw4, axis=0)
    down = np.zeros_like(fluid)
    down[:, :, 1:] = solid4[:, :, :-1] & fluid[:, :, 1:]
    up = np.zeros_like(fluid)
    up[:, :, :-1] = solid4[:, :, 1:] & fluid[:, :, :-1]
    down[zmax_cells:] = False
    up[zmax_cells:] = False
    return {
        "mean_speed_plus_x_side": float(speed[down].mean()),
        "mean_speed_minus_x_side": float(speed[up].mean()),
        "mean_u_fluid": float(uvw4[0][fluid].mean()),
    }


def run_wind(solid, geo):
    enc, net = load_models()
    lat_file = WIND_DIR / "latent_geometry.pt"
    if lat_file.exists():
        latent_geo = torch.load(lat_file, weights_only=True)
        latent_t = torch.load(WIND_DIR / "latent_initial.pt", weights_only=True)
    else:
        t0 = time.time()
        lat0, latbg = encode_domain(solid, enc)
        latent_t, latent_geo = lat0 / 10, latbg / 10
        torch.save(latent_geo, lat_file)
        torch.save(latent_t, WIND_DIR / "latent_initial.pt")
        log(f"encoded geometry once: latent {list(latent_geo.shape)} in {time.time() - t0:.0f}s")
    metrics_file = WIND_DIR / "metrics.json"
    metrics = {"steps": []}
    fluid1 = ~solid
    prev4 = cw.coarse_wind(
        (decode_domain(latent_t, enc) * 3 * fluid1)[:, :TEMP_LAYERS], geo["solid"], FACTOR
    )
    atomic_save(WIND_DIR / "wind4m_000.npy", prev4)
    fluid4 = ~geo["solid"]
    torch.manual_seed(THERMAL["seed"])
    torch.cuda.reset_peak_memory_stats()
    x = None
    for k in range(1, WIND_STEPS + 1):
        t0 = time.time()
        latent_t = latent_step(latent_t, latent_geo, net)
        if not torch.isfinite(latent_t).all():
            raise RuntimeError("Non-finite latent")
        t_inf = time.time() - t0
        torch.save(latent_t.to(torch.float16), LAT_DIR / f"{k:04d}.pt")
        x = decode_domain(latent_t, enc) * 3 * fluid1  # physical units, raw NN4PDEs u convention
        u4 = cw.coarse_wind(x[:, :TEMP_LAYERS], geo["solid"], FACTOR)
        atomic_save(WIND_DIR / f"wind4m_{k:03d}.npy", u4)
        speed = np.linalg.norm(u4, axis=0)[fluid4]
        entry = {
            "step": k,
            "time_seconds": k * STEP_SECONDS,
            "seconds": time.time() - t0,
            "inference_seconds": t_inf,
            "gpu_peak_allocated_GiB": torch.cuda.max_memory_allocated() / 1024**3,
            "fluid_speed_mean": float(speed.mean()),
            "fluid_speed_p95": float(np.percentile(speed, 95)),
            "fluid_speed_max": float(speed.max()),
            "change_from_previous_rms_4m": float(
                np.sqrt(np.mean((u4[:, fluid4] - prev4[:, fluid4]) ** 2))
            ),
            **wake_diagnostic(u4, geo["solid"]),
        }
        metrics["steps"].append(entry)
        metrics_file.write_text(json.dumps(metrics, indent=2) + "\n")
        prev4 = u4
        log(
            f"wind step {k}/{WIND_STEPS}: {entry['seconds']:.0f}s (infer {t_inf:.1f}s)  mean {entry['fluid_speed_mean']:.4f}  "
            f"max {entry['fluid_speed_max']:.3f}  change {entry['change_from_previous_rms_4m']:.5f}  u_mean {entry['mean_u_fluid']:+.4f}"
        )
    atomic_save(WIND_DIR / "velocity_final_4m_raw_czyx_float16.npy", x.astype(np.float16))
    del enc, net
    torch.cuda.empty_cache()
    return metrics


# ----------------------------------------------------------------------------- temperature
def wind_at(seconds):
    seconds = max(float(seconds), 0.0)
    lo = int(math.floor(seconds / STEP_SECONDS))
    frac = seconds / STEP_SECONDS - lo
    a = np.load(WIND_DIR / f"wind4m_{SPINUP_STEPS + lo:03d}.npy")
    if frac < 1e-10:
        return a
    b = np.load(WIND_DIR / f"wind4m_{SPINUP_STEPS + lo + 1:03d}.npy")
    return ((1 - frac) * a + frac * b).astype(np.float32)


def run_temperature(geo):
    cfg = dict(THERMAL)
    steps = cfg["temperature_steps"]
    times = [-180, -90, 0] + [90 * k for k in range(1, steps + 1)]
    np.save(TEMP_DIR / "solid_4m_zyx.npy", geo["solid"])
    np.save(TEMP_DIR / "roof_4m_zyx.npy", geo["roof"])
    np.save(TEMP_DIR / "height_4m_yx.npy", geo["height"])
    t = np.full(geo["solid"].shape, cfg["ambient_c"], np.float32)
    t[geo["roof"]] = cfg["roof_c"]
    refs = [t]
    solver_log = []
    for k in range(len(times) - 1):
        t0 = time.time()
        t, stats = cw.physical_step(refs[-1], wind_at(times[k]), geo, cfg, device)
        refs.append(t)
        solver_log.append(
            {
                "time_seconds": times[k + 1],
                **stats,
                "seconds": time.time() - t0,
                "fluid_mean_c": float(t[~geo["solid"]].mean()),
                "fluid_max_c": float(t[~geo["solid"]].max()),
            }
        )
        log(
            f"solver -> {times[k + 1]:+d} s: {stats['substeps']} substeps, mean {solver_log[-1]['fluid_mean_c']:.3f} C"
        )
    for k, r in enumerate(refs):
        np.save(TEMP_DIR / f"reference_{k:03d}.npy", r)
    (TEMP_DIR / "physical_solver.json").write_text(
        json.dumps(
            {
                "times_seconds": times,
                "frames": solver_log,
                "wind": f"SCALED latent-DD frames {SPINUP_STEPS}..{WIND_STEPS} = 0..{(WIND_STEPS - SPINUP_STEPS) * STEP_SECONDS:g} s, "
                "linearly interpolated to each frame start and held during its 90 s; warm-up uses the 0 s wind",
                "initialization": "ambient everywhere, roof cells at roof_c, warm-up from -180 s to 0 s",
            },
            indent=2,
        )
        + "\n"
    )
    model, stats, patch = cw.load_temperature(TEMPERATURE_WEIGHTS, device)
    mask = ~geo["solid"]
    history = np.stack(refs[:3])
    persistence = history[-1].copy()
    rows = []
    for k in range(steps):
        uvw = wind_at(k * 90)
        target = refs[k + 3]
        outputs = {}
        for mode in ("recursive", "one_step"):
            h = history if mode == "recursive" else np.stack(refs[k : k + 3])
            pred = cw.predict(
                model,
                cw.make_input(h, uvw, geo, cfg, stats),
                stats,
                patch,
                tuple(cfg["temperature_overlap"]),
                device,
            )
            np.save(TEMP_DIR / f"{mode}_{k + 1:03d}.npy", pred)
            outputs[mode] = pred
            rows.append(
                {"time_seconds": (k + 1) * 90, "mode": mode, **cw.metrics(pred, target, mask)}
            )
        rows.append(
            {
                "time_seconds": (k + 1) * 90,
                "mode": "persistence",
                **cw.metrics(persistence, target, mask),
            }
        )
        history = np.concatenate([history[1:], outputs["recursive"][None]], axis=0)
        log(
            f"temperature +{(k + 1) * 90} s: recursive MAE {rows[-3]['mae_c']:.4f} C, one-step MAE {rows[-2]['mae_c']:.4f} C, "
            f"persistence MAE {rows[-1]['mae_c']:.4f} C"
        )
    (TEMP_DIR / "metrics.json").write_text(json.dumps(rows, indent=2) + "\n")
    return {
        "grid_shape_zyx": list(geo["solid"].shape),
        "spacing_m": FACTOR,
        "patch": list(patch),
        "overlap": cfg["temperature_overlap"],
        "checkpoint_stats": {k: float(v) for k, v in stats.items()},
    }


# ----------------------------------------------------------------------------- main
if __name__ == "__main__":
    x0, y0, z0 = DOMAIN_LOWER_XYZ
    nx, ny, nz = DOMAIN_SIZE_XYZ
    full = np.load(GEOMETRY / "solid.npy", mmap_mode="r")  # [128,4096,4096] at 1 m
    pooled = np.zeros(
        (full.shape[0] // CELL_M, full.shape[1] // CELL_M, full.shape[2] // CELL_M), bool
    )
    for iz in range(pooled.shape[0]):  # 4x4x4 max-pool, chunked to limit RAM
        blk = np.asarray(full[iz * CELL_M : (iz + 1) * CELL_M])
        pooled[iz] = blk.reshape(CELL_M, pooled.shape[1], CELL_M, pooled.shape[2], CELL_M).any(
            axis=(0, 2, 4)
        )
    del full
    solid = np.zeros((nz // CELL_M, ny // CELL_M, nx // CELL_M), bool)  # [64,1024,1024]
    solid[: pooled.shape[0]] = pooled
    solid[0] = True  # v3 convention: z index 0 (ground layer) forced solid
    geo = cw.coarse_geometry(solid[:TEMP_LAYERS], factor=FACTOR, spacing=float(CELL_M))
    np.save(WIND_DIR / "solid_4m_full_zyx.npy", solid)
    run_config = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(),
        "geometry": str(GEOMETRY / "solid.npy"),
        "domain_lower_xyz_m": list(DOMAIN_LOWER_XYZ),
        "domain_upper_xyz_m": [a + b for a, b in zip(DOMAIN_LOWER_XYZ, DOMAIN_SIZE_XYZ)],
        "domain_region_lower_xyz_m": [x0 - 2116, y0 - 2124, 0],
        "cell_m": CELL_M,
        "grid_zyx": list(solid.shape),
        "building_fraction": float(solid.mean()),
        "geometry_derivation": "1 m voxels max-pooled 4x4x4 (conservative), 32 air layers appended above 128 m",
        "wind": {
            "model": "SCALED latent regression surrogate: AutoencoderKL (ratio 4, 4 latent ch) + UNet3Ds (8 in, 4 out)",
            "weights_repo": "https://github.com/acse-yl222/SCALED-Tutorial.git",
            "method_repo": "https://github.com/acse-yl222/SCALED-Surrogate-Computational-Physics-Model.git (inference_inmemory.py)",
            "inference_sha256": sha256(SCALED_REPO / "weight/inference.pth"),
            "compression_sha256": sha256(SCALED_REPO / "weight/compression.pth"),
            "domain_decomposition": {
                "encode": f"{TILE_PHYS} m tiles + {HALO_PHYS} m halo, once",
                "latent_inference": f"{TILE_LAT} latent cells ({TILE_LAT * SCALE} m) + {HALO_LAT} latent halo, replicate pad",
                "decode": f"{DEC_TILE_OUT} m tiles, {DEC_HALO_LAT} latent halo, reflect pad",
            },
            "steps": WIND_STEPS,
            "spinup_steps": SPINUP_STEPS,
            "step_seconds": STEP_SECONDS,
            "initial_state": "rest, boundary condition = geometry only; z=0 layer forced solid (v3 convention)",
            "units": "model state = physical uvw / 3; latent / 10; raw u along decreasing x index",
            "precision": "float32",
            "time_note": "CFL 0.5, ub 1, 4 m cells -> 50 CFD steps = 100 s if decoded velocity is read as m/s",
        },
        "temperature": {
            "model": "Yi Qi one-step 3D U-Net, 15 input channels",
            "checkpoint_sha256": sha256(TEMPERATURE_WEIGHTS),
            "controlled_solver": "cloud_workflow.physical_step",
            "scenario": THERMAL,
        },
        "limits": [
            "No CFD or measured reference for this geometry.",
            "SCALED weights trained on the original South Kensington 1024 m case.",
            "Grid is 4 m per cell although the model was trained with dx=1 units; physical scale rests on the INHALE geometry being ~4 m per cell.",
            "Flow starts from rest; 100 s per step follows the CFL scaling of the teacher interpretation.",
            "Thermal scenario values are chosen settings; reference is the adapted controlled solver.",
        ],
    }
    (OUT / "run_config.json").write_text(json.dumps(run_config, indent=2) + "\n")
    wm = run_wind(solid, geo)
    run_config["wind"]["total_wind_seconds"] = float(sum(s["seconds"] for s in wm["steps"]))
    run_config["temperature"].update(run_temperature(geo))
    (OUT / "run_config.json").write_text(json.dumps(run_config, indent=2) + "\n")
    log("Pipeline complete.")
