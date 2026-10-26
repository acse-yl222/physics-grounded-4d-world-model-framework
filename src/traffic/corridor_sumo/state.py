"""Per-edge traffic state from SUMO edgeData (meandata): flow, speed, density, LOS class.

Level of service (``los``) per edge and interval, documented in ``THRESHOLDS``:

1. speed ratio ``r = mean speed / edge free-flow speed`` (the edge speed limit) gives
   free (r >= 0.8), moderate (0.6-0.8), heavy (0.4-0.6) or congested (< 0.4);
2. density raises the class: ``k_lane >= 40`` veh/km/lane is at least heavy and
   ``k_lane >= 70`` congested (queues regardless of speed);
3. at low density (``k_lane < 7``) a slow edge is at most moderate: a few vehicles
   stopping at a signal or give-way lower the mean speed without congestion.

Edges without vehicles in an interval have no state (absent, never zero-filled).
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

LOS = ("free", "moderate", "heavy", "congested")
THRESHOLDS = {
    "speed_ratio": {"free": 0.8, "moderate": 0.6, "heavy": 0.4},
    "density_veh_km_lane": {"heavy_min": 40.0, "congested_min": 70.0, "low_max": 7.0},
    "free_speed": "edge speed limit (Overture speed_limits or class default)",
    "rules": [
        "r = mean speed / free speed: >=0.8 free, 0.6-0.8 moderate, 0.4-0.6 heavy, <0.4 congested",
        "k_lane >= 40 veh/km/lane: at least heavy; k_lane >= 70: congested",
        "k_lane < 7 veh/km/lane: at most moderate (isolated stops at signals/junctions)",
        "no vehicles in the interval: no state",
    ],
}


def classify(speed_ratio: float, k_lane: float, th: dict = THRESHOLDS) -> str:
    """Level-of-service class from speed ratio and lane density (see module docstring)."""
    sr, kd = th["speed_ratio"], th["density_veh_km_lane"]
    if speed_ratio >= sr["free"]:
        level = 0
    elif speed_ratio >= sr["moderate"]:
        level = 1
    elif speed_ratio >= sr["heavy"]:
        level = 2
    else:
        level = 3
    if k_lane >= kd["congested_min"]:
        level = 3
    elif k_lane >= kd["heavy_min"]:
        level = max(level, 2)
    elif k_lane < kd["low_max"]:
        level = min(level, 1)
    return LOS[level]


def read_edgedata(path: Path) -> list[dict]:
    """Intervals of a SUMO edgeData file: [{begin, end, edges: {id: attrs}}]."""
    out = []
    for _, el in ET.iterparse(path):
        if el.tag == "interval":
            edges = {e.get("id"): {k: _f(v) for k, v in e.attrib.items() if k != "id"} for e in el}
            out.append(
                {"begin": float(el.get("begin")), "end": float(el.get("end")), "edges": edges}
            )
            el.clear()
    return out


def _f(value: str):
    try:
        return float(value)
    except ValueError:
        return value


def edge_state(attrs: dict, duration: float, free_speed: float, lanes: int) -> dict | None:
    """{q veh/h, v m/s, k veh/km, k_lane veh/km/lane, occ %, wait s, los} or None if empty."""
    if attrs.get("sampledSeconds", 0) <= 0 or "speed" not in attrs:
        return None
    q = attrs.get("entered", 0.0) * 3600.0 / duration
    v = attrs["speed"]
    k = attrs.get("density", 0.0)
    k_lane = attrs.get("laneDensity", k / max(1, lanes))
    ratio = v / free_speed if free_speed > 0 else 1.0
    return {
        "q": round(q),
        "v": round(v, 2),
        "k": round(k, 1),
        "k_lane": round(k_lane, 1),
        "occ": round(attrs.get("occupancy", 0.0), 1),
        "wait": round(attrs.get("waitingTime", 0.0), 1),
        "ratio": round(ratio, 2),
        "los": classify(ratio, k_lane),
    }


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Douglas-Peucker polyline simplification (keeps both ends)."""
    if len(points) < 3:
        return list(points)
    (ax, ay), (bx, by) = points[0], points[-1]
    dx, dy = bx - ax, by - ay
    norm = math.hypot(dx, dy)
    best, index = -1.0, 0
    for i, (px, py) in enumerate(points[1:-1], 1):
        if norm == 0:
            d = math.hypot(px - ax, py - ay)
        else:
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
        if d > best:
            best, index = d, i
    if best <= tolerance:
        return [points[0], points[-1]]
    left = simplify(points[: index + 1], tolerance)
    return left[:-1] + simplify(points[index:], tolerance)


def los_shares(states: dict[str, dict], lengths: dict[str, float]) -> dict[str, float]:
    """Share of edge-km in each LOS class among edges with a state."""
    km = dict.fromkeys(LOS, 0.0)
    for edge, s in states.items():
        km[s["los"]] += lengths.get(edge, 0.0) / 1000
    total = sum(km.values())
    return {k: round(v / total, 3) if total else 0.0 for k, v in km.items()}


def summary(states: dict[str, dict], lengths: dict[str, float]) -> dict:
    """Length-weighted mean speed, edge-km per LOS class and edges with traffic."""
    km = sum(lengths.get(e, 0.0) for e in states) / 1000
    if not states:
        return {"edges_with_traffic": 0}
    vkm = sum(s["v"] * lengths.get(e, 0.0) for e, s in states.items()) / 1000
    return {
        "edges_with_traffic": len(states),
        "edge_km_with_traffic": round(km, 1),
        "mean_speed_kmh_length_weighted": round(3.6 * vkm / km, 1) if km else None,
        "los_edge_km_share": los_shares(states, lengths),
    }
