"""Exercise CLI geometry, protocol export and immutable retention in isolated storage."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from e2e_fixture import create_workspace
from check_browser import chrome_path, viewer_server

ROOT = Path(__file__).resolve().parents[1]


def run_cli(workspace, output, *args, expected=0):
    env = dict(os.environ)
    for name in ("PYTHONPATH", "P4D_ROOT", "UWM_ROOT"):
        env.pop(name, None)
    command = [sys.executable, "-m", "common.cli", "--root", str(workspace), *map(str, args)]
    with (output / "pipeline.log").open("a") as log:
        log.write("\n$ " + " ".join(command) + "\n")
        log.flush()
        result = subprocess.run(
            command, cwd=workspace, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=90
        )
    if result.returncode != expected:
        raise RuntimeError(
            f"CLI {args[0]} exited {result.returncode}, expected {expected}; "
            f"see {output / 'pipeline.log'}"
        )


def file_hashes(directory):
    return {
        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob("*")
        if p.is_file()
    }


def check_pipeline(base, output):
    workspace = create_workspace(base)
    run_cli(workspace, output, "run", "pipeline.json", "--run-id", "e2e_smoke", "--retain")
    trial = base / "scratch/south_ken/pipeline/e2e_smoke"
    status = json.loads((trial / "pipeline_status.json").read_text())
    if not status["complete"] or any(
        status["stages"].get(stage, {}).get("status") != "done"
        for stage in ("geometry", "visualize")
    ):
        raise RuntimeError("The pipeline must complete every requested stage without skips")
    footprint = np.load(trial / "geometry/voxel_1m/footprint_1m_yx.npy")
    height = np.load(trial / "geometry/voxel_1m/height_m.npy")
    if int(footprint.sum()) != 64 or not np.all(height[footprint] == 3):
        raise RuntimeError("Geometry rasterization changed the known 8 x 8 m roof")
    retained = base / "data/project/south_ken/runs/e2e_smoke_geometry"
    run_cli(workspace, output, "validate", retained / "manifest.json")
    view = workspace / "project/south_ken/views/run_e2e_smoke.json"
    if json.loads(view.read_text())["runs"] != ["e2e_smoke_geometry"]:
        raise RuntimeError("Retained view references the wrong run")
    catalog = json.loads((workspace / "project/index.json").read_text())
    if catalog["default"] != "south_ken" or "run_e2e_smoke" not in catalog["scenes"][0]["views"]:
        raise RuntimeError("Retained scene was not registered")
    before = file_hashes(retained) | {"view": hashlib.sha256(view.read_bytes()).hexdigest()}
    run_cli(workspace, output, "retain", trial / "protocol", expected=1)
    after = file_hashes(retained) | {"view": hashlib.sha256(view.read_bytes()).hexdigest()}
    if after != before:
        raise RuntimeError("Duplicate retention modified the completed run or view")
    shutil.rmtree(base / "scratch")
    run_cli(workspace, output, "validate", retained / "manifest.json")
    return workspace


def retain_binary_fixture(base, workspace, output):
    source = base / "binary-bundle"
    run = source / "synthetic_masked_grid"
    shutil.copytree(ROOT / "examples/contract-v1.1", run)
    manifest = json.loads((run / "manifest.json").read_text())
    layer = manifest["layers"][0]
    frames = np.concatenate([np.load(run / name) for name in layer["encoding"]["frame_assets"]])
    np.save(run / "flow.npy", frames)
    full = json.loads(json.dumps(layer))
    full.update(id="flow_full", format="npy", asset="flow.npy")
    full["encoding"].pop("frame_assets")
    manifest["layers"].append(full)
    (run / "manifest.json").write_text(json.dumps(manifest))
    project = json.loads((workspace / "project/south_ken/project.json").read_text())
    (source / "bundle.json").write_text(
        json.dumps(
            {
                "scene_id": "south_ken",
                "view_id": "binary_check",
                "project": project,
                "runs": [manifest["run_id"]],
                "view": {
                    "schema_version": "1.1.0",
                    "scene_id": "south_ken",
                    "title": "E2E binary data",
                    "time_alignment": "relative",
                    "runs": [manifest["run_id"]],
                    "layers": [
                        {"run_id": manifest["run_id"], "layer_id": item["id"], "visible": True}
                        for item in manifest["layers"]
                    ],
                },
            }
        )
    )
    run_cli(workspace, output, "retain", source)
    mask = np.load(run / "mask.npy")
    heights = np.load(run / "height.npy")
    indices = np.flatnonzero(mask.ravel() == 0)
    expected = {
        "indices": indices.tolist(),
        "positions": [
            [float(i % 5 + 0.5), float(i // 5 + 0.5), float(1 + heights.ravel()[i])]
            for i in indices
        ],
        "values": ((frames[0] + frames[1]) / 2).reshape(3, -1)[:, indices].T.tolist(),
    }
    (output / "binary-expected.json").write_text(json.dumps(expected))
    shutil.rmtree(source)


def check_browser(workspace, output):
    chrome = chrome_path()
    with viewer_server(workspace, output) as url:
        env = dict(os.environ, CHROME_PATH=chrome, UWM_BROWSER_OUTPUT=str(output))
        for script, target in (
            (
                "browser_contract.cjs",
                "src/visualization/viewer/?manifest=/examples/contract-v1/manifest.json",
            ),
            ("browser_e2e.cjs", "src/visualization/viewer/?scene=south_ken&view=run_e2e_smoke"),
        ):
            env["UWM_VIEWER_URL"] = url + target
            env["UWM_BROWSER_OUTPUT"] = str(
                output / "json" if script == "browser_contract.cjs" else output
            )
            subprocess.run(
                ["node", str(ROOT / "tests" / script)], cwd=ROOT, env=env, check=True, timeout=60
            )


def main():
    output = ROOT / "cache/framework/e2e"
    output.mkdir(parents=True, exist_ok=True)
    (output / "pipeline.log").write_text("")
    started = time.monotonic()
    report = {"passed": False}
    try:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = check_pipeline(base, output)
            retain_binary_fixture(base, workspace, output)
            check_browser(workspace, output)
        report["passed"] = True
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        report["seconds"] = round(time.monotonic() - started, 3)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
