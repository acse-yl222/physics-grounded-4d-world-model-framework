"""Convert Overture transportation segments/connectors to SUMO plain XML.

Input is the JSON written by ``urban_geometry.image_to_threejs.fetch_overture``
(geometry already in scene ENU metres). Every Overture connector that lies on a
kept segment becomes a SUMO node; segments are split at their connectors into
edges. Segment ends cut by the square domain become boundary (fringe) nodes.

Overture linear references (``between``/``at``) refer to the unclipped segment
geometry, so connector positions are matched by coordinates (connectors sit on
segment vertices) and ``at`` is only used to evaluate ``between`` ranges of
speed limits and access restrictions for each piece.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

MPS = {"mph": 0.44704, "km/h": 1 / 3.6, "kmh": 1 / 3.6}

# class: priority, lanes per direction (two-way road), lanes (one-way road), default speed m/s.
# Default speeds follow GB limits typical for inner London where Overture has no speed_limits:
# 40 mph trunk, 30 mph primary/secondary, 20 mph local roads, 10 mph service/living streets.
DEFAULT_CLASSES = {
    "motorway": {"priority": 14, "lanes_two_way": 3, "lanes_one_way": 3, "speed_mph": 50},
    "trunk": {"priority": 13, "lanes_two_way": 2, "lanes_one_way": 2, "speed_mph": 40},
    "primary": {"priority": 12, "lanes_two_way": 1, "lanes_one_way": 2, "speed_mph": 30},
    "secondary": {"priority": 11, "lanes_two_way": 1, "lanes_one_way": 2, "speed_mph": 30},
    "tertiary": {"priority": 10, "lanes_two_way": 1, "lanes_one_way": 1, "speed_mph": 20},
    "unclassified": {"priority": 8, "lanes_two_way": 1, "lanes_one_way": 1, "speed_mph": 20},
    "residential": {"priority": 7, "lanes_two_way": 1, "lanes_one_way": 1, "speed_mph": 20},
    "service": {"priority": 6, "lanes_two_way": 1, "lanes_one_way": 1, "speed_mph": 10},
    "living_street": {"priority": 5, "lanes_two_way": 1, "lanes_one_way": 1, "speed_mph": 10},
}
DEFAULT_OPTIONS = {
    "classes": DEFAULT_CLASSES,
    # Service roads that only serve parking/driveways add many dead ends without through
    # traffic; skipping them keeps the network small.
    "skip_subclasses": ["parking_aisle", "driveway"],
    "skip_flags": ["is_abandoned", "is_under_construction"],
    "include_tunnels": True,
    "include_private": False,
    "match_tolerance_m": 0.5,
    # Overture has no signal locations. Junctions where at least `tls_min_major` road pieces
    # of these classes meet are signalised (an assumption, flagged in provenance).
    "tls_classes": ["motorway", "trunk", "primary", "secondary", "tertiary"],
    "tls_min_major": 3,
}
CAR_MODES = {"vehicle", "motor_vehicle", "car"}
TAXI_MODES = CAR_MODES | {"taxi"}
BUS_MODES = {"vehicle", "motor_vehicle", "bus", "psv"}
GROUPS = {"passenger": CAR_MODES, "taxi": TAXI_MODES, "bus": BUS_MODES}


@dataclass
class Network:
    nodes: dict[str, tuple[float, float]] = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)
    tls: set[str] = field(default_factory=set)
    stats: Counter = field(default_factory=Counter)


def lines_of(geometry: dict) -> list[list[list[float]]]:
    kind = geometry.get("type")
    if kind == "LineString":
        return [geometry["line"]]
    if kind == "MultiLineString":
        return list(geometry["lines"])
    return []


def length(points) -> float:
    return sum(math.dist(a, b) for a, b in itertools.pairwise(points))


def _applies(rule: dict, at: float) -> bool:
    between = rule.get("between")
    return not between or between[0] - 1e-9 <= at <= between[1] + 1e-9


def flags_at(feature: dict, at: float) -> set[str]:
    out: set[str] = set()
    for rule in feature.get("road_flags") or []:
        if _applies(rule, at):
            out.update(rule.get("values") or [])
    return out


def access(feature: dict, at: float, heading: str, group: str, include_private: bool) -> bool:
    """Whether vehicle ``group`` may travel ``heading`` (forward/backward) at ``at``.

    Unconditional rules are applied first, then mode-specific rules, so e.g.
    ``denied`` + ``allowed when mode=[bus]`` yields a bus-only carriageway.
    Rules gated on time (``during``) or vehicle dimensions are ignored. An
    ``allowed`` rule limited to ``recognized`` users (OSM access=private,
    permissive, ...) means the public is denied unless ``include_private``.
    """
    modes = GROUPS[group]
    allowed = True
    for specific in (False, True):
        for rule in feature.get("access_restrictions") or []:
            when = rule.get("when") or {}
            if not _applies(rule, at) or when.get("during") or when.get("vehicle"):
                continue
            if when.get("heading") and when["heading"] != heading:
                continue
            rule_modes = set(when.get("mode") or [])
            if bool(rule_modes) != specific or (rule_modes and not rule_modes & modes):
                continue
            kind = rule.get("access_type")
            if kind == "denied":
                if not when.get("using") and not when.get("recognized"):
                    allowed = False
            elif when.get("recognized"):
                allowed = allowed and include_private
            elif kind in ("allowed", "designated"):
                allowed = True
    return allowed


def speed_at(feature: dict, at: float, heading: str) -> float | None:
    """Maximum speed (m/s) for passenger traffic, or None when not tagged."""
    best = None
    for rule in feature.get("speed_limits") or []:
        when = rule.get("when") or {}
        modes = set(when.get("mode") or [])
        if modes and not modes & CAR_MODES:
            continue
        if when.get("heading") and when["heading"] != heading:
            continue
        if not _applies(rule, at) or not rule.get("max_speed"):
            continue
        value = rule["max_speed"]
        factor = MPS.get(value.get("unit", "km/h"))
        if factor and value.get("value"):
            best = value["value"] * factor
    return best


def _project(p, a, b):
    """Parameter t in [0,1] and distance of point p from segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    seg = dx * dx + dy * dy
    t = 0.0 if seg == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / seg))
    q = (a[0] + t * dx, a[1] + t * dy)
    return t, math.dist(p, q)


def split_line(line, connectors, positions, tolerance):
    """Split a polyline at the connectors lying on it.

    ``connectors`` is the segment's ordered ``[{connector_id, at}]`` list and
    ``positions`` maps connector ids to ENU points. Returns a list of
    ``(points, start, end)`` where start/end are ``(connector_id | None, at | None)``;
    None marks a domain-boundary end without a connector.
    """
    pts = [tuple(p[:2]) for p in line]
    # Each cut is located as (segment index i, parameter t); cuts must advance along the
    # line so a loop whose start and end share a connector gets both ends.
    cuts: list[tuple[int, float, str, float | None]] = []
    prev = (0, -1.0)
    for conn in connectors or []:
        cid = conn.get("connector_id")
        if cid not in positions:
            continue
        p = positions[cid]
        found = None
        for i in range(prev[0], len(pts) - 1):
            t, d = _project(p, pts[i], pts[i + 1])
            if (i, t) <= (prev[0], prev[1] + 1e-9) or d > tolerance:
                continue
            found = (i, t)
            break
        if found is None:
            continue
        cuts.append((*found, cid, conn.get("at")))
        prev = found
    # Materialise the cuts as vertex indices of a refined polyline.
    refined = list(pts)
    marks: list[tuple[int, str, float | None]] = []
    offset = 0
    for i, t, cid, at in cuts:
        j = i + offset
        if t <= 1e-6:
            idx = j
        elif t >= 1 - 1e-6:
            idx = j + 1
        else:
            a, b = refined[j], refined[j + 1]
            refined.insert(j + 1, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
            offset += 1
            idx = j + 1
        if marks and idx <= marks[-1][0]:
            continue  # two connectors at the same place: keep the first
        marks.append((idx, cid, at))
    bounds = [(0, None, None)] if not marks or marks[0][0] != 0 else []
    bounds += marks
    if bounds[-1][0] != len(refined) - 1:
        bounds.append((len(refined) - 1, None, None))
    pieces = []
    for (i0, c0, a0), (i1, c1, a1) in itertools.pairwise(bounds):
        if i1 <= i0:
            continue
        pieces.append((refined[i0 : i1 + 1], (c0, a0), (c1, a1)))
    return pieces


def build(segments: list[dict], connectors: list[dict], options: dict | None = None) -> Network:
    """Build nodes and directed edges from Overture features (ENU geometry)."""
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    classes = {**DEFAULT_CLASSES, **opts.get("classes", {})}
    positions = {
        c["id"]: tuple(c["geometry"]["point"][:2])
        for c in connectors
        if c.get("geometry", {}).get("type") == "Point"
    }
    net = Network()
    node_ids: dict[str, str] = {}

    def node(key: str, xy) -> str:
        if key not in node_ids:
            node_ids[key] = f"n{len(node_ids)}"
            net.nodes[node_ids[key]] = (round(xy[0], 2), round(xy[1], 2))
        return node_ids[key]

    for index, feature in enumerate(segments):
        cls = feature.get("class")
        if feature.get("subtype") != "road" or cls not in classes:
            net.stats["skipped_class"] += 1
            continue
        if feature.get("subclass") in opts["skip_subclasses"]:
            net.stats["skipped_subclass"] += 1
            continue
        spec = classes[cls]
        for part, line in enumerate(lines_of(feature["geometry"])):
            if len(line) < 2:
                continue
            pieces = split_line(
                line, feature.get("connectors"), positions, opts["match_tolerance_m"]
            )
            for k, (points, (c0, a0), (c1, a1)) in enumerate(pieces):
                known = [a for a in (a0, a1) if a is not None]
                at = sum(known) / len(known) if known else 0.5
                flags = flags_at(feature, at)
                if flags & set(opts["skip_flags"]):
                    net.stats["skipped_flag"] += 1
                    continue
                if "is_tunnel" in flags and not opts["include_tunnels"]:
                    net.stats["skipped_tunnel"] += 1
                    continue
                if length(points) < 0.1:
                    net.stats["skipped_degenerate"] += 1
                    continue
                base = f"e{index}_{part}_{k}"
                start = node(c0 or f"{base}:start", points[0])
                end = node(c1 or f"{base}:end", points[-1])
                if start == end:
                    if len(points) < 3:
                        net.stats["skipped_loop"] += 1
                        continue
                    mid = len(points) // 2
                    via = node(f"{base}:mid", points[mid])
                    halves = [(points[: mid + 1], start, via, "a"), (points[mid:], via, end, "b")]
                else:
                    halves = [(points, start, end, "")]
                permissions = {}
                for heading in ("forward", "backward"):
                    permissions[heading] = [
                        g
                        for g in ("passenger", "taxi", "bus")
                        if access(feature, at, heading, g, opts["include_private"])
                    ]
                directions = [h for h in ("forward", "backward") if permissions[h]]
                if not directions:
                    net.stats["skipped_access"] += 1
                    continue
                one_way = len(directions) == 1
                lanes = spec["lanes_one_way"] if one_way else spec["lanes_two_way"]
                if feature.get("subclass") == "link" or "is_link" in flags:
                    lanes = 1
                for pts, a, b, suffix in halves:
                    for heading in directions:
                        speed = speed_at(feature, at, heading) or spec["speed_mph"] * MPS["mph"]
                        shape = pts if heading == "forward" else pts[::-1]
                        edge = {
                            "id": ("" if heading == "forward" else "-") + base + suffix,
                            "from": a if heading == "forward" else b,
                            "to": b if heading == "forward" else a,
                            "priority": spec["priority"] - (1 if lanes == 1 and one_way else 0),
                            "numLanes": lanes,
                            "speed": round(speed, 2),
                            "shape": shape,
                            "type": cls,
                            "allow": permissions[heading],
                            "one_way": one_way,
                            "name": feature.get("name"),
                            "overture_id": feature.get("id"),
                            "bridge": "is_bridge" in flags,
                            "tunnel": "is_tunnel" in flags,
                        }
                        net.edges.append(edge)
                        net.stats["edges"] += 1
    net.stats["nodes"] = len(net.nodes)
    incident: dict[str, set[str]] = {}
    for e in net.edges:
        if e["type"] in opts["tls_classes"] and not e["tunnel"]:
            piece = e["id"].lstrip("-")
            incident.setdefault(e["from"], set()).add(piece)
            incident.setdefault(e["to"], set()).add(piece)
    net.tls = {n for n, pieces in incident.items() if len(pieces) >= opts["tls_min_major"]}
    net.stats["tls_nodes"] = len(net.tls)
    return net


def _fmt(v: float) -> str:
    return f"{v:.2f}"


def write_plain_xml(net: Network, nodes_path, edges_path) -> None:
    """Write ``.nod.xml`` and ``.edg.xml`` (coordinates are scene ENU metres)."""
    with open(nodes_path, "w", encoding="utf-8") as out:
        out.write('<?xml version="1.0" encoding="UTF-8"?>\n<nodes>\n')
        for nid, (x, y) in net.nodes.items():
            kind = ' type="traffic_light"' if nid in net.tls else ""
            out.write(f'    <node id="{nid}" x="{_fmt(x)}" y="{_fmt(y)}"{kind}/>\n')
        out.write("</nodes>\n")
    with open(edges_path, "w", encoding="utf-8") as out:
        out.write('<?xml version="1.0" encoding="UTF-8"?>\n<edges>\n')
        for e in net.edges:
            shape = " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in e["shape"])
            attrs = (
                f'id="{e["id"]}" from="{e["from"]}" to="{e["to"]}" priority="{e["priority"]}" '
                f'numLanes="{e["numLanes"]}" speed="{e["speed"]}" type="{e["type"]}" '
                f'allow="{" ".join(e["allow"])}" shape="{shape}"'
            )
            if e["one_way"]:
                attrs += ' spreadType="center"'
            if e.get("name"):
                attrs += f" name={quoteattr(e['name'])}"
            params = [("overture_id", e.get("overture_id"))]
            params += [("bridge", "1")] if e.get("bridge") else []
            params += [("tunnel", "1")] if e.get("tunnel") else []
            params = [(k, v) for k, v in params if v]
            if params:
                out.write(f"    <edge {attrs}>\n")
                out.writelines(
                    f"        <param key={quoteattr(k)} value={quoteattr(str(v))}/>\n"
                    for k, v in params
                )
                out.write("    </edge>\n")
            else:
                out.write(f"    <edge {attrs}/>\n")
        out.write("</edges>\n")
