"""Build a protocol run of the image-to-three.js city model for a scene.

Steps: fetch Overture layers (if absent) -> fetch terrain tiles and resample the
DEM (if the scene config has a ``terrain`` block and no DEM yet) -> prepare the
scene description -> index landmark modules -> export GLB layers with three.js in
headless Chromium -> Meshopt-compress them -> write a retainable bundle (manifest,
view, project). Scenes with terrain get an extra ``terrain`` layer.

  PYTHONPATH=src python3 -m urban_geometry.image_to_threejs.build_run imperial_corridor
  p4d retain cache/imperial_corridor/image_to_threejs/<run_id>/bundle
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import secrets
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from common.contract import validate
from common.provenance import snapshot_sources
from common.storage import Storage

HERE = Path(__file__).resolve().parent
GLTF_TRANSFORM = ["npx", "--yes", "@gltf-transform/cli@4.5.1"]
LAYERS = {
    "buildings": "Generic buildings (Overture footprints, procedural facades)",
    "landmarks": "Landmark models reconstructed from reference material",
    "ground": "Roads, pavements, rail, land use, parks and water",
    "trees": "Mapped and scattered trees (resources/vegetation)",
    "street_furniture": "Lamps, benches, bus stops, post boxes, signals (resources/street)",
}
TERRAIN_LAYER = ("terrain", "Ground elevation heightfield (bare-earth DEM)")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(cmd, **kw):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kw)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("scene")
    p.add_argument("--run-id")
    p.add_argument("--view", default="default")
    p.add_argument(
        "--refetch", action="store_true", help="download Overture layers (and terrain) again"
    )
    args = p.parse_args()
    storage = Storage.load()
    meta = storage.metadata(args.scene)
    config_path = meta / "configs/image_to_threejs.json"
    config = json.loads(config_path.read_text())
    scene = config["scene_id"]
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ_") + secrets.token_hex(3)
    work = storage.scratch(scene, "image_to_threejs", run_id)
    if work.exists():
        raise FileExistsError(work)
    work.mkdir(parents=True)
    print(f"workspace: {work}")

    overture = storage.assets(scene, "input") / "overture"
    if args.refetch or not (overture / "index.json").exists():
        run(["python3", HERE / "fetch_overture.py", config_path, overture])
    index = json.loads((overture / "index.json").read_text())

    terrain_index = None
    layers = dict(LAYERS)
    if config.get("terrain"):
        terrain_dir = storage.assets(scene, "input") / "terrain"
        terrain_index = terrain_dir / "index.json"
        if args.refetch or not terrain_index.exists():
            tiles = storage.cache_root / scene / "terrain"
            run(["python3", HERE / "fetch_terrain.py", config_path, tiles, terrain_dir])
        layers = {TERRAIN_LAYER[0]: TERRAIN_LAYER[1], **LAYERS}
    dem = json.loads(terrain_index.read_text()) if terrain_index else None

    run(["node", HERE / "collect_landmarks.mjs"])
    landmark_index = HERE / "landmarks/index.json"
    scene_json = work / "scene.json"
    run(
        [
            "python3",
            HERE / "prepare_scene.py",
            config_path,
            overture,
            scene_json,
            "--claims",
            landmark_index,
            *(["--terrain", terrain_index] if terrain_index else []),
        ]
    )

    raw = work / "export"
    rel_scene = (
        "/" + str(scene_json.relative_to(storage.root))
        if scene_json.is_relative_to(storage.root)
        else None
    )
    if rel_scene is None:
        raise ValueError("The scratch workspace must be served from the repository root")
    run(
        [
            "node",
            HERE / "render.cjs",
            "export",
            "--out",
            raw,
            "--scene",
            rel_scene,
            "--half",
            str(config["domain_m"] / 2),
            "--layers",
            ",".join(layers),
        ]
    )
    report = json.loads((raw / "export-report.json").read_text())["domain"]
    if report.get("errors"):
        raise RuntimeError("Landmark export failed: " + "; ".join(report["errors"]))

    bundle = work / "bundle"
    target = bundle / run_id
    (target / "data").mkdir(parents=True)
    for layer in layers:
        # Merge duplicate materials/accessors and weld shared vertices before Meshopt;
        # flat-shaded batches carry no normals, so welding shrinks them considerably.
        welded = raw / f"{layer}.welded.glb"
        run([*GLTF_TRANSFORM, "dedup", raw / f"{layer}.glb", welded])
        run([*GLTF_TRANSFORM, "weld", welded, welded])
        run(
            [
                *GLTF_TRANSFORM,
                "meshopt",
                welded,
                target / f"data/{layer}.glb",
                "--level",
                "high",
            ]
        )
    shutil.copy2(landmark_index, target / "data/landmarks.json")
    if terrain_index:
        shutil.copy2(terrain_index, target / "data/terrain_source.json")
    snapshot = target / "provenance/source_snapshot.tar.gz"
    revision = snapshot_sources(storage.root, snapshot)

    prepared = json.loads(scene_json.read_text())
    half = config["domain_m"] / 2
    if dem:
        # Scene z is the DEM height; the origin's height is the datum zero.
        top = max(b["h"] + b.get("ground_z", 0) for b in prepared["buildings"])
        low = math.floor(prepared["source"]["terrain"]["min_m"] - 2)
        vertical = "Scene z is the DEM height in metres. " + dem["vertical_datum"]
    else:
        top = max(b["h"] for b in prepared["buildings"])
        low = 0
        vertical = "Flat ground at local zero; no terrain model applied"
    spatial = {
        "frame": "ENU",
        "units": "m",
        "origin": {**config["origin"], "height_m": 0, "vertical_datum": vertical},
        "bounds_m": {"min": [-half, -half, low], "max": [half, half, round(top + 10)]},
    }
    landmarks = json.loads(landmark_index.read_text())
    manifest = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "simulation": "image_to_threejs",
        "run_id": run_id,
        "status": "complete",
        "created_at": datetime.now(UTC).isoformat(),
        "provenance": {
            "code_revision": revision,
            "dirty": True,
            "parameters": {
                **config,
                "landmarks": len(landmarks),
                "claimed_footprints": sum(len(l["claims"]) for l in landmarks),
                "triangles": {k: report[k]["triangles"] for k in layers},
                "compression": "dedup, weld, EXT_meshopt_compression + KHR_mesh_quantization (gltf-transform 4.5.1)",
                "heights": "Overture height/num_floors where tagged; otherwise estimated "
                "(per-building flags in the prepared scene)",
                "landmark_references": "data/landmarks.json lists every source per landmark",
                **(
                    {
                        "terrain": {
                            **prepared["source"]["terrain"],
                            "source": dem["source"]["name"],
                            "zoom": dem["source"]["zoom"],
                            "imagery_sources": dem["source"]["imagery_sources"],
                            "attribution": dem["source"]["attribution"],
                            "tiles": "data/terrain_source.json lists every tile with SHA-256",
                        }
                    }
                    if dem
                    else {}
                ),
            },
            "inputs": [
                {"id": f"overture_{k}", "sha256": v["sha256"]}
                for k, v in sorted(index["layers"].items())
            ]
            + [{"id": "landmark_index", "sha256": digest(landmark_index)}]
            + ([{"id": "terrain_dem", "sha256": dem["sha256"]}] if dem else []),
        },
        "spatial": spatial,
        "time": {"unit": "s", "samples": []},
        "layers": [
            {
                "id": layer,
                "kind": "mesh",
                "format": "glb",
                "asset": f"data/{layer}.glb",
                "sampling": "static",
                "encoding": {"coordinate_frame": "glTF-y-up"},
                "display": {"widget": "mesh", "capabilities": ["pick", "opacity"]},
            }
            for layer in layers
        ],
        "artifacts": [
            {
                "id": "source_snapshot",
                "asset": "provenance/source_snapshot.tar.gz",
                "sha256": digest(snapshot),
                "media_type": "application/gzip",
            },
            {
                "id": "landmark_index",
                "asset": "data/landmarks.json",
                "sha256": digest(target / "data/landmarks.json"),
                "media_type": "application/json",
            },
        ]
        + (
            [
                {
                    "id": "terrain_source",
                    "asset": "data/terrain_source.json",
                    "sha256": digest(target / "data/terrain_source.json"),
                    "media_type": "application/json",
                }
            ]
            if dem
            else []
        ),
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    validate(target / "manifest.json")
    project = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "title": config["title"],
        "spatial": spatial,
        "inputs": [
            {
                "id": "overture",
                "path": "input/overture/index.json",
                "source": f"Overture Maps release {index['release']} (s3://overturemaps-us-west-2)",
                "sha256": digest(overture / "index.json"),
                "license": index["license"],
            },
        ]
        + (
            [
                {
                    "id": "terrain",
                    "path": "input/terrain/index.json",
                    "source": f"{dem['source']['name']} z{dem['source']['zoom']} "
                    f"({dem['source']['url_template']})",
                    "sha256": digest(terrain_index),
                    "license": " ".join(dem["source"]["attribution"])
                    + f" See {dem['source']['license']}",
                }
            ]
            if dem
            else []
        ),
        "default_view": args.view,
    }
    view = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "title": "City model",
        "time_alignment": "relative",
        "runs": [run_id],
        "layers": [{"run_id": run_id, "layer_id": layer, "visible": True} for layer in layers],
        "camera": {"position": [2600.0, -2600.0, 1500.0], "target": [-200.0, 0.0, 0.0]},
    }
    (bundle / "bundle.json").write_text(
        json.dumps(
            {
                "scene_id": scene,
                "view_id": args.view,
                "runs": [run_id],
                "view": view,
                "project": project,
            },
            indent=2,
        )
        + "\n"
    )
    sizes = {k: (target / f"data/{k}.glb").stat().st_size for k in layers}
    print(
        json.dumps(
            {
                "bundle": str(bundle),
                "bytes": sizes,
                "triangles": manifest["provenance"]["parameters"]["triangles"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
