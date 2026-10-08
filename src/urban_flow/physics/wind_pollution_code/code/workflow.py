"""Full-domain regression wind → pollution. Sources are bundled, weights are external."""

from __future__ import annotations

import ast
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
from contextlib import nullcontext

import h5py
import numpy as np
import torch
from tqdm.auto import tqdm

ROOT = Path(__file__).resolve().parent
YUHANG_COMMIT = "9817dd2b057b3b9f81efe886440a14285e52d066"
GEOMETRY_HASH = "fe6d1a16c75276a7b780b232e9091c3e0f9386ed3638238f81b75cae15b22765"
POLLUTION_SHA = "f6c496427e70e28728c00473e50d0fda41c2e82cb736ae1c0226815d44a2fbf8"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mask_hash(mask):
    return hashlib.sha256(np.ascontiguousarray(mask, dtype=np.float32).tobytes()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(tmp, path)


def save_h5(path, fields, attrs=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".partial")
    with h5py.File(tmp, "w") as f:
        for key, value in fields.items():
            if torch.is_tensor(value):
                value = value.detach().cpu().numpy()
            f.create_dataset(key, data=value, compression="lzf", shuffle=True)
        for key, value in (attrs or {}).items():
            f.attrs[key] = value
    os.replace(tmp, path)


def load_field(path, key, shape=None):
    path = Path(path)
    if path.suffix == ".npy":
        a = np.load(path, allow_pickle=False)
    else:
        with h5py.File(path, "r") as f:
            a = f[key][:]
    a = np.asarray(a, dtype=np.float32).squeeze()
    if shape and a.shape != tuple(shape):
        raise ValueError(f"{path}: expected {shape}, found {a.shape}; no implicit crop/transpose")
    if not np.isfinite(a).all():
        raise ValueError(f"Non-finite values in {path}")
    return a


def prepare_geometry(path, out_dir):
    a = np.squeeze(np.load(path, allow_pickle=False))
    if a.shape[0] != 64 and a.shape[-1] == 64:
        a = np.moveaxis(a, -1, 0)
    if a.ndim != 3 or a.shape[0] != 64 or min(a.shape[1:]) < 1024:
        raise ValueError(f"Unsupported geometry shape: {a.shape}")
    y, x = (a.shape[1] - 1024) // 2, (a.shape[2] - 1024) // 2
    solid = a[:, y : y + 1024, x : x + 1024] > 0.5
    if mask_hash(solid) != GEOMETRY_HASH:
        raise ValueError("Geometry differs from the executed 1024 notebook; check GEOMETRY_FILE")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "sigma.npy", (solid.astype(np.float32) * 1e8)[None, None])
    source = np.zeros(solid.shape, np.float32)
    source[2:8, 212:812, 40:60] = 1
    source[solid] = 0
    if source.sum() == 0:
        raise ValueError("The retained source has no fluid cells")
    np.save(out_dir / "source.npy", source)
    return solid, source


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def yuhang_modules():
    # Use the original scripts together in a scoped namespace.
    folder = ROOT / "vendor/yuhang"
    old_model = sys.modules.get("model")
    sys.modules["model"] = load_module("_pollution_original_model", folder / "model.py")
    try:
        inference = load_module("_pollution_original_inference", folder / "inference.py")
    finally:
        if old_model is None:
            sys.modules.pop("model", None)
        else:
            sys.modules["model"] = old_model
    latent = load_module(
        "_pollution_original_latents", folder / "data_generation/velocity_latents.py"
    )
    transport = load_module(
        "_pollution_original_transport", folder / "data_generation/physical_transport.py"
    )
    return inference, latent, transport


def download_pollution_checkpoint(destination, token):
    """Use Git LFS batch API; never place credentials in git URLs or output."""
    import requests

    path = Path(destination)
    if path.exists() and sha256(path) == POLLUTION_SHA:
        return path
    headers = {
        "Accept": "application/vnd.git-lfs+json",
        "Content-Type": "application/vnd.git-lfs+json",
    }
    r = requests.post(
        "https://github.com/ada-zy1725/environment-integration.git/info/lfs/objects/batch",
        auth=("x-access-token", token),
        headers=headers,
        json={
            "operation": "download",
            "transfers": ["basic"],
            "objects": [{"oid": POLLUTION_SHA, "size": 99085462}],
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"GitHub LFS access failed ({r.status_code}). Check token access to this private repo."
        )
    obj = r.json()["objects"][0]
    if "error" in obj or "download" not in obj.get("actions", {}):
        raise RuntimeError(
            "GitHub did not provide this LFS object. Check repository access and LFS availability."
        )
    action = obj["actions"]["download"]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".partial")
    # Signed LFS URL supplies its own headers; do not forward the GitHub token.
    try:
        with requests.get(
            action["href"], headers=action.get("header", {}), stream=True, timeout=120
        ) as response:
            if response.status_code != 200:
                raise RuntimeError(f"LFS object download failed ({response.status_code})")
            with tmp.open("wb") as f:
                for chunk in response.iter_content(8 << 20):
                    f.write(chunk)
    except requests.RequestException:
        raise RuntimeError(
            "LFS file transfer failed. Rerun this cell to retry; signed URL omitted."
        ) from None
    if sha256(tmp) != POLLUTION_SHA:
        raise RuntimeError("Downloaded pollution checkpoint hash mismatch")
    os.replace(tmp, path)
    return path


def transformed_cfd_source(source, sigma_path, work_dir):
    """Match notebook geometry replacement; retain solver definitions/initial state only."""
    source, n = re.subn(r"(?m)^save_path = .*", f"save_path = {str(work_dir)!r}", source, count=1)
    if n != 1:
        raise ValueError("Unexpected CFD source: save_path")
    source = re.sub(
        r"(?m)^geometry_path = .*", f"geometry_path = {str(sigma_path)!r}", source, count=1
    )
    start = source.index(
        "# #######################################################\n# ################# Only for IBM"
    )
    marker = "np.save('data/SCALED_dataset/south_kensington/sigma.npy', sigma.cpu().numpy())"
    end = source.index(marker, start) + len(marker)
    source = (
        source[:start]
        + "sigma = torch.from_numpy(np.load(geometry_path).astype(np.float32)).to(device)\n"
        + source[end:]
    )
    source = source[: source.index("model = AI4Urban().to(device)")]
    compile(source, "NN4PDEs_prepared", "exec")
    return source


CFD_FIELDS = [
    "values_u",
    "values_uu",
    "values_v",
    "values_vv",
    "values_w",
    "values_ww",
    "values_p",
    "values_pp",
    "b_uu",
    "b_vv",
    "b_ww",
    "k1",
    "dt",
    "iteration",
    "k_uu",
    "k_vv",
    "k_ww",
]


def prepare_physical_data(run_dir, dense_wind_dir=None, validation_wind_dir=None, end=6000):
    """Stream exact per-step wind + original transport; no temporal interpolation.

    C[n] is the state after n scalar updates. W[i] is the notebook's post-CFD-update
    file i; W[i] advances C[i] to C[i+1], following Yuhang's documented convention.
    """
    run_dir = Path(run_dir)
    data = run_dir / "physical"
    data.mkdir(exist_ok=True)
    solid = load_field(run_dir / "inputs/sigma.npy", "sigma", (64, 1024, 1024)) != 0
    source = load_field(run_dir / "inputs/source.npy", "source", solid.shape)
    _, _, transport = yuhang_modules()
    dense = Path(dense_wind_dir) if dense_wind_dir else None
    if dense:
        missing = [t for t in range(end + 1) if not (dense / f"{t:06d}.h5").is_file()]
        if missing:
            raise FileNotFoundError(
                f"Dense wind is incomplete (e.g. {missing[:5]}). Sparse 10/50-step files cannot be used here."
            )
        dense_solid = load_field(dense / "sigma.npy", "sigma", solid.shape) != 0
        if not np.array_equal(solid, dense_solid):
            raise ValueError("Dense wind geometry mismatch")
    settings = {
        "geometry_hash": mask_hash(solid),
        "source_hash": mask_hash(source),
        "source_rate": 0.1,
        "dt": 0.5,
        "ub": 1.0,
        "vb": 0.0,
        "u_negated": True,
        "source_commit": YUHANG_COMMIT,
        "transport_sha256": sha256(ROOT / "vendor/yuhang/data_generation/physical_transport.py"),
        "cfd_sha256": sha256(ROOT / "vendor/scaled/tools/NN4PDEs.py"),
        "wind_source": str(dense.resolve()) if dense else "streamed_NN4PDEs",
        "pairing": "W[i] advances C[i] to C[i+1]; W[i] is CFD update i+1",
    }
    meta = data / "manifest.json"
    if meta.exists() and json.loads(meta.read_text()) != settings:
        raise ValueError("Physical-data manifest mismatch; use a new RUN_NAME")
    atomic_json(meta, settings)
    if (data / f"C_{end:06d}.h5").exists() and (data / "W_005000.h5").exists():
        print("Physical inputs already complete:", data)
        return
    if not torch.cuda.is_available():
        raise RuntimeError("Select a GPU runtime to generate full-domain physical inputs")
    device = "cuda"
    solid_gpu = torch.from_numpy(solid).to(device)
    emission = torch.from_numpy(source).to(device) * 0.1
    c = torch.zeros_like(emission)
    env = None
    if dense is None:
        src = (ROOT / "vendor/scaled/tools/NN4PDEs.py").read_text()
        env = {"__name__": "_coupled_cfd"}
        exec(
            compile(
                transformed_cfd_source(src, run_dir / "inputs/sigma.npy", data / "scratch"),
                "prepared_CFD",
                "exec",
            ),
            env,
        )
        if (env["nx"], env["ny"], env["nz"], env["dt"], env["ub"]) != (1024, 1024, 64, 0.5, -1.0):
            raise ValueError("CFD configuration differs from notebook assumptions")
        env["model"] = env["AI4Urban"]().to(device).eval().requires_grad_(False)
    resume = data / "resume.pt"
    start = 0
    if resume.exists():
        checkpoint = torch.load(resume, map_location="cpu", weights_only=True)
        if checkpoint["settings"] != settings:
            raise ValueError("Physical resume settings mismatch")
        start = checkpoint["next_wind_index"]
        c = checkpoint["C"].to(device)
        if env is not None:
            for key, value in checkpoint["cfd_tensors"].items():
                env[key] = value.to(device)
        del checkpoint
        print("Resuming physical generation at wind index", start)
    t0 = time.perf_counter()
    with torch.inference_mode():
        for i in tqdm(range(start, end + 1), desc="CFD + physical pollution (first run only)"):
            if dense:
                raw = torch.from_numpy(
                    load_field(dense / f"{i:06d}.h5", "uvw", (3, *solid.shape))
                ).to(device)
            else:
                outputs = env["model"](*[env[k] for k in CFD_FIELDS])
                for key, value in zip(
                    ["values_u", "values_v", "values_w", "values_p"], outputs[:4]
                ):
                    env[key] = value
                pressure = outputs[4].abs().max().item()
                if not np.isfinite(pressure) or pressure > 80000:
                    raise RuntimeError(f"CFD diverged at index {i}")
                # Original notebook caches float16 physical wind.
                raw = (
                    torch.cat([env[k] for k in ["values_u", "values_v", "values_w"]], 1)[0]
                    .half()
                    .float()
                )
                del outputs
            if validation_wind_dir and i % 50 == 0:
                p = Path(validation_wind_dir) / f"{i:06d}.h5"
                if p.exists():
                    reference = load_field(p, "uvw", (3, *solid.shape))
                    delta = float(np.max(np.abs(raw.cpu().numpy() - reference)))
                    del reference
                    if delta > 0.01:
                        raise ValueError(
                            f"Rebuilt CFD differs from existing cache at {i}: max error {delta}. Check solver version/initialisation."
                        )
            if i >= 5000 and i % 50 == 0:
                save_h5(
                    data / f"C_{i:06d}.h5",
                    {"C": c},
                    {
                        "pollution_update_count": i,
                        "state_index": i,
                        "physical_time_solver_units": i * 0.5,
                    },
                )
                if i == 5000:
                    save_h5(
                        data / "W_005000.h5",
                        {"uvw": raw},
                        {"wind_file_index": i, "cfd_update_count": i + 1},
                    )
                save_h5(data / f"wind_planes_{i:06d}.h5", {"uvw": raw[:, [7, 15, 23]]})
            if i == end:
                break
            result = transport.upwind_step(
                c,
                -raw[0],
                raw[1],
                raw[2],
                solid_gpu,
                emission,
                dt=0.5,
                ub=1.0,
                vb=0.0,
                max_iter=200,
                tol=1e-6,
            )
            if not torch.isfinite(result.concentration).all():
                raise RuntimeError(f"Non-finite physical concentration at {i}")
            c = result.concentration
            del result, raw
            if (i + 1) % 50 == 0:
                saved = {
                    "settings": settings,
                    "next_wind_index": i + 1,
                    "C": c.cpu(),
                    "cfd_tensors": {},
                }
                if env:
                    saved["cfd_tensors"] = {
                        k: env[k].cpu() for k in CFD_FIELDS if torch.is_tensor(env[k])
                    }
                temp = resume.with_suffix(".partial")
                torch.save(saved, temp)
                os.replace(temp, resume)
                del saved
                elapsed = time.perf_counter() - t0
                if i == start + 49 or (i + 1) % 500 == 0:
                    print(
                        f"Completed {i + 1}/{end}; estimated remaining {(end - i - 1) * elapsed / (i - start + 1) / 3600:.2f} hours",
                        flush=True,
                    )
    print("Saved physical inputs and reference fields:", data)


def extract(output, mode="sample"):
    if torch.is_tensor(output):
        return output
    if hasattr(output, "latent_dist"):
        return getattr(output.latent_dist, mode)()
    if hasattr(output, "sample"):
        return output.sample
    if isinstance(output, (tuple, list)):
        return output[0]
    raise TypeError(type(output))


def starts(size, tile=256, halo=32):
    if size < tile or tile <= 2 * halo:
        raise ValueError("Invalid tiling")
    positions = list(range(0, size - tile + 1, tile - 2 * halo))
    if positions[-1] != size - tile:
        positions.append(size - tile)
    return positions


def tiles(height=1024, width=1024, tile=256, halo=32):
    for y in starts(height, tile, halo):
        for x in starts(width, tile, halo):
            sy = slice(0 if y == 0 else halo, tile if y + tile == height else tile - halo)
            sx = slice(0 if x == 0 else halo, tile if x + tile == width else tile - halo)
            yield y, x, sy, sx


def load_models(wind_ckpt, vae_ckpt, pollution_ckpt, pollution_vae_ckpt=None, device="cuda"):
    sys.path.insert(0, str(ROOT / "vendor/scaled"))
    from scaled.model.autoencoders.autoencoder3dv1 import AutoencoderKL
    from scaled.model.unets.unet_3ds import UNet3DsModel

    def vae(path):
        model = AutoencoderKL(
            in_channels=3,
            out_channels=3,
            down_block_types=["DownEncoderBlock3D"] * 3,
            up_block_types=["UpDecoderBlock3D"] * 3,
            block_out_channels=[128, 256, 384],
            latent_channels=4,
        )
        payload = torch.load(path, map_location="cpu", weights_only=True)
        payload = payload.get("state_dict", payload)
        state = {k.removeprefix("module."): v for k, v in payload.items() if torch.is_tensor(v)}
        model.load_state_dict(state, strict=True)
        return model.eval().requires_grad_(False).to(device)

    encoder = vae(vae_ckpt)
    other_path = pollution_vae_ckpt or vae_ckpt
    pollution_encoder = encoder if sha256(other_path) == sha256(vae_ckpt) else vae(other_path)
    wind = UNet3DsModel(
        in_channels=8,
        out_channels=4,
        down_block_types=("DownBlock3D",) * 4,
        up_block_types=("UpBlock3D",) * 4,
        block_out_channels=(128, 256, 384, 512),
        add_attention=False,
    )
    payload = torch.load(wind_ckpt, map_location="cpu", weights_only=False)
    if payload.get("geometry_hash") not in (None, GEOMETRY_HASH):
        raise ValueError("Wind checkpoint geometry mismatch")
    config = payload.get("config", {})
    for key, expected in {
        "domain_size": 1024,
        "patch_size": 256,
        "halo": 32,
        "delta_t": 50,
        "bc_mode": "geometry",
    }.items():
        if key in config and config[key] != expected:
            raise ValueError(f"Unexpected checkpoint {key}: {config[key]}")
    wind.load_state_dict(payload["model_state"], strict=True)
    wind = wind.eval().requires_grad_(False).to(device)
    del payload
    inference, latent, _ = yuhang_modules()
    if sha256(pollution_ckpt) != POLLUTION_SHA:
        raise ValueError("Pollution weight is not the checkpoint referenced by the bundled branch")
    pollution = inference.load_predictor(pollution_ckpt, device)
    return wind, encoder, pollution_encoder, pollution, latent


@torch.inference_mode()
def wind_step(x, solid, wind, encoder, device="cuda"):
    """Exactly the notebook's physical patch decode + halo assembly; x is raw convention /3."""
    result = np.zeros_like(x, dtype=np.float32)
    count = np.zeros(x.shape[-2:], np.uint8)
    for y, z, sy, sx in tqdm(list(tiles()), desc="Wind: 25 patches", leave=False):
        patch = torch.from_numpy(x[:, :, y : y + 256, z : z + 256].copy())[None].to(device)
        fluid = torch.from_numpy((~solid[:, y : y + 256, z : z + 256]).astype(np.float32))[
            None, None
        ].to(device)
        bg = fluid.expand(1, 3, -1, -1, -1).contiguous()
        # Keep original float32 evaluation precision and ordering: current then geometry.
        a = extract(encoder.encode(patch)) / 10
        b = extract(encoder.encode(bg)) / 10
        latent = extract(
            wind(torch.cat([a, b], 1), torch.zeros(1, dtype=torch.long, device=device))
        )
        pred = (extract(encoder.decode(latent * 10)) * fluid)[0].float().cpu().numpy()
        oy, ox = slice(y + sy.start, y + sy.stop), slice(z + sx.start, z + sx.stop)
        result[:, :, oy, ox] += pred[:, :, sy, sx]
        count[oy, ox] += 1
    if not np.all(count == 1):
        raise RuntimeError("Invalid wind core coverage")
    return result


@torch.inference_mode()
def pollution_latent(x, encoder, latent_module, device="cuda", seed=0):
    """Match Yuhang's FULL-domain halo cache, not a crop-wise approximation."""
    height, width = x.shape[-2:]
    result = np.zeros((4, x.shape[1] // 4, height // 4, width // 4), np.float16)
    cover = np.zeros((height // 4, width // 4), np.uint8)
    cuda_devices = [torch.cuda.current_device()] if str(device).startswith("cuda") else []
    with torch.random.fork_rng(devices=cuda_devices):
        torch.manual_seed(seed)
        for row in range(0, height, 192):
            for col in range(0, width, 192):
                y0 = min(max(row - 32, 0), height - 256)
                x0 = min(max(col - 32, 0), width - 256)
                y1, x1 = min(row + 192, height), min(col + 192, width)
                data = x[:, :, y0 : y0 + 256, x0 : x0 + 256].copy()
                data[0] *= -1
                data = torch.from_numpy(data)[None].to(device)
                amp = (
                    torch.autocast("cuda", dtype=torch.float16)
                    if str(device).startswith("cuda")
                    else nullcontext()
                )
                with amp:
                    zz = latent_module._latent(encoder.encode(data)) * 0.1
                zz = zz[0].float().cpu().numpy().astype(np.float16)
                if zz.shape != (4, x.shape[1] // 4, 64, 64):
                    raise ValueError(f"Unexpected encoded shape: {zz.shape}")
                ly, lx = (row - y0) // 4, (col - x0) // 4
                h, w = (y1 - row) // 4, (x1 - col) // 4
                result[:, :, row // 4 : y1 // 4, col // 4 : x1 // 4] = zz[
                    :, :, ly : ly + h, lx : lx + w
                ]
                cover[row // 4 : y1 // 4, col // 4 : x1 // 4] += 1
    if not np.all(cover == 1):
        raise RuntimeError("Invalid pollution latent tiling coverage")
    return result


@torch.inference_mode()
def pollution_step(c, solid, source, z, model, device="cuda", mode="full", amp=True):
    def predict(cp, mp, sp, zp):
        c_tensor = torch.from_numpy(np.ascontiguousarray(cp))[None, None].to(device)
        boundary = torch.from_numpy(np.stack([mp, sp]).astype(np.float32))[None].to(device)
        z_tensor = torch.from_numpy(np.ascontiguousarray(zp))[None].to(device)
        context = (
            torch.autocast("cuda", dtype=torch.float16)
            if amp and str(device).startswith("cuda")
            else nullcontext()
        )
        with context:
            prediction = model(c_tensor, boundary, z_tensor)
        return prediction[0, 0].float().cpu().numpy()

    if mode == "full":
        result = predict(c, solid, source, z)
    elif mode == "tiled":
        # GroupNorm makes this different from a full-volume forward pass.
        result = np.zeros_like(c)
        for y, x, sy, sx in tiles():
            sl = (slice(None), slice(y, y + 256), slice(x, x + 256))
            out = predict(
                c[sl],
                solid[sl],
                source[sl],
                z[:, :, y // 4 : (y + 256) // 4, x // 4 : (x + 256) // 4],
            )
            result[:, y + sy.start : y + sy.stop, x + sx.start : x + sx.stop] = out[:, sy, sx]
    else:
        raise ValueError("mode must be full or tiled")
    result[solid] = 0
    if not np.isfinite(result).all() or np.any(result < 0):
        raise RuntimeError(
            "Invalid pollution prediction; consider disabling AMP if overflow occurred"
        )
    return result


def field_metrics(c, ref, solid, cap):
    mask = ~solid
    a = c[mask].astype(np.float64)
    result = {
        "mean": float(a.mean()),
        "sum": float(a.sum()),
        "max": float(a.max()),
        "cap_fraction": float((a >= cap - 1e-6).mean()) if cap else 0.0,
    }
    if ref is not None:
        b = ref[mask].astype(np.float64)
        for name, target in [("raw", b), ("clipped", np.clip(b, 0, cap) if cap else b)]:
            result[f"rmse_{name}"] = float(np.sqrt(np.mean((a - target) ** 2)))
            result[f"mae_{name}"] = float(np.mean(np.abs(a - target)))
    return result


def run_coupled(run_dir, models, settings, mode="full", amp=True, save_wind=False):
    run_dir = Path(run_dir)
    out = run_dir / "coupled"
    out.mkdir(exist_ok=True)
    physical = run_dir / "physical"
    solid = load_field(run_dir / "inputs/sigma.npy", "sigma", (64, 1024, 1024)) != 0
    source = load_field(run_dir / "inputs/source.npy", "source", solid.shape)
    wind, encoder, poll_encoder, pollution, latent_module = models
    fingerprint = {
        **settings,
        "mode": mode,
        "amp": amp,
        "geometry": mask_hash(solid),
        "source": mask_hash(source),
        "physical_manifest": sha256(physical / "manifest.json"),
        "initial_wind": sha256(physical / "W_005000.h5"),
        "initial_pollution": sha256(physical / "C_005000.h5"),
        "workflow_sha256": sha256(Path(__file__)),
        "yuhang_commit": YUHANG_COMMIT,
    }
    manifest = out / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()) != fingerprint:
        raise ValueError(
            "Rollout configuration changed; use a new RUN_NAME or a separate coupled output folder"
        )
    atomic_json(manifest, fingerprint)
    if mode == "tiled":
        print(
            "EXPLICIT APPROXIMATION: tiled pollution uses tile-local GroupNorm statistics; not identical to full inference."
        )
    x = load_field(physical / "W_005000.h5", "uvw", (3, *solid.shape)) / 3
    c0 = load_field(physical / "C_005000.h5", "C", solid.shape)
    c = c0.copy()
    start = 5000
    resume = out / "resume.pt"
    if resume.exists():
        saved = torch.load(resume, map_location="cpu", weights_only=True)
        if saved["fingerprint"] != fingerprint:
            raise ValueError("Rollout resume manifest mismatch")
        x = saved["X"].numpy()
        c = saved["C"].numpy()
        start = saved["time"]
        torch.set_rng_state(saved["rng_cpu"])
        if torch.cuda.is_available():
            torch.cuda.set_rng_state(saved["rng_cuda"])
        del saved
        print("Resume coupled prediction at", start)
    else:
        torch.manual_seed(42)
    rows = []
    if (out / "metrics.json").exists():
        rows = json.loads((out / "metrics.json").read_text())
    device = next(wind.parameters()).device
    for t in range(start, 6001, 50):
        # Reference data are loaded ONLY for evaluation, never passed to either model.
        ref_path = physical / f"C_{t:06d}.h5"
        ref = load_field(ref_path, "C", solid.shape) if ref_path.exists() else None
        metrics = field_metrics(c, ref, solid, pollution.cap)
        baseline = field_metrics(c0, ref, solid, pollution.cap)
        rows = [r for r in rows if r["time"] != t]
        rows.append(
            {
                "time": t,
                **metrics,
                **{f"persistence_{k}": v for k, v in baseline.items() if k.startswith("rmse")},
            }
        )
        atomic_json(out / "metrics.json", rows)
        fields = {"C": c, "wind_planes_mps": x[:, [7, 15, 23]] * 3}
        if save_wind:
            fields["wind_scaled"] = x
        save_h5(
            out / f"state_{t:06d}.h5", fields, {"time_index": t, "mode": mode, "initial": t == 5000}
        )
        print(
            f"t={t}: mean C={metrics['mean']:.6g}, max C={metrics['max']:.6g}, RMSE={metrics.get('rmse_raw', 'reference not generated')}",
            flush=True,
        )
        if t == 6000:
            break
        z = pollution_latent(x, poll_encoder, latent_module, device=device, seed=700000 + t)
        c_next = pollution_step(c, solid, source, z, pollution, device=device, mode=mode, amp=amp)
        del z, ref
        x_next = wind_step(x, solid, wind, encoder, device=device)
        if not np.isfinite(x_next).all():
            raise RuntimeError("Non-finite wind forecast")
        x, c = x_next, c_next
        saved = {
            "fingerprint": fingerprint,
            "time": t + 50,
            "X": torch.from_numpy(x),
            "C": torch.from_numpy(c),
            "rng_cpu": torch.get_rng_state(),
            "rng_cuda": torch.cuda.get_rng_state()
            if torch.cuda.is_available()
            else torch.empty(0, dtype=torch.uint8),
        }
        temp = resume.with_suffix(".partial")
        torch.save(saved, temp)
        os.replace(temp, resume)
        del saved
    import pandas as pd

    pd.DataFrame(rows).sort_values("time").to_csv(out / "metrics.csv", index=False)
    print("Complete: 21 concentration fields and metrics in", out)
    return rows
