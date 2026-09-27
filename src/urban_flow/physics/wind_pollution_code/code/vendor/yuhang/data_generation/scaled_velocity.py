"""Load the original SCALED VAE for wind conditioning."""

from __future__ import annotations

import sys
from pathlib import Path

import torch


def load_scaled_vae(scaled_repo: Path | str, checkpoint: Path | str) -> torch.nn.Module:
    """Build the SCALED VAE and load a wind checkpoint."""

    repo = str(Path(scaled_repo).resolve())
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from scaled.model.autoencoders.autoencoder3dv1 import AutoencoderKL

    vae = AutoencoderKL(
        in_channels=3,
        out_channels=3,
        down_block_types=["DownEncoderBlock3D"] * 3,
        up_block_types=["UpDecoderBlock3D"] * 3,
        block_out_channels=[128, 256, 384],
        latent_channels=4,
    )
    vae.load_state_dict(torch.load(Path(checkpoint), map_location="cpu"))
    return vae
