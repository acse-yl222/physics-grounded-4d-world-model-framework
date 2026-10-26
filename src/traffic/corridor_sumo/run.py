"""End-to-end SUMO traffic run for an Overture-based scene.

network (Overture -> plain XML -> netconvert) -> demand (cached TfL buses when
present; synthetic randomTrips cars/taxis and, without TfL, synthetic buses) ->
headless SUMO with FCD -> protocol v1.1 bundle + viewer binary, all under
``cache/<scene>/traffic_sumo/<run_id>/``.

  PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor
  p4d retain cache/imperial_corridor/traffic_sumo/<run_id>/bundle
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import secrets
import shutil
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from common.contract import validate
from common.provenance import snapshot_sources
from common.storage import Storage

from . import demand, export, network, simulate, sumo_env, tfl

SIMULATION = "traffic_sumo"
FETCH_OVERTURE = Path(__file__).resolve().parents[2] / "urban_geometry/image_to_threejs"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def log(message: str) -> None:
    print(message, flush=True)


def source_dirty(root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", "src", "schemas"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode != 0 or bool(result.stdout.strip())


def ensure_overture(config_path: Path, overture: Path) -> dict:
    index_path = overture / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {"layers": {}}
    if not {"segments", "connectors"} <= set(index["layers"]):
        log(f"Overture transport layers missing; fetching into {overture}")
        cmd = [sys.executable, FETCH_OVERTURE / "fetch_overture.py", config_path, overture]
        subprocess.run([*map(str, cmd), "--layers", "segments", "connectors"], check=True)
        index = json.loads(index_path.read_text())
    return index


def bus_demand(
    args, storage, scene, cfg, geo, net_path, out, vtypes, sim
) -> tuple[list, list, dict]:
    """TfL buses from the cache when available, otherwise synthetic buses."""
    tcfg = cfg.get("tfl", {})
    cache = storage.assets(scene, "input") / "tfl"
    info: dict = {"cache": str(cache)}
    if tcfg.get("enabled", True) and args.tfl:
        if tfl.load_cache(cache) is None and tcfg.get("fetch_if_missing", True):
            try:
                log("TfL cache absent; trying api.tfl.gov.uk ...")
                tfl.fetch(cache, geo["origin"], geo["domain_m"] / 2, tcfg, log=log)
            except Exception as exc:  # noqa: BLE001 - any network failure means no TfL data
                log(f"TfL download unavailable ({type(exc).__name__}: {exc}); skipping TfL buses")
                info["fetch_error"] = f"{type(exc).__name__}: {exc}"
        provenance = tfl.load_cache(cache)
        if provenance is not None:
            built = tfl.build_sumo(
                cache,
                net_path,
                out,
                {"origin": geo["origin"], "half_m": geo["domain_m"] / 2},
                tcfg,
                sim,
                log=log,
            )
            info.update(
                source="tfl",
                synthetic=False,
                fetched_at=provenance.get("fetched_at"),
                cache_sha256=tfl.cache_digest(cache),
                report=built["report"],
            )
            if built["report"]["lines"]:
                return [built["routes"]], [built["additional"]], info
            log("TfL cache present but no line could be matched; using synthetic buses")
        else:
            log(f"No TfL cache at {cache}; TfL buses skipped")
    else:
        log("TfL buses disabled")
    routes, meta = demand.synthetic_buses(
        net_path,
        out,
        cfg["demand"]["synthetic_bus"],
        sim,
        cfg["demand"]["seed"] + 2,
        vtypes,
        out / "demand.log",
    )
    info.update(source="synthetic", **meta)
    return [routes], [], info


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("scene")
    p.add_argument("--run-id")
    p.add_argument("--view", default="traffic_sumo", help="view id written to bundle.json")
    p.add_argument("--no-tfl", dest="tfl", action="store_false", help="skip TfL buses")
    args = p.parse_args(argv)

    storage = Storage.load()
    meta = storage.metadata(args.scene)
    config_path = meta / "configs/traffic_sumo.json"
    cfg = json.loads(config_path.read_text())
    scene = cfg["scene_id"]
    geo_path = meta / cfg.get("geometry_config", "configs/image_to_threejs.json")
    geo = json.loads(geo_path.read_text())
    sim = cfg["simulation"]
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ_") + secrets.token_hex(3)
    work = storage.scratch(scene, SIMULATION, run_id)
    if work.exists():
        raise FileExistsError(work)
    work.mkdir(parents=True)
    log(f"workspace: {work}")
    log(f"SUMO {sumo_env.version()} at {sumo_env.sumo_home()}")

    # 1. network
    overture = storage.assets(scene, "input") / cfg.get("overture_dir", "overture_transport")
    index = ensure_overture(geo_path, overture)
    built = network.build_network(overture, work / "net", cfg["network"])
    net_path, net_stats = built["net"], built["stats"]
    log(f"network: {built['net']}")
    log(
        f"  {net_stats['edges']} edges, {net_stats['junctions']} junctions, "
        f"{net_stats['traffic_lights']} traffic lights, {net_stats['edge_length_km']} km"
    )

    # 2. demand
    out = work / "demand"
    out.mkdir()
    vtypes = demand.write_vtypes(out)
    dcfg, seed = cfg["demand"], cfg["demand"]["seed"]
    routes, additional = [], [vtypes]
    for offset, (name, vclass) in enumerate((("car", "passenger"), ("taxi", "taxi"))):
        c = dcfg[name]
        routes.append(
            demand.random_trips(
                net_path,
                out,
                name,
                name,
                vclass,
                sim["begin_s"],
                sim["end_s"],
                c["period_s"],
                seed + offset,
                vtypes,
                fringe_factor=c.get("fringe_factor", 1),
                min_distance=c.get("min_distance_m", 0),
                log=out / "demand.log",
            )
        )
    bus_routes, bus_additional, bus_info = bus_demand(
        args, storage, scene, cfg, geo, net_path, out, vtypes, sim
    )
    routes += bus_routes
    additional += bus_additional
    counts = {r.stem.split(".")[0]: demand.count_vehicles(r) for r in routes[:2]}
    log(
        f"demand: {out} ({counts['car']} cars, {counts['taxi']} taxis, buses: {bus_info['source']})"
    )

    # 3. simulation
    sim_dir = work / "sim"
    sim_dir.mkdir()
    result = simulate.run_sumo(net_path, routes, additional, sim_dir, sim)
    log(f"fcd: {result['fcd']}")
    stats = result["statistics"]

    # 4. exports
    rec = export.parse_fcd(result["fcd"], sim["record_from_s"], sim["end_s"])
    ecfg = cfg["export"]
    max_records = (ecfg["max_bin_bytes"] - 4 * len(rec.frames)) // export.RECORD.itemsize
    kept = export.select(rec, max_records, ecfg.get("max_concurrent_vehicles"))
    synthetic = True  # cars and taxis are always synthetic randomTrips demand
    bundle = work / "bundle"
    target = bundle / run_id
    data = target / "data"
    data.mkdir(parents=True)
    bin_path = data / "traffic.bin"
    size = export.write_binary(kept, bin_path)
    if size >= ecfg["max_bin_bytes"]:
        raise RuntimeError(f"traffic.bin is {size} bytes, over the budget")
    heading = export.heading_check(kept)
    recorded = {
        "window_s": [rec.times[0], rec.times[-1]],
        "frames": len(rec.times),
        "vehicles_simulated_in_window": len(rec.vehicles),
        "vehicles_exported": len(kept.vehicles),
        "exported_by_type": {
            t: sum(v["type"] == t for v in kept.vehicles) for t in export.VEHICLE_TYPES
        },
        "peak_concurrent_simulated": max(map(len, rec.frames)),
        "peak_concurrent_exported": max(map(len, kept.frames)),
        "selection": "whole trajectories only; all buses, then cars/taxis in SHA-1 order of "
        f"their ids until {ecfg['max_bin_bytes']} bytes of traffic.bin or "
        f"{ecfg.get('max_concurrent_vehicles')} concurrent vehicles; omitted vehicles are "
        "absent from every frame (no partial or invented samples)",
        "heading_vs_motion": heading,
    }

    # Reproducibility artefacts: compressed network and the exact demand/configuration.
    sumo_dir = target / "sumo"
    sumo_dir.mkdir()
    with net_path.open("rb") as src, gzip.open(sumo_dir / "net.net.xml.gz", "wb") as dst:
        shutil.copyfileobj(src, dst)
    with tarfile.open(sumo_dir / "demand.tar.gz", "w:gz") as tar:
        for path in [*routes, *additional, result["config"]]:
            tar.add(path, arcname=path.name)
    shutil.copy2(config_path, target / "traffic_sumo.json")
    snapshot = target / "provenance/source_snapshot.tar.gz"
    revision = snapshot_sources(storage.root, snapshot)

    demand_hashes = {p.name: digest(p) for p in [*routes, *additional]}
    provenance_params = {
        "synthetic": synthetic,
        "demand": {
            "car": {
                "source": "synthetic",
                "generator": "randomTrips.py",
                "vehicles": counts["car"],
                **dcfg["car"],
            },
            "taxi": {
                "source": "synthetic",
                "generator": "randomTrips.py",
                "vehicles": counts["taxi"],
                **dcfg["taxi"],
            },
            "bus": bus_info,
            "note": "Car and taxi demand is synthetic (random origin/destination pairs, fringe "
            "weighted, routed with duarouter); it is not derived from traffic counts.",
        },
        "sumo_version": sumo_env.version(),
        "network": {k: v for k, v in net_stats.items() if k != "bbox_xy"},
        "network_assumptions": "Lanes and default speeds by Overture class (speed_limits when "
        "tagged); one-way and bus-only from access_restrictions; signals at junctions of >= "
        f"{cfg['network'].get('tls_min_major', 3)} tertiary-or-higher road pieces plus netconvert "
        "TLS guessing (Overture has no signal data); left-hand traffic.",
        "net_sha256": digest(net_path),
        "demand_sha256": demand_hashes,
        "simulation": {**sim, "statistics": stats},
        "recorded": recorded,
        "config": cfg,
        "coordinates": "SUMO x,y == scene ENU metres (netconvert offset normalisation "
        "disabled; verified via location offset and node coordinates); z = 0 (flat ground)",
    }
    export.write_trajectory_frames(kept, data / "trajectories.json")
    export.write_traffic_json(
        kept,
        data / "traffic.json",
        bin_path,
        synthetic,
        {
            "run_id": run_id,
            "scene_id": scene,
            "simulation": SIMULATION,
            "synthetic": synthetic,
            "demand": {
                k: v.get("source")
                for k, v in provenance_params["demand"].items()
                if isinstance(v, dict)
            },
            "sumo_version": provenance_params["sumo_version"],
            "net_sha256": provenance_params["net_sha256"],
            "selection": recorded["selection"],
            "vehicles_simulated_in_window": recorded["vehicles_simulated_in_window"],
        },
    )
    half = geo["domain_m"] / 2
    spatial = {
        "frame": "ENU",
        "units": "m",
        "origin": {
            **geo["origin"],
            "height_m": 0,
            "vertical_datum": "Flat ground at local zero; no terrain model applied",
        },
        "bounds_m": {"min": [-half, -half, 0], "max": [half, half, 5]},
    }
    inputs = [
        {"id": f"overture_{k}", "sha256": v["sha256"]}
        for k, v in sorted(index["layers"].items())
        if k in ("segments", "connectors")
    ]
    inputs.append({"id": "traffic_sumo_config", "sha256": digest(config_path)})
    if bus_info.get("cache_sha256"):
        inputs.append({"id": "tfl_cache", "sha256": bus_info["cache_sha256"]})
    artifacts = [
        ("source_snapshot", "provenance/source_snapshot.tar.gz", "application/gzip"),
        ("viewer_index", "data/traffic.json", "application/json"),
        ("viewer_binary", "data/traffic.bin", "application/octet-stream"),
        ("sumo_network", "sumo/net.net.xml.gz", "application/gzip"),
        ("sumo_demand", "sumo/demand.tar.gz", "application/gzip"),
        ("config", "traffic_sumo.json", "application/json"),
    ]
    manifest = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "simulation": SIMULATION,
        "run_id": run_id,
        "status": "complete",
        "created_at": datetime.now(UTC).isoformat(),
        "provenance": {
            "code_revision": revision,
            "dirty": source_dirty(storage.root),
            "parameters": provenance_params,
            "inputs": inputs,
        },
        "spatial": spatial,
        "time": {"unit": "s", "samples": kept.times},
        "layers": [
            {
                "id": "traffic",
                "kind": "trajectories",
                "format": "trajectory_frames",
                "asset": "data/trajectories.json",
                "sampling": "linear",
                "display": {"widget": "trajectories", "capabilities": ["pick", "opacity"]},
            }
        ],
        "artifacts": [
            {"id": i, "asset": a, "sha256": digest(target / a), "media_type": m}
            for i, a, m in artifacts
        ],
    }
    manifest_path = target / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    validate(manifest_path)

    project = json.loads((meta / "project.json").read_text())
    view = {
        "schema_version": "1.1.0",
        "scene_id": scene,
        "title": "SUMO traffic (synthetic demand)" if synthetic else "SUMO traffic",
        "time_alignment": "relative",
        "runs": [run_id],
        "layers": [{"run_id": run_id, "layer_id": "traffic", "visible": True}],
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
    summary = {
        "workspace": str(work),
        "network": str(net_path),
        "fcd": str(result["fcd"]),
        "manifest": str(manifest_path),
        "trajectories": str(data / "trajectories.json"),
        "traffic_json": str(data / "traffic.json"),
        "traffic_bin": str(bin_path),
        "traffic_bin_bytes": size,
        "network_stats": {k: net_stats[k] for k in ("edges", "junctions", "traffic_lights")},
        "vehicles": stats.get("vehicles"),
        "teleports": stats.get("teleports"),
        "recorded": {k: v for k, v in recorded.items() if k != "selection"},
        "buses": bus_info["source"],
    }
    log(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
