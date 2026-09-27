"""Cache SCALED wind latents for pollution diffusion training."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from scaled_velocity import load_scaled_vae
from velocity_latents import cache_latents


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse wind latent cache options."""

    parser = argparse.ArgumentParser(description="Cache SCALED velocity latents.")
    parser.add_argument("--velocity-dir", type=Path, required=True)
    parser.add_argument("--scaled-repo", type=Path, required=True)
    parser.add_argument("--velocity-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timesteps", type=int, default=4000)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--latent-scale", type=float, default=0.1)
    parser.add_argument("--tile", type=int, default=256)
    parser.add_argument("--halo", type=int)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--flip-u", action="store_true")
    parser.add_argument("--fail-existing", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Load the wind VAE and cache all requested timesteps."""

    args = parse_args(argv)
    encoder = load_scaled_vae(args.scaled_repo, args.velocity_checkpoint)
    cache_latents(
        args.velocity_dir,
        args.output_dir,
        range(args.start, args.start + args.timesteps),
        encoder,
        latent_scale=args.latent_scale,
        device=args.device,
        tile=args.tile,
        halo=args.halo,
        checkpoint=str(args.velocity_checkpoint),
        flip_u=args.flip_u,
        fail_existing=args.fail_existing,
    )


if __name__ == "__main__":
    main()
