"""End-to-end SUMO traffic run for a scene.

Default (config has ``periods``): network (``network.source``: ``osm`` = OpenStreetMap
subset -> netconvert OSM importer, or ``overture`` = Overture -> plain XML -> netconvert) ->
DfT count targets per edge and period -> routeSampler-calibrated demand (+ GTFS buses
when present) -> SUMO per period with edgeData and an FCD window -> protocol v1.1 bundle
with per-edge traffic state and per-period viewer binaries.

``--synthetic``: the earlier single window with synthetic randomTrips cars/taxis and
TfL or synthetic buses. Everything is written under ``cache/<scene>/traffic_sumo/<run_id>/``.

  PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor
  PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor --reuse <run_id>
  PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor --network-only
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
import time
from datetime import UTC, datetime
from pathlib import Path

from common.contract import validate
from common.provenance import snapshot_sources
from common.storage import Storage
from urban_geometry.image_to_threejs import terrain

from . import (
    bus_status,
    calibrate,
    count_state,
    demand,
    dft,
    export,
    network,
    osm_extract,
    osm_net,
    periods,
    simulate,
    state,
    sumo_env,
    tfl,
)

SIMULATION = "traffic_sumo"
FETCH_OVERTURE = Path(__file__).resolve().parents[2] / "urban_geometry/image_to_threejs"


def z_bounds(half: float, surface) -> dict:
    """Spatial bounds; with terrain, z spans the DEM (plus vehicle height)."""
    if not surface:
        return {"min": [-half, -half, 0], "max": [half, half, 5]}
    lo, hi = float(surface.dem.min()), float(surface.road_values.max())
    return {"min": [-half, -half, int(lo // 1) - 1], "max": [half, half, int(hi // 1) + 6]}


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


def ensure_osm(storage: Storage, scene: str, cfg: dict) -> tuple[Path, dict]:
    """The scene's OSM subset (``osm_extract``), extracted when missing and allowed."""
    ocfg = cfg.get("osm", {})
    directory = storage.assets(scene, "input") / ocfg.get("dir", "osm")
    index_path, xml_path = directory / "index.json", directory / "osm.xml.gz"
    if not (index_path.is_file() and xml_path.is_file()):
        if not ocfg.get("fetch_if_missing", True):
            raise SystemExit(f"no OSM subset at {directory}; run osm_extract {scene}")
        log(f"OSM subset missing; extracting into {directory} (planet ORC on AWS Open Data)")
        osm_extract.extract(scene)
    index = json.loads(index_path.read_text())
    recorded = index["files"]["osm.xml.gz"]["sha256"]
    if digest(xml_path) != recorded:
        raise RuntimeError(f"{xml_path} does not match its index.json sha256")
    return directory, index


def build_scene_network(storage, scene, cfg, geo, geo_path, out_dir: Path) -> dict:
    """Build the configured network (``network.source``); paths, stats, inputs, report."""
    ncfg = cfg["network"]
    source = ncfg.get("source", "overture")
    half = geo["domain_m"] / 2
    if source == "overture":
        overture = storage.assets(scene, "input") / cfg.get("overture_dir", "overture_transport")
        index = ensure_overture(geo_path, overture)
        built = network.build_network(overture, out_dir, ncfg)
        inputs = [
            {"id": f"overture_{k}", "sha256": v["sha256"]}
            for k, v in sorted(index["layers"].items())
            if k in ("segments", "connectors")
        ]
        return {**built, "source": source, "inputs": inputs, "report": None, "osm_index": None}
    if source != "osm":
        raise SystemExit(f"unknown network.source {source!r} (osm or overture)")
    osm_dir, osm_index = ensure_osm(storage, scene, cfg)
    ocfg = ncfg.get("osm", {})
    buffer_m = osm_index["selection"]["buffer_m"]
    built = osm_net.build_network(
        osm_dir / "osm.xml.gz",
        out_dir,
        ocfg,
        geo["origin"],
        half + buffer_m,
        storage.metadata(scene) / "configs",
    )
    compare = None
    if ocfg.get("compare_run"):
        old = storage.scratch(scene, SIMULATION, ocfg["compare_run"]) / "net/net.net.xml"
        if old.is_file():
            compare = sumo_env.sumolib().net.readNet(str(old), withInternal=False)
        else:
            log(f"comparison network {old} not found; report without comparison")
    enu = tfl.Enu(geo["origin"]["longitude"], geo["origin"]["latitude"])
    report = osm_net.network_report(
        built["net_obj"],
        half,
        enu,
        built["tagged_nodes"],
        built["coords"],
        built["stats"],
        {k: tuple(v) for k, v in ocfg.get("places", {}).items()},
        compare,
    )
    report["osm_subset"] = {
        k: osm_index[k] for k in ("source", "licence", "selection", "counts", "files")
    }
    if compare is not None:
        report["previous_network"]["run_id"] = ocfg["compare_run"]
        report["previous_network"]["source"] = "overture"
    (out_dir / "network_report.json").write_text(json.dumps(report, indent=2) + "\n")
    inputs = [{"id": "osm_subset", "sha256": osm_index["files"]["osm.xml.gz"]["sha256"]}]
    inputs += [
        {"id": f"network_patch_{Path(p['file']).stem.replace('.', '_')}", "sha256": p["sha256"]}
        for p in built["stats"]["patches"]
    ]
    return {
        "net": built["net"],
        "stats": built["stats"],
        "source": source,
        "inputs": inputs,
        "report": report,
        "osm_index": osm_index,
    }


def network_text(source: str, cfg: dict) -> tuple[str, str]:
    """(statement, assumptions) describing the network source."""
    if source == "osm":
        statement = (
            "OpenStreetMap road network (ODbL 1.0, (c) OpenStreetMap contributors; planet "
            "ORC snapshot on AWS Open Data) imported with netconvert: lanes, turn lanes, "
            "bus lanes, speed limits, one-ways, access, signal locations and turn "
            "restrictions from OSM tags; left-hand traffic."
        )
        assumptions = (
            "OSM tags where present (lanes, lanes:forward/backward, turn:lanes, maxspeed in "
            "mph, oneway, junction=roundabout, access/motor_vehicle/bus/psv, bus:lanes/"
            "busway); untagged lanes from SUMO's osmNetconvert typemap and untagged speeds "
            "from GB urban defaults (osm_net.DEFAULT_SPEED_MPH); OSM traffic_signals nodes "
            "clustered onto junctions (tls.guess-signals) as actuated signals with "
            "netconvert's default phase plans (the real signal timings are unknown); "
            "service roads open to delivery only unless OSM allows more (SUMO typemap); "
            "the network extends a buffer beyond the scene domain (see network stats) "
            "that is simulated but not recorded. LGV/HGV/motorcycle vTypes use passenger "
            "permissions."
        )
        return statement, assumptions
    statement = (
        "Overture road network; signal locations are assumed (Overture has no signal "
        "data), lanes/speeds by class unless tagged; left-hand traffic."
    )
    assumptions = (
        "Lanes and default speeds by Overture class (speed_limits when tagged); one-way and "
        "bus-only from access_restrictions; signals at junctions of >= "
        f"{cfg['network'].get('tls_min_major', 3)} tertiary-or-higher road pieces plus "
        "netconvert TLS guessing (Overture has no signal data); left-hand traffic. "
        "LGV/HGV/motorcycle vTypes use passenger permissions (the network encodes "
        "passenger/taxi/bus access only)."
    )
    return statement, assumptions


def sim_model(sim: dict) -> str:
    """Short description of the SUMO traffic model of a simulation configuration."""
    if not sim.get("mesosim"):
        return "microscopic"
    if sim.get("extra_options", {}).get("meso-junction-control"):
        return "mesoscopic (with junction control: signals and right of way delay vehicles)"
    return "mesoscopic (without junction control)"


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
    p.add_argument(
        "--synthetic",
        action="store_true",
        help="legacy single window with synthetic randomTrips cars/taxis (and TfL/synthetic "
        "buses) instead of DfT-calibrated periods",
    )
    p.add_argument(
        "--no-tfl", dest="tfl", action="store_false", help="skip TfL buses (--synthetic)"
    )
    p.add_argument(
        "--reuse",
        metavar="RUN_ID",
        help="run the periods only, reusing the network (and candidate routes when their "
        "configuration is unchanged) of cache/<scene>/traffic_sumo/RUN_ID",
    )
    p.add_argument("--periods", help="comma-separated period ids to run (default: all)")
    p.add_argument(
        "--network-only",
        action="store_true",
        help="build the network (and its report) into a new run directory and stop; "
        "build GTFS buses on it, then run the periods with --reuse",
    )
    args = p.parse_args(argv)
    cfg = json.loads(
        (Storage.load().metadata(args.scene) / "configs/traffic_sumo.json").read_text()
    )
    if args.synthetic or "periods" not in cfg:
        if args.reuse or args.periods or args.network_only:
            p.error("--reuse/--periods apply to the DfT period runs only")
        return run_synthetic(args)
    return run_periods(args)


def run_synthetic(args) -> int:
    storage = Storage.load()
    meta = storage.metadata(args.scene)
    config_path = meta / "configs/traffic_sumo.json"
    cfg = json.loads(config_path.read_text())
    scene = cfg["scene_id"]
    geo_path = meta / cfg.get("geometry_config", "configs/image_to_threejs.json")
    geo = json.loads(geo_path.read_text())
    # With a scene DEM, vehicles stand on the terrain (river bridges at bank height).
    surface = terrain.load_surface(storage.assets(scene, "input"), geo)
    sim = cfg["simulation"]
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ_") + secrets.token_hex(3)
    work = storage.scratch(scene, SIMULATION, run_id)
    if work.exists():
        raise FileExistsError(work)
    work.mkdir(parents=True)
    log(f"workspace: {work}")
    log(f"SUMO {sumo_env.version()} at {sumo_env.sumo_home()}")

    # 1. network
    built = build_scene_network(storage, scene, cfg, geo, geo_path, work / "net")
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
        "network_assumptions": network_text(built["source"], cfg)[1],
        "net_sha256": digest(net_path),
        "demand_sha256": demand_hashes,
        "simulation": {**sim, "statistics": stats},
        "recorded": recorded,
        "config": cfg,
        "coordinates": "SUMO x,y == scene ENU metres (netconvert offset normalisation "
        "disabled; verified via location offset and node coordinates); z = the scene DEM "
        "with open water filled from the banks (terrain.DemSurface.road) when the geometry "
        "config has terrain, else 0 (flat ground); flyovers are not raised",
    }
    export.write_trajectory_frames(
        kept, data / "trajectories.json", surface.road if surface else 0.0
    )
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
            "vertical_datum": terrain.vertical_datum_text(surface.index if surface else None),
        },
        "bounds_m": z_bounds(half, surface),
    }
    inputs = list(built["inputs"])
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


def run_periods(args) -> int:
    """DfT-calibrated period simulations (see README, "DfT-calibrated periods")."""
    t_start = time.monotonic()
    storage = Storage.load()
    meta = storage.metadata(args.scene)
    config_path = meta / "configs/traffic_sumo.json"
    cfg = json.loads(config_path.read_text())
    scene = cfg["scene_id"]
    geo_path = meta / cfg.get("geometry_config", "configs/image_to_threejs.json")
    geo = json.loads(geo_path.read_text())
    # With a scene DEM, vehicles stand on the terrain (river bridges at bank height).
    surface = terrain.load_surface(storage.assets(scene, "input"), geo)
    dfcfg, pcfg, ccfg = cfg["dft"], cfg["periods"], cfg["calibration"]
    windows = periods.period_windows(pcfg)
    if args.periods:
        wanted = args.periods.split(",")
        unknown = set(wanted) - {w["id"] for w in windows}
        if unknown:
            raise SystemExit(f"unknown period ids: {sorted(unknown)}")
        windows = [w for w in windows if w["id"] in wanted]
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ_") + secrets.token_hex(3)
    work = storage.scratch(scene, SIMULATION, run_id)
    if work.exists():
        raise FileExistsError(work)
    work.mkdir(parents=True)
    log(f"workspace: {work}")
    log(f"SUMO {sumo_env.version()} at {sumo_env.sumo_home()}")

    # 1. network (built, or reused from an earlier run of this scene)
    half = geo["domain_m"] / 2
    reused, report, net_inputs = None, None, None
    source = cfg["network"].get("source", "overture")
    if args.reuse:
        prior = storage.scratch(scene, SIMULATION, args.reuse)
        net_path = prior / "net/net.net.xml"
        if not net_path.is_file():
            raise SystemExit(f"no network at {net_path}")
        net_stats = network.describe(net_path)
        stats_file = prior / "net/network_stats.json"
        if stats_file.is_file():
            net_stats = {**json.loads(stats_file.read_text()), **net_stats}
        reused_source = net_stats.get("source", "overture")
        net_path = net_path.resolve()
        reused = {"run_id": args.reuse, "net": str(net_path), "source": reused_source}
        # Link the reused network so this run can itself be reused.
        (work / "net").mkdir()
        (work / "net/net.net.xml").symlink_to(net_path)
        for name in ("network_stats.json", "network_report.json", "network_inputs.json"):
            if (prior / "net" / name).is_file():
                shutil.copy2(prior / "net" / name, work / "net" / name)
        if (work / "net/network_report.json").is_file():
            report = json.loads((work / "net/network_report.json").read_text())
        if (work / "net/network_inputs.json").is_file():
            net_inputs = json.loads((work / "net/network_inputs.json").read_text())
        source = reused_source
        log(f"network reused from {args.reuse}: {net_path}")
    else:
        built = build_scene_network(storage, scene, cfg, geo, geo_path, work / "net")
        net_path, net_stats, report = built["net"], built["stats"], built["report"]
        net_inputs = built["inputs"]
        (work / "net/network_inputs.json").write_text(json.dumps(net_inputs, indent=2) + "\n")
        log(f"network: {net_path}")
    if net_stats["location_offset"] != [0.0, 0.0]:
        raise RuntimeError("network is not in scene ENU coordinates")
    log(
        f"  {net_stats['edges']} edges, {net_stats['junctions']} junctions, "
        f"{net_stats['traffic_lights']} traffic lights, {net_stats['edge_length_km']} km"
    )
    if net_inputs is None:
        # A reused network from before network_inputs.json: Overture inputs as recorded.
        overture = storage.assets(scene, "input") / cfg.get("overture_dir", "overture_transport")
        index = ensure_overture(geo_path, overture)
        net_inputs = [
            {"id": f"overture_{k}", "sha256": v["sha256"]}
            for k, v in sorted(index["layers"].items())
            if k in ("segments", "connectors")
        ]
    if args.network_only:
        log(json.dumps({"workspace": str(work), "network": str(net_path)}, indent=2))
        return 0

    # 2. DfT counts -> edge targets
    dft_dir = storage.assets(scene, "input") / dfcfg.get("dir", "dft_traffic")
    la_ids = sorted(int(k) for k in dfcfg["local_authorities"])
    dft_index = (
        dft.fetch(dft_dir, la_ids, log=log)
        if dfcfg.get("fetch_if_missing", True)
        else (json.loads((dft_dir / "index.json").read_text()))
    )
    used_files = [dft.file_name(ds, la) for la in la_ids for ds in dft.DATASETS]
    bbox = dft.domain_bbox(geo["origin"], geo["domain_m"] / 2)
    tables = periods.load_tables(dft_dir, la_ids, bbox)
    enu = tfl.Enu(geo["origin"]["longitude"], geo["origin"]["latitude"])
    counts = periods.prepare_counts(net_path, dfcfg, tables, enu, windows, half)
    matches = periods.match_report(counts)
    log(
        f"DfT: {matches['points_inside_domain']} count points inside the domain, "
        f"{matches['points_used']} recent, {matches['points_matched']} matched "
        f"({matches['point_directions_matched']} directions, "
        f"{matches['edges_with_targets']} edges)"
    )

    # 3. candidate routes for routeSampler
    demand_dir = work / "demand"
    demand_dir.mkdir()
    candidates, cand_cfg = None, ccfg["candidates"]
    if reused:
        old = storage.scratch(scene, SIMULATION, args.reuse) / "demand"
        if (old / "candidates.json").is_file() and (
            json.loads((old / "candidates.json").read_text()) == {"seed": ccfg["seed"], **cand_cfg}
        ):
            candidates = old / "candidates.rou.xml"
            reused["candidates"] = str(candidates)
            log(f"candidate routes reused: {candidates}")
    if candidates is None:
        log("routing candidate trips (randomTrips + duarouter) ...")
        vt = demand.write_vtypes(demand_dir)
        candidates = calibrate.candidate_routes(
            net_path, demand_dir, vt, cand_cfg, ccfg["seed"], demand_dir / "candidates.log"
        )
        (demand_dir / "candidates.json").write_text(
            json.dumps({"seed": ccfg["seed"], **cand_cfg}, indent=2) + "\n"
        )
    n_candidates = demand.count_vehicles_or_routes(candidates)
    log(f"candidate routes: {n_candidates}")

    # 4. periods
    gtfs_dir = storage.cache_root / scene / SIMULATION / cfg.get("gtfs_dir", "gtfs")
    results = []
    for w in windows:
        mix = dft.class_mix(
            tables["rawcount"], w["hour"], dfcfg.get("profile", {}).get("min_year", 2015)
        )
        res = periods.simulate_period(w, counts, candidates, net_path, work, cfg, mix, gtfs_dir)
        fit = res["fit"]["simulated_vs_observed"]
        log(
            f"[{w['id']}] {res['summary']['general_vehicles_sampled']} general vehicles, buses: "
            f"{res['bus']['source'] or 'none'}; GEH<5 {fit.get('geh_lt_5_pct')}%, "
            f"R2 {fit.get('r2')}; {res['runtime_s']} s"
        )
        results.append(res)

    # 5. exports
    ecfg = cfg["export"]
    bundle = work / "bundle"
    target = bundle / run_id
    data = target / "data"
    data.mkdir(parents=True)
    recordings, samples = {}, None
    for res in results:
        w = res["period"]
        rec = export.parse_fcd(res["fcd"], w["fcd_begin_s"], w["end_s"] - 1, res["kinds"], half)
        max_records = (ecfg["max_bin_bytes"] - 4 * len(rec.frames)) // export.RECORD.itemsize
        kept = export.select(rec, max_records, ecfg.get("max_concurrent_vehicles"))
        rel = [round(t - w["fcd_begin_s"], 6) for t in rec.times]
        if samples is None:
            samples = rel
        elif rel != samples:
            raise RuntimeError("FCD windows of the periods differ in length")
        bin_path = data / f"traffic_{w['id']}.bin"
        size = export.write_binary(kept, bin_path)
        if size >= ecfg["max_bin_bytes"]:
            raise RuntimeError(f"{bin_path.name} is {size} bytes, over the budget")
        export.write_trajectory_frames(
            kept, data / f"trajectories_{w['id']}.json", surface.road if surface else 0.0
        )
        recordings[w["id"]] = {
            "window_s": [rec.times[0], rec.times[-1]],
            "window_clock": f"{periods.clock(rec.times[0])}-{periods.clock(rec.times[-1] + 1)}",
            "frames": len(rec.times),
            "vehicles_simulated_in_window": len(rec.vehicles),
            "vehicles_exported": len(kept.vehicles),
            "exported_by_type": {
                t: sum(v["type"] == t for v in kept.vehicles) for t in export.VEHICLE_TYPES
            },
            "peak_concurrent_simulated": max(map(len, rec.frames)),
            "peak_concurrent_exported": max(map(len, kept.frames)),
            "traffic_bin_bytes": size,
            "heading_vs_motion": export.heading_check(kept),
        }
        res["kept"], res["bin"] = kept, bin_path
    selection = (
        "whole trajectories only; all buses, then other vehicles in SHA-1 order of their ids "
        f"until {ecfg['max_bin_bytes']} bytes per period binary or "
        f"{ecfg.get('max_concurrent_vehicles')} concurrent vehicles; omitted vehicles are "
        "absent from every frame (no partial or invented samples)"
    )
    buses_present = any(r["bus"]["source"] == "gtfs" for r in results)
    statement = {
        "counts": "Hourly targets are derived from UK DfT road traffic counts (AADF, AADF by "
        "direction and raw manual counts; Open Government Licence v3.0). Each count point "
        "is either Counted or Estimated by DfT, recorded per point as estimation_method.",
        "hourly_profiles": "Share of AADF per hour from the point's recent weekday raw counts "
        "(07:00-19:00 only); points without raw counts use the pooled median profile of "
        "their road type (flagged as profile_source). No night (19:00-07:00) profile is "
        "used or invented.",
        "demand": "General traffic (all motor vehicles minus buses and coaches) is "
        "calibrated to the edge targets with SUMO routeSampler from randomTrips/duarouter "
        "candidate routes; routes, origins and destinations are model choices, and traffic "
        "on roads without counts is only what passes through counted edges. Sampled "
        "vehicles whose route would exceed an assumed per-lane edge capacity "
        "(calibration.capacity_screening) are dropped before simulation; the fit before and "
        "after screening and after simulation is reported per period.",
        "state": "Speeds, densities, occupancies, waiting times and LOS classes are SUMO "
        f"{sim_model(cfg['simulation'])} model output, not observations.",
        "network": network_text(source, cfg)[0],
        "buses": "Bus demand from GTFS (separate step) where present for a period; "
        + (
            "present for: " + ", ".join(r["period"]["id"] for r in results if r["bus"]["source"])
            if buses_present
            else "absent in this run (no buses simulated)."
        ),
    }
    dft_inputs = {n: dft_index["files"][n]["sha256"] for n in used_files}
    provenance_doc = {
        "run_id": run_id,
        "scene_id": scene,
        "simulation": SIMULATION,
        "statement": statement,
        "licence": dft.LICENCE,
        "network_licence": osm_extract.LICENCE if source == "osm" else None,
        "dft_files": {n: dft_index["files"][n]["url"] for n in used_files},
        "sumo_version": sumo_env.version(),
    }
    doc, five = periods.state_document(
        counts, results, ecfg.get("shape_tolerance_m", 2.0), provenance_doc
    )
    state_bytes = periods.write_json(data / "traffic_state.json", doc)
    five_bytes = periods.write_json(data / "traffic_state_5min.json", five)
    if state_bytes > ecfg.get("max_state_bytes", 14_000_000):
        raise RuntimeError(f"traffic_state.json is {state_bytes} bytes, over the budget")
    extra_artifacts = []
    # Count-based hourly state on the same network (observation-led, all hours 07-19).
    cs_doc = count_state.document(counts, dft_dir, net_path, half)
    cs_bytes = periods.write_json(data / "count_state.json", cs_doc)
    extra_artifacts.append(("count_state", "data/count_state.json", "application/json"))
    log(f"count_state: {len(cs_doc['segments'])} segments, lanes {cs_doc['lanes_sources']}")
    # Bus status of the period runs against the GTFS schedule (when GTFS was built).
    bus_doc = None
    if (gtfs_dir / "schedule.json").is_file():
        bus_doc = bus_status_document(gtfs_dir, results, cfg)
        periods.write_json(data / "bus_status.json", bus_doc)
        shutil.copy2(gtfs_dir / "stops.json", data / "bus_stops.json")
        extra_artifacts += [
            ("bus_status", "data/bus_status.json", "application/json"),
            ("bus_stops", "data/bus_stops.json", "application/json"),
        ]
    if report is not None:
        periods.write_json(data / "network_report.json", report)
        extra_artifacts.append(("network_report", "data/network_report.json", "application/json"))

    for res in results:
        w = res["period"]
        export.write_traffic_json(
            res["kept"],
            data / f"traffic_{w['id']}.json",
            res["bin"],
            False,
            {
                "run_id": run_id,
                "scene_id": scene,
                "simulation": SIMULATION,
                "period": {k: w[k] for k in ("id", "label", "start_s", "end_s")},
                "synthetic": False,
                "demand": {"general": "dft_calibrated_route_sampler", "bus": res["bus"]["source"]},
                "sumo_version": sumo_env.version(),
                "net_sha256": digest(net_path),
                "selection": selection,
                "vehicles_simulated_in_window": recordings[w["id"]]["vehicles_simulated_in_window"],
            },
        )

    # Reproducibility artefacts: network and the exact per-period demand/configuration.
    sumo_dir = target / "sumo"
    sumo_dir.mkdir()
    with net_path.open("rb") as src, gzip.open(sumo_dir / "net.net.xml.gz", "wb") as dst:
        shutil.copyfileobj(src, dst)
    with tarfile.open(sumo_dir / "demand.tar.gz", "w:gz") as tar:
        for res in results:
            pid = res["period"]["id"]
            files = [res["routes"], res["config"], res["dir"] / "targets.edgedata.xml"]
            files += [*res["additional"], *res["route_files"][1:]]
            for path in dict.fromkeys(files):
                tar.add(path, arcname=f"{pid}/{Path(path).name}")
            if res["stopinfos"] and res["stopinfos"].is_file():
                tar.add(res["stopinfos"], arcname=f"{pid}/stopinfos.xml")
    shutil.copy2(config_path, target / "traffic_sumo.json")
    snapshot = target / "provenance/source_snapshot.tar.gz"
    revision = snapshot_sources(storage.root, snapshot)

    period_prov = {}
    for res in results:
        w = res["period"]
        period_prov[w["id"]] = {
            "window": {
                k: w[k] for k in ("label", "start_s", "end_s", "sim_begin_s", "fcd_begin_s")
            },
            "targets_edges": len(counts["targets"][w["id"]]),
            "targets_total_veh_h": round(sum(counts["targets"][w["id"]].values())),
            "class_mix": {k: round(v, 4) for k, v in res["class_mix"].items()},
            "calibration": res["fit"],
            "summary": res["summary"],
            "bus": res["bus"],
            "recorded": recordings[w["id"]],
            "routes_sha256": digest(res["routes"]),
            "runtime_s": res["runtime_s"],
        }
    pooled = {
        k: {
            "n_profiles": v["n_profiles"],
            "share": {str(h): round(s, 4) for h, s in v["share"].items()},
        }
        for k, v in counts["pooled"].items()
    }
    provenance_params = {
        "synthetic": False,
        "statement": statement,
        "dft": {
            "licence": dft.LICENCE,
            "local_authorities": dfcfg["local_authorities"],
            "points_per_local_authority_in_domain": {
                str(k): v for k, v in tables["points_per_la"].items()
            },
            "domain_bbox_lonlat": [round(v, 6) for v in bbox],
            "matching": {k: v for k, v in matches.items() if k != "unmatched"},
            "unmatched": matches["unmatched"],
            "stale_points": sorted(
                (
                    {"cp": cp, "year": p.year, "road": p.road_name}
                    for cp, p in counts["stale"].items()
                ),
                key=lambda d: int(d["cp"]),
            ),
            "point_profiles": counts["profiles_n"],
            "pooled_profiles": pooled,
            "share_of_aadf_outside_07_19_mean": None
            if counts["night_share"] is None
            else round(counts["night_share"], 3),
            "night_note": "Aggregate only: mean share of AADF outside 07:00-19:00 over the "
            "matched counts (1 - sum of the 07-19 hourly shares). Not simulated; DfT has no "
            "hourly night counts.",
            "files_sha256": dft_inputs,
        },
        "calibration": {
            "method": "SUMO tools/routeSampler.py (greedy sampling of candidate routes to match "
            "edge counts; 'entered' attribute); fit = GEH per count, % GEH<5, R^2",
            "candidates": {"routes": n_candidates, "sha256": digest(candidates), **cand_cfg},
            "route_sampler_args": ccfg.get("route_sampler_args", []),
            "warmup": f"{pcfg['warmup_s']} s before each hour, demand from the previous hour's "
            "profile scaled to the warm-up length (same hour when the previous is not in 07-19)",
        },
        "periods": period_prov,
        "thresholds": state.THRESHOLDS,
        "sumo_version": sumo_env.version(),
        "network": {k: v for k, v in net_stats.items() if k != "bbox_xy"},
        "network_reused": reused,
        "network_source": source,
        "network_licence": osm_extract.LICENCE if source == "osm" else None,
        "network_report": None
        if report is None
        else {k: report[k] for k in ("tag_completeness", "signals", "connectivity")},
        "network_assumptions": network_text(source, cfg)[1],
        "recorded_domain": f"state, count points, count_state and playback restricted to "
        f"|x|, |y| <= {half:g} m (scene domain); the network may extend beyond it",
        "count_state": {
            "segments": len(cs_doc["segments"]),
            "lanes_sources": cs_doc["lanes_sources"],
            "bytes": cs_bytes,
        },
        "bus_status": None if bus_doc is None else bus_doc.get("status_counts"),
        "net_sha256": digest(net_path),
        "simulation": cfg["simulation"],
        "selection": selection,
        "time": "Seconds since midnight of a representative weekday for SUMO and the viewer "
        "indexes (t0); manifest samples are seconds since the start of each period's FCD "
        "window (the same length for all periods); absolute windows are in periods.*.window.",
        "config": cfg,
        "coordinates": "SUMO x,y == scene ENU metres (netconvert offset normalisation "
        "disabled; verified via location offset and node coordinates); z = the scene DEM "
        "with open water filled from the banks (terrain.DemSurface.road) when the geometry "
        "config has terrain, else 0 (flat ground); flyovers are not raised",
        "runtime_s": round(time.monotonic() - t_start, 1),
    }
    half = geo["domain_m"] / 2
    spatial = {
        "frame": "ENU",
        "units": "m",
        "origin": {
            **geo["origin"],
            "height_m": 0,
            "vertical_datum": terrain.vertical_datum_text(surface.index if surface else None),
        },
        "bounds_m": z_bounds(half, surface),
    }
    inputs = list(net_inputs)
    inputs.append({"id": "traffic_sumo_config", "sha256": digest(config_path)})
    inputs += [{"id": f"dft_{Path(n).stem}", "sha256": h} for n, h in sorted(dft_inputs.items())]
    for res in results:
        for key, h in (res["bus"].get("sha256") or {}).items():
            inputs.append({"id": f"gtfs_{res['period']['id']}_{key}", "sha256": h})
    artifacts = [
        ("source_snapshot", "provenance/source_snapshot.tar.gz", "application/gzip"),
        ("traffic_state", "data/traffic_state.json", "application/json"),
        ("traffic_state_5min", "data/traffic_state_5min.json", "application/json"),
        ("sumo_network", "sumo/net.net.xml.gz", "application/gzip"),
        ("sumo_demand", "sumo/demand.tar.gz", "application/gzip"),
        ("config", "traffic_sumo.json", "application/json"),
        *extra_artifacts,
    ]
    for res in results:
        pid = res["period"]["id"]
        artifacts += [
            (f"viewer_index_{pid}", f"data/traffic_{pid}.json", "application/json"),
            (f"viewer_binary_{pid}", f"data/traffic_{pid}.bin", "application/octet-stream"),
        ]
    layers = [
        {
            "id": f"traffic_{res['period']['id']}",
            "kind": "trajectories",
            "format": "trajectory_frames",
            "asset": f"data/trajectories_{res['period']['id']}.json",
            "sampling": "linear",
            "display": {"widget": "trajectories", "capabilities": ["pick", "opacity"]},
        }
        for res in results
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
        "time": {"unit": "s", "samples": samples},
        "layers": layers,
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
        "title": "SUMO traffic (DfT-calibrated periods)",
        "time_alignment": "relative",
        "runs": [run_id],
        "layers": [
            {"run_id": run_id, "layer_id": layer["id"], "visible": k == 0}
            for k, layer in enumerate(layers)
        ],
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
        "manifest": str(manifest_path),
        "traffic_state": str(data / "traffic_state.json"),
        "traffic_state_bytes": state_bytes,
        "traffic_state_5min_bytes": five_bytes,
        "dft_matching": {k: v for k, v in matches.items() if k != "unmatched"},
        "periods": {
            pid: {
                "calibration": p["calibration"],
                "summary": {k: v for k, v in p["summary"].items() if k != "trip_statistics"},
                "bus": p["bus"]["source"],
                "traffic_bin_bytes": p["recorded"]["traffic_bin_bytes"],
                "vehicles_exported": p["recorded"]["vehicles_exported"],
                "runtime_s": p["runtime_s"],
            }
            for pid, p in period_prov.items()
        },
        "runtime_s": round(time.monotonic() - t_start, 1),
    }
    log(json.dumps(summary, indent=2))
    return 0


def bus_status_document(gtfs_dir: Path, results: list[dict], cfg: dict) -> dict:
    """``bus_status.compute`` over this run's period directories (stop output)."""
    schedule = json.loads((gtfs_dir / "schedule.json").read_text())
    stops = json.loads((gtfs_dir / "stops.json").read_text())
    thresholds = dict(bus_status.THRESHOLDS)
    for k, v in cfg.get("gtfs", {}).get("status", {}).items():
        key = k if k in thresholds else k.removesuffix("_min") + "_min"
        if key in thresholds:
            thresholds[key] = v
    by_period = {r["period"]["id"]: r for r in results}
    runs = {}
    for period in schedule["periods"]:
        trips_path = gtfs_dir / period / "trips.json"
        trips = json.loads(trips_path.read_text()) if trips_path.is_file() else {}
        res = by_period.get(period)
        info = res["stopinfos"] if res and res["bus"]["source"] == "gtfs" else None
        runs[period] = {"trips": trips, "stopinfos": info if info and info.is_file() else None}
    doc = bus_status.compute(schedule, stops, runs, thresholds)
    counts: dict[str, dict[str, int]] = {}
    for r in doc["routes"]:
        for period, cls in r["status"].items():
            counts.setdefault(period, {}).setdefault(cls, 0)
            counts[period][cls] += 1
    doc["status_counts"] = counts
    return doc


if __name__ == "__main__":
    sys.exit(main())
