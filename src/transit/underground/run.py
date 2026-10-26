"""London Underground scheduled-service run for a scene -> protocol v1.1 bundle.

Reads the OSM railway subset (``osm.py``) and the Underground GTFS subset (``gtfs.py``)
from ``project/<scene>/input/underground/`` and writes
``cache/<scene>/underground/<run_id>/bundle/<run_id>/``:

* ``data/underground.json``: lines, tracks (with the assumed vertical profile),
  stations with platforms and entrances, provenance;
* ``data/underground_trains_<period>.json``: map-matched stop patterns and the
  timetabled trips inside the domain during [start - lead, end];
* ``data/underground_status.json``: scheduled frequency, headway, run time and speed
  per line/direction/period and per station;
* ``data/trajectories_<period>.json``: protocol ``trajectory_frames`` layers (scheduled
  positions every ``trajectory_dt_s`` seconds);
* ``manifest.json`` (validated), config copy and a source snapshot.

Nothing is registered under ``project/``.

  PYTHONPATH=src python3 -m transit.underground.osm imperial_corridor    # ~1 h, once
  PYTHONPATH=src python3 -m transit.underground.gtfs imperial_corridor   # ~2 min, once
  PYTHONPATH=src python3 -m transit.underground.run imperial_corridor
  python3 tools/check_contract.py cache/imperial_corridor/underground/<run_id>/bundle/<run_id>/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shutil
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from common.contract import validate
from common.provenance import snapshot_sources

from . import build
from . import gtfs as gtfs_mod
from .config import SIMULATION, load_scene, log


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_dirty(root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", "src", "schemas"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode != 0 or bool(result.stdout.strip())


def write_json(path: Path, doc, limit: int) -> int:
    text = json.dumps(doc, separators=(",", ":"), allow_nan=False)
    path.write_text(text + "\n")
    size = path.stat().st_size
    if size > limit:
        raise SystemExit(f"{path.name}: {size} bytes exceeds max_json_bytes {limit}")
    return size


def depth_text(dcfg: dict, ref_layers: dict) -> dict:
    return {
        "nature": "assumed: no measured track or platform depths were available; every tunnel "
        "depth below is a typical value, flagged depth_source 'assumed_typical'",
        "tunnel": "OSM tunnel=yes (also covered/culvert) marks underground sections; covered=yes "
        "and building_passage count as surface",
        "subsurface_lines_m": dcfg["subsurface_m"],
        "deep_tube_lines_m": dcfg["deep_m"],
        "other_rail_tunnels_m": dcfg["rail_tunnel_m"],
        "per_line_override_m": dcfg.get("per_line_m", {}),
        "line_kind": "sub-surface (cut-and-cover): District, Circle, Hammersmith & City, "
        "Metropolitan; deep-level tube: Bakerloo, Central, Jubilee, Northern, Piccadilly, "
        "Victoria, Waterloo & City; Elizabeth/Overground/national rail: rail",
        "layers": "OSM layer is relative: each line's length-weighted most common tunnel "
        f"layer is its reference at the typical depth; each layer below/above adds/removes "
        f"{dcfg['layer_step_m']} m, clamped to 1 step shallower and "
        f"{dcfg.get('max_layer_steps', 2)} steps deeper, within [{dcfg.get('min_tunnel_m', 3.0)}, "
        f"{dcfg.get('max_depth_m', 40.0)}] m",
        "unknown_line": "tunnels without a line from OSM route relations use the "
        "sub-surface depth (railway=subway) or the rail tunnel depth (depth_source "
        "'assumed_typical_line_unknown')",
        "portals": f"depth rises linearly from 0 at a portal (vertex shared with a non-tunnel "
        f"way) to the tunnel depth over {dcfg['portal_ramp_m']} m into the tunnel; layer "
        "changes between tunnels ramp with the same gradient",
        "bridges": f"bridge/viaduct or layer > 0: +{dcfg['bridge_layer_m']} m per layer (as the "
        f"road model's 6.5 m deck), ramped down over {dcfg.get('bridge_ramp_m', 100.0)} m "
        "onto the approaches",
        "surface": "all other track at z = 0 (embankments and cuttings not modelled; flat "
        "ground, no terrain)",
        "stations": "platform level = assumed track level at the platform",
        "reference_layers": ref_layers,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("scene")
    p.add_argument("--run-id")
    args = p.parse_args(argv)
    t_start = time.monotonic()
    ctx = load_scene(args.scene)
    cfg, storage, enu, half = ctx["cfg"], ctx["storage"], ctx["enu"], ctx["half"]
    scene = args.scene
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ_") + secrets.token_hex(3)
    work = storage.scratch(scene, SIMULATION, run_id)
    target = work / "bundle" / run_id
    data = target / "data"
    data.mkdir(parents=True, exist_ok=False)
    inp = storage.assets(scene, "input") / cfg.get("input_dir", "underground")
    log(f"scene {scene}: input {inp}, output {target}")
    osm_index = json.loads((inp / "osm/index.json").read_text())
    osm_path = inp / "osm/osm_rail.json.gz"
    if digest(osm_path) != osm_index["files"]["osm_rail.json.gz"]["sha256"]:
        raise SystemExit(f"{osm_path} does not match its index.json sha256")
    osm = build.load_osm(osm_path)
    sub = gtfs_mod.load(inp / "gtfs")
    limit = cfg.get("max_json_bytes", 12_000_000)

    log("track network ...")
    net = build.Network(osm, enu, half, cfg["buffer_m"], cfg)
    tracks = net.tracks()
    conflicts = net.crossing_conflicts(tracks)
    log(f"  {len(tracks)} tracks in the domain; {conflicts['n_conflicts']} level conflicts")
    tt = build.Timetable(sub, enu)
    stations, st_report = build.build_stations(net, tt, osm, cfg)
    log(f"  {len(stations)} stations; {st_report}")
    log("patterns ...")
    patterns, assign = build.build_patterns(net, tt, cfg)
    ratios = [
        p["match"]["path_over_straight"]
        for p in patterns.values()
        if p["match"]["path_over_straight"]
    ]
    methods = Counter()
    for pat in patterns.values():
        methods.update(pat["match"]["methods"])
    log(f"  {len(patterns)} patterns; pair methods {dict(methods)}")

    lines = build.line_table(tt, tracks, stations, sub["index"])
    gidx = sub["index"]
    timetable_prov = {
        "source": gidx["source"],
        "license": gidx["license"],
        "attribution": gidx["attribution"],
        "feed_version": gidx["feed_info"].get("feed_version"),
        "feed_sha256": gidx["download"].get("sha256"),
        "url": gidx["download"].get("url"),
        "service_date": gidx["service_date"],
        "service_date_selection": gidx["service_date_selection"],
        "lines_on_service_date": gidx["lines_on_service_date"],
        "feed_coverage": {
            k: gidx["feed_coverage"][k]
            for k in ("elizabeth_line_present", "london_overground_present", "rule")
        },
        "time_resolution": "GTFS times are whole minutes with arrival == departure "
        "(no dwell times in the feed)",
        "nature": gidx["nature"],
        "derived_parent_stations": tt.derived_parents,
    }
    geometry_prov = {
        "source": osm_index["source"],
        "licence": osm_index["licence"],
        "selection": osm_index["selection"],
        "counts": osm_index["counts"],
        "osm_sha256": osm_index["files"]["osm_rail.json.gz"]["sha256"],
    }
    provenance = {
        "synthetic": False,
        "status": "scheduled",
        "real_time": "none: no real-time train positions, delays or crowding were available or used",
        "geometry": geometry_prov,
        "timetables": timetable_prov,
        "depth_model": depth_text(cfg["depth"], net.ref_layers),
        "colours": build.colour_reference(),
        "coordinates": "scene ENU metres (tfl.Enu equirectangular about the scene origin), z metres "
        "relative to flat local ground (negative = below)",
        "domain": f"|x|, |y| <= {half:g} m; tracks/platforms clipped at the boundary; the "
        f"track graph extends {cfg['buffer_m']} m beyond it for continuity",
    }
    level_counts = Counter(t["depth_source"] for t in tracks)
    und = {
        "schema": "underground-network-v1",
        "lines": lines,
        "tracks": tracks,
        "stations": stations,
        "summary": {
            "tracks": len(tracks),
            "track_km": round(sum(t["length_m"] for t in tracks) / 1000, 2),
            "tunnel_track_km": round(sum(t["length_m"] for t in tracks if t["tunnel"]) / 1000, 2),
            "depth_sources": dict(level_counts),
            "stations": len(stations),
            "stations_timetabled": sum(1 for s in stations if s["timetable"]),
            "platforms": sum(len(s["platforms"]) for s in stations),
            "entrances": sum(len(s["entrances"]) for s in stations),
            "station_report": st_report,
            "tunnel_crossings": conflicts,
        },
        "provenance": provenance,
    }
    sizes = {"underground.json": write_json(data / "underground.json", und, limit)}

    periods = cfg["periods"]
    lead, dt = cfg.get("lead_s", 600), cfg.get("trajectory_dt_s", 10)
    pattern_out = {
        pid: {k: v for k, v in pat.items() if not k.startswith("_")}
        for pid, pat in patterns.items()
    }
    period_summary = {}
    layers, samples = [], None
    for pid_name, (h0, h1) in periods.items():
        t0, t1 = h0 * 3600 - lead, h1 * 3600
        res = build.period_trains(patterns, assign, tt, (t0, t1), half)
        used = sorted({t["pattern"] for t in res["trips"]})
        doc = {
            "schema": "underground-trains-v1",
            "period": {"id": pid_name, "hours": [h0, h1], "start_s": h0 * 3600, "end_s": h1 * 3600},
            "t0": t0,
            "t1": t1,
            "time": "seconds after midnight of the service day "
            f"{gidx['service_date']}; trips inside the domain during [start - {lead} s, end]",
            "patterns": [pattern_out[p] for p in used],
            "trips": res["trips"],
            "interpolation": "linear in distance along path between the departure from one "
            "station and the arrival at the next (constant speed; no acceleration profile); "
            "stationary between arrival and departure (GTFS gives none). station_offsets_m are "
            "distances along path from its first point (negative / beyond its length for the "
            "outside neighbour stations); a train is shown only while its distance lies in "
            "[0, path length]. A trip split into runs has ids <gtfs trip id>#k",
            "provenance": TRAIN_PROVENANCE_TEXT,
        }
        sizes[f"underground_trains_{pid_name}.json"] = write_json(
            data / f"underground_trains_{pid_name}.json", doc, limit
        )
        frames = build.sample_frames(patterns, res["trips"], t0, t1, dt, half)
        traj = {"frames": frames}
        sizes[f"trajectories_{pid_name}.json"] = write_json(
            data / f"trajectories_{pid_name}.json", traj, limit
        )
        rel = list(range(0, t1 - t0 + 1, dt))
        samples = samples or rel
        per_line = Counter(patterns[t["pattern"]]["line"] for t in res["trips"])
        period_summary[pid_name] = {
            "trips": len(res["trips"]),
            "patterns": len(used),
            "trips_per_line": dict(sorted(per_line.items())),
            "max_concurrent_trains": max(len(f["ids"]) for f in frames),
            "frames": len(frames),
        }
        layers.append(
            {
                "id": f"underground_{pid_name}",
                "kind": "trajectories",
                "format": "trajectory_frames",
                "asset": f"data/trajectories_{pid_name}.json",
                "sampling": "linear",
                "display": {"widget": "trajectories", "capabilities": ["pick", "opacity"]},
            }
        )
    st = build.status(patterns, assign, tt, periods, half, stations)
    status_doc = {
        "schema": "underground-status-v1",
        "status": "scheduled",
        "note": "Scheduled (timetabled) service only; no real-time data available. Trains per "
        "hour count departures in [start, end) at the busiest domain station of each "
        "line/direction; run time/speed are medians over trains crossing the whole domain "
        "on their pattern, entering it within the hour. First/last trains count calls from "
        "04:00 (times past 24:00 allowed); 00:00-04:00 calls are in calls_before_04h.",
        "service_date": gidx["service_date"],
        "periods": periods,
        **st,
        "provenance": {"timetables": timetable_prov, "status": "scheduled"},
    }
    sizes["underground_status.json"] = write_json(
        data / "underground_status.json", status_doc, limit
    )

    match_summary = {
        "patterns": len(patterns),
        "pair_methods": dict(methods),
        "path_over_straight": {
            "min": min(ratios) if ratios else None,
            "median": sorted(ratios)[len(ratios) // 2] if ratios else None,
            "max": max(ratios) if ratios else None,
        },
        "worst": sorted(
            (
                {
                    "pattern": p["id"],
                    "ratio": p["match"]["path_over_straight"],
                    "methods": p["match"]["methods"],
                }
                for p in patterns.values()
                if p["match"]["path_over_straight"]
            ),
            key=lambda d: -d["ratio"],
        )[:5],
    }

    shutil.copy2(ctx["config_path"], target / "underground.json")
    snapshot = target / "provenance/source_snapshot.tar.gz"
    revision = snapshot_sources(storage.root, snapshot)
    inputs = [
        {"id": "underground_config", "sha256": digest(ctx["config_path"])},
        {"id": "scene_geometry_config", "sha256": digest(ctx["geo_path"])},
        {"id": "osm_rail_subset", "sha256": geometry_prov["osm_sha256"]},
        {"id": "gtfs_feed_zip", "sha256": gidx["download"].get("sha256", "")},
    ]
    inputs += [
        {"id": f"gtfs_subset_{name.split('.')[0]}", "sha256": meta["sha256"]}
        for name, meta in sorted(gidx["files"].items())
    ]
    inputs = [i for i in inputs if i["sha256"]]
    artifacts = [
        ("source_snapshot", "provenance/source_snapshot.tar.gz", "application/gzip"),
        ("config", "underground.json", "application/json"),
        ("underground", "data/underground.json", "application/json"),
        ("underground_status", "data/underground_status.json", "application/json"),
    ] + [
        (f"underground_trains_{p}", f"data/underground_trains_{p}.json", "application/json")
        for p in periods
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
            "parameters": {
                **provenance,
                "trajectories": f"scheduled positions sampled every {dt} s from period start - "
                f"{lead} s to period end; manifest samples are seconds since that window start "
                "(the same length for all periods); absolute windows in periods",
                "periods": {
                    p: {"start_s": h0 * 3600 - lead, "end_s": h1 * 3600, **period_summary[p]}
                    for p, (h0, h1) in periods.items()
                },
                "map_matching": match_summary,
                "train_positions": TRAIN_PROVENANCE_TEXT,
                "config": cfg,
                "runtime_s": round(time.monotonic() - t_start, 1),
            },
            "inputs": inputs,
        },
        "spatial": {
            "frame": "ENU",
            "units": "m",
            "origin": {
                **ctx["origin"],
                "height_m": 0,
                "vertical_datum": "Flat ground at local zero; track depths assumed (see "
                "provenance depth_model)",
            },
            "bounds_m": {"min": [-half, -half, -60], "max": [half, half, 30]},
        },
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
    summary = {
        "manifest": str(manifest_path),
        "sizes": sizes,
        "lines": [(ln["id"], ln["timetable"]) for ln in lines],
        "summary": und["summary"] | {"tunnel_crossings": conflicts["n_conflicts"]},
        "periods": period_summary,
        "map_matching": match_summary,
        "runtime_s": round(time.monotonic() - t_start, 1),
    }
    del summary["summary"]["station_report"]
    log(json.dumps(summary, indent=2))
    (work / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0


TRAIN_PROVENANCE_TEXT = (
    "scheduled positions interpolated between timetabled station calls; not real-time. "
    "Viewers interpolate linearly in distance along the pattern path between departure and "
    "arrival (no acceleration profile)."
)


if __name__ == "__main__":
    raise SystemExit(main())
