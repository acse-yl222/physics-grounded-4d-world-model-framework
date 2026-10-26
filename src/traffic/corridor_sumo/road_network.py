"""SUMO network -> viewer road network (``road_network.json``, ``corridor-road-network-v1``).

The viewer draws the drivable road surface from the same network the vehicles drive on:
every motor-vehicle lane (normal and internal junction lanes) with its width and centre
line, the lane connections and the junction polygons, inside the scene domain. Lanes
that cross the domain boundary are kept whole (not clipped), so lane lengths and vehicle
timing along them stay SUMO's.

Coordinates are scene ENU metres (the net is built with offset normalisation disabled,
so SUMO x,y are scene x,y); ``z`` is the terrain street surface ``DemSurface.road(x, y)``
(open water filled from the banks) plus, on OSM bridges, a deck height:

* The net carries no bridge/layer tags, so they are read from the scene OSM subset
  (``osm.xml.gz``) and matched to lanes through the lane parameter ``origId`` (the OSM
  way ids netconvert built the edge from). A lane sample lies on a bridge when it
  projects onto a bridge way of its own edge within ``ON_WAY_M`` (and at most ``END_M``
  beyond its ends); off-bridge gaps shorter than ``GAP_M`` inside a run are closed.
* Deck level as in the city model (``three/ground.mjs``): ``max(layer, 1 if bridge)``,
  ``DECK_M`` = 6.5 m per level. Along a bridge run the base is the straight line between
  the street heights at the run ends (no dip into a river or railway cutting below) and
  the deck is ``level * DECK_M`` slope limited to ``RAMP_GRADE``: it rises from the run
  ends and ramps between levels. Junctions whose incident lanes all end on a bridge
  (mid-span nodes) are raised by the lowest deck height of those lane ends (iterated with
  the slope limit until lanes and nodes agree), and lanes do not ramp down there, so
  lanes, internal lanes and junction polygons meet at one height.
* Tunnels and covered ways are flagged (``structure``) but kept on the street surface:
  their depth is unknown.
"""

from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

SCHEMA = "corridor-road-network-v1"
INDEX_SCHEMA = "corridor-road-network-index-v1"
DECK_M = 6.5  # per OSM layer level, as three/ground.mjs DECK_M
RAMP_GRADE = 0.06  # deck rise per metre from the street at the ends of a bridge run
ON_WAY_M = 15.0  # max distance of a lane sample from its OSM bridge way centre line
END_M = 2.0  # along-way tolerance beyond a bridge way end
GAP_M = 40.0  # off-bridge gaps this short inside a bridge run are closed
SAMPLE_M = 10.0  # terrain sampling step along lanes before simplification
Z_TOLERANCE_M = 0.1  # 3D Douglas-Peucker tolerance of exported lane shapes
DECIMALS = 1  # coordinates rounded to 0.1 m
MAX_BYTES = 12_000_000
# vClasses whose lanes are drawn (pedestrian/bicycle/rail-only lanes are dropped).
MOTOR = {
    "passenger",
    "private",
    "taxi",
    "bus",
    "coach",
    "delivery",
    "truck",
    "trailer",
    "motorcycle",
    "moped",
    "evehicle",
    "emergency",
    "authority",
    "hov",
}
# Reported in ``allow`` for lanes closed to general traffic.
ALLOW_REPORTED = ("bus", "coach", "taxi", "delivery", "truck", "emergency", "motorcycle")


# ---------------------------------------------------------------- OSM structures


def _level(tags: dict) -> tuple[int, str | None]:
    """(deck level, structure) of an OSM way: level as the city model, structure flag."""
    try:
        layer = round(float(tags.get("layer", "0")))
    except ValueError:
        layer = 0
    bridge = tags.get("bridge") not in (None, "no")
    tunnel = tags.get("tunnel")
    if tunnel in ("yes", "culvert") or (layer < 0 and tunnel not in (None, "no")):
        return 0, "tunnel"
    if tunnel in ("building_passage", "covered") or tags.get("covered") == "yes":
        return 0, "covered"
    level = max(layer, 1 if bridge else 0)
    return level, "bridge" if level > 0 else None


def osm_structures(osm_path: Path, enu) -> dict[str, dict]:
    """``{way id: {level, structure, line}}`` for OSM bridges, tunnels and covered ways."""
    opener = gzip.open if str(osm_path).endswith(".gz") else open
    coords: dict[str, tuple[float, float]] = {}
    out = {}
    with opener(osm_path, "rb") as f:
        for _, el in ET.iterparse(f):
            if el.tag == "node":
                coords[el.get("id")] = (float(el.get("lon")), float(el.get("lat")))
                el.clear()
            elif el.tag == "way":
                tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
                level, structure = _level(tags)
                if structure:
                    nds = [coords[n.get("ref")] for n in el.findall("nd") if n.get("ref") in coords]
                    if len(nds) >= 2:
                        out[el.get("id")] = {
                            "level": level,
                            "structure": structure,
                            "line": np.array([enu(*ll) for ll in nds], dtype=np.float64),
                        }
                el.clear()
            elif el.tag == "relation":
                break
    return out


def on_way(points: np.ndarray, line: np.ndarray, max_dist: float = ON_WAY_M) -> np.ndarray:
    """Whether each point projects onto ``line`` within ``max_dist`` and not more than
    ``END_M`` along the line beyond either end (lanes are offset from the way centre)."""
    a, b = line[:-1], line[1:]
    d = b - a
    seg = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)
    rel = points[:, None, :] - a[None, :, :]
    t = (rel * d[None]).sum(2) / (seg * seg)[None]
    tc = np.clip(t, 0.0, 1.0)
    near = a[None] + tc[..., None] * d[None]
    dist = np.hypot(*(points[:, None, :] - near).transpose(2, 0, 1))
    k = dist.argmin(1)
    rows = np.arange(len(points))
    tk, dk = t[rows, k], dist[rows, k]
    before = np.where(k == 0, -tk * seg[k], 0.0)
    after = np.where(k == len(a) - 1, (tk - 1) * seg[k], 0.0)
    return (dk <= max_dist) & (before <= END_M) & (after <= END_M)


def close_gaps(raw: np.ndarray, s: np.ndarray, gap_m: float = GAP_M) -> np.ndarray:
    """Fill off-bridge stretches shorter than ``gap_m`` between bridge samples (joins of
    OSM ways, lane offsets at bends) with the lower neighbouring level."""
    out = raw.copy()
    on = np.flatnonzero(raw > 0)
    for i, j in itertools.pairwise(on):
        if j > i + 1 and s[j] - s[i] <= gap_m:
            out[i + 1 : j] = min(raw[i], raw[j])
    return out


# ---------------------------------------------------------------- geometry helpers


def resample(shape, step: float = SAMPLE_M) -> tuple[np.ndarray, np.ndarray]:
    """Polyline vertices plus points every <= ``step`` m; (points, arc length)."""
    pts = np.asarray([p[:2] for p in shape], dtype=np.float64)
    out = [pts[:1]]
    for p, q in itertools.pairwise(pts):
        n = max(1, math.ceil(math.hypot(*(q - p)) / step))
        f = np.arange(1, n + 1)[:, None] / n
        out.append(p + f * (q - p))
    pts = np.vstack(out)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
    return pts, s


def simplify3(points: np.ndarray, tol: float) -> np.ndarray:
    """Douglas-Peucker in 3D (keeps both ends)."""
    n = len(points)
    if n < 3:
        return points
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = points[i], points[j]
        seg = points[i + 1 : j]
        d = b - a
        dd = float(d @ d)
        if dd < 1e-12:
            dist = np.linalg.norm(seg - a, axis=1)
        else:
            t = np.clip((seg - a) @ d / dd, 0.0, 1.0)
            dist = np.linalg.norm(seg - (a + t[:, None] * d), axis=1)
        k = int(dist.argmax())
        if dist[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return points[keep]


def touches_square(shape, half: float) -> bool:
    """Whether a polyline has a point inside or a segment crossing ``|x|, |y| <= half``."""
    pts = [p[:2] for p in shape]
    if any(abs(x) <= half and abs(y) <= half for x, y in pts):
        return True
    for (x0, y0), (x1, y1) in itertools.pairwise(pts):
        t0, t1 = 0.0, 1.0
        ok = True
        for p, q in ((-(x1 - x0), x0 + half), (x1 - x0, half - x0)) + (
            (-(y1 - y0), y0 + half),
            (y1 - y0, half - y0),
        ):
            if p == 0:
                if q < 0:
                    ok = False
                    break
                continue
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                ok = False
                break
        if ok:
            return True
    return False


def deck_offsets(
    s: np.ndarray, raw: np.ndarray, road: np.ndarray, deck_from: float, deck_to: float
) -> tuple[np.ndarray, np.ndarray]:
    """(heights, deck offsets) along a lane: ``road`` off bridges; on a bridge run the
    straight line between the street heights at the run ends plus a deck of
    ``raw * DECK_M``, slope limited to ``RAMP_GRADE``: it rises from 0 at the run ends,
    from the node's deck (``deck_from``/``deck_to``, metres) at the lane ends, and ramps
    between levels."""
    n = len(s)
    z = road.astype(np.float64).copy()
    target = DECK_M * raw.astype(np.float64)
    target[0] = min(target[0], deck_from)
    target[-1] = min(target[-1], deck_to)
    off = target.copy()
    for k in range(1, n):
        off[k] = min(off[k], off[k - 1] + RAMP_GRADE * (s[k] - s[k - 1]))
    for k in range(n - 2, -1, -1):
        off[k] = min(off[k], off[k + 1] + RAMP_GRADE * (s[k + 1] - s[k]))
    on = raw > 0
    k = 0
    while k < n:
        if not on[k]:
            k += 1
            continue
        a = k
        while k + 1 < n and on[k + 1]:
            k += 1
        b = k
        k += 1
        span = s[b] - s[a]
        frac = (s[a : b + 1] - s[a]) / span if span > 0 else np.zeros(b - a + 1)
        z[a : b + 1] = road[a] + (road[b] - road[a]) * frac
    return z + off, off


def _r(v: float) -> float:
    return round(float(v), DECIMALS)


def _shape(points: np.ndarray, z: np.ndarray) -> list[list[float]]:
    p3 = np.column_stack([points, z])
    return [[_r(x), _r(y), _r(h)] for x, y, h in simplify3(p3, Z_TOLERANCE_M)]


def _allows_motor(lane) -> bool:
    return bool(MOTOR & set(lane.getPermissions()))


def _restricted(lane) -> str | None:
    perms = set(lane.getPermissions())
    if "passenger" in perms:
        return None
    return " ".join(c for c in ALLOW_REPORTED if c in perms) or None


def shape_length(shape) -> float:
    pts = np.asarray([p[:2] for p in shape], dtype=np.float64)
    return float(np.hypot(*np.diff(pts, axis=0).T).sum()) if len(pts) > 1 else 0.0


# ---------------------------------------------------------------- export


def build(net, half: float | None, road=None, structures: dict | None = None) -> dict:
    """The road network document for lanes reaching ``|x|, |y| <= half``.

    ``net``: sumolib net read with ``withInternal=True``; ``road(xs, ys)``: street height
    (None: 0); ``structures``: ``osm_structures`` output (None: no decks/flags).
    Returns the document plus ``lane_index`` (lane id -> index in ``lanes``).
    """
    structures = structures or {}

    def zroad(pts):
        if road is None:
            return np.zeros(len(pts))
        return np.asarray(road(pts[:, 0], pts[:, 1]), dtype=np.float64)

    # 1. normal lanes in the domain
    normal = []
    for e in net.getEdges():
        if e.getFunction() not in ("", "normal"):
            continue
        for ln in e.getLanes():
            if _allows_motor(ln) and (half is None or touches_square(ln.getShape(), half)):
                normal.append(ln)
    kept = {ln.getID() for ln in normal}
    # 2. internal lanes of connections between kept lanes (whole via chains)
    internal: dict[str, object] = {}
    connections = []
    for ln in normal:
        for c in ln.getOutgoing():
            to = c.getToLane()
            if to.getID() not in kept:
                continue
            chain, via = [], c.getViaLaneID()
            while via:
                vl = net.getLane(via)
                chain.append(vl)
                nxt = [c2 for c2 in vl.getOutgoing() if c2.getToLane().getID() == to.getID()]
                via = nxt[0].getViaLaneID() if nxt else ""
            if not all(_allows_motor(v) for v in chain):
                continue
            for v in chain:
                internal[v.getID()] = v
            hops = [ln, *chain, to]
            for k in range(len(hops) - 1):
                connections.append(
                    (
                        hops[k].getID(),
                        to.getID(),
                        hops[k + 1].getID() if k + 1 < len(hops) - 1 else None,
                        c.getDirection(),
                        c.getTLSID() or None,
                    )
                )
    connections = list(dict.fromkeys(connections))

    # 3. per-lane samples, bridge levels and node levels
    samples = {}
    for ln in normal:
        pts, s = resample(ln.getShape())
        raw = np.zeros(len(pts), dtype=np.int64)
        flags = set()
        for wid in (ln.getParam("origId") or "").split():
            w = structures.get(wid.lstrip("-"))
            if w is None:
                continue
            if w["level"] > 0:
                hit = on_way(pts, w["line"])
                if hit.any():
                    raw = np.maximum(raw, np.where(hit, w["level"], 0))
                    flags.add("bridge")
            else:
                flags.add(w["structure"])
        raw = close_gaps(raw, s)
        samples[ln.getID()] = (pts, s, raw, flags)
    # Node decks: the lowest deck of the incident lane ends, iterated until the lanes
    # (slope limited) and their nodes agree, so lanes, internal lanes and junction
    # polygons meet at one height.
    ends: dict[str, list[float]] = {}
    for ln in normal:
        e = ln.getEdge()
        raw = samples[ln.getID()][2]
        ends.setdefault(e.getFromNode().getID(), []).append(DECK_M * int(raw[0]))
        ends.setdefault(e.getToNode().getID(), []).append(DECK_M * int(raw[-1]))
    node_deck = {nid: min(v) for nid, v in ends.items()}
    heights: dict[str, np.ndarray] = {}
    bridged = [ln for ln in normal if samples[ln.getID()][2].any()]
    for _ in range(50):
        ends = {}
        for ln in bridged:
            pts, s, raw, _ = samples[ln.getID()]
            a, b = ln.getEdge().getFromNode().getID(), ln.getEdge().getToNode().getID()
            z, off = deck_offsets(s, raw, zroad(pts), node_deck[a], node_deck[b])
            heights[ln.getID()] = z
            ends.setdefault(a, []).append(off[0])
            ends.setdefault(b, []).append(off[-1])
        changed = False
        for nid, v in ends.items():
            low = min(node_deck[nid], *v)
            if low < node_deck[nid] - 1e-6:
                node_deck[nid], changed = low, True
        if not changed:
            break

    # 4. documents
    edges_doc, edge_index = [], {}
    lanes_doc, lane_index = [], {}
    for ln in normal:
        e = ln.getEdge()
        if e.getID() not in edge_index:
            edge_index[e.getID()] = len(edges_doc)
            edges_doc.append(
                {
                    "id": e.getID(),
                    "name": e.getName() or "",
                    "type": e.getType() or "",
                    "from": e.getFromNode().getID(),
                    "to": e.getToNode().getID(),
                    "speed": round(e.getSpeed(), 2),
                    "priority": e.getPriority(),
                    "lanes": [],
                }
            )
        pts, s, raw, flags = samples[ln.getID()]
        z = heights[ln.getID()] if ln.getID() in heights else zroad(pts)
        ed = edges_doc[edge_index[e.getID()]]
        level = int(raw.max())
        if level:
            ed["level"] = max(ed.get("level", 0), level)
        for flag in sorted(flags):
            if flag != "bridge" or level:
                structure = ed.setdefault("structure", [])
                if flag not in structure:
                    structure.append(flag)
        lane_index[ln.getID()] = len(lanes_doc)
        ed["lanes"].append(len(lanes_doc))
        lanes_doc.append(_lane(ln, edge_index[e.getID()], None, _shape(pts, z)))
    junctions_doc, junction_index = [], {}
    for nid in sorted({n for ed in edges_doc for n in (ed["from"], ed["to"])}):
        node = net.getNode(nid)
        shape = node.getShape()
        junction_index[nid] = len(junctions_doc)
        doc = {"id": nid, "type": node.getType()}
        lift = node_deck.get(nid, 0.0)
        if lift:
            doc["deck_m"] = _r(lift)
        if len(shape) >= 3:
            pts = np.asarray([p[:2] for p in shape], dtype=np.float64)
            z = zroad(pts) + lift
            doc["shape"] = [[_r(x), _r(y), _r(h)] for (x, y), h in zip(pts, z, strict=True)]
        else:
            doc["shape"] = []
        junctions_doc.append(doc)
    for vid in sorted(internal):
        vl = internal[vid]
        nid = vl.getEdge().getFromNode().getID()
        pts, _ = resample(vl.getShape(), 5.0)
        z = zroad(pts) + node_deck.get(nid, 0.0)
        lane_index[vid] = len(lanes_doc)
        lanes_doc.append(_lane(vl, None, junction_index.get(nid), _shape(pts, z)))
    conns_doc = []
    for f, t, via, d, tl in connections:
        row = {
            "from_lane": lane_index[f],
            "to_lane": lane_index[t],
            "via": lane_index[via] if via else None,
            "dir": d,
        }
        if tl:
            row["tl"] = tl
        conns_doc.append(row)
    n_internal = len(internal)
    return {
        "schema": SCHEMA,
        "lefthand": True,
        "coordinate_frame": "ENU",
        "units": "m",
        "edges": edges_doc,
        "lanes": lanes_doc,
        "connections": conns_doc,
        "junctions": junctions_doc,
        "counts": {
            "edges": len(edges_doc),
            "lanes": len(lanes_doc),
            "normal_lanes": len(lanes_doc) - n_internal,
            "internal_lanes": n_internal,
            "connections": len(conns_doc),
            "junctions": len(junctions_doc),
            "bus_only_lanes": sum(
                1 for ln in lanes_doc if ln.get("allow") == "bus" and ln["edge"] is not None
            ),
            "restricted_lanes": sum(
                1 for ln in lanes_doc if "allow" in ln and ln["edge"] is not None
            ),
            "bridge_edges": sum(1 for ed in edges_doc if ed.get("level")),
            "raised_junctions": sum(1 for j in junctions_doc if j.get("deck_m")),
            "tunnel_edges": sum(1 for ed in edges_doc if "tunnel" in ed.get("structure", [])),
        },
        "lane_index": lane_index,
    }


def _lane(lane, edge: int | None, junction: int | None, shape: list) -> dict:
    doc = {
        "id": lane.getID(),
        "edge": edge,
        "index": lane.getIndex(),
        "width": round(lane.getWidth(), 2),
        "speed": round(lane.getSpeed(), 2),
        "length": round(lane.getLength(), 2),
    }
    if junction is not None:
        doc["junction"] = junction
    allow = _restricted(lane)
    if allow:
        doc["allow"] = allow
    doc["shape"] = shape
    return doc


def describe_elevation() -> str:
    return (
        "z = terrain street surface DemSurface.road(x, y) (DEM with open water and foreshore "
        "filled from the banks). OSM bridges (bridge=* or layer>0 from the scene OSM subset, "
        "matched to lanes by the lane origId OSM way ids and by projection onto the way) get "
        f"a deck of max(layer, 1) x {DECK_M} m (city model DECK_M) above the straight line "
        "between the street heights at the ends of the bridge run, rising from the run ends "
        f"at {RAMP_GRADE:g} m/m; junctions whose incident lanes all end on a bridge are "
        "raised by the lowest level and runs there do not ramp. Tunnels and covered ways are "
        "flagged in edges[].structure and kept on the street surface (depth unknown). "
        f"Shapes resampled every {SAMPLE_M:g} m for terrain and simplified in 3D at "
        f"{Z_TOLERANCE_M:g} m; coordinates rounded to {10**-DECIMALS:g} m."
    )


def _dump(doc) -> bytes:
    return (json.dumps(doc, separators=(",", ":"), allow_nan=False) + "\n").encode()


def write(doc: dict, data_dir: Path, provenance: dict, max_bytes: int = MAX_BYTES) -> list[str]:
    """Write ``road_network.json`` (whole document, or an index of ``road_network_<k>.json``
    chunks when it exceeds ``max_bytes``); return the written file names (index first).

    Chunks split ``edges``, ``lanes``, ``connections`` and ``junctions`` into contiguous
    slices; indices inside them stay global (``offsets`` give each slice's first index).
    """
    body = {k: v for k, v in doc.items() if k != "lane_index"}
    body["provenance"] = provenance
    whole = _dump(body)
    if len(whole) <= max_bytes:
        (data_dir / "road_network.json").write_bytes(whole)
        return ["road_network.json"]
    keys = ("edges", "lanes", "connections", "junctions")
    parts = math.ceil(len(whole) / (0.9 * max_bytes))
    while True:
        chunks = []
        for k in range(parts):
            chunk = {
                "schema": SCHEMA,
                "part": k,
                "parts": parts,
                "offsets": {},
            }
            for key in keys:
                n = len(body[key])
                lo, hi = n * k // parts, n * (k + 1) // parts
                chunk["offsets"][key] = lo
                chunk[key] = body[key][lo:hi]
            chunks.append(_dump(chunk))
        if max(map(len, chunks)) <= max_bytes:
            break
        parts += 1
    names, entries = [], []
    for k, raw in enumerate(chunks):
        name = f"road_network_{k}.json"
        (data_dir / name).write_bytes(raw)
        names.append(name)
        info = json.loads(raw)
        entries.append(
            {
                "asset": name,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "offsets": info["offsets"],
                "counts": {key: len(info[key]) for key in keys},
            }
        )
    index = {
        "schema": INDEX_SCHEMA,
        "chunk_schema": SCHEMA,
        "lefthand": doc["lefthand"],
        "coordinate_frame": doc["coordinate_frame"],
        "units": doc["units"],
        "counts": doc["counts"],
        "chunks": entries,
        "assembly": "concatenate edges, lanes, connections and junctions of the chunks in "
        "part order; all indices (edges[].lanes, lanes[].edge/junction, connections[]) are "
        "global indices into the concatenated arrays",
        "provenance": provenance,
    }
    (data_dir / "road_network.json").write_bytes(_dump(index))
    return ["road_network.json", *names]


def load(data_dir: Path) -> dict:
    """Read ``road_network.json`` (whole or chunked) as one document."""
    doc = json.loads((data_dir / "road_network.json").read_text())
    if doc.get("schema") == SCHEMA:
        return doc
    if doc.get("schema") != INDEX_SCHEMA:
        raise ValueError(f"unknown road network schema {doc.get('schema')!r}")
    out = {k: doc[k] for k in ("lefthand", "coordinate_frame", "units", "counts", "provenance")}
    out["schema"] = SCHEMA
    for key in ("edges", "lanes", "connections", "junctions"):
        out[key] = []
    for entry in doc["chunks"]:
        chunk = json.loads((data_dir / entry["asset"]).read_text())
        for key in ("edges", "lanes", "connections", "junctions"):
            if chunk["offsets"][key] != len(out[key]):
                raise ValueError(f"{entry['asset']}: {key} offset does not follow")
            out[key] += chunk[key]
    return out
