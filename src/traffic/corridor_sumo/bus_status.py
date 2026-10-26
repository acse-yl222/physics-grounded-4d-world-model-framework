"""Bus status per route-direction and stop: SUMO stop output vs the BODS GTFS schedule.

Reads ``schedule.json`` and ``stops.json`` written by ``gtfs_bus build`` and, for
each simulated period, the period's ``trips.json`` plus the run directory's
``stopinfos.xml`` (SUMO ``--stop-output``). Writes ``bus_status.json``.

  PYTHONPATH=src python3 -m traffic.corridor_sumo.bus_status \\
      project/imperial_corridor/configs/traffic_sumo.json [RUN_DIR ...] [--out PATH]

A run directory is assigned to a period by ``period=DIR``, by a ``period.json`` in
it, or by a period name (``am_peak``, ...) in its path. Periods without stop output
are reported from the schedule alone (status ``"schedule only"``).

Schedule (stop locations, timetables, trips/h, headways, run times) is real BODS
GTFS data; simulated delays, speeds, regularity and status are SUMO model estimates
driven partly by synthetic car/taxi demand. No real-time vehicle positions or
passenger loads were available.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

CLASSES = ["on time", "minor delay", "major delay", "severe"]
SCHEDULE_ONLY = "schedule only"
NO_CALLS = "no simulated calls"
NO_SERVICE = "no service"
NOT_SIMULATED = "not simulated"
MODEL_GAP = "model gap"
THRESHOLDS = {
    "classes": CLASSES,
    "mean_delay_min": [2.0, 5.0, 10.0],
    "p90_delay_min": [5.0, 10.0, 20.0],
    "unreached_share_gap": 0.25,
    "bunching_factor": 0.5,
    "censor_margin_min": 10.0,
    "other_statuses": {
        "schedule only": "no stop output for the period (schedule-based fields only)",
        "no service": "no scheduled trips of the route-direction in the period",
        "not simulated": "scheduled, but its stops could not be mapped onto the SUMO net",
        "no simulated calls": "simulated, but no scheduled call fell inside the evaluated window",
        "model gap": "more than unreached_share_gap of the scheduled calls were never reached "
        "in the model (buses teleported past simulated jams), so its delays are not reliable",
    },
    "rule": "class = worse of (mean arrival delay vs mean_delay_min) and (90th percentile "
    "delay vs p90_delay_min): below the first bound 'on time', below the second "
    "'minor delay', below the third 'major delay', else 'severe'; 'model gap' instead "
    "when more than unreached_share_gap of the scheduled calls in the window were not "
    "reached. Delay = simulated arrival (stopinfo 'started') - scheduled arrival, over "
    "calls scheduled in [period start, period end - censor_margin_min] (warm-up and the "
    "last minutes, whose late buses would be cut off by the end of the run, excluded). "
    "Bunching = share of simulated headways at the busiest stop shorter than "
    "bunching_factor x the scheduled mean headway; regularity = coefficient of "
    "variation of those headways.",
}


# ---------------------------------------------------------------- parsing


def parse_stopinfos(path: Path) -> dict[str, list[dict]]:
    """SUMO stop output -> ``{vehicle: [{bus_stop, started, ended, lane}]}`` by start."""
    out = defaultdict(list)
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag != "stopinfo":
            continue
        a = el.attrib
        stop = a.get("busStop") or a.get("parkingArea") or a.get("containerStop")
        out[a["id"]].append(
            {
                "bus_stop": stop,
                "started": float(a["started"]),
                "ended": float(a["ended"]) if a.get("ended") not in (None, "") else None,
                "lane": a.get("lane"),
            }
        )
        el.clear()
    for calls in out.values():
        calls.sort(key=lambda c: c["started"])
    return dict(out)


def match_calls(scheduled: list, observed: list[dict]) -> list[dict]:
    """Pair scheduled calls ``[atco, busStop, arr, dep, offset_m]`` with observed stops in
    order (each observation is used once; repeated stops are matched sequentially)."""
    out, j = [], 0
    for call in scheduled:
        atco, bus_stop, arr, dep = call[:4]
        offset = call[4] if len(call) > 4 else None
        rec = {"stop": atco, "bus_stop": bus_stop, "arr": arr, "dep": dep, "offset": offset}
        k = j
        while k < len(observed) and observed[k]["bus_stop"] != bus_stop:
            k += 1
        if k < len(observed):
            rec["obs_arr"], rec["obs_dep"] = observed[k]["started"], observed[k]["ended"]
            j = k + 1
        out.append(rec)
    return out


# ---------------------------------------------------------------- metrics


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile (``q`` in 0..100)."""
    ordered = sorted(values)
    if not ordered:
        return math.nan
    pos = (len(ordered) - 1) * q / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def classify(mean_delay_s, p90_delay_s, unreached_share=0.0, thresholds=THRESHOLDS) -> str:
    def level(value_min, bounds):
        return next((i for i, b in enumerate(bounds) if value_min < b), len(bounds))

    if unreached_share > thresholds["unreached_share_gap"]:
        return MODEL_GAP
    lvl = max(
        level(mean_delay_s / 60, thresholds["mean_delay_min"]),
        level(p90_delay_s / 60, thresholds["p90_delay_min"]),
    )
    return CLASSES[lvl]


def regularity(arrivals: list[float], scheduled_headway_s: float | None, factor: float) -> dict:
    """Headway CV and bunching share from arrival times at one stop."""
    times = sorted(arrivals)
    gaps = [b - a for a, b in itertools.pairwise(times)]
    out = {"headways": len(gaps)}
    if len(gaps) >= 2:
        mean = statistics.fmean(gaps)
        out["headway_mean_min"] = round(mean / 60, 2)
        out["headway_cv"] = round(statistics.pstdev(gaps) / mean, 3) if mean > 0 else None
    if gaps and scheduled_headway_s:
        out["bunching_share"] = round(
            sum(g < factor * scheduled_headway_s for g in gaps) / len(gaps), 3
        )
    return out


def route_period(
    vehicles: dict, observed: dict, route: dict, period: str, window, thresholds=THRESHOLDS
) -> tuple[dict, list[dict]]:
    """Simulated metrics of one route-direction in one period; also the call events."""
    t0, t1 = window
    t_eval = t1 - 60 * thresholds["censor_margin_min"]
    events, runtimes, sched_runtimes, speeds = [], [], [], []
    for vid, veh in vehicles.items():
        calls = match_calls(veh["stops"], observed.get(vid, []))
        events += [dict(c, vehicle=vid) for c in calls if t0 <= c["arr"] <= t_eval]
        first, last = calls[0], calls[-1]
        if (
            t0 <= first["dep"] < t1
            and first.get("obs_dep") is not None
            and last.get("obs_arr") is not None
        ):
            rt = last["obs_arr"] - first["obs_dep"]
            if rt > 0:
                runtimes.append(rt)
                sched_runtimes.append(last["arr"] - first["dep"])
                if last.get("offset") is not None:
                    speeds.append((last["offset"] - first["offset"]) / rt * 3.6)
    sim = {"calls_scheduled": len(events)}
    delays = [e["obs_arr"] - e["arr"] for e in events if "obs_arr" in e]
    sim["calls_reached"] = len(delays)
    unreached = (1 - len(delays) / len(events)) if events else 0.0
    sim["unreached_share"] = round(unreached, 3)
    if delays:
        sim["mean_delay_min"] = round(statistics.fmean(delays) / 60, 2)
        sim["p90_delay_min"] = round(percentile(delays, 90) / 60, 2)
    if runtimes:
        sim["runtime_min"] = round(statistics.median(runtimes) / 60, 2)
        sim["scheduled_runtime_min"] = round(statistics.median(sched_runtimes) / 60, 2)
        sim["runtime_ratio"] = round(
            statistics.median(
                r / s for r, s in zip(runtimes, sched_runtimes, strict=True) if s > 0
            ),
            3,
        )
        sim["trips_completed"] = len(runtimes)
    if speeds:
        sim["speed_kmh"] = round(statistics.median(speeds), 2)
    busiest = route.get("busiest_stop")
    sched = (route.get("schedule") or {}).get(period, {})
    head_s = sched.get("headway_min", 0) * 60 or None
    arrivals = [e["obs_arr"] for e in events if e["stop"] == busiest and "obs_arr" in e]
    sim["regularity"] = {
        "stop": busiest,
        **regularity(arrivals, head_s, thresholds["bunching_factor"]),
    }
    if not events and not sched.get("trips_per_h") and not vehicles:
        status = NO_SERVICE  # nothing scheduled at the busiest stop in this period
    elif not vehicles:
        status = NOT_SIMULATED  # scheduled, but not mapped onto the SUMO network
    elif not events:
        status = NO_CALLS
    elif not delays:
        status = CLASSES[-1]
    else:
        status = classify(statistics.fmean(delays), percentile(delays, 90), unreached, thresholds)
    sim["status"] = status
    return sim, events


def compute(schedule: dict, stops: list[dict], runs: dict, thresholds=THRESHOLDS) -> dict:
    """``runs``: ``{period: {"trips": trips.json dict, "stopinfos": path or None}}``."""
    periods = schedule["periods"]
    observed = {}
    for period, run in runs.items():
        path = run.get("stopinfos")
        observed[period] = parse_stopinfos(Path(path)) if path and Path(path).is_file() else None
    by_key = defaultdict(lambda: defaultdict(dict))
    for period, run in runs.items():
        for vid, veh in (run.get("trips") or {}).get("vehicles", {}).items():
            by_key[veh["key"]][period][vid] = veh
    stop_delays = defaultdict(lambda: defaultdict(list))
    routes = []
    for route in schedule["routes"]:
        simulated, status = {}, {}
        for period, (h0, h1) in periods.items():
            if observed.get(period) is None:
                status[period] = SCHEDULE_ONLY
                continue
            sim, events = route_period(
                by_key[route["key"]][period],
                observed[period],
                route,
                period,
                (3600 * h0, 3600 * h1),
                thresholds,
            )
            simulated[period] = sim
            status[period] = sim["status"]
            for e in events:
                if "obs_arr" in e:
                    stop_delays[e["stop"]][period].append(e["obs_arr"] - e["arr"])
        sched = {}
        for period in periods:
            w = route["schedule"].get(period, {})
            sched[period] = {
                "trips_per_h": w.get("trips_per_h", 0),
                "headway_min": w.get("headway_min"),
                "headway_busiest_stop_min": w.get("headway_busiest_stop_min"),
                "runtime_min": w.get("runtime_min"),
                "speed_kmh": w.get("speed_kmh"),
            }
        routes.append(
            {
                "route": route["route"],
                "direction": route["direction"],
                "route_id": route.get("route_id"),
                "agency": route.get("agency"),
                "headsign": route.get("headsign"),
                "stops": route["stops"],
                "path": route["path"],
                "busiest_stop": route.get("busiest_stop"),
                "matching": route.get("matching"),
                "schedule": sched,
                "simulated": simulated,
                "status": status,
            }
        )
    per_h = schedule.get("stop_buses_per_h", {})
    stop_out = []
    for s in stops:
        rec = dict(s)
        rec["scheduled_buses_per_h"] = {p: per_h.get(s["id"], {}).get(p, 0) for p in periods}
        rec["est_mean_delay_min"] = {
            p: round(statistics.fmean(v) / 60, 2) for p, v in stop_delays[s["id"]].items() if v
        }
        stop_out.append(rec)
    return {
        "schema": "corridor-bus-status-v1",
        "service_date": schedule.get("service_date"),
        "periods": {
            p: {
                "window": [f"{a:02d}:00", f"{b:02d}:00"],
                "simulated": observed.get(p) is not None,
                "stopinfos": str(runs.get(p, {}).get("stopinfos") or "") or None,
            }
            for p, (a, b) in periods.items()
        },
        "routes": routes,
        "stops": stop_out,
        "thresholds": thresholds,
        "provenance": {
            **schedule.get("provenance", {}),
            "simulated_metrics": "SUMO model estimates (stop output) from the period runs "
            "listed in 'periods'; not observed bus performance",
            "created_at": datetime.now(UTC).isoformat(),
        },
    }


# ---------------------------------------------------------------- CLI


def assign_runs(run_args: list[str], periods) -> dict[str, Path]:
    out = {}
    for arg in run_args:
        if "=" in arg:
            name, path = arg.split("=", 1)
        else:
            path, name = arg, None
            info = Path(path) / "period.json"
            if info.is_file():
                name = json.loads(info.read_text()).get("period")
            if name is None:
                name = next((p for p in periods if p in str(Path(path).resolve())), None)
        if name not in periods:
            raise SystemExit(f"cannot tell the period of run directory {path}; use period=DIR")
        out[name] = Path(path)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("config", help="traffic_sumo.json path or scene id")
    p.add_argument("runs", nargs="*", help="period run directories (period=DIR or DIR)")
    p.add_argument("--gtfs-dir", type=Path, help="gtfs_bus build output (default from config)")
    p.add_argument("--stopinfos", default="stopinfos.xml", help="file name in each run dir")
    p.add_argument("--out", type=Path, help="default: <gtfs-dir>/bus_status.json")
    args = p.parse_args(argv)

    gtfs_dir = args.gtfs_dir
    cfg = {}
    if gtfs_dir is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from common.storage import Storage

        storage = Storage.load()
        cfg_path = Path(args.config)
        if not cfg_path.is_file():
            cfg_path = storage.metadata(args.config) / "configs/traffic_sumo.json"
        cfg = json.loads(cfg_path.read_text())
        gcfg = cfg.get("gtfs", {})
        gtfs_dir = storage.scratch(cfg["scene_id"], "traffic_sumo", gcfg.get("output_dir", "gtfs"))
    schedule = json.loads((gtfs_dir / "schedule.json").read_text())
    stops = json.loads((gtfs_dir / "stops.json").read_text())
    thresholds = dict(THRESHOLDS)
    for k, v in cfg.get("gtfs", {}).get("status", {}).items():
        key = k if k in thresholds else k.removesuffix("_min") + "_min"
        if key in thresholds:
            thresholds[key] = v
    assigned = assign_runs(args.runs, schedule["periods"])
    runs = {}
    for period in schedule["periods"]:
        trips_path = gtfs_dir / period / "trips.json"
        trips = json.loads(trips_path.read_text()) if trips_path.is_file() else {}
        run_dir = assigned.get(period)
        stopinfos = run_dir / args.stopinfos if run_dir else None
        if run_dir and not stopinfos.is_file():
            print(f"warning: {stopinfos} missing; {period} reported from the schedule only")
            stopinfos = None
        runs[period] = {"trips": trips, "stopinfos": stopinfos}
    result = compute(schedule, stops, runs, thresholds)
    out = args.out or gtfs_dir / "bus_status.json"
    out.write_text(json.dumps(result, separators=(",", ":")) + "\n")
    counts = defaultdict(lambda: defaultdict(int))
    for r in result["routes"]:
        for period, cls in r["status"].items():
            counts[period][cls] += 1
    print(json.dumps({"out": str(out), "status_counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
