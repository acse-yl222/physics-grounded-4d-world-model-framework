"""Hourly traffic state on counted roads, estimated directly from DfT counts.

The calibrated SUMO periods (``periods.py``) under-carry the main roads on this
Overture network, so this module gives a second, observation-led estimate that does
not depend on the simulation:

* flow ``q`` (veh/h, general traffic, per direction) for every hour 07:00-19:00 is the
  count point's directional AADF times its hourly share from DfT raw counts (the same
  records ``periods.prepare_counts`` builds for calibration);
* capacity ``c`` = assumed lanes x assumed per-lane capacity by road type
  (``ASSUMPTIONS``);
* travel time per km: on grade-separated roads the BPR volume-delay function
  ``t = t0 (1 + a (q/c)^b)``; on signalised and junction-controlled roads the running
  time at the edge free speed plus HCM 2000 control delay per signal (uniform delay
  ``d1 = 0.5 C (1-g)^2 / (1 - min(1,x) g)`` and incremental delay
  ``d2 = 900 T [(x-1) + sqrt((x-1)^2 + 8 k I x / (c T))]``) times an assumed number
  of controlled junctions per km; speed ``v = 1 km / t``, density ``k = q / v``
  (veh/km) and ``k_lane = k / lanes``;
* level of service from the volume/capacity ratio ``x = q/c`` (``LOS_BOUNDS``) on
  junction-controlled roads, and from the speed ratio ``v / v0`` (``SPEED_BOUNDS``, as
  in ``state.py``) on grade-separated roads, where flow near capacity still moves.

Flows are observation-based; capacities, BPR parameters and so speeds, densities and
states are assumptions and say so in the output. Each estimate is drawn on the matched
edge and extended along same-named edges up to ``EXTEND_M`` each way. No hour outside
07:00-19:00 is estimated: DfT manual counts do not cover it.

  PYTHONPATH=src python3 -m traffic.corridor_sumo.count_state \
      project/imperial_corridor/configs/traffic_sumo.json --net NET --out count_state.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from common.storage import Storage

from . import dft, periods, tfl
from .state import simplify

LOS = ("free", "moderate", "heavy", "congested")
LOS_BOUNDS = (0.5, 0.75, 0.9)  # x = q/c: < 0.5 free, < 0.75 moderate, < 0.9 heavy, else congested
SPEED_BOUNDS = (0.8, 0.6, 0.4)  # v/v0: >= 0.8 free, >= 0.6 moderate, >= 0.4 heavy
EXTEND_M = 300.0
ASSUMPTIONS = {
    "bpr": {"a": 0.15, "b": 4},
    "signals": {
        "cycle_s": 90,
        "green_ratio": 0.5,
        "analysis_period_h": 0.25,
        "k": 0.5,
        "I": 1.0,
        "per_km": {
            "motorway": 0,
            "trunk_grade_separated": 0,
            "a_road_signalised": 3.0,
            "b_road": 2.5,
            "minor": 1.5,
        },
    },
    "capacity_veh_h_lane": {
        "motorway": 1800,
        "trunk_grade_separated": 1600,
        "a_road_signalised": 900,
        "b_road": 800,
        "minor": 600,
    },
    "min_lanes_per_direction": {"motorway": 3, "a_road": 2, "other": 1},
    "notes": [
        (
            "Per-lane capacities are typical urban values (saturation flow about 1,800 "
            "veh/h with roughly half of each signal cycle green on signalised roads); "
            "they are assumptions, not measured at these sites."
        ),
        (
            "Overture lane counts are often missing, so major roads get at least the "
            "minimum lanes per direction above."
        ),
        "Flows are general traffic (all motor vehicles minus buses and coaches).",
        (
            "Controlled junctions per km, cycle length and green share are typical inner "
            "London values assumed uniformly per road type, not the actual signal plans."
        ),
    ],
}


def road_kind(road_name: str, edge_type: str, speed_ms: float) -> str:
    name = (road_name or "").upper()
    if name.startswith("M") or "motorway" in edge_type:
        return "motorway"
    if "trunk" in edge_type and speed_ms >= 50 / 3.6:
        return "trunk_grade_separated"
    if name.startswith("A"):
        return "a_road_signalised"
    if name.startswith("B"):
        return "b_road"
    return "minor"


def lanes_for(kind: str, edge_lanes: int) -> int:
    floor = ASSUMPTIONS["min_lanes_per_direction"]
    minimum = (
        floor["motorway"]
        if kind == "motorway"
        else floor["a_road"]
        if kind in ("a_road_signalised", "trunk_grade_separated")
        else floor["other"]
    )
    return max(edge_lanes, minimum)


def classify(x: float, bounds=LOS_BOUNDS) -> str:
    return LOS[next((i for i, b in enumerate(bounds) if x < b), len(bounds))]


def control_delay_s(x: float, capacity: float) -> float:
    """HCM 2000 signal control delay (s/veh) at volume/capacity ``x``."""
    sg = ASSUMPTIONS["signals"]
    cyc, g, t = sg["cycle_s"], sg["green_ratio"], sg["analysis_period_h"]
    d1 = 0.5 * cyc * (1 - g) ** 2 / (1 - min(1.0, x) * g)
    d2 = 900 * t * ((x - 1) + math.sqrt((x - 1) ** 2 + 8 * sg["k"] * sg["I"] * x / (capacity * t)))
    return d1 + d2


def link_state(q: float, capacity: float, v0_ms: float, lanes: int, kind: str) -> dict:
    """Flow (veh/h) -> speed (m/s), density (veh/km, veh/km/lane), x and LOS."""
    x = q / capacity if capacity > 0 else math.inf
    per_km = ASSUMPTIONS["signals"]["per_km"][kind]
    if per_km:
        t_km = 1000 / v0_ms + per_km * control_delay_s(x, capacity)
    else:
        a, b = ASSUMPTIONS["bpr"]["a"], ASSUMPTIONS["bpr"]["b"]
        t_km = 1000 / v0_ms * (1 + a * x**b)
    v = 1000 / t_km
    k = q / (v * 3.6)
    if per_km:
        los = classify(x)
    else:
        ratio = v / v0_ms
        los = LOS[next((i for i, b in enumerate(SPEED_BOUNDS) if ratio >= b), len(SPEED_BOUNDS))]
    return {
        "q": round(q),
        "v": round(v, 2),
        "k": round(k, 1),
        "k_lane": round(k / lanes, 1),
        "x": round(x, 3),
        "los": los,
    }


def _name(edge) -> str:
    return (edge.getName() or "").strip().lower()


def _angle(a, b) -> float:
    (ax0, ay0), (ax1, ay1) = a.getShape()[-2], a.getShape()[-1]
    (bx0, by0), (bx1, by1) = b.getShape()[0], b.getShape()[1]
    h1 = math.atan2(ay1 - ay0, ax1 - ax0)
    h2 = math.atan2(by1 - by0, bx1 - bx0)
    return abs(math.atan2(math.sin(h2 - h1), math.cos(h2 - h1)))


def extend(edge, limit_m: float, taken: set[str]) -> list:
    """Edges continuing ``edge`` with the same name, upstream then downstream."""
    name = _name(edge)
    if not name:
        return [edge]

    def walk(start, forward):
        out, length, cur = [], 0.0, start
        while length < limit_m:
            nxt = (
                [e for e in cur.getOutgoing() if e.getToNode() != cur.getFromNode()]
                if forward
                else [e for e in cur.getIncoming() if e.getFromNode() != cur.getToNode()]
            )
            nxt = [e for e in nxt if _name(e) == name and e.getID() not in taken]
            if not nxt:
                break
            here = cur
            cur = min(nxt, key=lambda e: _angle(here, e) if forward else _angle(e, here))
            if cur in out or cur == start:
                break
            out.append(cur)
            length += cur.getLength()
        return out

    return [*reversed(walk(edge, False)), edge, *walk(edge, True)]


def estimate(counts: dict) -> dict:
    """Segments with hourly BPR states for every matched count record."""
    net = counts["net"]
    taken: set[str] = set()
    segments = []
    for r in sorted(counts["records"], key=lambda r: -r["aadf_general_dir"] * r["fraction"]):
        if r["edge"] in taken:
            continue
        edge = net.getEdge(r["edge"])
        point = counts["points"][r["cp"]]
        speed = edge.getSpeed()
        kind = road_kind(point.road_name, edge.getType() or "", speed)
        lanes = lanes_for(kind, sum(1 for ln in edge.getLanes() if ln.allows("passenger")) or 1)
        capacity = lanes * ASSUMPTIONS["capacity_veh_h_lane"][kind]
        chain = extend(edge, EXTEND_M, taken)
        taken.update(e.getID() for e in chain)
        shape = []
        for e in chain:
            pts = [(round(x, 1), round(y, 1)) for x, y in e.getShape()]
            shape += pts[1:] if shape and pts[0] == shape[-1] else pts
        hourly = {}
        for h in dft.DFT_HOURS:
            q = r["aadf_general_dir"] * r["fraction"] * r["share"][h]
            hourly[str(h)] = link_state(q, capacity, speed, lanes, kind)
        segments.append(
            {
                "count_point_id": int(r["cp"]),
                "direction": r["direction"],
                "road_name": point.road_name,
                "road_type": point.road_type,
                "year": point.year,
                "estimation_method": point.estimation_method,
                "profile_source": r["profile_source"],
                "match_quality": r["quality"],
                "edges": [e.getID() for e in chain],
                "kind": kind,
                "lanes_assumed": lanes,
                "capacity_veh_h": capacity,
                "free_speed": round(speed, 2),
                "shape": [list(p) for p in simplify(shape, 1.0)],
                "hourly": hourly,
            }
        )
    return {"segments": segments, "summary": summarise(segments)}


def summarise(segments: list[dict]) -> dict:
    """Per hour: share of segment length by LOS and length-weighted mean speed."""
    out = {}
    for h in dft.DFT_HOURS:
        km, by, speed_km = 0.0, defaultdict(float), 0.0
        for s in segments:
            pts = s["shape"]
            length = sum(math.dist(a, b) for a, b in itertools.pairwise(pts)) / 1000
            st = s["hourly"][str(h)]
            km += length
            by[st["los"]] += length
            speed_km += st["v"] * 3.6 * length
        out[str(h)] = {
            "km": round(km, 1),
            "share": {k: round(by[k] / km, 4) if km else 0.0 for k in LOS},
            "mean_speed_kmh": round(speed_km / km, 1) if km else None,
        }
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("config", type=Path)
    p.add_argument("--net", type=Path, required=True, help="SUMO net the periods ran on")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    cfg = json.loads(args.config.read_text())
    storage = Storage.load()
    scene = cfg["scene_id"]
    geo = json.loads((storage.metadata(scene) / cfg["geometry_config"]).read_text())
    dfcfg = cfg["dft"]
    dft_dir = storage.assets(scene, "input") / dfcfg.get("dir", "dft_traffic")
    la_ids = sorted(int(k) for k in dfcfg["local_authorities"])
    tables = periods.load_tables(
        dft_dir, la_ids, dft.domain_bbox(geo["origin"], geo["domain_m"] / 2)
    )
    enu = tfl.Enu(geo["origin"]["longitude"], geo["origin"]["latitude"])
    counts = periods.prepare_counts(args.net, dfcfg, tables, enu, [])
    doc = {
        "schema": "corridor-count-state-v1",
        "coordinate_frame": "ENU",
        "units": {"q": "veh/h", "v": "m/s", "k": "veh/km", "k_lane": "veh/km/lane"},
        "hours": list(dft.DFT_HOURS),
        **estimate(counts),
        "los_rules": {
            "junction_controlled": {"x_below": dict(zip(LOS[:-1], LOS_BOUNDS, strict=True))},
            "grade_separated": {
                "speed_ratio_at_least": dict(zip(LOS[:-1], SPEED_BOUNDS, strict=True))
            },
        },
        "assumptions": ASSUMPTIONS,
        "provenance": {
            "created_at": datetime.now(UTC).isoformat(),
            "counts": "UK DfT road traffic counts (AADF, AADF by direction, raw manual "
            "counts), Open Government Licence v3.0; estimation_method per point",
            "dft_index": str(dft_dir / "index.json"),
            "net": str(args.net),
            "flows": "observation-based: directional AADF x weekday hourly share 07-19",
            "state": "speed, density and LOS are BPR / HCM control-delay estimates from "
            "assumed capacities and signal settings",
            "hours_not_covered": "19:00-07:00 (no DfT hourly counts)",
        },
    }
    args.out.write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    print(f"{len(doc['segments'])} segments -> {args.out} ({args.out.stat().st_size} bytes)")
    for h, s in doc["summary"].items():
        print(h, s["mean_speed_kmh"], s["share"])


if __name__ == "__main__":
    main()
