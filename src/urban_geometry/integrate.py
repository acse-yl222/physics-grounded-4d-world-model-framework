#!/usr/bin/env python3
"""
integrate.py — run bird simulation and MFMU UAV scheduler on shared geometry.

Sits at the project root alongside both repos.  Reads shared geometry from
geometry/, calls into both projects via subprocess (neither repo is modified),
and writes combined results to outputs/.

Expected layout:
    project_root/
    ├── geometry/
    │   ├── birds_scene.glb        ← GLB for bird voxelisation
    │   ├── stations.csv           ← station positions & roles (shared)
    │   └── requests.json          ← (optional) MFMU delivery requests
    ├── birds/                     ← bird sim repo
    │   ├── scripts/
    │   └── sim/
    ├── mfmu-uwm-integration-preview/  ← MFMU scheduler repo
    │   └── mfmu_scheduler/
    ├── integrate.py               ← this file
    └── outputs/

Prerequisites:
    - Bird sim dependencies installed (numpy, trimesh, etc.)
    - MFMU installed:  cd mfmu-uwm-integration-preview && pip install -e .
    - GLB placed in geometry/

Usage:
    python integrate.py
    python integrate.py --skip-birds          # MFMU only
    python integrate.py --skip-mfmu           # birds only
    python integrate.py --skip-voxelise       # reuse existing geo.npz
    python integrate.py --requests geometry/my_requests.json
"""

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION — edit these paths and constants to match your setup
# ═══════════════════════════════════════════════════════════════════════════════

# ── shared geometry inputs ────────────────────────────────────────────────────
GEOMETRY_DIR = "geometry"
BIRDS_GLB = os.path.join(GEOMETRY_DIR, "birds_scene.glb")  # GLB for bird voxelisation
STATIONS_CSV = os.path.join(GEOMETRY_DIR, "stations.csv")  # station positions + roles

# ── repo locations (relative to this script) ──────────────────────────────────
BIRDS_DIR = "birds"
MFMU_DIR = "mfmu-uwm-integration-preview"

# ── output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "outputs"

# ── bird sim ──────────────────────────────────────────────────────────────────
# The voxelised geometry is written here, relative to the birds repo root.
# config.py in the bird sim must have:  geometry_path = "data/geometry.npz"
# (one-line edit in birds/sim/config.py)
BIRDS_GEO_RELPATH = "data/geometry.npz"

# ── MFMU UAV scheduler constants ─────────────────────────────────────────────
# These control how stations.csv is turned into the MFMU scenario dict.
# Values from build_city_sk_authority_v2.py (the frozen scheduler geometry).
MFMU_SPEED_MPS = 15.0  # UAV cruise speed in m/s
MFMU_SLOT_DT_S = 10  # seconds per scheduler time slot
MFMU_STEP_M = MFMU_SPEED_MPS * MFMU_SLOT_DT_S  # metres per slot (150 m)
MFMU_HORIZON = 240  # total time slots (from INTERFACE.md)
MFMU_N_UAV = 10  # number of UAVs
MFMU_BATTERY = {  # frozen homogeneous battery model
    "max_soc": 75,
    "initial_soc": 75,
    "energy_per_flight_slot": 4,
    "reserve": 0,
    "swap_duration_slots": 2,
    "swap_completion_soc": 75,
}

# ── coordinate alignment ─────────────────────────────────────────────────────
# If the station coordinates and bird sim coordinates are in different frames,
# set an offset here.  The bird sim uses metres with origin at
# config.scaled_grid_origin (default -512, -512, 0).
# For now we assume both use the same coordinate system.
COORD_OFFSET_X = 0.0
COORD_OFFSET_Y = 0.0

# ── traffic model ─────────────────────────────────────────────────────────────
# The traffic model generates road networks procedurally for training/eval.
# It does NOT consume the shared GLB or stations.csv.
# The London verification pipeline (traffic/verification/) uses roads.geojson
# but is separate from the main train/eval loop.
# A pre-trained model must exist in traffic/train/ before running evaluation.
# Train one with:  cd traffic && python train.py
TRAFFIC_DIR = "traffic"


# ═══════════════════════════════════════════════════════════════════════════════
# STATIONS — read stations.csv and build distance / travel-time matrices
# ═══════════════════════════════════════════════════════════════════════════════


def read_stations(csv_path):
    """Read stations.csv and return a list of dicts.

    Expected columns: source_id, scene_object_id, role, name, x_m, y_m, z_roof_m
    Role values: HUB, COLLECTION, DROPOFF
    """
    with open(csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"stations.csv is empty: {csv_path}")

    stations = []
    for r in rows:
        stations.append(
            {
                "source_id": r["source_id"],
                "name": r["name"],
                "role": r["role"].strip().upper(),  # HUB / COLLECTION / DROPOFF
                "x_m": float(r["x_m"]),
                "y_m": float(r["y_m"]),
                "z_roof_m": float(r["z_roof_m"]),
            }
        )
    return stations


def compute_matrices(stations, speed_mps, slot_dt_s):
    """Compute Euclidean distance (km) and travel-time (slots) matrices.

    Travel time = ceil(distance / step_distance), minimum 1 for off-diagonal.
    This is the same arithmetic as build_city_sk_authority_v2.py without the
    SHA-verification gates.
    """
    n = len(stations)
    step_m = speed_mps * slot_dt_s

    # pairwise Euclidean distance in metres (horizontal only, matching authority)
    dist_m = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            if i != j:
                dx = stations[i]["x_m"] - stations[j]["x_m"]
                dy = stations[i]["y_m"] - stations[j]["y_m"]
                dist_m[i, j] = math.hypot(dx, dy)

    # travel time in slots: ceil(dist / step), min 1 off-diagonal
    T = np.zeros((n, n), dtype=int)
    for i in range(n):
        for j in range(n):
            if i != j:
                T[i, j] = max(1, math.ceil(dist_m[i, j] / step_m))

    # distance in km for the MFMU cost matrix
    dist_km = dist_m / 1000.0

    return dist_km, T


# ═══════════════════════════════════════════════════════════════════════════════
# MFMU SCENARIO BUILDER
# ═══════════════════════════════════════════════════════════════════════════════


def build_mfmu_scenario(stations, dist_km, T_slots, requests=None):
    """Assemble the JSON scenario dict that mfmu_scheduler.schedule() expects.

    If no requests are provided, generates synthetic COLLECTION→DROPOFF
    deliveries evenly spaced across the time horizon.
    """
    n = len(stations)

    # ── stations ──────────────────────────────────────────────────────────────
    # MFMU uses role "hub" or "station" (not COLLECTION/DROPOFF).
    mfmu_stations = []
    for s in stations:
        role = "hub" if s["role"] == "HUB" else "station"
        mfmu_stations.append(
            {
                "id": s["name"],
                "x": s["x_m"] + COORD_OFFSET_X,
                "y": s["y_m"] + COORD_OFFSET_Y,
                "role": role,
            }
        )

    # ── matrices (as nested Python lists for JSON) ────────────────────────────
    travel_time_list = T_slots.tolist()
    distance_km_list = dist_km.tolist()

    # ── fleet — all UAVs start at the first HUB ──────────────────────────────
    hub_ids = [s["name"] for s in stations if s["role"] == "HUB"]
    if not hub_ids:
        raise RuntimeError("No HUB station found in stations.csv")
    start_hub = hub_ids[0]

    fleet = []
    for i in range(MFMU_N_UAV):
        fleet.append(
            {
                "id": f"uav-{i+1:02d}",
                "start_station": start_hub,
                "initial_soc": MFMU_BATTERY["initial_soc"],
            }
        )

    # ── requests ──────────────────────────────────────────────────────────────
    if requests is None:
        requests = generate_synthetic_requests(stations, T_slots)

    # ── assemble ──────────────────────────────────────────────────────────────
    scenario = {
        "schema_version": "mfmu.integration.v1",
        "horizon_slots": MFMU_HORIZON,
        "stations": mfmu_stations,
        "travel_time_slots": travel_time_list,
        "distance_km": distance_km_list,
        "fleet": fleet,
        "battery": MFMU_BATTERY,
        "requests": requests,
    }
    return scenario


def generate_synthetic_requests(stations, T_slots):
    """Create evenly-spaced COLLECTION→DROPOFF requests across the horizon.

    This is a placeholder so the script works out of the box.  Replace with
    a real requests file via --requests for meaningful scheduling.

    Each COLLECTION station is paired with each DROPOFF station once.
    Requests are spread across the first 80% of the horizon to leave room
    for travel and service.
    """
    collections = [(i, s) for i, s in enumerate(stations) if s["role"] == "COLLECTION"]
    dropoffs = [(i, s) for i, s in enumerate(stations) if s["role"] == "DROPOFF"]

    if not collections or not dropoffs:
        print(
            "[WARN] No COLLECTION or DROPOFF stations — generating empty request list."
        )
        print(
            "       Provide a requests file via --requests if your station roles differ."
        )
        return []

    pairs = [(ci, cs, di, ds) for ci, cs in collections for di, ds in dropoffs]
    n_req = len(pairs)

    # spread collection slots across the usable portion of the horizon
    usable = int(MFMU_HORIZON * 0.8)
    spacing = max(1, usable // max(n_req, 1))

    requests = []
    for idx, (ci, cs, di, ds) in enumerate(pairs):
        c_slot = 10 + idx * spacing  # collection time slot
        travel = int(T_slots[ci, di])  # slots to fly collection→dropoff
        d_start = c_slot + travel  # first eligible dropoff slot
        d_end = d_start + 4  # 5-slot window (MFMU convention)

        if d_end >= MFMU_HORIZON:
            print(
                f"[WARN] Request {idx+1} dropoff window {d_end} exceeds horizon {MFMU_HORIZON}, skipping"
            )
            continue

        requests.append(
            {
                "id": f"request-{idx+1:03d}",
                "collection_station": cs["name"],
                "dropoff_station": ds["name"],
                "collection_slot": c_slot,
                "dropoff_service_window": [d_start, d_end],
            }
        )

    print(
        f"[mfmu] Generated {len(requests)} synthetic requests from "
        f"{len(collections)} collection × {len(dropoffs)} dropoff stations"
    )
    return requests


# ═══════════════════════════════════════════════════════════════════════════════
# RUNNERS — subprocess calls to each project
# ═══════════════════════════════════════════════════════════════════════════════


def run_voxelise(glb_path, out_path):
    """Run glb_to_geo.py to produce the voxel geometry .npz."""
    script = os.path.join(BIRDS_DIR, "scripts", "glb_to_geo.py")
    if not os.path.isfile(script):
        raise RuntimeError(f"Bird voxeliser not found: {script}")
    if not os.path.isfile(glb_path):
        raise RuntimeError(
            f"GLB not found: {glb_path}\n"
            f"Place your GLB in {GEOMETRY_DIR}/ and update BIRDS_GLB at the top of integrate.py"
        )

    # absolute paths so they resolve correctly regardless of subprocess cwd
    cmd = [
        sys.executable,
        os.path.abspath(script),
        os.path.abspath(glb_path),
        "-o",
        os.path.abspath(out_path),
    ]
    print(f"\n{'='*60}")
    print(f"[voxelise] {' '.join(cmd)}")
    print(f"{'='*60}")
    subprocess.run(cmd, check=True)
    print(f"[voxelise] wrote {out_path}")


def run_birds(output_path):
    """Run the bird flock simulation via subprocess."""
    script = os.path.join(BIRDS_DIR, "scripts", "run_sim.py")
    if not os.path.isfile(script):
        raise RuntimeError(f"Bird sim not found: {script}")

    # run from inside the birds directory so that relative paths in config.py
    # (geometry_path, scaled_wind_path, etc.) resolve correctly
    cmd = [
        sys.executable,
        os.path.abspath(script),
        "--output",
        os.path.abspath(output_path),
    ]
    print(f"\n{'='*60}")
    print(f"[birds] {' '.join(cmd)}")
    print(f"[birds] cwd = {os.path.abspath(BIRDS_DIR)}")
    print(f"{'='*60}")
    subprocess.run(cmd, check=True, cwd=BIRDS_DIR)
    print(f"[birds] wrote {output_path}")


def run_mfmu(scenario_path, output_path):
    """Run the MFMU scheduler via its CLI entry point.

    Requires prior:  cd mfmu-uwm-integration-preview && pip install -e .
    which registers the `mfmu-schedule` command.
    """
    cmd = ["mfmu-schedule", scenario_path, "--output", output_path]
    print(f"\n{'='*60}")
    print(f"[mfmu] {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        # fall back to calling as a Python module (in case CLI entry point
        # isn't on PATH but the package is importable)
        print(
            "[mfmu] `mfmu-schedule` not on PATH, trying `python -m mfmu_scheduler` ..."
        )
        cmd = [
            sys.executable,
            "-m",
            "mfmu_scheduler",
            scenario_path,
            "--output",
            output_path,
        ]
        subprocess.run(cmd, check=True)

    print(f"[mfmu] wrote {output_path}")


def find_latest_traffic_model():
    """Find the most recent best_model_*.pt in traffic/train/."""
    import glob

    pattern = os.path.join(TRAFFIC_DIR, "train", "best_model_*.pt")
    models = sorted(glob.glob(pattern), key=os.path.getmtime)
    if not models:
        return None
    # extract the date portion: best_model_MM-DD_HH-MM-SS.pt → MM-DD_HH-MM-SS
    basename = os.path.basename(models[-1])
    return basename.replace("best_model_", "").replace(".pt", "")


def run_traffic_train():
    """Train the traffic model (slow — runs 250 epochs by default)."""
    script = os.path.join(TRAFFIC_DIR, "train.py")
    if not os.path.isfile(script):
        raise RuntimeError(f"Traffic train.py not found: {script}")

    cmd = [sys.executable, os.path.abspath(script)]
    print(f"\n{'='*60}")
    print(f"[traffic] training: {' '.join(cmd)}")
    print(f"[traffic] cwd = {os.path.abspath(TRAFFIC_DIR)}")
    print(f"{'='*60}")
    subprocess.run(cmd, check=True, cwd=TRAFFIC_DIR)


def run_traffic_eval(model_date, output_dir):
    """Run traffic model evaluation and save metrics.

    evaluate.py prints metrics (ADE, FDE, counterfactual results) to stdout
    via its log=print pattern.  We capture stdout and save it alongside
    copies of the model weights and eval log for provenance.
    """
    script = os.path.join(TRAFFIC_DIR, "evaluate.py")
    if not os.path.isfile(script):
        raise RuntimeError(f"Traffic evaluate.py not found: {script}")

    cmd = [sys.executable, os.path.abspath(script), "--model", model_date]
    print(f"\n{'='*60}")
    print(f"[traffic] evaluating model {model_date}")
    print(f"[traffic] {' '.join(cmd)}")
    print(f"[traffic] cwd = {os.path.abspath(TRAFFIC_DIR)}")
    print(f"{'='*60}")
    result = subprocess.run(
        cmd, check=True, cwd=TRAFFIC_DIR, capture_output=True, text=True
    )

    # save the evaluation output (metrics printed to stdout)
    eval_out = os.path.join(output_dir, "eval_output.txt")
    with open(eval_out, "w") as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- stderr ---\n")
            f.write(result.stderr)
    print(result.stdout)  # also show in terminal
    print(f"[traffic] evaluation output saved to {eval_out}")

    # copy model weights and eval log for provenance
    import shutil

    for filename in [f"best_model_{model_date}.pt", f"eval_log_{model_date}.txt"]:
        src = os.path.join(TRAFFIC_DIR, "train", filename)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(output_dir, filename))

    return eval_out


# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST — tie the outputs together
# ═══════════════════════════════════════════════════════════════════════════════


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(out_dir, parts):
    """Write a manifest.json linking all outputs for downstream consumption.

    `parts` is a dict of model_name → {config: ..., output_path: ...}.
    Extensible: future urban models just add another key.
    """
    manifest = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "integrator": "integrate.py",
        "models": {},
    }

    for name, info in parts.items():
        entry = {"status": info.get("status", "ok")}
        if "output_path" in info and os.path.isfile(info["output_path"]):
            entry["output_file"] = os.path.relpath(info["output_path"], out_dir)
            entry["sha256"] = file_sha256(info["output_path"])
        if "config_summary" in info:
            entry["config_summary"] = info["config_summary"]
        if "note" in info:
            entry["note"] = info["note"]
        manifest["models"][name] = entry

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)
    print(f"\n[manifest] wrote {manifest_path}")
    return manifest_path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Run bird sim and MFMU UAV scheduler on shared geometry"
    )
    parser.add_argument(
        "--skip-birds", action="store_true", help="skip the bird simulation"
    )
    parser.add_argument(
        "--skip-mfmu", action="store_true", help="skip the MFMU scheduler"
    )
    parser.add_argument(
        "--skip-voxelise",
        action="store_true",
        help="skip GLB voxelisation (reuse existing geo.npz)",
    )
    parser.add_argument(
        "--requests",
        type=str,
        default=None,
        help="path to a JSON file with MFMU delivery requests "
        "(default: generate synthetic requests from station roles)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=OUTPUT_DIR,
        help=f"output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--skip-traffic", action="store_true", help="skip the traffic model evaluation"
    )
    parser.add_argument(
        "--traffic-model",
        type=str,
        default=None,
        help="date string of a trained traffic model "
        "(e.g. 08-16_07-31-30).  Default: most recent "
        "best_model_*.pt in traffic/train/",
    )
    parser.add_argument(
        "--train-traffic",
        action="store_true",
        help="train the traffic model before evaluating "
        "(slow — 250 epochs by default)",
    )
    args = parser.parse_args()

    out = args.output
    out_birds = os.path.join(out, "birds")
    out_mfmu = os.path.join(out, "mfmu")
    os.makedirs(out_birds, exist_ok=True)
    os.makedirs(out_mfmu, exist_ok=True)

    parts = {}  # model_name → info dict for the manifest

    # ── STEP 1: voxelise the GLB for the bird sim ─────────────────────────────
    # Produces a .npz voxel grid that the bird sim uses for obstacle avoidance
    # and wave routing.  Placed inside the birds repo so run_sim.py can find it
    # via config.geometry_path.
    #
    # IMPORTANT: set this one line in birds/sim/config.py:
    #     geometry_path: str = "data/geometry.npz"
    #
    geo_abs = os.path.join(BIRDS_DIR, BIRDS_GEO_RELPATH)
    if not args.skip_birds and not args.skip_voxelise:
        os.makedirs(os.path.dirname(geo_abs), exist_ok=True)
        run_voxelise(BIRDS_GLB, geo_abs)

    # ── STEP 2: run bird simulation ───────────────────────────────────────────
    birds_out = os.path.join(out_birds, "sim_result.npz")
    if not args.skip_birds:
        run_birds(birds_out)
        parts["birds"] = {
            "output_path": birds_out,
            "config_summary": {
                "glb": BIRDS_GLB,
                "geometry_npz": geo_abs,
            },
        }
    else:
        parts["birds"] = {"status": "skipped"}

    # ── STEP 3: build MFMU scenario from stations.csv ─────────────────────────
    # Read station positions, compute distance and travel-time matrices,
    # optionally load explicit requests or generate synthetic ones.
    if not args.skip_mfmu:
        if not os.path.isfile(STATIONS_CSV):
            raise RuntimeError(
                f"stations.csv not found: {STATIONS_CSV}\n"
                f"Place it in {GEOMETRY_DIR}/ and update STATIONS_CSV at the "
                f"top of integrate.py if needed."
            )

        stations = read_stations(STATIONS_CSV)
        print(f"\n[mfmu] Read {len(stations)} stations from {STATIONS_CSV}")
        for s in stations:
            print(
                f"       {s['name']:20s}  role={s['role']:12s}  "
                f"x={s['x_m']:.1f}  y={s['y_m']:.1f}"
            )

        dist_km, T_slots = compute_matrices(stations, MFMU_SPEED_MPS, MFMU_SLOT_DT_S)
        print(f"[mfmu] Travel-time matrix (slots):\n{T_slots}")

        # load explicit requests if provided, otherwise generate synthetic ones
        requests = None
        if args.requests:
            with open(args.requests) as f:
                requests = json.load(f)
            # if the file is a full scenario with a "requests" key, extract it
            if isinstance(requests, dict) and "requests" in requests:
                requests = requests["requests"]
            print(f"[mfmu] Loaded {len(requests)} requests from {args.requests}")

        scenario = build_mfmu_scenario(stations, dist_km, T_slots, requests)

        # write the assembled scenario so it can be inspected / rerun manually
        scenario_path = os.path.join(out_mfmu, "scenario.json")
        with open(scenario_path, "w") as f:
            json.dump(scenario, f, indent=2)
        print(f"[mfmu] Wrote scenario to {scenario_path}")

        # ── STEP 4: run the MFMU scheduler ────────────────────────────────────
        mfmu_out = os.path.join(out_mfmu, "schedule_result.json")
        run_mfmu(scenario_path, mfmu_out)

        parts["mfmu"] = {
            "output_path": mfmu_out,
            "config_summary": {
                "stations_csv": STATIONS_CSV,
                "n_stations": len(stations),
                "n_uavs": MFMU_N_UAV,
                "horizon_slots": MFMU_HORIZON,
                "speed_mps": MFMU_SPEED_MPS,
                "slot_dt_s": MFMU_SLOT_DT_S,
                "n_requests": len(scenario["requests"]),
                "requests_source": args.requests or "synthetic",
            },
        }
    else:
        parts["mfmu"] = {"status": "skipped"}

    # ── STEP 5: traffic model ─────────────────────────────────────────────────
    # Runs independently of the shared geometry — road networks are generated
    # procedurally inside generate_complex.py.  Requires a pre-trained model
    # unless --train-traffic is passed.
    out_traffic = os.path.join(out, "traffic")
    if not args.skip_traffic:
        os.makedirs(out_traffic, exist_ok=True)

        if args.train_traffic:
            run_traffic_train()

        model_date = args.traffic_model or find_latest_traffic_model()
        if model_date is None:
            print("[traffic] No trained model found in traffic/train/.")
            print("          Run with --train-traffic first, or train manually:")
            print("            cd traffic && python train.py")
            parts["traffic"] = {"status": "skipped", "note": "no trained model found"}
        else:
            eval_out = run_traffic_eval(model_date, out_traffic)
            parts["traffic"] = {
                "output_path": eval_out,
                "config_summary": {
                    "model_date": model_date,
                    "grid_size": 56,
                    "cell_size_m": 3.0,
                    "road_length_m": 168.0,
                    "geometry_source": "procedural (not from shared geometry)",
                },
            }
    else:
        parts["traffic"] = {"status": "skipped"}

    # ── STEP 6: write manifest ────────────────────────────────────────────────
    write_manifest(out, parts)

    print(f"\n{'='*60}")
    print(f"Integration complete.  Results in {out}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
