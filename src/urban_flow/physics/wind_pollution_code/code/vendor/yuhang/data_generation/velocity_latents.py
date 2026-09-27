"""Cache tiled SCALED wind latents for diffusion conditioning."""

from __future__ import annotations

import os
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np
import torch
from torch import nn


def _latent(out: object) -> torch.Tensor:
    """Return the deterministic latent tensor from an encoder output."""

    if torch.is_tensor(out):
        return out
    dist = getattr(out, "latent_dist", None)
    if dist is None or not callable(getattr(dist, "mode", None)):
        raise TypeError("encoder output must be a tensor or expose latent_dist.mode")
    return dist.mode()


def _tiled_latent(encoder: nn.Module, data: torch.Tensor, size: int, halo: int) -> torch.Tensor:
    """Encode tiles and keep only the SCALED-style valid core."""

    height, width = data.shape[-2:]
    if height <= size and width <= size:
        return _latent(encoder.encode(data))
    core = size - 2 * halo
    if core <= 0:
        raise ValueError("halo must be smaller than half the tile size")
    out = None
    for row in range(0, height, core):
        for col in range(0, width, core):
            y0 = min(max(row - halo, 0), max(height - size, 0))
            x0 = min(max(col - halo, 0), max(width - size, 0))
            y1 = min(row + core, height)
            x1 = min(col + core, width)
            tile = data[..., y0 : y0 + size, x0 : x0 + size]
            latent = _latent(encoder.encode(tile))
            scale_h = tile.shape[-2] // latent.shape[-2]
            scale_w = tile.shape[-1] // latent.shape[-1]
            if tile.shape[-2] % latent.shape[-2] or tile.shape[-1] % latent.shape[-1]:
                raise ValueError("tile shape must match latent scale")
            if (row - y0) % scale_h or (col - x0) % scale_w:
                raise ValueError("halo must match latent scale")
            if out is None:
                shape = (*latent.shape[:-2], height // scale_h, width // scale_w)
                out = torch.zeros(shape, device=latent.device, dtype=latent.dtype)
            y = row // scale_h
            x = col // scale_w
            ly = (row - y0) // scale_h
            lx = (col - x0) // scale_w
            h = (y1 - row) // scale_h
            w = (x1 - col) // scale_w
            out[..., y : y + h, x : x + w] = latent[..., ly : ly + h, lx : lx + w]
    return out


def cache_latents(
    velocity_dir: Path,
    output_dir: Path,
    timesteps: Iterable[int],
    encoder: nn.Module,
    checkpoint: str,
    latent_scale: float = 0.1,
    device: str = "cpu",
    tile: int | None = None,
    halo: int | None = None,
    flip_u: bool = False,
    fail_existing: bool = False,
) -> None:
    """Encode velocity files and save scaled latents."""
    if latent_scale <= 0:
        raise ValueError("latent_scale must be positive")
    if tile is not None and tile <= 0:
        raise ValueError("tile must be positive")
    if halo is not None and halo < 0:
        raise ValueError("halo must be non-negative")
    if tile is not None and halo is not None and halo * 2 >= tile:
        raise ValueError("halo must be smaller than half the tile size")
    output_dir.mkdir(parents=True, exist_ok=True)
    encoder.requires_grad_(False)
    encoder.eval()
    encoder.to(device)
    for timestep in timesteps:
        source = velocity_dir / f"{timestep:06d}.h5"
        target = output_dir / f"{timestep:06d}.h5"
        if fail_existing and target.exists():
            raise FileExistsError(f"latent output already exists: {target}")
        with h5py.File(source, "r") as file:
            uvw = torch.from_numpy(np.asarray(file["uvw"], dtype=np.float32)).div_(3)
        if flip_u:
            uvw[0].neg_()
        amp = (
            torch.autocast(device_type="cuda", dtype=torch.float16)
            if str(device).startswith("cuda")
            else nullcontext()
        )
        with torch.inference_mode(), amp:
            data = uvw.unsqueeze(0).to(device)
            if tile:
                use_halo = halo if halo is not None else tile // 8
                z_v = _tiled_latent(encoder, data, tile, use_halo)
            else:
                use_halo = None
                z_v = _latent(encoder.encode(data))
            z_v = z_v * latent_scale
        data = z_v.squeeze(0).detach().cpu().numpy().astype(np.float16)
        fd, tmp_name = tempfile.mkstemp(dir=output_dir, suffix=".h5")
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            with h5py.File(tmp, "w") as file:
                file.create_dataset(
                    "z_v",
                    data=data,
                    chunks=True,
                    compression="gzip",
                    compression_opts=4,
                    shuffle=True,
                )
                file.attrs["source_timestep"] = timestep
                file.attrs["latent_scale"] = latent_scale
                file.attrs["source_checkpoint"] = checkpoint
                file.attrs["source_shape"] = np.asarray(uvw.shape, dtype=np.int64)
                file.attrs["latent_shape"] = np.asarray(data.shape, dtype=np.int64)
                file.attrs["velocity_convention"] = "u_negated" if flip_u else "raw"
                if tile:
                    file.attrs["tile_mode"] = "core_crop"
                    file.attrs["tile_size"] = tile
                    file.attrs["tile_halo"] = use_halo
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
