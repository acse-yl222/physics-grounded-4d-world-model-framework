"""Register preserved city geometry and complete wind arrays without resampling them."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from common.storage import Storage
from common.contract import validate
from common.catalog import view as validate_view


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def register(storage, scene):
    root = storage.run(scene, "legacy_web")
    old = json.loads((root / "scene.json").read_text())
    model = root / old["model"]["url"]
    wind = old["layers"]["wind"]
    field = root / "physics" / wind["file"]
    arrays = np.load(field, mmap_mode="r")
    grid = old["grid"]
    x0 = float(grid["x0"])
    y0 = -float(grid["z_south"])
    if scene == "south_ken":
        coordinate = json.loads(
            (storage.assets(scene, "geometry") / "authoring/coordinate_contract.json").read_text()
        )
        lon, lat = coordinate["origin_wgs84"]
        vertical = coordinate["vertical_datum"]
    else:
        config = json.loads((storage.metadata(scene) / "configs/pipeline.json").read_text())
        geo = config["georeference"]
        lon, lat = geo["longitude_deg"], geo["latitude_deg"]
        vertical = geo["terrain"]
    spatial = {
        "frame": "ENU",
        "units": "m",
        "origin": {"longitude": lon, "latitude": lat, "height_m": 0, "vertical_datum": vertical},
        "bounds_m": {
            "min": [x0, y0, 0],
            "max": [x0 + grid["cols"] * grid["cell_m"], y0 + grid["rows"] * grid["cell_m"], 128],
        },
    }
    if arrays.shape[0] != wind["frames"] or arrays.shape[1] != 3:
        raise ValueError("Legacy wind metadata differs from its array")
    manifest = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "simulation": "urban_flow",
        "run_id": "legacy_web",
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "code_revision": "preserved-legacy-export",
            "dirty": False,
            "parameters": {
                "imported": True,
                "source_scene": old["id"],
                "operation": "Register existing GLB and full NPY wind arrays; no numerical recomputation or resampling.",
            },
            "inputs": [
                {"id": "city_glb", "sha256": digest(model)},
                {"id": "wind_npy", "sha256": digest(field)},
                {"id": "legacy_scene_metadata", "sha256": digest(root / "scene.json")},
            ],
        },
        "spatial": spatial,
        "time": {
            "unit": "s",
            "samples": [wind["t0_s"] + i * wind["step_s"] for i in range(arrays.shape[0])],
        },
        "layers": [
            {
                "id": "geometry",
                "kind": "mesh",
                "format": "glb",
                "asset": str(model.relative_to(root)),
                "sampling": "static",
                "encoding": {"coordinate_frame": "glTF-y-up"},
                "display": {"widget": "mesh", "capabilities": ["pick", "opacity"]},
            },
            {
                "id": "wind",
                "kind": "vector_field",
                "format": "npy",
                "asset": str(field.relative_to(root)),
                "sampling": "linear",
                "field": {"name": "velocity", "unit": "m/s"},
                "encoding": {
                    "coordinate_frame": "ENU",
                    "dtype": arrays.dtype.str,
                    "shape": list(arrays.shape),
                    "axes": "TCYX",
                    "origin_m": [x0, y0, wind["y"]],
                    "spacing_m": [wind["cell_m"], wind["cell_m"]],
                    "sample_location": "cell_center",
                    "byte_order": "little",
                    "compression": "none",
                },
                "display": {
                    "widget": "vector_field",
                    "capabilities": ["pick", "legend", "opacity"],
                    "range": wind["range"],
                },
            },
        ],
    }
    path = root / "manifest.json"
    if path.exists():
        raise FileExistsError(f"Already registered: {path}")
    write(path, manifest)
    validate(path)
    metadata = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "title": old["title"],
        "spatial": spatial,
        "inputs": [
            {
                "id": "city_glb",
                "path": f"runs/legacy_web/{model.relative_to(root)}",
                "source": "Preserved local scene export",
                "sha256": digest(model),
                "license": "Local inherited asset; public redistribution not determined by this import.",
            }
        ],
        "default_view": "default",
    }
    write(storage.metadata(scene) / "project.json", metadata)
    write(
        storage.metadata(scene) / "views/default.json",
        {
            "schema_version": "1.1.0",
            "scene_id": scene,
            "title": "Geometry and wind",
            "time_alignment": "relative",
            "runs": ["legacy_web"],
            "layers": [
                {"run_id": "legacy_web", "layer_id": layer["id"], "visible": True}
                for layer in manifest["layers"]
            ],
        },
    )
    validate_view(storage, scene, "default")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", choices=["south_ken", "white_city"])
    args = parser.parse_args()
    print(register(Storage.load(), args.scene))


if __name__ == "__main__":
    main()
