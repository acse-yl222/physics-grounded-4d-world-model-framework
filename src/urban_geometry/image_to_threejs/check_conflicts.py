"""Report spatial conflicts in a prepared scene: buildings on carriageways or in
water, carriageways crossing water without a bridge, and trees in buildings,
water or on carriageways.

  python3 check_conflicts.py cache/imperial_corridor/image_to_threejs/scene.json \
      --out cache/imperial_corridor/image_to_threejs/conflicts.json
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

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
MIN_OVERLAP_M2 = 4.0


def polygon(poly):
    shape = Polygon(poly[0], poly[1:])
    return shape if shape.is_valid else shape.buffer(0)


def footprints(scene):
    for b in scene["buildings"]:
        for poly in b["polys"]:
            yield b, polygon(poly)


def carriageways(scene, drivable_only=True):
    """Drawn carriageway areas, honouring per-side widths and covered segments
    recorded by resolve_conflicts; wet segments are drawn as decks (bridges)."""
    for r in scene["roads"]:
        if drivable_only and r["cls"] not in DRIVABLE:
            continue
        line = r["line"]
        if len(line) < 2:
            continue
        if "wl" not in r and "covered" not in r:
            yield r, LineString(line).buffer(r["w"] / 2, cap_style="flat"), set()
            continue
        wl = r.get("wl") or [r["w"] / 2] * len(line)
        wr = r.get("wr") or wl
        skip = set(r.get("covered", []))
        parts = []
        for k in range(len(line) - 1):
            (ax, ay), (bx, by) = line[k], line[k + 1]
            ln = math.hypot(bx - ax, by - ay)
            if k in skip or ln < 1e-6:
                continue
            nx, ny = -(by - ay) / ln, (bx - ax) / ln
            parts.append(
                Polygon(
                    [
                        (ax + nx * wl[k], ay + ny * wl[k]),
                        (bx + nx * wl[k + 1], by + ny * wl[k + 1]),
                        (bx - nx * wr[k + 1], by - ny * wr[k + 1]),
                        (ax - nx * wr[k], ay - ny * wr[k]),
                    ]
                ).buffer(0)
            )
        if parts:
            yield r, unary_union(parts), set(r.get("wet", []))


def check(scene):
    water = [
        Polygon(w["poly"][0], w["poly"][1:]).buffer(0) for w in scene["water"] if w.get("poly")
    ]
    water_union = unary_union(water) if water else Polygon()
    roads = list(carriageways(scene))
    road_tree = STRtree([g for _, g, _ in roads])
    out = {
        "building_on_road": [],
        "building_in_water": [],
        "road_over_water": [],
        "tree_in_building": 0,
        "tree_in_water": 0,
        "tree_on_road": 0,
    }
    prints = list(footprints(scene))
    for b, shape in prints:
        if b.get("vessel"):
            continue
        for k in road_tree.query(shape):
            r, g, _ = roads[k]
            if r["level"]:
                continue
            area = shape.intersection(g).area
            if area >= MIN_OVERLAP_M2:
                out["building_on_road"].append(
                    {
                        "building": b["id"],
                        "name": b.get("name"),
                        "cls": b.get("cls"),
                        "landmark": b.get("landmark"),
                        "road": r.get("name"),
                        "road_cls": r["cls"],
                        "overlap_m2": round(area, 1),
                        "share": round(area / max(shape.area, 1e-6), 3),
                    }
                )
        wet = shape.intersection(water_union).area if not water_union.is_empty else 0.0
        if wet >= MIN_OVERLAP_M2:
            out["building_in_water"].append(
                {
                    "building": b["id"],
                    "name": b.get("name"),
                    "cls": b.get("cls"),
                    "landmark": b.get("landmark"),
                    "overlap_m2": round(wet, 1),
                    "share": round(wet / max(shape.area, 1e-6), 3),
                }
            )
    for r, g, wet_segments in roads:
        if r["level"] or r["bridge"] or wet_segments:
            continue
        wet = g.intersection(water_union).area if not water_union.is_empty else 0.0
        if wet >= MIN_OVERLAP_M2:
            out["road_over_water"].append(
                {"road": r.get("name"), "cls": r["cls"], "overlap_m2": round(wet, 1)}
            )
    prints = [(b, s) for b, s in prints if not b.get("vessel")]
    building_tree = STRtree([s for _, s in prints])
    for x, y, _ in scene["trees"]:
        p = Point(x, y)
        if any(prints[k][1].contains(p) for k in building_tree.query(p)):
            out["tree_in_building"] += 1
        elif water_union.contains(p):
            out["tree_in_water"] += 1
        elif any(roads[k][1].contains(p) for k in road_tree.query(p)):
            out["tree_on_road"] += 1
    return out


def summary(report):
    lines = []
    for key in ("building_on_road", "building_in_water", "road_over_water"):
        items = report[key]
        lines.append(f"{key}: {len(items)}")
        if key != "road_over_water":
            lines.append(
                "  by class: "
                + ", ".join(f"{c}={n}" for c, n in Counter(i["cls"] for i in items).most_common(6))
            )
            big = [i for i in items if i["share"] > 0.25]
            lines.append(f"  more than 25% of footprint: {len(big)}")
        else:
            lines.append(
                "  by road class: "
                + ", ".join(f"{c}={n}" for c, n in Counter(i["cls"] for i in items).most_common(6))
            )
    for key in ("tree_in_building", "tree_in_water", "tree_on_road"):
        lines.append(f"{key}: {report[key]}")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("scene", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = check(json.loads(args.scene.read_text()))
    print(summary(report))
    if args.out:
        args.out.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
