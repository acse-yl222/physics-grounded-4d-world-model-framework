"""Build selected lossless website resources without changing retained simulation runs."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def chunks(source, destination, size):
    parts = []
    total = 0
    with source.open("rb") as stream:
        while block := stream.read(size):
            path = destination / f"{len(parts):04d}.gz"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as output:
                with gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as compressed:
                    compressed.write(block)
            parts.append(
                {
                    "file": path.name,
                    "bytes": len(block),
                    "compressed_bytes": path.stat().st_size,
                    "sha256": digest(path),
                    "offset": total,
                    "encoding": "gzip",
                }
            )
            total += len(block)
    return {"total_bytes": total, "sha256": digest(source), "parts": parts}


def build(source, resources):
    manifest = json.loads((source / "manifest.json").read_text())
    if manifest["status"] != "complete" or manifest["simulation"] != "city_presentation":
        raise ValueError("Select a completed city presentation")
    scene_id, version = manifest["scene_id"], manifest["run_id"]
    base = resources / "project" / scene_id / "previews" / version
    if base.exists():
        raise FileExistsError(base)
    descriptor = next(a for a in manifest["artifacts"] if a["id"] == "city_scene")
    scene_path = source / descriptor["asset"]
    scene = json.loads(scene_path.read_text())
    model = scene_path.parent / scene["model"]["url"]
    expected = next(a for a in manifest["layers"] if a["asset"] == str(model.relative_to(source)))
    if digest(model) != expected.get("sha256", digest(model)):
        raise ValueError("Model differs from source")
    model_parts = chunks(model, base / "model", 32 * 1024 * 1024)
    write(base / "model/manifest.json", model_parts)
    scene["model"]["parts_manifest"] = "model/manifest.json"
    transport = {"schema_version": "1.0.0", "encoding": "lossless-gzip-chunks", "npy": {}}
    artifacts = {a["asset"]: a for a in manifest["artifacts"]}
    for path in sorted((scene_path.parent / "physics").rglob("*.npy")):
        if digest(path) != artifacts[path.relative_to(source).as_posix()]["sha256"]:
            raise ValueError("Array differs from source")
        relative = path.relative_to(scene_path.parent / "physics").as_posix()
        packed = chunks(path, base / "physics/packed" / relative, 8 * 1024 * 1024)
        for part in packed["parts"]:
            part["file"] = "packed/" + relative + "/" + part["file"]
        with path.open("rb") as stream:
            version_number = np.lib.format.read_magic(stream)
            reader = (
                np.lib.format.read_array_header_1_0
                if version_number == (1, 0)
                else np.lib.format.read_array_header_2_0
            )
            shape, fortran, dtype = reader(stream)
            if fortran or dtype.str not in ["<f2", "<f4", "|u1", "|b1"]:
                raise ValueError("Unsupported presentation NPY encoding")
            packed["meta"] = {
                "descr": dtype.str,
                "shape": list(shape),
                "itemsize": dtype.itemsize,
                "offset": stream.tell(),
                "block": int(np.prod(shape[1:])),
            }
        transport["npy"][relative] = packed
    write(base / "transport.json", transport)
    write(base / "scene.json", scene)
    (base / "physics").mkdir(exist_ok=True)
    shutil.copy2(scene_path.parent / "physics/manifest.json", base / "physics/manifest.json")
    write(base / "provenance/source_manifest.json", manifest)
    shutil.copy2(source / "manifest.json", base / "provenance/source_manifest.json")
    shutil.copy2(source.parents[1] / "project.json", base / "provenance/project.json")
    config = source / "provenance/presentation_config.json"
    shutil.copy2(config, base / "provenance/presentation_config.json")
    catalog_path = resources / "resources.json"
    catalog = json.loads(catalog_path.read_text())
    resource = {
        "id": scene_id + "_previews_" + manifest["run_id"],
        "scene_id": scene_id,
        "title": scene["title"],
        "category": "previews",
        "version": manifest["run_id"],
        "format": "city_presentation_gzip_v1",
        "entry": (base / "scene.json").relative_to(resources).as_posix(),
        "transport": (base / "transport.json").relative_to(resources).as_posix(),
        "model_manifest": (base / "model/manifest.json").relative_to(resources).as_posix(),
        "coordinate_frame": "glTF-y-up",
        "units": "m",
        "provenance": {
            "repository": "acse-yl222/physics-grounded-4d-world-model-framework",
            "revision": manifest["provenance"]["code_revision"],
            "original_path": source.relative_to(source.parents[3]).as_posix(),
            "source_manifest_sha256": digest(source / "manifest.json"),
            "publication": "User explicitly authorized deployment on 2026-10-12; lossless transport, no new simulation",
        },
        "license": "User-authorized publication; preserve the input licensing/source notes in framework project metadata. No blanket licence asserted.",
        "assets": [
            {
                "path": p.relative_to(resources).as_posix(),
                "bytes": p.stat().st_size,
                "sha256": digest(p),
            }
            for p in sorted(base.rglob("*"))
            if p.is_file()
        ],
    }
    catalog["resources"].append(resource)
    write(catalog_path, catalog)
    write(
        resources / "project" / scene_id / "resources.json",
        {
            "scene_id": scene_id,
            "resource_ids": [r["id"] for r in catalog["resources"] if r["scene_id"] == scene_id],
        },
    )
    print(
        json.dumps(
            {
                "scene": scene_id,
                "bytes": sum(a["bytes"] for a in resource["assets"]),
                "resource_id": resource["id"],
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("retained_run", type=Path)
    parser.add_argument("resource_checkout", type=Path)
    args = parser.parse_args()
    build(args.retained_run.resolve(), args.resource_checkout.resolve())


if __name__ == "__main__":
    main()
