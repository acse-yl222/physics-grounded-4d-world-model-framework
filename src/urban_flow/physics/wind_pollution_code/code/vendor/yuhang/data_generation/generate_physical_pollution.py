from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch

from physical_dataset import generate


def _span(text: str) -> slice:
    """Parse a ``start:stop`` source-bound string into a Python slice."""

    start, stop = text.split(":", 1)
    return slice(int(start), int(stop))


def load_source(path: Path, shape: tuple[int, ...]) -> torch.Tensor:
    """Load a source field and validate its shape."""

    source = np.load(path)
    if source.shape != shape:
        raise ValueError(f"source shape {source.shape} does not match {shape}")
    return torch.from_numpy(source.astype(np.float32))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse physical pollution generation paths, solver settings, and source options."""

    parser = argparse.ArgumentParser(description="Generate boundary-correct pollution data.")
    parser.add_argument("--velocity-dir", type=Path, required=True)
    parser.add_argument("--sigma-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--dt", type=float, default=0.5)
    parser.add_argument("--ub", type=float, default=1.0)
    parser.add_argument("--vb", type=float, default=0.0)
    parser.add_argument("--source-rate", type=float, default=0.1)
    parser.add_argument("--source-path", type=Path)
    parser.add_argument("--source-z", default="2:8")
    parser.add_argument("--source-y", default="212:812")
    parser.add_argument("--source-x", default="40:60")
    parser.add_argument("--max-iter", type=int, default=200)
    parser.add_argument("--tol", type=float, default=1e-7)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--flip-u", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Build the configured source tensor and run the physical dataset generator."""

    args = parse_args(argv)
    shape = np.load(args.sigma_path, mmap_mode="r").squeeze().shape
    if args.source_path:
        source = load_source(args.source_path, shape)
    else:
        source = torch.zeros(shape, dtype=torch.float32)
        source[_span(args.source_z), _span(args.source_y), _span(args.source_x)] = 1
    generate(
        args.velocity_dir,
        args.sigma_path,
        args.output_dir,
        source,
        steps=args.steps,
        dt=args.dt,
        ub=args.ub,
        vb=args.vb,
        source_rate=args.source_rate,
        device=args.device,
        max_iter=args.max_iter,
        tol=args.tol,
        flip_u=args.flip_u,
    )


if __name__ == "__main__":
    main()
