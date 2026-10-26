"""Count points -> SUMO edges, hourly edge targets and routeSampler calibration.

Matching: DfT major roads carry route numbers ("A4"). On an OSM network the edges keep
the OSM ``ref`` tag (e.g. "A4;A315"), so an edge whose ref contains the DfT route number
is preferred and edges with only other refs are skipped. Overture names are street names
("Cromwell Road") without refs, so there a name test only applies when the DfT road name
is a street name. Otherwise a count point direction is matched to the nearest passenger
edge within
``radius_m`` that has a class compatible with the DfT road type and whose heading agrees
with the direction of travel; edges named after the link's start/end junction roads (the
crossing streets) are not used. The match quality is recorded per count.
"""

from __future__ import annotations

import itertools
import math
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from . import sumo_env
from .osm_net import road_class

# ENU heading (radians CCW from east) of each DfT direction of travel.
CARDINAL = {"E": 0.0, "N": math.pi / 2, "W": math.pi, "S": -math.pi / 2}
MAJOR_CLASSES = ("motorway", "trunk", "primary", "secondary")
MINOR_CLASSES = ("secondary", "tertiary", "unclassified", "residential", "living_street")
# Weaker but acceptable class pairings (recorded as such).
WEAK_CLASSES = {"Major": ("tertiary",), "Minor": ("primary", "trunk", "service")}
REF = re.compile(r"^[ABMCU]\d*[A-Z]?$")
ABBREVIATIONS = {
    "rd": "road",
    "st": "street",
    "ave": "avenue",
    "av": "avenue",
    "ln": "lane",
    "pl": "place",
    "sq": "square",
    "gdns": "gardens",
    "cres": "crescent",
    "tce": "terrace",
    "hwy": "highway",
    "gr": "grove",
    "ct": "court",
    "dr": "drive",
    "cl": "close",
    "pk": "park",
    "bdy": "broadway",
    "bri": "bridge",
}


def normalise_name(name: str | None) -> str:
    """Lower case, punctuation removed, common GB street abbreviations expanded."""
    words = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower().replace("'", "")).split()
    return " ".join(ABBREVIATIONS.get(w, w) for w in words)


def refs_of(value: str | None) -> set[str]:
    """OSM ``ref`` values of an edge ("A4;A315" -> {"A4", "A315"}), upper case, no spaces."""
    return {r.strip().replace(" ", "").upper() for r in (value or "").split(";") if r.strip()}


def is_ref(road_name: str) -> bool:
    """True for DfT route numbers/classes such as A4, A315, B302, C, U."""
    return bool(REF.match((road_name or "").strip().upper()))


def angle_diff(a: float, b: float) -> float:
    """Absolute difference of two angles in radians, in [0, pi]."""
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


def heading_matches(heading: float, direction: str, tolerance_deg: float = 75.0) -> bool:
    """Whether an ENU edge heading agrees with a DfT direction of travel (N/E/S/W).

    ``C`` (combined) and ``J`` accept any heading. DfT labels a diagonal road with a
    single cardinal direction, hence the generous tolerance (< 90 degrees still rejects
    the opposite carriageway).
    """
    if direction not in CARDINAL:
        return True
    return math.degrees(angle_diff(heading, CARDINAL[direction])) <= tolerance_deg


def class_fit(road_type: str, edge_class: str) -> int | None:
    """0 = compatible, 1 = weak, None = incompatible."""
    good = MAJOR_CLASSES if road_type == "Major" else MINOR_CLASSES
    if edge_class in good:
        return 0
    if edge_class in WEAK_CLASSES.get(road_type, ()):
        return 1
    return None


def heading_at(shape: list[tuple[float, float]], x: float, y: float) -> tuple[float, float]:
    """(distance, ENU heading) of the shape segment closest to (x, y)."""
    best = (math.inf, 0.0)
    for (ax, ay), (bx, by) in itertools.pairwise(shape):
        dx, dy = bx - ax, by - ay
        seg = dx * dx + dy * dy
        t = 0.0 if seg == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / seg))
        d = math.hypot(ax + t * dx - x, ay + t * dy - y)
        if d < best[0] and seg > 0:
            best = (d, math.atan2(dy, dx))
    return best


def choose_edge(candidates: list[dict], point: dict, direction: str, cfg: dict) -> dict:
    """Pick the edge for one count point direction from pre-computed candidates.

    ``candidates``: {id, name, cls, dist, heading, passenger}. Returns
    {edge, quality, dist} or {edge: None, reason}.
    """
    tol = cfg.get("heading_tolerance_deg", 75.0)
    junctions = {normalise_name(point.get(k)) for k in ("start_junction", "end_junction")}
    junctions.discard("")
    junction_refs = set().union(
        *(refs_of(point.get(k)) for k in ("start_junction", "end_junction"))
    )
    road = point.get("road_name", "")
    want_ref = road.strip().replace(" ", "").upper() if is_ref(road) else ""
    want_name = "" if want_ref else normalise_name(road)
    options, reasons = [], defaultdict(int)
    for c in candidates:
        if not c["passenger"]:
            reasons["no_passenger_access"] += 1
            continue
        if not heading_matches(c["heading"], direction, tol):
            reasons["heading"] += 1
            continue
        refs = refs_of(c.get("ref"))
        if want_ref and want_ref in refs:
            options.append((0, 0, c["dist"], c, "ref+heading"))
            continue
        if want_ref and refs and len(want_ref) > 1:
            # Another numbered road (a crossing or parallel route): only as a last resort
            # when it is near and class-compatible (OSM and DfT numbering can disagree).
            fit = class_fit(point.get("road_type", ""), c["cls"])
            if (
                fit is not None
                and not refs & junction_refs
                and c["dist"] <= cfg.get("near_m", 20.0)
            ):
                options.append((2, fit, c["dist"], c, "class+heading (other ref)"))
            else:
                reasons["other_ref"] += 1
            continue
        if refs & junction_refs:
            reasons["junction_road"] += 1
            continue
        name = normalise_name(c["name"])
        if want_name and name == want_name:
            options.append((0, 0, c["dist"], c, "name+heading"))
            continue
        if name and name in junctions and name != want_name:
            reasons["junction_road"] += 1
            continue
        fit = class_fit(point.get("road_type", ""), c["cls"])
        if fit is None:
            reasons["class"] += 1
            continue
        near = c["dist"] <= cfg.get("near_m", 20.0)
        quality = ("class+heading" if fit == 0 else "weak_class+heading") + (
            "" if near else " (far)"
        )
        options.append((1, fit, c["dist"], c, quality))
    if not options:
        if not candidates:
            return {"edge": None, "reason": f"no edge within {cfg.get('radius_m', 40)} m"}
        why = ", ".join(f"{k}: {v}" for k, v in sorted(reasons.items()))
        return {"edge": None, "reason": f"no compatible edge ({why})"}
    _, _, dist, best, quality = min(options, key=lambda o: o[:3])
    return {"edge": best["id"], "quality": quality, "dist_m": round(dist, 1)}


def edge_candidates(net, x: float, y: float, radius: float) -> list[dict]:
    """Edges near (x, y) with distance and local heading (sumolib network)."""
    out = []
    for edge, _ in net.getNeighboringEdges(x, y, radius, includeJunctions=False):
        dist, heading = heading_at(edge.getShape(), x, y)
        if dist <= radius:
            out.append(
                {
                    "id": edge.getID(),
                    "name": edge.getName(),
                    "cls": road_class(edge.getType()),
                    "ref": edge.getParam("ref"),
                    "dist": dist,
                    "heading": heading,
                    "passenger": edge.allows("passenger"),
                }
            )
    return out


# ---------------------------------------------------------------- fit statistics


def geh(model: float, observed: float) -> float:
    """GEH statistic of hourly flows: sqrt(2 (M - C)^2 / (M + C))."""
    if model + observed <= 0:
        return 0.0
    return math.sqrt(2 * (model - observed) ** 2 / (model + observed))


def r_squared(observed: list[float], model: list[float]) -> float | None:
    """Coefficient of determination of ``model`` against ``observed`` (1 - SSres/SStot)."""
    if len(observed) < 2:
        return None
    mean = statistics.fmean(observed)
    ss_tot = sum((o - mean) ** 2 for o in observed)
    ss_res = sum((o - m) ** 2 for o, m in zip(observed, model, strict=True))
    return None if ss_tot == 0 else 1 - ss_res / ss_tot


def fit_summary(pairs: list[tuple[float, float]]) -> dict:
    """GEH distribution and R^2 for (observed, model) hourly flow pairs."""
    if not pairs:
        return {"n": 0}
    gehs = sorted(geh(m, o) for o, m in pairs)
    obs, mod = [o for o, _ in pairs], [m for _, m in pairs]
    r2 = r_squared(obs, mod)
    return {
        "n": len(pairs),
        "geh_lt_5_pct": round(100 * sum(g < 5 for g in gehs) / len(gehs), 1),
        "geh_lt_10_pct": round(100 * sum(g < 10 for g in gehs) / len(gehs), 1),
        "geh_median": round(statistics.median(gehs), 2),
        "geh_p90": round(gehs[int(0.9 * (len(gehs) - 1))], 2),
        "r2": None if r2 is None else round(r2, 3),
        "observed_total_veh_h": round(sum(obs)),
        "model_total_veh_h": round(sum(mod)),
    }


# ---------------------------------------------------------------- routeSampler


def write_edgedata(intervals: list[dict], path: Path, attribute: str = "entered") -> None:
    """edgeData counts for routeSampler: [{id, begin, end, counts: {edge: veh}}]."""
    root = ET.Element("data")
    for iv in intervals:
        el = ET.SubElement(
            root, "interval", id=iv["id"], begin=f"{iv['begin']:g}", end=f"{iv['end']:g}"
        )
        for edge, value in sorted(iv["counts"].items()):
            ET.SubElement(el, "edge", {"id": edge, attribute: str(round(value))})
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


def candidate_routes(net: Path, out_dir: Path, vtypes: Path, cfg: dict, seed: int, log) -> Path:
    """Large routed candidate set (randomTrips + duarouter) for routeSampler.

    Two pools: long fringe-weighted trips biased toward fast roads (through traffic) and
    unweighted shorter trips (local traffic).
    """
    files = []
    for k, pool in enumerate(cfg["pools"]):
        name = f"cand_{pool['id']}"
        trips, routes = out_dir / f"{name}.trips.xml", out_dir / f"{name}.rou.xml"
        cmd = [sys.executable, sumo_env.tool("randomTrips.py"), "-n", net, "-a", vtypes]
        cmd += ["-o", trips, "-r", routes, "-b", 0, "-e", pool["trips"], "-p", 1]
        cmd += ["--seed", seed + k, "--prefix", f"{pool['id']}_"]
        cmd += ["--trip-attributes", 'type="car"', "--edge-permission", "passenger"]
        cmd += ["--fringe-factor", pool.get("fringe_factor", 1), "--validate"]
        cmd += ["--remove-loops", "--min-distance", pool.get("min_distance_m", 0)]
        if pool.get("speed_exponent"):
            cmd += ["--speed-exponent", pool["speed_exponent"]]
        if pool.get("random_routing_factor"):
            cmd += ["--random-routing-factor", pool["random_routing_factor"]]
        cmd += ["--threads", cfg.get("threads", 4)]
        sumo_env.run(cmd, log=log, cwd=out_dir)
        files.append(routes)
    merged = out_dir / "candidates.rou.xml"
    with merged.open("w") as out:
        out.write("<routes>\n")
        for path in files:
            for _, el in ET.iterparse(path):
                if el.tag == "vehicle" and el.find("route") is not None:
                    edges = el.find("route").get("edges")
                    out.write(f'    <route id="{el.get("id")}" edges="{edges}"/>\n')
                    el.clear()
        out.write("</routes>\n")
    return merged


def route_sampler(
    candidates: Path,
    edgedata: Path,
    out: Path,
    *,
    prefix: str,
    vtype: str,
    seed: int,
    log: Path,
    extra: list | None = None,
) -> Path:
    """Run SUMO's routeSampler; returns the mismatch output (per-edge over/underflow)."""
    mismatch = out.with_suffix(".mismatch.xml")
    cmd = [sys.executable, sumo_env.tool("routeSampler.py"), "-r", candidates, "-d", edgedata]
    cmd += ["-o", out, "--mismatch-output", mismatch, "--prefix", prefix, "-s", seed]
    cmd += ["-a", f'type="{vtype}" departLane="best" departSpeed="max"', "-v"]
    sumo_env.run([*cmd, *(extra or [])], log=log)
    return mismatch


def sampled_counts(routes: Path, begin: float, end: float) -> dict[str, int]:
    """Vehicles per edge of the sampled routes departing within [begin, end)."""
    counts: dict[str, int] = defaultdict(int)
    named: dict[str, str] = {}
    for _, el in ET.iterparse(routes):
        if el.tag == "route" and el.get("id"):
            named[el.get("id")] = el.get("edges")
        elif el.tag == "vehicle":
            depart = float(el.get("depart", "0"))
            if begin <= depart < end:
                route = el.find("route")
                edges = route.get("edges") if route is not None else named.get(el.get("route"))
                for e in set((edges or "").split()):
                    counts[e] += 1
            el.clear()
    return dict(counts)


# ---------------------------------------------------------------- capacity screening


def edge_capacities(net, per_lane: dict[str, float], default: float) -> dict[str, float]:
    """Hourly capacity per edge: class capacity per lane x lanes (sumolib network)."""
    return {
        e.getID(): per_lane.get(road_class(e.getType()), default)
        * max(1, sum(1 for ln in e.getLanes() if ln.allows("passenger")))
        for e in net.getEdges()
    }


def screen_capacity(
    routes: Path,
    out: Path,
    capacity: dict[str, float],
    targets: dict[str, float],
    intervals: list[tuple[float, float]],
    seed: int,
) -> dict:
    """Drop sampled vehicles whose route overloads an edge beyond its capacity.

    routeSampler only bounds counted edges; random candidate routes can push far more
    traffic over uncounted (or under-laned) edges than they can carry, which gridlocks
    the simulation. Per departure interval, the bound of an edge is
    ``max(capacity, target) * interval / 3600`` (a counted edge keeps at least its
    observed count). Vehicles are visited in a seeded random order and dropped while any
    edge of their route is above its bound; one pass leaves every edge within bounds.
    """
    import random

    tree = ET.parse(routes)
    root = tree.getroot()
    vehicles = [el for el in root if el.tag == "vehicle"]

    def interval_of(el):
        t = float(el.get("depart", "0"))
        for k, (b, e) in enumerate(intervals):
            if b <= t < e:
                return k
        return None

    loads: dict[tuple[int, str], int] = defaultdict(int)
    info = []
    for el in vehicles:
        k = interval_of(el)
        edges = set(el.find("route").get("edges").split()) if k is not None else set()
        info.append((el, k, edges))
        for e in edges:
            loads[(k, e)] += 1

    def bound(k, e):
        b, end = intervals[k]
        return max(capacity.get(e, math.inf), targets.get(e, 0.0)) * (end - b) / 3600

    order = list(range(len(info)))
    random.Random(seed).shuffle(order)
    dropped = 0
    over_before = {key for key, n in loads.items() if n > bound(*key)}
    for i in order:
        el, k, edges = info[i]
        if k is None or not any(loads[(k, e)] > bound(k, e) for e in edges):
            continue
        root.remove(el)
        dropped += 1
        for e in edges:
            loads[(k, e)] -= 1
    tree.write(out, encoding="UTF-8", xml_declaration=True)
    return {
        "vehicles_in": len(vehicles),
        "vehicles_dropped": dropped,
        "vehicles_out": len(vehicles) - dropped,
        "edge_intervals_over_capacity_before": len(over_before),
        "edges_over_capacity_before": len({e for _, e in over_before}),
    }
