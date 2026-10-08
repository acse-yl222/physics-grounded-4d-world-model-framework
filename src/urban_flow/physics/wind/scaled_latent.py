"""SCALED latent tiling kernels extracted unchanged from run_core008_scaled_latent.py.
Tile and halo sizes below are counts of grid CELLS, not physical metres.
"""
import math
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
SCALE = 4
TILE_PHYS, HALO_PHYS = 256, 8
TILE_LAT, HALO_LAT = 256, 4
DEC_TILE_OUT, DEC_HALO_LAT = 256, 4
device = torch.device('cuda')

def load_models(weights_root, target_device=device):
    from scaled.model.autoencoders.autoencoder3dv1 import AutoencoderKL
    from scaled.model.unets.unet_3ds import UNet3DsModel
    weights_root = Path(weights_root).expanduser().resolve()
    enc = AutoencoderKL(in_channels=3, out_channels=3, down_block_types=['DownEncoderBlock3D'] * 3,
                        up_block_types=['UpDecoderBlock3D'] * 3, block_out_channels=[128, 256, 384], latent_channels=4)
    enc.load_state_dict(torch.load(weights_root / 'compression.pth', map_location='cpu', weights_only=True), strict=True)
    net = UNet3DsModel(in_channels=8, out_channels=4, down_block_types=('DownBlock3D',) * 4,
                       up_block_types=('UpBlock3D',) * 4, block_out_channels=(128, 256, 384, 512), add_attention=False)
    net.load_state_dict(torch.load(weights_root / 'inference.pth', map_location='cpu', weights_only=True), strict=True)
    return enc.eval().requires_grad_(False).to(target_device), net.eval().requires_grad_(False).to(target_device)

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
            geo = torch.from_numpy(solid[:, y0:y1, x0:x1].astype(np.float32)).unsqueeze(1)   # [D,1,h,w]
            pad = (max(0, HALO_PHYS - (ws - x0)), max(0, (we + HALO_PHYS) - x1),
                   max(0, HALO_PHYS - (hs - y0)), max(0, (he + HALO_PHYS) - y1))
            geo = F.pad(geo, pad, mode='replicate').squeeze(1)                                 # [D,272,272]
            bg = (1.0 - geo).unsqueeze(0).unsqueeze(0).expand(1, 3, *geo.shape).contiguous().to(device)
            zero = torch.zeros_like(bg)
            l0 = enc.encode(zero); lbg = enc.encode(bg)
            sl = (slice(None), slice(None), slice(None), slice(halo_lat, halo_lat + tile_lat), slice(halo_lat, halo_lat + tile_lat))
            lat0[:, :, :, i * tile_lat:(i + 1) * tile_lat, j * tile_lat:(j + 1) * tile_lat] = l0[sl].cpu()
            latbg[:, :, :, i * tile_lat:(i + 1) * tile_lat, j * tile_lat:(j + 1) * tile_lat] = lbg[sl].cpu()
    return lat0, latbg

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
            sub = stacked[:, :, :, max(0, wy0):min(H_lat, wy1), max(0, wx0):min(W_lat, wx1)].contiguous()
            pad = (max(0, -wx0), max(0, wx1 - W_lat), max(0, -wy0), max(0, wy1 - H_lat), 0, 0)
            if any(pad):
                sub = F.pad(sub, pad, mode='replicate')
            pred = net(sub.to(device)).sample
            core = pred[:, :, :, HALO_LAT:HALO_LAT + TILE_LAT, HALO_LAT:HALO_LAT + TILE_LAT].cpu()
            Y1, X1 = min(y0 + TILE_LAT, H_lat), min(x0 + TILE_LAT, W_lat)
            nxt[:, :, :, y0:Y1, x0:X1] = core[:, :, :, :Y1 - y0, :X1 - x0]
    return nxt

@torch.inference_mode()
def decode_domain(latent_t, enc):
    """decode_single_visualize_distributed with full depth; input latent in /10 units; returns model units (uvw/3)."""
    _, _, D_lat, H_lat, W_lat = latent_t.shape
    tile_lat = DEC_TILE_OUT // SCALE
    expected = SCALE * (tile_lat + 2 * DEC_HALO_LAT)
    trim = (expected - DEC_TILE_OUT) // 2
    lp = F.pad(latent_t * 10, (DEC_HALO_LAT,) * 4 + (0, 0), mode='reflect')
    H, W = H_lat * SCALE, W_lat * SCALE
    out = np.zeros((3, D_lat * SCALE, H, W), np.float32)
    for i in range(math.ceil(H_lat / tile_lat)):
        for j in range(math.ceil(W_lat / tile_lat)):
            y0, x0 = i * tile_lat, j * tile_lat
            sub = lp[:, :, :, y0:y0 + tile_lat + 2 * DEC_HALO_LAT, x0:x0 + tile_lat + 2 * DEC_HALO_LAT].to(device)
            dec = enc.decode(sub)
            core = dec[0, :, :, trim:expected - trim, trim:expected - trim].float().cpu().numpy()
            Y0, X0 = i * DEC_TILE_OUT, j * DEC_TILE_OUT
            Y1, X1 = min(Y0 + DEC_TILE_OUT, H), min(X0 + DEC_TILE_OUT, W)
            out[:, :, Y0:Y1, X0:X1] = core[:, :, :Y1 - Y0, :X1 - X0]
    return out

def wake_diagnostic(uvw4, solid4, zmax_cells=5):
    fluid = ~solid4
    speed = np.linalg.norm(uvw4, axis=0)
    down = np.zeros_like(fluid); down[:, :, 1:] = solid4[:, :, :-1] & fluid[:, :, 1:]
    up = np.zeros_like(fluid); up[:, :, :-1] = solid4[:, :, 1:] & fluid[:, :, :-1]
    down[zmax_cells:] = False; up[zmax_cells:] = False
    return {'mean_speed_plus_x_side': float(speed[down].mean()), 'mean_speed_minus_x_side': float(speed[up].mean()),
            'mean_u_fluid': float(uvw4[0][fluid].mean())}
