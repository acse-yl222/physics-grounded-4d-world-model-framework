"""Register preserved flow experiments without moving or resampling their arrays.

Legacy metadata remains at its original path. New self-contained protocol runs use
hardlinks (copy fallback), so specialized viewers and raw scientific records survive.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import os
import shutil
import numpy as np
from common.contract import validate
from common.runs import refresh_catalog
from common.storage import Storage


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def link(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def import_run(storage, scene, name, metadata, files, geometry=None):
    record = read(metadata)
    if not record.get("complete"):
        return None
    target = storage.run(scene, "imported_" + name)
    if target.exists():
        validate(target / "manifest.json")
        return target.name
    array = np.load(files[0], mmap_mode="r", allow_pickle=False)
    times = record["times"]
    cell = record["cell_m"]
    origin = list(geometry["origin_xyz_m"]) if geometry else [0, 0, 0]
    size = geometry["size_xyz_m"] if geometry else record["domain_xyz_m"]
    spatial = {
        "frame": "ENU",
        "units": "m",
        "georeferenced": False,
        "origin": {
            "longitude": 0,
            "latitude": 0,
            "height_m": 0,
            "vertical_datum": "local engineering coordinates; geographic origin unrecorded",
        },
        "bounds_m": {"min": origin, "max": [a + b for a, b in zip(origin, size)]},
    }
    series = len(files) > 1
    encoding = {
        "coordinate_frame": "ENU",
        "dtype": array.dtype.str,
        "shape": [len(times), *array.shape[1:]],
        "axes": "TCYX",
        "origin_m": [
            origin[0],
            origin[1],
            record["slice_agl_m"] if geometry else record["disk_xyz_m"][2],
        ],
        "spacing_m": [cell, cell],
        "sample_location": "cell_center",
        "byte_order": "little",
        "compression": "none",
    }
    layer = {
        "id": "velocity",
        "kind": "vector_field",
        "format": "npy_frames" if series else "npy",
        "asset": "metadata.json" if series else "data/" + files[0].name,
        "sampling": "linear",
        "field": {"name": "velocity", "unit": "m/s"},
        "encoding": encoding,
        "display": {
            "widget": "vector_field",
            "capabilities": ["pick", "legend", "opacity"],
            "range": [0, 12],
        },
    }
    if series:
        encoding["frame_assets"] = ["data/" + f.name for f in files]
    manifest = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "run_id": target.name,
        "simulation": "urban_flow",
        "status": "complete",
        "created_at": datetime.fromtimestamp(metadata.stat().st_mtime, timezone.utc).isoformat(),
        "spatial": spatial,
        "time": {"unit": "s", "samples": times},
        "layers": [layer],
        "provenance": {
            "code_revision": "legacy-unrecorded",
            "dirty": False,
            "parameters": {
                "imported": True,
                "reproducibility": "Original source revision and dirty state were not recorded; this is a preserved result, not a reproducibility claim.",
                "original_metadata": "metadata.json",
            },
            "inputs": [{"id": "original_metadata", "sha256": digest(metadata)}],
        },
    }
    try:
        link(metadata, target / "metadata.json")
        for file in files:
            link(file, target / "data" / file.name)
        if geometry:
            ground = metadata.parent / "ground.npy"
            link(ground, target / "ground.npy")
            heights = np.load(ground, mmap_mode="r", allow_pickle=False)
            encoding.update(height_asset="ground.npy", height_dtype=heights.dtype.str)
            if (metadata.parent / "mask.npy").is_file():
                link(metadata.parent / "mask.npy", target / "mask.npy")
                encoding.update(
                    mask_asset="mask.npy", mask_dtype="|u1", mask_semantics="invalid_nonzero"
                )
        write(target / "manifest.json", manifest)
        validate(target / "manifest.json")
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        raise
    return target.name


def main():
    storage = Storage.load()
    report = []
    for scene in ("windfarm", "actuator_lab"):
        runs = []
        if scene == "windfarm":
            for metadata in sorted(storage.assets(scene, "runs").glob("*/manifest.json")):
                info = read(metadata)
                if "files" not in info:
                    continue
                if not info.get("complete"):
                    report.append(
                        {
                            "source": str(metadata.relative_to(storage.data_root)),
                            "status": "incomplete; preserved, not registered",
                        }
                    )
                    continue
                try:
                    rid = import_run(
                        storage,
                        scene,
                        metadata.parent.name,
                        metadata,
                        [metadata.parent / f for f in info["files"]],
                        read(metadata.parent / "geometry.json"),
                    )
                    runs.append(rid)
                except ValueError as exc:
                    report.append(
                        {
                            "source": str(metadata.relative_to(storage.data_root)),
                            "status": "preserved; validation rejected",
                            "reason": str(exc),
                        }
                    )
        else:
            for metadata in sorted(storage.assets(scene, "runs").glob("*/*/result.json")):
                rid = import_run(
                    storage,
                    scene,
                    metadata.parent.parent.name + "_" + metadata.parent.name,
                    metadata,
                    [metadata.parent / "hub_uvw_tcyx.npy"],
                )
                if rid:
                    runs.append(rid)
        if not runs:
            continue
        preferred = (
            "imported_np4m_paper_opentop"
            if scene == "windfarm"
            else "imported_fullgradient_disk_1p0m"
        )
        for rid in runs:
            view = {
                "schema_version": "1.1.0",
                "scene_id": scene,
                "title": rid.removeprefix("imported_").replace("_", " "),
                "time_alignment": "relative",
                "runs": [rid],
                "layers": [{"run_id": rid, "layer_id": "velocity", "visible": True}],
            }
            write(storage.metadata(scene) / "views" / f"{rid}.json", view)
            if rid == preferred:
                write(storage.metadata(scene) / "views/default.json", view)
            report.append({"scene": scene, "run_id": rid, "status": "validated"})
        spatial = read(storage.run(scene, preferred) / "manifest.json")["spatial"]
        write(
            storage.metadata(scene) / "project.json",
            {
                "schema_version": "1.1.0",
                "scene_id": scene,
                "title": "Wind farm" if scene == "windfarm" else "Actuator laboratory",
                "spatial": spatial,
                "inputs": [],
                "default_view": "default",
            },
        )
    refresh_catalog(storage)
    write(storage.root / "docs/framework/experiment-import.json", report)
    print(f"Checked {len(report)} experiment records.")


if __name__ == "__main__":
    main()
