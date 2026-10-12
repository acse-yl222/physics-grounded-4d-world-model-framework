"""Reuse the website city renderer with a self-contained retained presentation run."""

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from common.catalog import view as check_view
from common.contract import validate
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runs import promote
from common.storage import Storage, identifier


def package(storage, scene, source_view, legacy_export, run_id, presentation_config):
    _, runs = check_view(storage, scene, source_view, check_assets=True)
    by_kind = {run["simulation"]: run for run in runs.values()}
    source = Path(legacy_export).resolve()
    config = json.loads((source / "scene.json").read_text())
    if config["id"] != scene:
        raise ValueError("Export belongs to another scene")
    target = storage.scratch(scene, "presentation", identifier(run_id, run=True))
    if target.exists() or storage.run(scene, run_id).exists():
        raise FileExistsError(run_id)
    # The display adapter must preserve the exact retained model and field arrays.
    inputs = []
    for kind in ["geometry", *(k for k in config["layers"] if k != "solar")]:
        manifest = by_kind[kind]
        layer = manifest["layers"][0]
        retained = storage.run(scene, manifest["run_id"]) / layer["asset"]
        exported = source / (
            config["model"]["url"]
            if kind == "geometry"
            else "physics/" + config["layers"][kind]["file"]
        )
        if digest(retained) != digest(exported):
            raise ValueError(f"{kind} differs from the retained simulation")
        inputs.append(
            {
                "id": kind + "_source_manifest",
                "sha256": digest(storage.run(scene, manifest["run_id"]) / "manifest.json"),
            }
        )
        inputs.append({"id": kind + "_data", "sha256": digest(retained)})
        if kind != "geometry":
            times = manifest["time"]["samples"]
            config["layers"][kind]["time_s"] = times
            if len(times) != config["layers"][kind]["frames"]:
                raise ValueError("Frame count differs from recorded times")
    for tag, day in config["layers"].get("solar", {}).get("dates", {}).items():
        date = f"{tag[:4]}_{tag[4:6]}_{tag[6:8]}"
        manifest = by_kind.get("solar_" + date) or by_kind["solar_" + tag]
        retained = storage.run(scene, manifest["run_id"]) / manifest["layers"][0]["asset"]
        if digest(retained) != digest(source / "physics" / day["ghi"]):
            raise ValueError("Solar irradiance differs from retained data")
        inputs.extend(
            [
                {
                    "id": "solar_" + tag + "_manifest",
                    "sha256": digest(storage.run(scene, manifest["run_id"]) / "manifest.json"),
                },
                {"id": "solar_" + tag + "_data", "sha256": digest(retained)},
            ]
        )
    settings = json.loads(Path(presentation_config).read_text())
    for key in ["title", "description", "limits", "presentation", "focus"]:
        if key in settings:
            config[key] = settings[key]
    if "temp" in config["layers"]:
        config["layers"]["temp"]["own_clock"] = True
    inputs.append({"id": "presentation_config", "sha256": digest(Path(presentation_config))})
    target.mkdir(parents=True)
    data = target / "data"
    shutil.copytree(source, data, ignore=shutil.ignore_patterns("web"))
    write(data / "scene.json", config)
    revision = snapshot_sources(storage.root, target / "provenance/source_snapshot.tar.gz")
    shutil.copy2(presentation_config, target / "provenance/presentation_config.json")
    artifacts = [
        {
            "id": "source_snapshot",
            "asset": "provenance/source_snapshot.tar.gz",
            "sha256": digest(target / "provenance/source_snapshot.tar.gz"),
            "media_type": "application/gzip",
        }
    ]
    artifacts.append(
        {
            "id": "presentation_configuration",
            "asset": "provenance/presentation_config.json",
            "sha256": digest(target / "provenance/presentation_config.json"),
            "media_type": "application/json",
        }
    )
    model_path = "data/" + config["model"]["url"]
    for index, path in enumerate(sorted(data.rglob("*"))):
        if not path.is_file() or path.relative_to(target).as_posix() == model_path:
            continue
        relative = path.relative_to(target).as_posix()
        artifacts.append(
            {
                "id": "city_scene"
                if relative == "data/scene.json"
                else f"presentation_asset_{index}",
                "asset": relative,
                "sha256": digest(path),
                "media_type": "application/octet-stream",
            }
        )
    manifest = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "run_id": run_id,
        "simulation": "city_presentation",
        "status": "complete",
        "created_at": datetime.now(UTC).isoformat(),
        "provenance": {
            "code_revision": revision,
            "dirty": True,
            "parameters": {
                "source_view": source_view,
                "source_runs": [r["run_id"] for r in runs.values()],
                "renderer": "Existing legacy/viewer/3d; raw NPY data, continuous planes and velocity-driven trails",
                "new_simulation": False,
                "recorded_times_preserved": True,
            },
            "inputs": inputs,
        },
        "spatial": by_kind["geometry"]["spatial"],
        "time": {"unit": "s", "samples": []},
        "layers": [
            {
                "id": "geometry",
                "kind": "mesh",
                "format": "glb",
                "asset": model_path,
                "sampling": "static",
                "encoding": {"coordinate_frame": "glTF-y-up"},
                "display": {"widget": "mesh", "capabilities": ["pick", "opacity"]},
            }
        ],
        "artifacts": artifacts,
    }
    write(target / "manifest.json", manifest)
    validate(target / "manifest.json")
    return promote(storage, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene")
    parser.add_argument("--source-view", required=True)
    parser.add_argument("--legacy-export", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--presentation-config", type=Path, required=True)
    args = parser.parse_args()
    print(
        package(
            Storage.load(),
            args.scene,
            args.source_view,
            args.legacy_export,
            args.run_id,
            args.presentation_config,
        )
    )


if __name__ == "__main__":
    main()
