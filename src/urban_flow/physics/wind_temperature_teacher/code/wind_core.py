from __future__ import annotations
import numpy as np
import torch
from tqdm.auto import tqdm


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
