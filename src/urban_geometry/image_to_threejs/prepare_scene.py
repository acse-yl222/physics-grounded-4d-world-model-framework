"""Turn fetched Overture layers into the compact scene description rendered by three.js.

Every building gets a resolved height, roof form and facade style. Values taken
from the source are kept; inferred values are flagged per building in
``inferred`` so downstream users can tell measured from estimated geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

try:  # imported as part of the package (tests) or run as a script (build_run)
    from .resolve_conflicts import resolve
except ImportError:
    from resolve_conflicts import resolve

FLOOR_M = 3.2
TERRACE_PLOT_M = 22.0  # deepest single terraced-house plot; longer footprints are rows
# Building parts: uncovered remainder of the outline kept as its own volume when at
# least this large (m2, and per piece at least REST_MIN_M2 and REST_MIN_WIDTH_M wide).
REST_MIN_M2 = 4.0
REST_MIN_WIDTH_M = 0.8
PITCHED = {"gabled", "hipped", "half_hipped", "saltbox", "gambrel", "mansard", "pyramidal"}
HOUSE = {"house", "terrace", "semidetached_house", "detached", "bungalow", "houseboat"}
SMALL = {"garage", "garages", "shed", "hut", "roof", "carport", "kiosk", "toilets"}
CLASS_GROUP = {
    **{c: "house" for c in HOUSE},
    **{c: "small" for c in SMALL},
    "residential": "residential",
    "apartments": "residential",
    "dormitory": "residential",
    "commercial": "commercial",
    "retail": "commercial",
    "supermarket": "commercial",
    "office": "office",
    "hotel": "office",
    "school": "civic",
    "university": "civic",
    "college": "civic",
    "hospital": "civic",
    "public": "civic",
    "civic": "civic",
    "government": "civic",
    "train_station": "civic",
    "church": "church",
    "chapel": "church",
    "cathedral": "church",
    "mosque": "church",
    "synagogue": "church",
    "temple": "church",
    "religious": "church",
    "industrial": "industrial",
    "warehouse": "industrial",
    "service": "industrial",
    "transportation": "industrial",
    "parking": "industrial",
}
DEFAULT_HEIGHT = {  # metres, (low, high) drawn deterministically per building
    "house": (9.5, 13.5),
    "small": (2.8, 3.6),
    "residential": (12.0, 19.0),
    "commercial": (8.0, 15.0),
    "office": (16.0, 30.0),
    "civic": (12.0, 20.0),
    "church": (12.0, 18.0),
    "industrial": (7.0, 11.0),
    None: (9.0, 15.0),
}
FACADE_MATERIAL = {
    "brick": "red_brick",
    "plaster": "stucco",
    "stone": "portland_stone",
    "concrete": "concrete",
    "glass": "glass",
    "metal": "metal_clad",
    "wood": "timber",
    "timber_framing": "timber",
}
ROAD_WIDTH = {
    "motorway": 15.0,
    "trunk": 13.0,
    "primary": 11.5,
    "secondary": 10.0,
    "tertiary": 9.0,
    "residential": 7.5,
    "unclassified": 7.0,
    "living_street": 6.0,
    "service": 4.5,
    "pedestrian": 6.0,
    "track": 3.5,
    "footway": 2.4,
    "path": 2.0,
    "cycleway": 2.4,
    "steps": 2.4,
    "bridleway": 2.4,
    "unknown": 5.0,
}
GREEN = {
    "grass",
    "park",
    "garden",
    "recreation_ground",
    "village_green",
    "cemetery",
    "dog_park",
    "golf_course",
    "meadow",
    "allotments",
    "flowerbed",
    "nature_reserve",
    "common",
    "grave_yard",
    "zoo",
    "camp_site",
}


def unit(key: str) -> float:
    """Stable pseudo-random number in [0, 1) derived from a string."""
    return int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) / 2**32


def rings_of(geom: dict) -> list[list[list[list[float]]]]:
    if geom["type"] == "Polygon":
        return [geom["rings"]]
    if geom["type"] == "MultiPolygon":
        return geom["polygons"]
    return []


def ring_area(ring) -> float:
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))


def simplify_ring(ring, tol=0.15):
    """Drop the closing duplicate and near-collinear / near-duplicate vertices."""
    pts = [p for i, p in enumerate(ring) if i == 0 or p != ring[i - 1]]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            ab = math.dist(a, b)
            cross = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
            if ab < tol or cross / max(math.dist(a, c), 1e-6) < tol * 0.5:
                pts.pop(i)
                changed = True
                break
    return pts


def footprint(geom: dict):
    """Normalised polygons: outer CCW, holes CW, closing vertex removed."""
    polys = []
    for poly in rings_of(geom):
        out = []
        for k, ring in enumerate(poly):
            r = simplify_ring(ring)
            if len(r) < 3 or abs(ring_area(r)) < 0.5:
                if k == 0:
                    break
                continue
            ccw = ring_area(r) > 0
            if (k == 0) != ccw:
                r.reverse()
            out.append(r)
        if out:
            polys.append(out)
    return polys


def area_centroid(polys):
    a = cx = cy = 0.0
    for poly in polys:
        for ring in poly:
            for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
                c = x0 * y1 - x1 * y0
                a += c
                cx += (x0 + x1) * c
                cy += (y0 + y1) * c
    if abs(a) < 1e-9:
        x, y = polys[0][0][0]
        return 0.0, x, y
    return a / 2, cx / (3 * a), cy / (3 * a)


def obb(ring):
    """Minimum-area oriented rectangle: (angle_rad, length, width) with length >= width."""
    best = None
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        ang = math.atan2(y1 - y0, x1 - x0)
        c, s = math.cos(ang), math.sin(ang)
        us = [x * c + y * s for x, y in ring]
        vs = [-x * s + y * c for x, y in ring]
        du, dv = max(us) - min(us), max(vs) - min(vs)
        if best is None or du * dv < best[0]:
            best = (du * dv, ang, du, dv)
    _, ang, du, dv = best
    return (ang, du, dv) if du >= dv else (ang + math.pi / 2, dv, du)


def classify_style(f: dict, group, height: float, x: float, y: float, key: str) -> str:
    """Facade style from tagged material/colour, else a London-typical guess."""
    mat = f.get("facade_material")
    if mat in FACADE_MATERIAL:
        return FACADE_MATERIAL[mat]
    colour = (f.get("facade_color") or "").lower()
    if colour in ("white", "#ffffff", "#fff", "ivory", "beige", "#f5f5dc", "cream"):
        return "stucco"
    if colour in ("brown", "red", "#8b4513", "#a52a2a", "maroon"):
        return "red_brick"
    r = unit(key + "style")
    east = x > -700  # Kensington / Chelsea / Bayswater character
    if group == "house":
        if east:
            return "stucco" if r < 0.45 else ("london_stock" if r < 0.85 else "red_brick")
        return "london_stock" if r < 0.5 else ("red_brick" if r < 0.85 else "stucco")
    if group == "residential":
        if height > 30:
            return "concrete" if r < 0.4 else ("modern_clad" if r < 0.8 else "glass")
        if east:
            return "red_brick" if r < 0.45 else ("stucco" if r < 0.7 else "london_stock")
        return "red_brick" if r < 0.35 else ("london_stock" if r < 0.65 else "modern_clad")
    if group == "office":
        return (
            "glass" if height > 22 or r < 0.4 else ("portland_stone" if r < 0.7 else "modern_clad")
        )
    if group == "commercial":
        return (
            "london_stock"
            if r < 0.35
            else ("red_brick" if r < 0.6 else ("stucco" if r < 0.8 else "modern_clad"))
        )
    if group == "civic":
        return "portland_stone" if r < 0.35 else ("red_brick" if r < 0.7 else "modern_clad")
    if group == "church":
        return "ragstone" if r < 0.6 else "london_stock"
    if group == "industrial":
        return "metal_clad" if r < 0.6 else "london_stock"
    if group == "small":
        return "london_stock" if r < 0.6 else "concrete"
    return (
        "london_stock"
        if r < 0.4
        else ("red_brick" if r < 0.65 else ("stucco" if r < 0.85 else "modern_clad"))
    )


def resolve_height(f, group, polys, area, key, local_median):
    inferred = []
    h = f.get("height")
    floors = f.get("num_floors")
    if h is None and floors:
        roof = f.get("roof_height") or (2.5 if f.get("roof_shape") in PITCHED else 0.0)
        h = floors * FLOOR_M + 0.8 + roof
        inferred.append("height_from_floors")
    if h is None:
        if local_median is not None and group not in ("small",):
            h = local_median * (0.85 + 0.3 * unit(key + "h"))
            inferred.append("height_from_neighbours")
        else:
            lo, hi = DEFAULT_HEIGHT.get(group, DEFAULT_HEIGHT[None])
            if group is None and area < 40:
                lo, hi = DEFAULT_HEIGHT["small"]
            h = lo + (hi - lo) * unit(key + "h")
            inferred.append("height_from_class")
    if not floors:
        floors = max(1, round((h - (2.5 if group == "house" else 0)) / FLOOR_M))
    return float(h), int(floors), inferred


def ridge_angle(f, group, ang, length, width):
    """Ridge direction (radians from east): tagged, else along the oriented rectangle."""
    direction = f.get("roof_direction")
    if direction is not None:
        return math.radians(90 - direction) + math.pi / 2
    # London terraced houses have ridges parallel to the street, across the plot
    # depth; footprints longer than a plot are whole rows, ridged along their length.
    across = (
        group == "house"
        and length / max(width, 1e-6) > 1.4
        and width < 8
        and length < TERRACE_PLOT_M
    )
    return ang + (math.pi / 2 if across else 0.0)


def resolve_roof(f, group, h, polys, inferred):
    shape = f.get("roof_shape")
    ang, length, width = obb(polys[0][0])
    rect = abs(ring_area(polys[0][0])) / max(length * width, 1e-6)
    if shape is None:
        if group == "house" and width < 14 and rect > 0.72 and len(polys) == 1:
            shape = "gabled" if width < 9 else "hipped"
        elif group in ("church",) and rect > 0.7:
            shape = "gabled"
        else:
            shape = "flat"
        inferred.append("roof_shape")
    if shape in PITCHED and (rect < 0.6 or width > 30 or len(polys) > 1 or len(polys[0]) > 1):
        # Pitched roofs are fitted to the oriented rectangle of a single ring.
        shape = "flat"
        inferred.append("roof_simplified")
    roof_h = f.get("roof_height")
    if shape in PITCHED and roof_h is None:
        roof_h = min(0.5 * width * math.tan(math.radians(38)), 5.5, h * 0.4)
    if shape not in PITCHED:
        roof_h = 0.0
    ridge = ridge_angle(f, group, ang, length, width)
    return shape, round(roof_h, 2), round(ridge, 4)


def resolve_part_roof(p, group, polys, h, minh):
    """(shape, roofH, ridge) of a building part: tagged pitched roofs over a single ring
    that fits its oriented rectangle, with their own ridge; otherwise flat."""
    shape = p.get("roof_shape") or "flat"
    if shape not in PITCHED:
        return shape, float(p.get("roof_height") or 0.0), None
    ang, length, width = obb(polys[0][0])
    rect = abs(ring_area(polys[0][0])) / max(length * width, 1e-6)
    if rect < 0.6 or width > 30 or len(polys) > 1 or len(polys[0]) > 1:
        return "flat", 0.0, None
    roof_h = p.get("roof_height") or min(
        0.5 * width * math.tan(math.radians(38)), 5.5, (h - minh) * 0.4
    )
    ridge = ridge_angle(p, group, ang, length, width)
    return shape, round(float(roof_h), 2), round(ridge, 4)


def polys_of_shape(geom):
    """Shapely (Multi)Polygon -> normalised polygons (outer CCW, holes CW)."""
    from shapely.geometry import mapping

    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type != "Polygon" or g.is_empty:
            continue
        m = mapping(g)
        out.extend(
            footprint({"type": "Polygon", "rings": [list(map(list, r)) for r in m["coordinates"]]})
        )
    return out


def remainder(polys, parts):
    """Part of the outline not covered by any part, as polygons (slivers dropped)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    outer = unary_union([Polygon(p[0], p[1:]).buffer(0) for p in polys])
    covered = unary_union([Polygon(q[0], q[1:]).buffer(0) for part in parts for q in part["polys"]])
    rest = outer.difference(covered)
    keep = [
        g
        for g in getattr(rest, "geoms", [rest])
        if g.geom_type == "Polygon"
        and g.area >= REST_MIN_M2
        and not g.buffer(-REST_MIN_WIDTH_M / 2).is_empty
    ]
    return polys_of_shape(unary_union(keep)) if keep else []


def round_polys(polys):
    return [[[[round(x, 2), round(y, 2)] for x, y in ring] for ring in poly] for poly in polys]


def build_buildings(buildings, parts, claimed):
    records, known = [], defaultdict(list)
    prepared = []
    for f in buildings:
        if f.get("is_underground"):
            continue
        polys = footprint(f["geometry"])
        if not polys:
            continue
        area, cx, cy = area_centroid(polys)
        group = CLASS_GROUP.get(f.get("class"))
        prepared.append((f, polys, area, cx, cy, group))
        if f.get("height") or f.get("num_floors"):
            h = f.get("height") or f["num_floors"] * FLOOR_M + 0.8
            known[(int(cx // 150), int(cy // 150), group == "house")].append(h)
    medians = {k: statistics.median(v) for k, v in known.items() if len(v) >= 3}

    def neighbourhood(cx, cy, house):
        i, j = int(cx // 150), int(cy // 150)
        vals = [
            medians[(i + a, j + b, house)]
            for a in (-1, 0, 1)
            for b in (-1, 0, 1)
            if (i + a, j + b, house) in medians
        ]
        return statistics.median(vals) if vals else None

    part_map = defaultdict(list)
    for p in parts:
        if p.get("building_id") and not p.get("is_underground"):
            part_map[p["building_id"]].append(p)

    for f, polys, area, cx, cy, group in prepared:
        key = f["id"]
        h, floors, inferred = resolve_height(
            f, group, polys, area, key, neighbourhood(cx, cy, group == "house")
        )
        shape, roof_h, ridge = resolve_roof(f, group, h, polys, inferred)
        style = classify_style(f, group, h, cx, cy, key)
        rec = {
            "id": key,
            "c": [round(cx, 1), round(cy, 1)],
            "polys": round_polys(polys),
            "h": round(h, 2),
            "minh": round(f.get("min_height") or 0.0, 2),
            "floors": floors,
            "roof": shape,
            "roofH": roof_h,
            "ridge": ridge,
            "style": style,
            "cls": f.get("class"),
            "group": group,
            "seed": round(unit(key), 4),
        }
        if f.get("name"):
            rec["name"] = f["name"]
        if f.get("roof_color"):
            rec["roofColor"] = f["roof_color"]
        if f.get("facade_color"):
            rec["facadeColor"] = f["facade_color"]
        if inferred:
            rec["inferred"] = inferred
        if key in claimed:
            rec["landmark"] = claimed[key]
        sub = []
        for p in part_map.get(key, []):
            pp = footprint(p["geometry"])
            if not pp:
                continue
            ph = p.get("height") or (p["num_floors"] * FLOOR_M + 0.8 if p.get("num_floors") else h)
            pmin = p.get("min_height") or ((p.get("min_floor") or 0) * FLOOR_M)
            if ph <= pmin:
                continue
            pshape, proof_h, pridge = resolve_part_roof(p, group, pp, ph, pmin)
            sub.append(
                {
                    "id": p["id"],
                    "polys": round_polys(pp),
                    "h": round(ph, 2),
                    "minh": round(pmin, 2),
                    "roof": pshape,
                    "roofH": proof_h,
                    **({"ridge": pridge} if pridge is not None else {}),
                    **(
                        {"style": FACADE_MATERIAL[p["facade_material"]]}
                        if p.get("facade_material") in FACADE_MATERIAL
                        else {}
                    ),
                }
            )
        if sub:
            # The outline is not drawn when a building has parts; keep what the parts
            # leave uncovered (often a rear extension) as a flat volume no higher than
            # the parts' eaves unless it is most of the building.
            rest = remainder(polys, sub)
            if rest:
                rest_area = sum(
                    abs(ring_area(p[0])) - sum(abs(ring_area(r)) for r in p[1:]) for p in rest
                )
                eaves = [
                    q["h"] - (q["roofH"] if q["roof"] in PITCHED else 0.0)
                    for q in sub
                    if q["minh"] <= 0.5
                ]
                rest_h = h if rest_area >= 0.5 * abs(area) or not eaves else min(h, max(eaves))
                if rest_h > rec["minh"]:
                    sub.append(
                        {
                            "id": f"{key}:rest",
                            "polys": round_polys(rest),
                            "h": round(rest_h, 2),
                            "minh": rec["minh"],
                            "roof": "flat",
                            "roofH": 0.0,
                            "rest": True,
                        }
                    )
                    inferred.append("parts_remainder")
                    rec["inferred"] = inferred
        if sub:
            rec["parts"] = sub
        records.append(rec)
    return records


def lines_of(geom):
    if geom["type"] == "LineString":
        return [geom["line"]]
    if geom["type"] == "MultiLineString":
        return geom["lines"]
    return []


def level_of(f) -> int:
    for rule in f.get("level_rules") or []:
        if rule.get("value") and not rule.get("between"):
            return int(rule["value"])
    return 0


def flags_of(f) -> set[str]:
    out = set()
    for rule in f.get("road_flags") or []:
        if not rule.get("between"):
            out.update(rule.get("values") or [])
    return out


def build_ways(segments):
    roads, rails = [], []
    for f in segments:
        flags = flags_of(f)
        if "is_tunnel" in flags or "is_underground" in flags:
            continue
        lvl = level_of(f)
        if lvl < 0:
            continue
        bridge = "is_bridge" in flags or lvl > 0
        for line in lines_of(f["geometry"]):
            pts = [[round(x, 2), round(y, 2)] for x, y in line]
            if len(pts) < 2:
                continue
            if f.get("subtype") == "rail":
                if f.get("class") in ("subway",) and not bridge:
                    continue
                rails.append({"line": pts, "bridge": bridge, "level": max(lvl, 1 if bridge else 0)})
            elif f.get("subtype") == "road":
                cls = f.get("class") or "unknown"
                width = ROAD_WIDTH.get(cls, 5.0)
                for rule in f.get("width_rules") or []:
                    if rule.get("value") and not rule.get("between"):
                        width = float(rule["value"])
                roads.append(
                    {
                        "line": pts,
                        "cls": cls,
                        "w": round(width, 2),
                        "bridge": bridge,
                        "level": max(lvl, 1 if bridge else 0),
                        **({"name": f["name"]} if f.get("name") else {}),
                    }
                )
    return roads, rails


def build_areas(land_use, land, land_cover, water):
    areas, water_out, trees = [], [], []
    for f in land_use:
        cls = f.get("class")
        kind = None
        if cls in GREEN or f.get("subtype") in ("park",):
            kind = "grass" if cls not in ("cemetery", "grave_yard", "allotments") else cls
            if cls in ("park", "garden", "nature_reserve", "common"):
                kind = "park"
        elif cls in ("pitch", "playground", "track", "stadium"):
            kind = {"pitch": "pitch", "playground": "playground"}.get(cls, "track")
        elif cls in ("pedestrian", "plaza"):
            kind = "plaza"
        elif cls in ("railway",):
            kind = "railway"
        elif cls in ("parking",):
            kind = "parking"
        elif cls in ("construction", "brownfield"):
            kind = "bare"
        if kind:
            for poly in footprint(f["geometry"]):
                areas.append(
                    {
                        "kind": kind,
                        "poly": round_polys([poly])[0],
                        **({"surface": f["surface"]} if f.get("surface") else {}),
                    }
                )
    for f in land:
        sub, geom = f.get("subtype"), f["geometry"]
        if sub == "tree" and geom["type"] == "Point":
            x, y = geom["point"]
            trees.append([round(x, 1), round(y, 1), round(unit(f["id"]), 3)])
        elif sub == "tree" and geom["type"] == "LineString":
            line = geom["line"]
            for (x0, y0), (x1, y1) in itertools.pairwise(line):
                n = max(1, int(math.dist((x0, y0), (x1, y1)) // 9))
                for k in range(n):
                    t = (k + 0.5) / n
                    trees.append(
                        [
                            round(x0 + t * (x1 - x0), 1),
                            round(y0 + t * (y1 - y0), 1),
                            round(unit(f["id"] + str(k)), 3),
                        ]
                    )
        elif sub in ("forest", "shrub", "grass", "wetland", "sand") and geom["type"] != "Point":
            kind = {
                "forest": "wood",
                "shrub": "scrub",
                "grass": "grass",
                "wetland": "wetland",
                "sand": "sand",
            }[sub]
            for poly in footprint(geom):
                areas.append({"kind": kind, "poly": round_polys([poly])[0]})
    for f in water:
        geom = f["geometry"]
        if geom["type"] in ("Polygon", "MultiPolygon"):
            for poly in footprint(geom):
                water_out.append(
                    {"kind": f.get("class") or "water", "poly": round_polys([poly])[0]}
                )
        else:
            for line in lines_of(geom):
                width = {"river": 12.0, "canal": 12.0, "stream": 3.0, "drain": 2.0}.get(
                    f.get("class"), 3.0
                )
                water_out.append({"kind": f.get("class"), "line": line, "w": width})
    return areas, water_out, trees


# Mapped point features -> reusable asset ids in resources/.
ASSET_FOR_CLASS = {
    "street_lamp": "street_lamp",
    "bench": "bench",
    "bus_stop": "bus_stop",
    "post_box": "post_box",
    "telephone": "telephone_box",
    "bollard": "bollard",
    "traffic_signals": "traffic_signal",
    "waste_basket": "waste_basket",
    "bicycle_parking": "bicycle_stand",
    "bicycle_rental": "cycle_hire_dock",
}
LIT_ROADS = {"primary", "secondary", "tertiary", "trunk", "residential", "unclassified"}
LAMP_SPACING_M = 32.0


class RoadIndex:
    """Grid of carriageway segments for nearest-road queries."""

    def __init__(self, roads, cell=40.0):
        self.cell, self.grid = cell, defaultdict(list)
        for r in roads:
            if r["level"] or prepare_kind(r["cls"]) is None:
                continue
            for a, b in itertools.pairwise(r["line"]):
                for key in self.cells(a, b):
                    self.grid[key].append((a, b, r))

    def cells(self, a, b):
        c = self.cell
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        for i in range(int(x0 // c), int(x1 // c) + 1):
            for j in range(int(y0 // c), int(y1 // c) + 1):
                yield i, j

    def nearest(self, x, y, radius=45.0):
        best = None
        i, j = int(x // self.cell), int(y // self.cell)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for a, b, r in self.grid.get((i + di, j + dj), ()):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    ll = dx * dx + dy * dy or 1e-9
                    t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / ll))
                    px, py = a[0] + t * dx, a[1] + t * dy
                    d = math.hypot(x - px, y - py)
                    if d <= radius and (best is None or d < best[0]):
                        best = (d, px, py, r)
        return best


def prepare_kind(cls):
    return None if cls in ("footway", "path", "steps", "cycleway", "bridleway", "track") else cls


def heading_to(x, y, near):
    """Rotation about z turning an asset's front (+y) towards the nearest road."""
    if near is None:
        return 0.0
    _, px, py, _ = near
    return round(math.atan2(py - y, px - x) - math.pi / 2, 3)


def build_placements(infra, roads):
    """Asset placements {asset: [[x, y, heading, procedural]]}.

    Mapped points keep their position (procedural = 0). Street lamps are also
    spaced along lit roads where none is mapped nearby (procedural = 1).
    """
    index = RoadIndex(roads)
    out = defaultdict(list)
    for f in infra:
        asset = ASSET_FOR_CLASS.get(f.get("class"))
        if asset and f["geometry"]["type"] == "Point":
            x, y = f["geometry"]["point"]
            out[asset].append([round(x, 1), round(y, 1), heading_to(x, y, index.nearest(x, y)), 0])
    mapped = defaultdict(list)
    for x, y, *_ in out["street_lamp"]:
        mapped[(int(x // 40), int(y // 40))].append((x, y))

    def near_mapped(x, y):
        i, j = int(x // 40), int(y // 40)
        return any(
            math.hypot(x - mx, y - my) < 20
            for di in (-1, 0, 1)
            for dj in (-1, 0, 1)
            for mx, my in mapped.get((i + di, j + dj), ())
        )

    for r in roads:
        if r["cls"] not in LIT_ROADS or r["level"]:
            continue
        side, carry = 1, LAMP_SPACING_M / 2
        for a, b in itertools.pairwise(r["line"]):
            length = math.dist(a, b)
            if length < 1e-6:
                continue
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            t = carry
            while t < length:
                off = r["w"] / 2 + 1.2
                x = a[0] + ux * t - uy * off * side
                y = a[1] + uy * t + ux * off * side
                if not near_mapped(x, y):
                    # Lamp arm (+y) points back across the carriageway.
                    heading = math.atan2(uy * side, -ux * side) - math.pi / 2
                    out["street_lamp"].append([round(x, 1), round(y, 1), round(heading, 3), 1])
                side = -side
                t += LAMP_SPACING_M
            carry = t - length
    return dict(out)


def build_fixtures(infra):
    out = defaultdict(list)
    for f in infra:
        cls, geom = f.get("class"), f["geometry"]
        if geom["type"] == "LineString" and cls in ("wall", "fence", "hedge", "retaining_wall"):
            out[cls].append([[round(x, 1), round(y, 1)] for x, y in geom["line"]])
    return dict(out)


def add_terrain(scene, cfg, index_path):
    """Attach the configured DEM to the scene (see terrain.py)."""
    try:
        from .fetch_terrain import load_dem
        from .terrain import apply_terrain, scene_terrain
    except ImportError:
        from fetch_terrain import load_dem
        from terrain import apply_terrain, scene_terrain

    opts = cfg.get("terrain") or {}
    dem, index = load_dem(index_path)
    record = scene_terrain(
        dem,
        index,
        dx=opts.get("scene_grid_m", 10.0),
        half=opts.get("half_m", cfg["domain_m"] / 2 + 100),
    )
    scene["source"]["terrain"] = apply_terrain(scene, record)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("overture", type=Path, help="directory written by fetch_overture.py")
    p.add_argument("out", type=Path, help="scene JSON to write (normally under cache/)")
    p.add_argument(
        "--claims",
        type=Path,
        help="landmarks/index.json; tags footprints replaced by landmark modules",
    )
    p.add_argument(
        "--terrain",
        type=Path,
        help="DEM index.json (fetch_terrain.py); adds scene terrain and ground levels",
    )
    args = p.parse_args()
    cfg = json.loads(args.config.read_text())
    load = lambda name: json.loads((args.overture / f"{name}.json").read_text())["features"]
    claimed = {}
    if args.claims and args.claims.exists():
        for entry in json.loads(args.claims.read_text()):
            for i in entry["claims"]:
                claimed[i] = entry["id"]
    buildings = build_buildings(load("buildings"), load("building_parts"), claimed)
    roads, rails = build_ways(load("segments"))
    areas, water, trees = build_areas(
        load("land_use"), load("land"), load("land_cover"), load("water")
    )
    infra = load("infrastructure")
    index = json.loads((args.overture / "index.json").read_text())
    scene = {
        "scene_id": cfg["scene_id"],
        "origin": cfg["origin"],
        "half_m": cfg["domain_m"] / 2,
        "source": {
            "overture_release": index["release"],
            "license": index["license"],
            "layers": {k: v["sha256"] for k, v in index["layers"].items()},
        },
        "buildings": buildings,
        "roads": roads,
        "rails": rails,
        "areas": areas,
        "water": water,
        "trees": trees,
        "fixtures": build_fixtures(infra),
        "placements": build_placements(infra, roads),
    }
    scene["source"]["conflicts_resolved"] = resolve(scene)
    if args.terrain:
        add_terrain(scene, cfg, args.terrain)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scene, separators=(",", ":")))
    inferred = sum(
        1
        for b in buildings
        if "height_from_floors" not in b.get("inferred", [])
        and any(i.startswith("height") for i in b.get("inferred", []))
    )
    print(
        f"buildings={len(buildings)} (height estimated without floors: {inferred}) "
        f"roads={len(roads)} rails={len(rails)} areas={len(areas)} water={len(water)} "
        f"trees={len(scene['trees'])} claimed={len(claimed)} "
        f"conflicts={scene['source']['conflicts_resolved']} -> {args.out}"
    )


if __name__ == "__main__":
    main()
