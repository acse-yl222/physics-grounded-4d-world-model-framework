"""Extract only the four wind assets needed from the previously shared large ZIP."""

from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import zipfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def safe(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe bundle path: {name}")
    return name


def prepare(archive, destination):
    archive, destination = Path(archive), Path(destination).resolve()
    if not archive.is_file():
        raise FileNotFoundError(
            f"Download wind_pollution_reproduction_bundle.zip first and set DATA_ARCHIVE. Not found: {archive}"
        )
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError("Duplicate ZIP entries")
        manifest = json.loads(z.read("bundle_manifest.json"))
        if manifest.get("schema") != 1:
            raise ValueError("Unsupported original bundle manifest")
        exp_data = z.read("experiment.json")
        if hashlib.sha256(exp_data).hexdigest() != manifest["files"]["experiment.json"]["sha256"]:
            raise ValueError("Experiment metadata checksum mismatch")
        experiment = json.loads(exp_data)
        names = {
            "wind": experiment["weights"]["wind"],
            "wind_vae": experiment["weights"]["wind_vae"],
            "geometry": "data/inputs/sigma.npy",
            "initial_wind": "data/physical/W_005000.h5",
        }
        for key, name in names.items():
            safe(name)
            entry = manifest["files"][name]
            path = destination / name
            if not path.resolve().is_relative_to(destination):
                raise ValueError("Extraction path escapes destination")
            if (
                path.is_file()
                and path.stat().st_size == entry["bytes"]
                and sha(path) == entry["sha256"]
            ):
                print("Verified existing:", key)
                continue
            if path.exists():
                raise ValueError(f"Existing asset differs: {path}. Choose a new ASSET_DIR.")
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_suffix(".partial")
            h, size = hashlib.sha256(), 0
            with z.open(name) as src, partial.open("wb") as dst:
                for b in iter(lambda: src.read(8 << 20), b""):
                    h.update(b)
                    dst.write(b)
                    size += len(b)
            if h.hexdigest() != entry["sha256"] or size != entry["bytes"]:
                raise ValueError(f"Corrupt asset: {key}")
            os.replace(partial, path)
            print("Extracted and verified:", key)
    return {k: destination / v for k, v in names.items()}
