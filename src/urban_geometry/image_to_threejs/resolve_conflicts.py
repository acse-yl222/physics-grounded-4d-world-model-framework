"""Reconcile mapped geometry that overlaps once road widths are assumed.

Overture carries road centrelines without kerb lines, so a carriageway drawn at its
class width can run into footprints, and a few mapped features sit in water. This
step keeps every source feature and records how each one is drawn instead:

* roads: carriageway (``wl``/``wr``) and pavement (``pl``/``pr``) half widths per
  vertex and side, narrowed to the clearance from the nearest footprint on that side,
  never below ``MIN_HALF_M``; segments whose midpoint lies inside a
  footprint (arches, passages, covered yards) are listed in ``covered`` and not drawn;
  segments over water that are not mapped as bridges are listed in ``wet`` and get
  parapets.
* buildings: houseboats and small unnamed footprints lying wholly in water are
  flagged ``vessel`` and drawn as moored boats.
* trees: mapped trees inside footprints or water are dropped; those on a carriageway
  are moved to its kerb.

Counts of every change are returned for the scene's provenance.
"""

from __future__ import annotations

import itertools
import math
from collections import defaultdict

CELL_M = 24.0
MIN_HALF_M = 1.6
CLEARANCE_M = 0.4
DENSIFY_M = 8.0
PAVEMENT_M = 2.5
VESSEL_MAX_M2 = 450.0
DRIVABLE = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "residential",
    "unclassified",
    "living_street",
    "service",
}


def point_in_ring(ring, x, y) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def point_in_poly(poly, x, y) -> bool:
    return point_in_ring(poly[0], x, y) and not any(point_in_ring(h, x, y) for h in poly[1:])


def closest(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / ((dx * dx + dy * dy) or 1e-12)
    t = min(1.0, max(0.0, t))
    return ax + t * dx, ay + t * dy


def seg_dist(px, py, ax, ay, bx, by) -> float:
    cx, cy = closest(px, py, ax, ay, bx, by)
    return math.hypot(px - cx, py - cy)


def normals(line):
    """Unit left normals per vertex (averaged at interior vertices)."""
    out = []
    n = len(line)
    for k in range(n):
        a, b = line[max(0, k - 1)], line[min(n - 1, k + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1.0
        out.append((-dy / ln, dx / ln))
    return out


def bbox(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


class PolyIndex:
    """Grid of polygons (by bounding box) and their edges for point queries."""

    def __init__(self, polys):
        self.polys = polys
        self.boxes = [bbox(p[0]) for p in polys]
        self.cells = defaultdict(list)
        self.edges = defaultdict(list)
        for k, (x0, y0, x1, y1) in enumerate(self.boxes):
            for c in self._span(x0, y0, x1, y1):
                self.cells[c].append(k)
            for ring in polys[k]:
                for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
                    for c in self._span(
                        min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])
                    ):
                        self.edges[c].append((a[0], a[1], b[0], b[1]))

    @staticmethod
    def _span(x0, y0, x1, y1):
        for i in range(math.floor(x0 / CELL_M), math.floor(x1 / CELL_M) + 1):
            for j in range(math.floor(y0 / CELL_M), math.floor(y1 / CELL_M) + 1):
                yield i, j

    def containing(self, x, y):
        for k in self.cells.get((math.floor(x / CELL_M), math.floor(y / CELL_M)), ()):
            x0, y0, x1, y1 = self.boxes[k]
            if x0 <= x <= x1 and y0 <= y <= y1 and point_in_poly(self.polys[k], x, y):
                return k
        return None

    def clearance(self, x, y, nx, ny, limit):
        """Distances to the nearest edges left (+n) and right (-n) of a point, each
        capped at ``limit``. Edges ahead or behind along the way (more than 60 degrees
        off the normal) are ignored so a building closing a street does not narrow it.
        """
        left = right = limit
        r = math.ceil(limit / CELL_M)
        ci, cj = math.floor(x / CELL_M), math.floor(y / CELL_M)
        seen = set()
        for i in range(ci - r, ci + r + 1):
            for j in range(cj - r, cj + r + 1):
                for e in self.edges.get((i, j), ()):
                    if e in seen:
                        continue
                    seen.add(e)
                    cx, cy = closest(x, y, *e)
                    d = math.hypot(cx - x, cy - y)
                    if d >= max(left, right):
                        continue
                    lateral = (cx - x) * nx + (cy - y) * ny
                    if abs(lateral) < 0.5 * d:
                        continue
                    if lateral > 0:
                        left = min(left, d)
                    else:
                        right = min(right, d)
        return left, right


def densify(line, step=DENSIFY_M):
    out = [line[0]]
    for a, b in itertools.pairwise(line):
        n = max(1, math.ceil(math.dist(a, b) / step))
        for k in range(1, n + 1):
            t = k / n
            out.append([round(a[0] + t * (b[0] - a[0]), 2), round(a[1] + t * (b[1] - a[1]), 2)])
    return out


def resolve_roads(roads, footprints, water):
    counts = defaultdict(int)
    for r in roads:
        if r["level"] or r["bridge"] or len(r["line"]) < 2:
            continue
        line = densify(r["line"])
        mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in itertools.pairwise(line)]
        covered = [k for k, m in enumerate(mids) if footprints.containing(*m) is not None]
        wet = [
            k for k, m in enumerate(mids) if k not in covered and water.containing(*m) is not None
        ]
        half = r["w"] / 2
        outer = half + PAVEMENT_M
        sides = None
        if r["cls"] in DRIVABLE:
            sides = {"wl": [], "wr": [], "pl": [], "pr": []}
            for p, (nx, ny) in zip(line, normals(line), strict=True):
                if footprints.containing(*p) is not None:
                    clear = (MIN_HALF_M, MIN_HALF_M)
                else:
                    clear = footprints.clearance(p[0], p[1], nx, ny, outer + CLEARANCE_M)
                for side, c in zip("lr", clear, strict=True):
                    w = max(MIN_HALF_M, min(half, c - CLEARANCE_M))
                    sides["w" + side].append(round(w, 2))
                    sides["p" + side].append(round(max(w, min(outer, c - 0.05)), 2))
            if all(
                v >= limit - 0.05
                for key, limit in (("wl", half), ("wr", half), ("pl", outer), ("pr", outer))
                for v in sides[key]
            ):
                sides = None
        if not (sides or covered or wet):
            continue
        r["line"] = line
        if sides:
            r |= sides
            if any(v < half - 0.05 for v in sides["wl"] + sides["wr"]):
                counts["roads_narrowed"] += 1
            else:
                counts["pavements_narrowed"] += 1
        if covered:
            r["covered"] = covered
            counts["road_segments_covered"] += len(covered)
        if wet:
            r["wet"] = wet
            counts["road_segments_over_water"] += len(wet)
    return counts


def resolve_buildings(buildings, water):
    counts = defaultdict(int)
    for b in buildings:
        if b.get("landmark"):
            continue
        ring = b["polys"][0][0]
        afloat = all(water.containing(x, y) is not None for x, y in ring)
        area = abs(
            sum(a[0] * c[1] - c[0] * a[1] for a, c in zip(ring, ring[1:] + ring[:1], strict=True))
            / 2
        )
        if b.get("cls") == "houseboat" or (afloat and area <= VESSEL_MAX_M2 and not b.get("name")):
            b["vessel"] = True
            counts["vessels"] += 1
    return counts


def resolve_trees(trees, roads, footprints, water):
    counts = defaultdict(int)
    carriage = defaultdict(list)
    for r in roads:
        if r["level"] or r["cls"] not in DRIVABLE:
            continue
        line = r["line"]
        wl = r.get("wl") or [r["w"] / 2] * len(line)
        wr = r.get("wr") or wl
        for k, (a, b) in enumerate(itertools.pairwise(line)):
            h = max(wl[k], wl[k + 1], wr[k], wr[k + 1])
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            for c in PolyIndex._span(x0 - h, y0 - h, x1 + h, y1 + h):
                carriage[c].append((a, b, h))
    kept = []
    for x, y, s in trees:
        if footprints.containing(x, y) is not None:
            counts["trees_dropped_in_buildings"] += 1
            continue
        if water.containing(x, y) is not None:
            counts["trees_dropped_in_water"] += 1
            continue
        for a, b, h in carriage.get((math.floor(x / CELL_M), math.floor(y / CELL_M)), ()):
            d = seg_dist(x, y, a[0], a[1], b[0], b[1])
            if d < h:
                dx, dy = b[0] - a[0], b[1] - a[1]
                ln = math.hypot(dx, dy) or 1.0
                nx, ny = -dy / ln, dx / ln
                side = 1.0 if (x - a[0]) * nx + (y - a[1]) * ny >= 0 else -1.0
                shift = h + 1.2 - d
                x, y = round(x + nx * side * shift, 1), round(y + ny * side * shift, 1)
                counts["trees_moved_to_kerb"] += 1
                break
        kept.append([x, y, s])
    return kept, counts


def resolve(scene):
    """Apply the rules above to a prepared scene in place; return change counts."""
    water = PolyIndex([w["poly"] for w in scene["water"] if w.get("poly")])
    counts = {}
    counts |= resolve_buildings(scene["buildings"], water)
    # Vessels float; roads and trees need only clear solid footprints.
    footprints = PolyIndex(
        [p for b in scene["buildings"] if not b.get("vessel") for p in b["polys"]]
    )
    counts |= resolve_roads(scene["roads"], footprints, water)
    scene["trees"], tree_counts = resolve_trees(scene["trees"], scene["roads"], footprints, water)
    counts |= tree_counts
    return dict(sorted(counts.items()))
