from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np


def _same(value: object, expected: object) -> bool:
    """Compare scalar or array-like HDF5 metadata by value."""

    return bool(np.array_equal(np.asarray(value), np.asarray(expected)))


def validate_latents(
    data_dir: Path,
    start: int,
    stop: int,
    shape: tuple[int, ...],
    source_shape: tuple[int, ...],
    spots: list[int],
) -> dict[str, object]:
    """Check a complete corrected wind-latent cache."""
    names = {f"{step:06d}.h5" for step in range(start, stop)}
    found = {path.name for path in data_dir.glob("*.h5")}
    missing = sorted(names - found)
    extra = sorted(found - names)
    if missing or extra:
        raise ValueError(f"missing={missing[:10]} unexpected={extra[:10]}")

    expected = {
        "latent_scale": 0.1,
        "source_shape": source_shape,
        "latent_shape": shape,
        "velocity_convention": "u_negated",
        "tile_mode": "core_crop",
        "tile_size": 256,
        "tile_halo": 32,
    }
    errors = []
    for step in range(start, stop):
        path = data_dir / f"{step:06d}.h5"
        try:
            with h5py.File(path, "r") as file:
                if set(file.keys()) != {"z_v"}:
                    errors.append(f"{path.name}: datasets")
                    continue
                z_v = file["z_v"]
                if z_v.shape != shape:
                    errors.append(f"{path.name}: shape={z_v.shape}")
                if z_v.dtype != np.dtype("float16"):
                    errors.append(f"{path.name}: dtype={z_v.dtype}")
                if file.attrs.get("source_timestep") != step:
                    errors.append(f"{path.name}: source_timestep")
                checkpoint = str(file.attrs.get("source_checkpoint", ""))
                if Path(checkpoint).name != "compression.pth":
                    errors.append(f"{path.name}: source_checkpoint")
                for key, value in expected.items():
                    if key not in file.attrs or not _same(file.attrs[key], value):
                        errors.append(f"{path.name}: {key}")
        except OSError as exc:
            errors.append(f"{path.name}: unreadable ({exc})")

    for step in spots:
        if step < start or step >= stop:
            errors.append(f"spot {step}: out of range")
            continue
        with h5py.File(data_dir / f"{step:06d}.h5", "r") as file:
            if not np.isfinite(file["z_v"][:]).all():
                errors.append(f"{step:06d}.h5: non-finite values")

    if errors:
        raise ValueError("; ".join(errors[:50]))
    return {
        "status": "pass",
        "files": len(found),
        "start": start,
        "stop": stop,
        "shape": list(shape),
        "dtype": "float16",
        "spot_checks": spots,
    }


def _dims(text: str) -> tuple[int, ...]:
    """Parse a comma-separated dimension list into integers."""

    return tuple(int(value) for value in text.split(","))


def main() -> None:
    """Validate a latent cache and optionally save the validation summary as JSON."""

    parser = argparse.ArgumentParser(description="Validate corrected wind latent files.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int, default=4000)
    parser.add_argument("--shape", type=_dims, default=(4, 16, 256, 256))
    parser.add_argument("--source-shape", type=_dims, default=(3, 64, 1024, 1024))
    parser.add_argument("--spots", type=_dims, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate_latents(
        args.data_dir,
        args.start,
        args.stop,
        args.shape,
        args.source_shape,
        list(args.spots),
    )
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text + "\n")


if __name__ == "__main__":
    main()
