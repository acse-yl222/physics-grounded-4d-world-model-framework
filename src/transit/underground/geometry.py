"""Track graph, assumed depth model, clipping and station-sequence map matching.

Pure Python (no SciPy/Shapely), so tests run on synthetic graphs. Coordinates are scene
ENU metres (``tfl.Enu``); ``z`` is metres relative to local ground (negative = below).
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import pairwise

from .config import LINES, line_id

# ---------------------------------------------------------------- OSM tag rules

ACTIVE_RAILWAYS = {"subway", "rail", "light_rail", "narrow_gauge"}


def parse_layer(value) -> int | None:
    """OSM ``layer`` as an int (first value of ``-1;-2``; None when absent/invalid)."""
    if value is None:
        return None
    text = str(value).split(";")[0].strip()
    try:
        return round(float(text))
    except ValueError:
        return None


def is_tunnel(tags: dict) -> bool:
    """OSM ``tunnel=yes`` (also ``tunnel=covered``/``culvert``); ``covered=yes`` and
    ``building_passage`` count as surface."""
    return tags.get("tunnel") in {"yes", "covered", "culvert", "flooded"}


def is_bridge(tags: dict) -> bool:
    return tags.get("bridge") in {"yes", "viaduct", "aqueduct", "cantilever", "movable"} or (
        not is_tunnel(tags) and (parse_layer(tags.get("layer")) or 0) > 0
    )


def relation_line(tags: dict) -> str | None:
    """Line id of an OSM route relation: Underground lines (network London Underground
    or ``route=subway``), Elizabeth line and London Overground; None for other rail."""
    name = tags.get("name") or ""
    network = (tags.get("network") or "").lower()
    if "london underground" in network or tags.get("route") == "subway":
        return line_id(name) or line_id(tags.get("ref"))
    lid = line_id(name) or line_id(tags.get("ref"))
    if lid in ("elizabeth", "overground"):
        return lid
    if "overground" in network:
        return "overground"
    return None


def depth_base(tags: dict, lines: list[str], dcfg: dict) -> tuple[float, str, bool]:
    """Typical tunnel depth (m) of a way, the key its reference layer is taken from
    (the line setting the depth, else ``railway:<value>``) and whether a line is known.

    Base = configured per-line depth (deepest of the way's lines), else by line kind:
    deep tube ``deep_m``, sub-surface ``subsurface_m``, other rail ``rail_tunnel_m``;
    ways without a known line use ``subsurface_m`` (railway=subway) or ``rail_tunnel_m``.
    """
    per_line = dcfg.get("per_line_m", {})
    known = [lid for lid in lines if lid in LINES]
    if not known:
        sub = tags.get("railway") == "subway"
        return (
            (dcfg["subsurface_m"] if sub else dcfg["rail_tunnel_m"]),
            (f"railway:{tags.get('railway')}"),
            False,
        )

    def base(lid):
        if lid in per_line:
            return per_line[lid]
        kind = LINES[lid]["kind"]
        return {"deep": dcfg["deep_m"], "subsurface": dcfg["subsurface_m"]}.get(
            kind, dcfg["rail_tunnel_m"]
        )

    key = max(sorted(known), key=base)
    return base(key), key, True


def depth_target(
    tags: dict, lines: list[str], dcfg: dict, ref_layers: dict | None = None
) -> tuple[float, str, str]:
    """Target height ``z`` (m) of a track way, its class and ``depth_source``.

    * ``tunnel``: ``-(base + layer_step * (ref - layer))`` (``depth_base``), where
      ``ref`` is the reference layer of the way's depth key (``ref_layers``; default
      -1) - the length-weighted most common tunnel layer of that line - so a line's
      usual layer sits at its typical depth and OSM layers below/above it (where lines
      cross) are one step deeper/shallower per layer. A missing layer counts as the
      reference. Clamped to [max(``min_tunnel_m``, base - step),
      min(``max_depth_m``, base + ``max_layer_steps`` x step)].
    * ``bridge`` (bridge/viaduct or layer > 0): ``bridge_layer_m * max(1, layer)``.
    * ``surface``: 0 (embankments/cuttings are not modelled).
    """
    layer = parse_layer(tags.get("layer"))
    if is_tunnel(tags):
        base, key, known = depth_base(tags, lines, dcfg)
        ref = (ref_layers or {}).get(key, -1)
        eff = layer if layer is not None and layer < 0 else ref
        step = dcfg["layer_step_m"]
        depth = base + step * (ref - eff)
        lo = max(dcfg.get("min_tunnel_m", 3.0), base - step)
        hi = min(dcfg.get("max_depth_m", 40.0), base + step * dcfg.get("max_layer_steps", 2))
        depth = min(max(depth, lo), hi)
        source = "assumed_typical" if known else "assumed_typical_line_unknown"
        return -depth, "tunnel", source
    if is_bridge(tags):
        return dcfg["bridge_layer_m"] * max(1, layer or 1), "bridge", "osm_bridge_assumed_height"
    return 0.0, "surface", "surface_no_tunnel_tag"


def reference_layers(ways: list[tuple[dict, list[str], float]], dcfg: dict) -> dict:
    """Length-weighted most common (ties: shallower) tunnel layer per depth key.

    ``ways``: ``(tags, lines, length_m)``; only tunnels with a negative layer count.
    """
    from collections import Counter

    weight: dict[str, Counter] = defaultdict(Counter)
    for tags, lines, length in ways:
        layer = parse_layer(tags.get("layer"))
        if is_tunnel(tags) and layer is not None and layer < 0:
            weight[depth_base(tags, lines, dcfg)[1]][layer] += length
    return {k: max(c, key=lambda lay: (c[lay], lay)) for k, c in weight.items()}


# ---------------------------------------------------------------- polylines


def seg_len(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def polyline_length(points) -> float:
    return sum(seg_len(a, b) for a, b in pairwise(points))


def densify(points: list, step: float) -> list:
    """Insert points so no 2D segment is longer than ``step`` (all dims interpolated)."""
    out = [tuple(points[0])]
    for a, b in pairwise(points):
        n = max(1, math.ceil(seg_len(a, b) / step))
        for k in range(1, n + 1):
            t = k / n
            out.append(tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a))))
    return out


def _clip_segment(a, b, half):
    """Liang-Barsky clip of segment a->b to |x|,|y| <= half: (t0, t1) or None."""
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] + half), (dx, half - a[0]), (-dy, a[1] + half), (dy, half - a[1])):
        if p == 0:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return None
    return t0, t1


def _lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def clip_polyline(points: list, half: float, min_len: float = 0.5) -> list[list]:
    """Pieces of a polyline inside the square |x|, |y| <= half.

    A segment crossing the boundary is cut exactly at the boundary (all coordinates,
    including z, interpolated), so a line whose first point lies outside starts on the
    boundary. Pieces shorter than ``min_len`` are dropped.
    """
    pieces, cur = [], []
    for a, b in pairwise(points):
        c = _clip_segment(a, b, half)
        if c is None:
            if cur:
                pieces.append(cur)
                cur = []
            continue
        t0, t1 = c
        p0, p1 = _lerp(a, b, t0), _lerp(a, b, t1)
        if not cur:
            cur = [p0]
        elif seg_len(cur[-1], p0) > 1e-9:
            pieces.append(cur)
            cur = [p0]
        cur.append(p1)
        if t1 < 1.0:
            pieces.append(cur)
            cur = []
    if cur:
        pieces.append(cur)
    out = []
    for piece in pieces:
        dedup = [piece[0]] + [p for q, p in pairwise(piece) if seg_len(q, p) > 1e-9]
        if len(dedup) >= 2 and polyline_length(dedup) >= min_len:
            out.append(dedup)
    return out


def _point_seg_dist3(p, a, b) -> float:
    d = [b[i] - a[i] for i in range(3)]
    den = sum(v * v for v in d)
    t = 0.0 if den == 0 else max(0.0, min(1.0, sum((p[i] - a[i]) * d[i] for i in range(3)) / den))
    return math.dist(p, [a[i] + d[i] * t for i in range(3)])


def simplify3d(points: list, tol: float) -> list:
    """Douglas-Peucker in 3D (iterative); endpoints kept."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        best, idx = 0.0, None
        for k in range(i + 1, j):
            d = _point_seg_dist3(points[k], points[i], points[j])
            if d > best:
                best, idx = d, k
        if idx is not None and best > tol:
            keep[idx] = True
            stack += [(i, idx), (idx, j)]
    return [p for p, k in zip(points, keep, strict=True) if k]


def project(points: list, p) -> tuple[float, float, int]:
    """(distance along polyline, distance from it, segment index) of the nearest point."""
    best = (math.inf, 0.0, 0)
    s = 0.0
    for i, (a, b) in enumerate(pairwise(points)):
        dx, dy = b[0] - a[0], b[1] - a[1]
        den = dx * dx + dy * dy
        t = 0.0 if den == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den))
        q = (a[0] + dx * t, a[1] + dy * t)
        d = math.hypot(p[0] - q[0], p[1] - q[1])
        if d < best[0]:
            best = (d, s + t * math.sqrt(den), i)
        s += math.sqrt(den)
    return best[1], best[0], best[2]


def point_at(points: list, s: float) -> tuple:
    """Point at distance ``s`` along a polyline (clamped)."""
    if s <= 0:
        return tuple(points[0])
    acc = 0.0
    for a, b in pairwise(points):
        d = seg_len(a, b)
        if acc + d >= s and d > 0:
            return _lerp(a, b, (s - acc) / d)
        acc += d
    return tuple(points[-1])


def sub_polyline(points: list, s0: float, s1: float) -> list:
    """Part of a polyline between distances s0 < s1 (endpoints interpolated)."""
    s0, s1 = max(0.0, s0), min(polyline_length(points), s1)
    out = [point_at(points, s0)]
    acc = 0.0
    for a, b in pairwise(points):
        acc += seg_len(a, b)
        if s0 < acc < s1:
            out.append(tuple(b))
    out.append(point_at(points, s1))
    return out


# ---------------------------------------------------------------- graph


@dataclass
class Graph:
    """Undirected track graph on densified OSM way vertices."""

    xy: list = field(default_factory=list)  # vertex -> (x, y)
    adj: dict = field(default_factory=lambda: defaultdict(list))  # v -> [(u, length, way)]
    ways: dict = field(default_factory=dict)  # way id -> [vertices in order]
    way_lines: dict = field(default_factory=dict)  # way id -> set(line ids)
    key: dict = field(default_factory=dict)  # OSM node id -> vertex

    def vertex(self, xy, node_id=None) -> int:
        if node_id is not None and node_id in self.key:
            return self.key[node_id]
        self.xy.append((float(xy[0]), float(xy[1])))
        v = len(self.xy) - 1
        if node_id is not None:
            self.key[node_id] = v
        return v

    def add_way(self, way_id, coords: list, node_ids: list, step: float, lines=()) -> None:
        """Add a way: OSM nodes are shared vertices, densified points are private."""
        chain = [self.vertex(coords[0], node_ids[0])]
        for k in range(1, len(coords)):
            a, b = coords[k - 1], coords[k]
            n = max(1, math.ceil(seg_len(a, b) / step))
            for j in range(1, n):
                chain.append(self.vertex(_lerp(a, b, j / n)))
            chain.append(self.vertex(b, node_ids[k]))
        for u, v in pairwise(chain):
            if u == v:
                continue
            d = seg_len(self.xy[u], self.xy[v])
            self.adj[u].append((v, d, way_id))
            self.adj[v].append((u, d, way_id))
        self.ways[way_id] = chain
        self.way_lines[way_id] = set(lines)


def ramp_depths(graph: Graph, targets: dict, ramp_m: float) -> dict[int, float]:
    """Depth below ground per vertex with linear ramps at portals and layer changes.

    ``targets``: ``{way: z}`` (z <= 0 for tunnels, >= 0 otherwise). A vertex's target
    depth is the smallest depth of its ways (portal vertices shared with a surface way
    get 0). Depth is then limited by ``d(v) <= d(u) + g * |uv|`` along edges, with
    gradient ``g = D / ramp_m`` (D the tunnel way's target depth), i.e. it rises
    linearly from 0 at a portal to the full depth ``ramp_m`` into the tunnel (and from
    one layer depth to another at layer changes). Min-plus Dijkstra relaxation.
    """
    target = {}
    for way, chain in graph.ways.items():
        d = max(0.0, -targets[way])
        for v in chain:
            target[v] = min(target.get(v, math.inf), d)
    depth = dict(target)
    heap = [(d, v) for v, d in depth.items()]
    heapq.heapify(heap)
    while heap:
        d, v = heapq.heappop(heap)
        if d > depth[v]:
            continue
        for u, length, way in graph.adj[v]:
            g = max(0.0, -targets[way]) / ramp_m
            nd = d + g * length
            if nd < depth.get(u, math.inf) - 1e-9:
                depth[u] = nd
                heapq.heappush(heap, (nd, u))
    return depth


def ramp_heights(graph: Graph, targets: dict, ramp_m: float, height_m: float) -> dict[int, float]:
    """Height above ground per vertex for bridges, ramped *outward* onto the approaches
    (``h(v) >= h(u) - g |uv|`` with ``g = height_m / ramp_m``); max-plus Dijkstra.
    Tunnel ways do not carry height."""
    g = height_m / ramp_m
    height = {}
    for way, chain in graph.ways.items():
        h = max(0.0, targets[way])
        for v in chain:
            height[v] = max(height.get(v, 0.0), h)
    heap = [(-h, v) for v, h in height.items() if h > 0]
    heapq.heapify(heap)
    while heap:
        nh, v = heapq.heappop(heap)
        h = -nh
        if h < height[v]:
            continue
        for u, length, way in graph.adj[v]:
            if targets[way] < 0:
                continue
            cand = h - g * length
            if cand > height.get(u, 0.0) + 1e-9:
                height[u] = cand
                heapq.heappush(heap, (-cand, u))
    return height


def vertex_z(graph: Graph, targets: dict, dcfg: dict) -> dict[int, float]:
    """Final z per vertex: -depth on tunnel vertices with depth > 0, else bridge height."""
    depth = ramp_depths(graph, targets, dcfg["portal_ramp_m"])
    height = ramp_heights(graph, targets, dcfg.get("bridge_ramp_m", 100.0), dcfg["bridge_layer_m"])
    return {v: (-depth[v] if depth.get(v, 0.0) > 1e-6 else height.get(v, 0.0)) for v in depth}


# ---------------------------------------------------------------- routing


def shortest_path(
    graph: Graph,
    sources: dict[int, float],
    targets: dict[int, float],
    allowed=None,
    max_cost: float = math.inf,
) -> tuple[float, list[int]] | None:
    """Multi-source Dijkstra: min over (s, t) of ``sources[s] + path + targets[t]``.

    ``allowed(way)`` restricts edges. Returns ``(cost, vertices)`` or None.
    """
    dist = dict(sources)
    prev: dict[int, int] = {}
    heap = [(c, v) for v, c in sources.items()]
    heapq.heapify(heap)
    best, best_v = math.inf, None
    while heap:
        d, v = heapq.heappop(heap)
        if d > dist.get(v, math.inf) or d >= best or d > max_cost:
            continue
        if v in targets and d + targets[v] < best:
            best, best_v = d + targets[v], v
        for u, length, way in graph.adj[v]:
            if allowed is not None and not allowed(way):
                continue
            nd = d + length
            if nd < dist.get(u, math.inf):
                dist[u] = nd
                prev[u] = v
                heapq.heappush(heap, (nd, u))
    if best_v is None:
        return None
    path = [best_v]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    return best, path[::-1]


def nearest_vertices(
    graph: Graph, p, radius: float, ways_ok=None, per_way: bool = True, grid=None
) -> dict[int, float]:
    """Vertices within ``radius`` of ``p`` (nearest one per way when ``per_way``)."""
    cand = grid.near(p, radius) if grid is not None else range(len(graph.xy))
    best: dict = {}
    for v in cand:
        d = seg_len(graph.xy[v], p)
        if d > radius:
            continue
        ways = {w for _, _, w in graph.adj[v]}
        if ways_ok is not None:
            ways = {w for w in ways if ways_ok(w)}
            if not ways:
                continue
        for w in ways if per_way else [None]:
            if w not in best or d < best[w][0]:
                best[w] = (d, v)
    out: dict[int, float] = {}
    for d, v in best.values():
        out[v] = min(out.get(v, math.inf), d)
    return out


class Grid:
    """Uniform bucket grid over graph vertices for radius queries."""

    def __init__(self, xy: list, cell: float = 100.0):
        self.cell = cell
        self.buckets = defaultdict(list)
        for v, (x, y) in enumerate(xy):
            self.buckets[(int(x // cell), int(y // cell))].append(v)

    def near(self, p, radius: float):
        r = int(radius // self.cell) + 1
        cx, cy = int(p[0] // self.cell), int(p[1] // self.cell)
        for i in range(cx - r, cx + r + 1):
            for j in range(cy - r, cy + r + 1):
                yield from self.buckets.get((i, j), ())


def match_sequence(
    graph: Graph,
    points: list,
    radius: float,
    allowed=None,
    grid=None,
    detour_max: float = 4.0,
) -> dict:
    """Map-match a station sequence onto the track graph.

    Consecutive stations are joined by the shortest track path restricted to
    ``allowed`` ways, from track vertices within ``radius`` of each station (cost: path
    length + 2 x snapping distances). A pair without such a path, or whose path is more
    than ``detour_max`` times the straight distance, is joined by a straight segment and
    flagged. Returns ``{path: [(x, y, vertex|None)], offsets, pairs: [{ratio, method}]}``.
    """
    path: list = []
    offsets: list[float] = []
    pairs = []
    prev_end = None
    for k, p in enumerate(points):
        if k == 0:
            offsets.append(0.0)
            continue
        a = points[k - 1]
        straight = seg_len(a, p)
        src = nearest_vertices(graph, a, radius, allowed, grid=grid)
        dst = nearest_vertices(graph, p, radius, allowed, grid=grid)
        if prev_end is not None and prev_end in src:
            src = {prev_end: 0.0}
        res = None
        if src and dst:
            res = shortest_path(
                graph,
                {v: 2 * d for v, d in src.items()},
                {v: 2 * d for v, d in dst.items()},
                allowed,
                max_cost=detour_max * straight + 4 * radius,
            )
        seg: list = []
        if res is not None:
            verts = res[1]
            seg = [(*graph.xy[v], v) for v in verts]
            length = polyline_length(seg)
            if straight > 0 and length / straight > detour_max:
                res = None
        if res is None:
            seg = [(a[0], a[1], None), (p[0], p[1], None)]
            method = "straight_fallback"
            prev_end = None
        else:
            method = "track"
            prev_end = res[1][-1]
        if not path:
            path.append(seg[0])
        elif seg_len(path[-1], seg[0]) > 1e-6:
            path.append(seg[0])  # cross-over between parallel tracks at a station
        start_len = polyline_length(path)
        path += seg[1:]
        length = polyline_length(path) - start_len
        pairs.append(
            {
                "length_m": round(length, 1),
                "straight_m": round(straight, 1),
                "ratio": round(length / straight, 3) if straight > 0 else None,
                "method": method,
            }
        )
        offsets.append(polyline_length(path))
    if not path and points:
        path = [(points[0][0], points[0][1], None)]
    return {"path": path, "offsets": offsets, "pairs": pairs}
