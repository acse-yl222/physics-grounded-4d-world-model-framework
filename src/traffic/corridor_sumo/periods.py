"""DfT-calibrated period simulations: counts -> edge targets -> routeSampler -> SUMO -> state.

``prepare_counts`` turns the DfT tables into hourly per-edge targets for the scene network;
``simulate_period`` calibrates and runs one period (a clock hour plus warm-up) and returns
edge states, the calibration fit and an FCD recording window. Times are seconds since
midnight of a representative weekday (DfT manual counts are weekday counts).

Bus interface: when ``<gtfs_dir>/<period_id>/bus_stops.add.xml`` and ``buses.rou.xml``
exist they are added to that period's simulation (with ``stopinfos.xml`` stop output);
bus departures are expected in the same seconds-since-midnight clock.
"""

from __future__ import annotations

import json
import re
import shutil
import statistics
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from . import calibrate, demand, dft, export, simulate, state, sumo_env
from .osm_net import road_class


def log(message: str) -> None:
    print(message, flush=True)


def clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}"


def period_windows(pcfg: dict) -> list[dict]:
    """Period definitions with absolute simulation windows (seconds since midnight)."""
    warmup, fcd = float(pcfg["warmup_s"]), float(pcfg["fcd_window_s"])
    out = []
    for p in pcfg["list"]:
        hour = int(p["hour"])
        if hour not in dft.DFT_HOURS:
            raise ValueError(f"{p['id']}: DfT raw counts cover 07-19 only, not hour {hour}")
        start = hour * 3600.0
        out.append(
            {
                "id": p["id"],
                "label": p.get("label", f"{hour:02d}:00-{hour + 1:02d}:00"),
                "hour": hour,
                "start_s": start,
                "end_s": start + 3600.0,
                "sim_begin_s": start - warmup,
                "fcd_begin_s": start + 3600.0 - fcd,
            }
        )
    return out


# ---------------------------------------------------------------- counts and targets


def load_tables(dest: Path, la_ids: list[int], bbox) -> dict:
    """DfT rows inside the domain, per table, plus per-LA point counts."""
    tables: dict[str, list[dict]] = {k: [] for k in dft.DATASETS}
    per_la = {}
    for la in la_ids:
        for ds in dft.DATASETS:
            rows = dft.inside(dft.read_rows(dest / dft.file_name(ds, la)), bbox)
            tables[ds] += rows
            if ds == "aadf":
                per_la[la] = len({r["count_point_id"] for r in rows})
    tables["points_per_la"] = per_la
    return tables


def opposite_edge(edge):
    """The reverse edge of a two-way road piece (same end nodes), if any."""
    base = edge.getID().lstrip("-")
    for out in edge.getToNode().getOutgoing():
        if out.getToNode() == edge.getFromNode() and out.getID().lstrip("-") == base:
            return out
    return None


def domain_edges(net, half: float | None) -> set[str] | None:
    """Ids of edges with a shape point inside ``|x|, |y| <= half`` (None: no limit)."""
    if half is None:
        return None
    return {
        e.getID()
        for e in net.getEdges()
        if any(abs(x) <= half and abs(y) <= half for x, y in (p[:2] for p in e.getShape()))
    }


def prepare_counts(
    net_path: Path,
    dfcfg: dict,
    tables: dict,
    enu,
    periods: list[dict],
    half: float | None = None,
) -> dict:
    """Count points, edge matches and hourly general-traffic targets per period.

    ``half``: the recorded domain (edge state is only reported for edges reaching into
    it; the network may extend beyond it as a buffer).
    """
    pcfg = dfcfg.get("profile", {})
    min_year = pcfg.get("min_year", 2015)
    points = dft.latest_points(tables["aadf"], enu)
    stale = {cp: p for cp, p in points.items() if p.year < dfcfg.get("min_aadf_year", 2018)}
    points = {cp: p for cp, p in points.items() if cp not in stale}
    by_dir = dft.direction_aadf(tables["aadf_direction"])
    raw = tables["rawcount"]
    profiles = dft.point_profiles(
        raw,
        by_dir,
        min_year=min_year,
        max_dates=pcfg.get("max_dates", 3),
        weekdays_only=pcfg.get("weekdays_only", True),
    )
    pooled = dft.pooled_profiles(profiles, {cp: p.road_type for cp, p in points.items()})
    dft.assign_directions(points, by_dir, dft.raw_direction_split(raw, min_year))

    sumolib = sumo_env.sumolib()
    net = sumolib.net.readNet(str(net_path), withInternal=False)
    mcfg = dfcfg.get("match", {})
    radius = mcfg.get("radius_m", 40.0)
    records, unmatched = [], []
    for cp, point in sorted(points.items(), key=lambda kv: int(kv[0])):
        cands = calibrate.edge_candidates(net, point.x, point.y, radius)
        info = {
            "road_name": point.road_name,
            "road_type": point.road_type,
            "start_junction": point.start_junction,
            "end_junction": point.end_junction,
        }
        for direction, d in point.directions.items():
            choice = calibrate.choose_edge(cands, info, direction, mcfg)
            prof = dft.profile_for(cp, direction, point.road_type, profiles, pooled)
            base = {
                "cp": cp,
                "direction": direction,
                "aadf_general_dir": round(d["general"], 1),
                "profile_source": prof["source"],
                "profile_dates": prof.get("dates", []),
                "share": prof["share"],
            }
            if choice["edge"] is None:
                unmatched.append({**base, "reason": choice["reason"]})
                continue
            edge = net.getEdge(choice["edge"])
            split = [(edge, 1.0, None)]
            if direction == "C":
                rev = opposite_edge(edge)
                if rev is not None and rev.allows("passenger"):
                    split = [(edge, 0.5, "C split 50/50"), (rev, 0.5, "C split 50/50")]
            for e, frac, note in split:
                records.append(
                    {
                        **base,
                        "edge": e.getID(),
                        "fraction": frac,
                        "quality": choice["quality"] + (f"; {note}" if note else ""),
                        "dist_m": choice["dist_m"],
                    }
                )
    targets, warmups = {}, {}
    for p in periods:
        targets[p["id"]] = edge_targets(records, p["hour"])
        prev = p["hour"] - 1 if p["hour"] - 1 in dft.DFT_HOURS else p["hour"]
        warmups[p["id"]] = edge_targets(records, prev)
    night = statistics.fmean(1 - sum(r["share"].values()) for r in records) if records else None
    return {
        "points": points,
        "stale": stale,
        "records": records,
        "unmatched": unmatched,
        "targets": targets,
        "warmup_targets": warmups,
        "pooled": pooled,
        "profiles_n": len(profiles),
        "night_share": night,
        "net": net,
        "half": half,
        "domain_edges": domain_edges(net, half),
    }


def edge_targets(records: list[dict], hour: int) -> dict[str, float]:
    """Hourly general-traffic target per edge (mean over count points sharing an edge)."""
    per_edge: dict[str, list[float]] = defaultdict(list)
    for r in records:
        per_edge[r["edge"]].append(r["aadf_general_dir"] * r["fraction"] * r["share"][hour])
    return {e: statistics.fmean(v) for e, v in per_edge.items()}


# ---------------------------------------------------------------- buses (GTFS agent)


def gtfs_files(gtfs_dir: Path, period_id: str) -> dict | None:
    """Bus files written by the GTFS step for a period, if both exist."""
    d = gtfs_dir / period_id
    stops, routes = d / "bus_stops.add.xml", d / "buses.rou.xml"
    if stops.is_file() and routes.is_file():
        return {"stops": stops, "routes": routes}
    return None


def defined_vtypes(paths: list[Path]) -> set[str]:
    ids = set()
    for path in paths:
        for _, el in ET.iterparse(path):
            if el.tag in ("vType", "vTypeDistribution") and el.get("id"):
                ids.add(el.get("id"))
            el.clear()
    return ids


def bus_departures(path: Path) -> tuple[int, float | None, float | None]:
    n, lo, hi = 0, None, None
    for _, el in ET.iterparse(path):
        if el.tag in ("vehicle", "flow", "trip"):
            n += 1
            t = el.get("depart") or el.get("begin")
            try:
                v = float(t)
            except (TypeError, ValueError):
                v = None
            if v is not None:
                lo = v if lo is None else min(lo, v)
                hi = v if hi is None else max(hi, v)
        el.clear()
    return n, lo, hi


# ---------------------------------------------------------------- one period


def simulate_period(
    period: dict,
    counts: dict,
    candidates: Path,
    net_path: Path,
    work: Path,
    cfg: dict,
    mix: dict,
    gtfs_dir: Path,
) -> dict:
    """Calibrate demand with routeSampler, simulate, read edge state and FCD window."""
    t0 = time.monotonic()
    pid = period["id"]
    pdir = work / "periods" / pid
    if pdir.exists():
        shutil.rmtree(pdir)
    pdir.mkdir(parents=True)
    ccfg, sim = cfg["calibration"], cfg["simulation"]
    seed = ccfg.get("seed", 7)

    targets = counts["targets"][pid]
    warm = counts["warmup_targets"][pid]
    w = period["start_s"] - period["sim_begin_s"]
    edgedata = pdir / "targets.edgedata.xml"
    intervals = []
    if w > 0:
        intervals.append(
            {
                "id": "warmup",
                "begin": period["sim_begin_s"],
                "end": period["start_s"],
                "counts": {e: v * w / 3600 for e, v in warm.items()},
            }
        )
    intervals.append(
        {"id": pid, "begin": period["start_s"], "end": period["end_s"], "counts": targets}
    )
    calibrate.write_edgedata(intervals, edgedata)
    sampled_routes = pdir / "sampled.rou.xml"
    routes = pdir / "general.rou.xml"
    mismatch = calibrate.route_sampler(
        candidates,
        edgedata,
        sampled_routes,
        prefix=f"{pid}_",
        vtype=demand.GENERAL_DISTRIBUTION,
        seed=seed,
        log=pdir / "routesampler.log",
        extra=ccfg.get("route_sampler_args", []),
    )
    sampled_all = calibrate.sampled_counts(sampled_routes, period["start_s"], period["end_s"])
    screening = None
    cap = ccfg.get("capacity_screening")
    if cap and cap.get("enabled", True):
        capacity = calibrate.edge_capacities(
            counts["net"], cap["veh_h_lane"], cap.get("default_veh_h_lane", 500)
        )
        windows = [(iv["begin"], iv["end"]) for iv in intervals]
        screening = calibrate.screen_capacity(
            sampled_routes, routes, capacity, targets, windows, seed
        )
        log(
            f"[{pid}] capacity screening dropped {screening['vehicles_dropped']} of "
            f"{screening['vehicles_in']} sampled vehicles"
        )
    else:
        shutil.copy2(sampled_routes, routes)
    sampled = calibrate.sampled_counts(routes, period["start_s"], period["end_s"])
    general_vehicles = demand.count_vehicles(routes)

    buses = gtfs_files(gtfs_dir, pid)
    bus_info: dict = {"source": None, "gtfs_dir": str(gtfs_dir / pid)}
    route_files, add_files = [routes], []
    if buses:
        external = defined_vtypes([buses["stops"], buses["routes"]])
        n, lo, hi = bus_departures(buses["routes"])
        bus_info = {
            "source": "gtfs",
            "files": {k: str(v) for k, v in buses.items()},
            "sha256": {k: _digest(v) for k, v in buses.items()},
            "vehicles_or_flows": n,
            "depart_range_s": [lo, hi],
        }
        if lo is not None and (hi < period["sim_begin_s"] or lo >= period["end_s"]):
            bus_info["warning"] = "no bus departure inside the simulated window"
        vtypes = demand.write_general_vtypes(
            pdir / "vtypes.add.xml", mix, include_bus="bus" not in external
        )
        add_files = [vtypes, buses["stops"]]
        route_files.append(buses["routes"])
        kinds = {t: "bus" for t in external if not t.startswith(export.VEHICLE_TYPES)}
    else:
        vtypes = demand.write_general_vtypes(pdir / "vtypes.add.xml", mix)
        add_files = [vtypes]
        kinds = {}
    general_types = list(demand.GENERAL_VTYPES)
    meandata = simulate.write_meandata(
        pdir / "meandata.add.xml", pdir, period["start_s"], period["end_s"], general_types
    )
    add_files.append(pdir / "meandata.add.xml")
    log(f"[{pid}] simulating {clock(period['sim_begin_s'])}-{clock(period['end_s'])} ...")
    try:
        result = simulate.run_period(
            net_path, route_files, add_files, pdir, period, sim, stop_output=bool(buses)
        )
    except RuntimeError as exc:
        if not buses:
            raise
        # The GTFS files are produced by a separate step; a file SUMO rejects must not
        # stop the period. Run without buses and record why.
        log(f"[{pid}] SUMO rejected the GTFS bus files; running without buses:\n{exc}")
        bus_info.update(source=None, error=str(exc)[-2000:], used=False)
        (pdir / "sumo.log").rename(pdir / "sumo_with_gtfs_failed.log")
        vtypes = demand.write_general_vtypes(pdir / "vtypes.add.xml", mix)
        add_files = [vtypes, pdir / "meandata.add.xml"]
        route_files, kinds, buses = [routes], {}, None
        result = simulate.run_period(net_path, route_files, add_files, pdir, period, sim)

    net = counts["net"]
    edges_info = {}

    def info(eid):
        if eid not in edges_info:
            e = net.getEdge(eid)
            edges_info[eid] = (e.getSpeed(), e.getLaneNumber(), e.getLength())
        return edges_info[eid]

    hourly = {}
    for iv in state.read_edgedata(meandata["edge_3600s"]):
        dur = iv["end"] - iv["begin"]
        for eid, attrs in iv["edges"].items():
            free, lanes, _ = info(eid)
            s = state.edge_state(attrs, dur, free, lanes)
            if s:
                hourly[eid] = s
    five = []
    for iv in state.read_edgedata(meandata["edge_300s"]):
        dur = iv["end"] - iv["begin"]
        states = {}
        for eid, attrs in iv["edges"].items():
            free, lanes, _ = info(eid)
            s = state.edge_state(attrs, dur, free, lanes)
            if s:
                states[eid] = s
        five.append({"begin": iv["begin"], "end": iv["end"], "edges": states})
    keep = counts.get("domain_edges")
    if keep is not None:
        # The buffer beyond the scene domain is simulated but not reported.
        hourly = {e: s for e, s in hourly.items() if e in keep}
        for iv in five:
            iv["edges"] = {e: s for e, s in iv["edges"].items() if e in keep}
    general_q = {}
    for iv in state.read_edgedata(meandata["general_3600s"]):
        dur = iv["end"] - iv["begin"]
        for eid, attrs in iv["edges"].items():
            general_q[eid] = attrs.get("entered", 0.0) * 3600 / dur

    # Calibration fit: per matched count (point direction), observed vs simulated.
    pairs_sim, pairs_sampled, pairs_rs, per_count = [], [], [], {}
    for r in counts["records"]:
        obs = r["aadf_general_dir"] * r["fraction"] * r["share"][period["hour"]]
        simq = general_q.get(r["edge"], 0.0)
        samp = sampled.get(r["edge"], 0)
        pairs_sim.append((obs, simq))
        pairs_sampled.append((obs, samp))
        pairs_rs.append((obs, sampled_all.get(r["edge"], 0)))
        per_count[(r["cp"], r["direction"], r["edge"])] = {
            "observed": round(obs),
            "sampled": samp,
            "simulated": round(simq),
            "geh": round(calibrate.geh(simq, obs), 2),
        }
    lengths = {e: info(e)[2] for e in hourly}
    stats = result["statistics"]
    return {
        "period": period,
        "dir": pdir,
        "hourly": hourly,
        "five_min": five,
        "per_count": per_count,
        "fit": {
            "route_sampler_sampled_vs_target": calibrate.fit_summary(pairs_rs),
            "after_capacity_screening_vs_target": calibrate.fit_summary(pairs_sampled),
            "simulated_vs_observed": calibrate.fit_summary(pairs_sim),
        },
        "summary": {
            **state.summary(hourly, lengths),
            "general_vehicles_sampled": general_vehicles,
            "capacity_screening": screening,
            "vehicles": stats.get("vehicles"),
            "teleports": stats.get("teleports"),
            "trip_statistics": stats.get("vehicleTripStatistics"),
        },
        "class_mix": mix,
        "bus": bus_info,
        "routes": routes,
        "mismatch": mismatch,
        "fcd": result["fcd"],
        "kinds": kinds,
        "config": result["config"],
        "additional": add_files,
        "route_files": route_files,
        "edgedata": meandata,
        "stopinfos": result.get("stopinfos"),
        "runtime_s": round(time.monotonic() - t0, 1),
    }


def _digest(path: Path) -> str:
    import hashlib

    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


# ---------------------------------------------------------------- viewer state document


def count_point_entries(counts: dict, results: list[dict]) -> list[dict]:
    """Count points with observed/simulated hourly flows and GEH per period."""
    by_point: dict[str, dict] = {}
    for r in counts["records"]:
        p = counts["points"][r["cp"]]
        key = f"{r['cp']}_{r['direction']}_{r['edge']}"
        entry = {
            "id": key,
            "count_point_id": int(r["cp"]),
            "road_name": p.road_name,
            "road_type": p.road_type,
            "x": p.x,
            "y": p.y,
            "direction": r["direction"],
            "aadf": round(p.aadf["all_motor_vehicles"]),
            "aadf_general_direction": round(r["aadf_general_dir"] * r["fraction"]),
            "estimation_method": p.estimation_method,
            "estimation_method_detailed": p.estimation_method_detailed,
            "year": p.year,
            "local_authority": p.local_authority_name,
            "matched_edge": r["edge"],
            "match_quality": r["quality"],
            "match_dist_m": r["dist_m"],
            "profile_source": r["profile_source"],
            "observed": {},
            "simulated": {},
            "geh": {},
        }
        for res in results:
            pid = res["period"]["id"]
            pc = res["per_count"][(r["cp"], r["direction"], r["edge"])]
            entry["observed"][pid] = pc["observed"]
            entry["simulated"][pid] = pc["simulated"]
            entry["geh"][pid] = pc["geh"]
        by_point[key] = entry
    return list(by_point.values())


def state_document(counts: dict, results: list[dict], tolerance: float, provenance: dict) -> tuple:
    """(traffic_state.json document, 5-minute document)."""
    net = counts["net"]
    used = sorted({e for r in results for e in r["hourly"]})
    edges = []
    for eid in used:
        e = net.getEdge(eid)
        shape = state.simplify([tuple(p[:2]) for p in e.getShape()], tolerance)
        if counts.get("half") is not None:
            shape = state.clip_square(shape, counts["half"]) or shape
        edges.append(
            {
                "id": eid,
                "name": e.getName() or "",
                "cls": road_class(e.getType()),
                "lanes": e.getLaneNumber(),
                "free_speed": round(e.getSpeed(), 2),
                "length": round(e.getLength(), 1),
                "shape": [[round(x, 1), round(y, 1)] for x, y in shape],
            }
        )
    keep = ("q", "v", "k", "k_lane", "occ", "wait", "los")
    doc = {
        "schema": "corridor-traffic-state-v1",
        "coordinate_frame": "ENU",
        "units": {
            "q": "veh/h",
            "v": "m/s",
            "k": "veh/km",
            "k_lane": "veh/km/lane",
            "occ": "%",
            "wait": "s (summed over vehicles in the interval)",
            "free_speed": "m/s",
            "x": "m",
            "y": "m",
        },
        "periods": [
            {k: r["period"][k] for k in ("id", "label", "hour", "start_s", "end_s", "sim_begin_s")}
            for r in results
        ],
        "edges": edges,
        "state": {
            r["period"]["id"]: {e: {k: s[k] for k in keep} for e, s in r["hourly"].items()}
            for r in results
        },
        "summary": {r["period"]["id"]: r["summary"] for r in results},
        "calibration": {r["period"]["id"]: r["fit"] for r in results},
        "count_points": count_point_entries(counts, results),
        "thresholds": state.THRESHOLDS,
        "provenance": provenance,
    }
    los_index = {k: i for i, k in enumerate(state.LOS)}
    five = {
        "schema": "corridor-traffic-state-5min-v1",
        "fields": ["q", "v", "k_lane", "los_index"],
        "los": list(state.LOS),
        "edges": used,
        "periods": {},
    }
    for r in results:
        ivs = r["five_min"]
        values = {}
        for eid in used:
            row = []
            for iv in ivs:
                s = iv["edges"].get(eid)
                row.append(
                    None if s is None else [s["q"], s["v"], s["k_lane"], los_index[s["los"]]]
                )
            if any(v is not None for v in row):
                values[eid] = row
        five["periods"][r["period"]["id"]] = {
            "intervals": [[iv["begin"], iv["end"]] for iv in ivs],
            "values": values,
        }
    return doc, five


def match_report(counts: dict) -> dict:
    recs, unmatched = counts["records"], counts["unmatched"]
    quality = defaultdict(int)
    for r in recs:
        quality[re.sub(r"; C split 50/50$", "", r["quality"])] += 1
    reasons = defaultdict(int)
    for u in unmatched:
        reasons[re.sub(r" \(.*\)$", "", u["reason"])] += 1
    pts_matched = {r["cp"] for r in recs}
    return {
        "points_inside_domain": len(counts["points"]) + len(counts["stale"]),
        "points_dropped_stale": len(counts["stale"]),
        "points_used": len(counts["points"]),
        "points_matched": len(pts_matched),
        "point_directions_matched": len({(r["cp"], r["direction"]) for r in recs}),
        "point_directions_unmatched": len(unmatched),
        "edges_with_targets": len({r["edge"] for r in recs}),
        "match_quality": dict(quality),
        "unmatched_reasons": dict(reasons),
        "unmatched": [{k: u[k] for k in ("cp", "direction", "reason")} for u in unmatched],
        "profile_sources": dict(
            sorted(
                {
                    s: sum(r["profile_source"] == s for r in recs)
                    for s in {r["profile_source"] for r in recs}
                }.items()
            )
        ),
        "direction_sources": dict(
            sorted(
                {
                    s: sum(p.direction_source == s for p in counts["points"].values())
                    for s in {p.direction_source for p in counts["points"].values()}
                }.items()
            )
        ),
    }


def write_json(path: Path, doc) -> int:
    path.write_text(json.dumps(doc, separators=(",", ":"), allow_nan=False) + "\n")
    return path.stat().st_size
