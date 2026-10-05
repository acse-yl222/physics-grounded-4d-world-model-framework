"""img2city/scene/assets.py -- the NON-BUILDING scene layer (supervisor direction, 2026-07-07:
"reconstruct all the assets in the area, not just buildings ... split the scene into
parts, generate each, then composite"). Two deterministic, zero-LLM sources:

  trees  DeepForest (weecology, pretrained aerial tree-crown detector) run on the
         SAME bbox-cropped satellite tile the aligned top comparison uses, so each
         detection's pixel maps straight to scene metres. False positives on roofs
         are killed exactly: any detection whose centre falls inside an OSM building
         footprint is dropped (we have the true polygons). Crown radius comes from
         the detected box size in metres; tree height is scaled from the radius.
         (related_work_methods.md M: "lowest-effort item in this whole report")
  roads  Overpass highway ways (same bbox + mirror fallback as city_pilot.fetch_osm),
         projected with the SAME equirect anchor as the buildings, each a centreline
         polyline + a per-class width -- the scene builds them as flat ribbons.

Both cache to JSON next to buildings.json and are picked up by city_generate
--assemble-only; refetch/redetect only runs when the cache is missing.

Usage:
  python -m img2city.scene.assets --out data/city_sk            # trees + roads (cached)
  python -m img2city.scene.assets --out data/city_sk --force    # ignore caches
"""
from __future__ import annotations
import argparse
import json
import math
import os
import time
import urllib.parse
import urllib.request

from img2city import config

OVERPASS = tuple(config.OVERPASS_URLS)      # mirrors, tried in order (IMG2CITY_OVERPASS_URLS)

# ribbon width (m) per OSM highway class; classes not listed are skipped
ROAD_WIDTH = {
    "trunk": 12.0, "trunk_link": 8.0,
    "primary": 10.0, "primary_link": 8.0, "secondary": 9.0, "tertiary": 8.0,
    "unclassified": 6.0, "residential": 6.0, "living_street": 5.0,
    "service": 4.0, "pedestrian": 5.0, "footway": 2.5, "path": 2.0,
    "cycleway": 2.5, "track": 3.0,
    # busway: bus-only carriageway (Amsterdam Marnixstraat corridor) -- a REAL
    # road the 08-13 verifier caught as never-drawn, same class as residential
    "busway": 6.0,
}

# highway classes we deliberately do NOT draw as carriageways (vertical or
# indoor pedestrian micro-features); the pipeline verifier treats these as
# fine-to-skip rather than missing roads
ROAD_SKIP_OK = {"steps", "corridor", "platform", "elevator", "proposed",
                "construction", "razed", "abandoned", "services", "bridleway"}


def _overpass(query):
    last = None
    for url in OVERPASS:
        try:
            req = urllib.request.Request(
                url, data=urllib.parse.urlencode({"data": query}).encode(),
                headers={"User-Agent": "img2city/0.1"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)["elements"]
        except Exception as e:                       # noqa: BLE001 - try next mirror
            last = e
            time.sleep(2)
    # RuntimeError, NOT SystemExit: assemble() treats the scene layer as
    # additive-never-fatal via `except Exception`, and SystemExit is not an
    # Exception -- an Overpass outage was killing the whole assembly (city_cw
    # bootstrap, 08-10) instead of skipping roads/trees for that run
    raise RuntimeError(f"Overpass failed on all mirrors: {last}")


def fetch_roads(bbox, cache, force=False):
    """Highway ways with geometry in bbox -> raw element list, cached to JSON."""
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    s, w, n, e = bbox
    els = _overpass(
        f'[out:json][timeout:60];way["highway"]({s},{w},{n},{e});out geom;')
    with open(cache, "w") as f:
        json.dump(els, f)
    return els


def roads_to_local(elements, anchor):
    """Overpass highway ways -> [{id, class, width, pts:[[x,y],...]}] in scene metres
    (same equirect anchor as the building footprints)."""
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0
    roads = []
    for el in elements:
        tags = el.get("tags") or {}
        cls = tags.get("highway", "")
        if cls not in ROAD_WIDTH or tags.get("area") == "yes":
            continue
        pts = [[round((g["lon"] - anchor["lon0"]) * kx, 2),
                round((g["lat"] - anchor["lat0"]) * ky, 2)]
               for g in el.get("geometry") or []]
        if len(pts) < 2:
            continue
        roads.append({"id": el["id"], "class": cls,
                      "width": ROAD_WIDTH[cls], "pts": pts,
                      "name": tags.get("name", "")})
    return roads


def fetch_green(bbox, cache, force=False):
    """Green-infrastructure ways (parks/grass/gardens/woods + hedges) in bbox,
    cached like fetch_roads."""
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    s, w, n, e = bbox
    bb = f"({s},{w},{n},{e})"
    els = _overpass(
        '[out:json][timeout:60];('
        f'way["leisure"~"^(park|garden|pitch|playground|recreation_ground|common)$"]{bb};'
        f'way["landuse"~"^(grass|recreation_ground|village_green|meadow|forest|'
        f'flowerbed|greenfield|cemetery)$"]{bb};'
        f'way["natural"~"^(wood|scrub|grassland)$"]{bb};'
        # WATER (Canary Wharf demo, 08-10): docks/basins/riversides are the
        # visual anchor of any waterfront area -- rides in the green layer as
        # kind="water", rendered as a water plane instead of grass
        f'way["natural"="water"]{bb};'
        f'way["waterway"~"^(riverbank|dock)$"]{bb};'
        f'way["landuse"~"^(basin|reservoir)$"]{bb};'
        f'way["barrier"="hedge"]{bb};'
        ');out geom;')
    with open(cache, "w") as f:
        json.dump(els, f)
    return els


def _poly_area(pts):
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1]
                   - pts[(i + 1) % len(pts)][0] * pts[i][1]
                   for i in range(len(pts)))) / 2.0


def _bbox_ext(anchor, margin=40.0):
    """Model extent in scene metres (bbox + the Ground apron margin)."""
    s, w, n, e = anchor["bbox"]
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0
    return ((w - anchor["lon0"]) * kx - margin, (s - anchor["lat0"]) * ky - margin,
            (e - anchor["lon0"]) * kx + margin, (n - anchor["lat0"]) * ky + margin)


def green_to_local(elements, anchor):
    """Overpass green ways -> (areas, hedges) in scene metres. areas are CLOSED
    polygons [{id, kind, pts}], hedges polylines [{id, pts}] (open hedge ways;
    a closed hedge way is BOTH: its ring is drawn as a hedge line, not a lawn).
    Every geometry is CLIPPED to the model bbox (+ground apron): Overpass
    returns the FULL way for anything touching the query box, so a park like
    Kensington Gardens otherwise drags a kilometre of lawn + thousands of
    in-fill trees outside the model (Albert Hall area, 08-20)."""
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0
    from shapely.geometry import Polygon, LineString, box as _box
    clip = _box(*_bbox_ext(anchor))
    areas, hedges = [], []
    for el in elements:
        tags = el.get("tags") or {}
        pts = [[round((g["lon"] - anchor["lon0"]) * kx, 2),
                round((g["lat"] - anchor["lat0"]) * ky, 2)]
               for g in el.get("geometry") or []]
        if len(pts) < 2:
            continue
        closed = math.dist(pts[0], pts[-1]) < 1.0
        if closed and len(pts) > 3:
            pts = pts[:-1]
        if tags.get("barrier") == "hedge":
            line = pts + ([pts[0]] if closed else [])
            try:
                g = LineString(line).intersection(clip)
                parts = list(getattr(g, "geoms", [g]))
            except Exception:
                parts = []
            for j, seg in enumerate(p for p in parts if p.length > 1.0):
                hedges.append({"id": el["id"] * 10 + j,
                               "pts": [[round(x, 2), round(y, 2)]
                                       for x, y in seg.coords]})
            continue
        if not closed or _poly_area(pts) < 25.0:
            continue
        if (tags.get("natural") == "water" or tags.get("waterway")
                or tags.get("landuse") in ("basin", "reservoir")):
            kind = "water"
        else:
            kind = (tags.get("leisure") or tags.get("landuse")
                    or tags.get("natural") or "grass")
        try:
            g = Polygon(pts).buffer(0).intersection(clip)
            parts = list(getattr(g, "geoms", [g]))
        except Exception:
            parts = []
        for j, part in enumerate(p for p in parts
                                 if getattr(p, "area", 0) >= 25.0):
            areas.append({"id": el["id"] * 10 + j, "kind": kind,
                          "pts": [[round(x, 2), round(y, 2)]
                                  for x, y in part.exterior.coords[:-1]],
                          "name": tags.get("name", "")})
    return areas, hedges


def scatter_park_trees(areas, trees, buildings, target_m2_per_tree=160.0):
    """Deterministic in-fill: parks/lawns where DeepForest found fewer trees than
    ~1 per target_m2_per_tree get seeded jittered-grid trees (satellite shadows
    and winter canopies make the detector miss park trees). Never inside a
    building footprint, never within 4 m of a detected tree. Returns the ADDED
    trees only."""
    import random
    added = []
    for ar in areas:
        if ar["kind"] in ("pitch", "playground", "flowerbed", "water"):
            continue                                # open turf stays open;
                                                    # water grows no trees (CW
                                                    # docks got 1031 of them)
        pts = ar["pts"]
        area = _poly_area(pts)
        if area < 300.0:
            continue
        inside = [t for t in trees
                  if _point_in_poly(t["x"], t["y"], pts)]
        want = int(area / target_m2_per_tree)
        if len(inside) >= want:
            continue
        rng = random.Random(ar["id"])
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        step = max(8.0, math.sqrt(area / max(1, want)) * 0.9)
        cand = []
        y = min(ys) + step / 2
        while y < max(ys):
            x = min(xs) + step / 2
            while x < max(xs):
                jx = x + rng.uniform(-step / 3, step / 3)
                jy = y + rng.uniform(-step / 3, step / 3)
                if _point_in_poly(jx, jy, pts):
                    cand.append((jx, jy))
                x += step
            y += step
        rng.shuffle(cand)
        near = inside + added
        for jx, jy in cand:
            if len(inside) + len([a for a in added
                                  if _point_in_poly(a["x"], a["y"], pts)]) >= want:
                break
            if any((t["x"] - jx) ** 2 + (t["y"] - jy) ** 2 < 16.0 for t in near):
                continue
            if any(_point_in_poly(jx, jy, b["pts"]) for b in buildings):
                continue
            t = {"x": round(jx, 2), "y": round(jy, 2),
                 "r": round(rng.uniform(2.2, 4.5), 2), "score": 0.0}
            added.append(t); near.append(t)
    return added


def fetch_transport(bbox, cache, force=False):
    """Rail lines (DLR/heavy rail, with bridge/tunnel tags) + non-rail bridge
    ways -- Canary Wharf's DLR viaduct and dock footbridges made the case
    (08-11): OSM has them all, the scene never drew them."""
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    s, w, n, e = bbox
    bb = f"({s},{w},{n},{e})"
    els = _overpass(
        '[out:json][timeout:60];('
        f'way["railway"~"^(rail|light_rail|subway|tram)$"]{bb};'
        f'way["highway"]["bridge"="yes"]{bb};'
        f'way["man_made"="bridge"]{bb};'
        ');out geom;')
    with open(cache, "w") as f:
        json.dump(els, f)
    return els


def _clip_runs(pts, anchor, margin=40.0):
    """Split a polyline into the runs that lie inside the block bbox + margin.
    Unclipped linework (rail lines, boundary walls) runs for hundreds of metres
    past the block and reads as stray scratches on the top view."""
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0
    s_, w_, n_, e_ = anchor["bbox"]
    x_lo, x_hi = (w_ - anchor["lon0"]) * kx - margin, (e_ - anchor["lon0"]) * kx + margin
    y_lo, y_hi = (s_ - anchor["lat0"]) * ky - margin, (n_ - anchor["lat0"]) * ky + margin
    runs, cur = [], []
    for q in pts:
        if x_lo <= q[0] <= x_hi and y_lo <= q[1] <= y_hi:
            cur.append(q)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) >= 2]


def transport_to_local(elements, anchor, water=None):
    """-> (rails, bridges). Rails skip tunnels, negative layers AND cuttings
    (the District line's open cut ran at grade straight through the SK block).
    Bridges keep ONLY foot bridges that actually CROSS WATER: road bridges are
    already drawn by the road layer (the raised duplicate deck was the "messy
    roads" report, 08-11), mall-connector walkways read as clutter, and closed
    man_made=bridge rings drew stray outlines outside the block."""
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0
    def _clip(pts):
        return _clip_runs(pts, anchor)

    rails, bridges = [], []
    for el in elements:
        tags = el.get("tags") or {}
        pts = [[round((g["lon"] - anchor["lon0"]) * kx, 2),
                round((g["lat"] - anchor["lat0"]) * ky, 2)]
               for g in el.get("geometry") or []]
        if len(pts) < 2:
            continue
        if tags.get("railway"):
            lay = int(tags.get("layer") or 0)
            # negative layer = below grade (the Jubilee/Elizabeth lines under
            # the dock carry layer -2..-4 with no tunnel tag) -- invisible
            if tags.get("tunnel") == "yes" or lay < 0 \
                    or tags.get("cutting") == "yes" \
                    or tags.get("location") == "underground":
                continue
            # OSM values the bridge KEY freely: DLR is bridge=viaduct, layer=2
            elev = bool(tags.get("bridge")) or lay > 0
            # at-grade HEAVY rail/subway inside a city block is an untagged
            # open cut (SK's District line carries no layer/cutting/tunnel at
            # all) -- draw grade track only for light_rail/tram
            if not elev and tags["railway"] not in ("light_rail", "tram"):
                continue
            for ci, run in enumerate(_clip(pts)):
                rails.append({"id": el["id"] * 10 + ci, "pts": run,
                              "bridge": elev, "layer": lay})
        elif tags.get("bridge") == "yes":
            cls = tags.get("highway", "footway")
            foot = cls in ("footway", "path", "pedestrian", "cycleway", "steps")
            closed = len(pts) > 3 and math.dist(pts[0], pts[-1]) < 1.0
            if not foot or closed:
                continue                # road decks: the road layer draws them
            for ci, run in enumerate(_clip(pts)):
                over_water = water and any(
                    _point_in_poly((q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2, w)
                    for q1, q2 in zip(run, run[1:]) for w in water)
                if not over_water:
                    continue            # inner walkway connectors: clutter
                bridges.append({"id": el["id"] * 10 + ci, "pts": run,
                                "width": ROAD_WIDTH.get(cls, 3.0), "foot": True})
    return rails, bridges


def fetch_furniture(bbox, cache, force=False):
    """Street furniture (signals/crossings/bus stops/phone+post boxes/bollards)
    and linear barriers (fences/railings/walls) in bbox, cached."""
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    s, w, n, e = bbox
    bb = f"({s},{w},{n},{e})"
    els = _overpass(
        '[out:json][timeout:60];('
        f'node["highway"~"^(traffic_signals|street_lamp|bus_stop|crossing)$"]{bb};'
        f'node["amenity"~"^(post_box|telephone)$"]{bb};'
        f'node["barrier"="bollard"]{bb};'
        f'way["barrier"~"^(fence|railing|wall|bollard)$"]{bb};'
        ');out geom;')
    with open(cache, "w") as f:
        json.dump(els, f)
    return els


DRIVABLE = {"trunk", "trunk_link", "primary", "primary_link", "secondary",
            "tertiary", "unclassified", "residential", "living_street", "service"}


def furniture_to_local(elements, anchor, roads):
    """Overpass furniture -> categorised scene-metre features. Crossings get the
    bearing + width of the NEAREST drivable road so the zebra stripes lie across
    the actual carriageway."""
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0

    def loc(el):
        return ((el["lon"] - anchor["lon0"]) * kx,
                (el["lat"] - anchor["lat0"]) * ky)

    segs = []
    for r in roads:
        if r["class"] not in DRIVABLE:
            continue
        for i in range(len(r["pts"]) - 1):
            segs.append((r["pts"][i], r["pts"][i + 1], r["width"]))

    def near_road(x, y):
        best = None
        for (x1, y1), (x2, y2), w in segs:
            dx, dy = x2 - x1, y2 - y1
            ll = dx * dx + dy * dy
            if ll < 1e-9:
                continue
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / ll))
            px, py = x1 + t * dx, y1 + t * dy
            d2 = (x - px) ** 2 + (y - py) ** 2
            if best is None or d2 < best[0]:
                best = (d2, math.atan2(dy, dx), w, px, py)
        return best

    out = {"signals": [], "crossings": [], "bus_stops": [], "phones": [],
           "posts": [], "bollards": [], "fences": [], "walls": []}
    for el in elements:
        tags = el.get("tags") or {}
        if el["type"] == "node":
            x, y = loc(el)
            hw = tags.get("highway"); am = tags.get("amenity")
            if hw == "traffic_signals":
                # OSM puts the signal node ON the carriageway (stop-line
                # position); the physical pole stands at the kerb. Push it out
                # perpendicular to its road -- and because junction corners sit
                # inside the OTHER road's ribbon too, keep stepping candidates
                # (both sides, growing offsets) until the pole is clear of
                # EVERY drivable ribbon.
                def _in_any_road(qx, qy):
                    for (x1, y1), (x2, y2), w_ in segs:
                        dx_, dy_ = x2 - x1, y2 - y1
                        ll = dx_ * dx_ + dy_ * dy_
                        if ll < 1e-9:
                            continue
                        tt = max(0.0, min(1.0, ((qx - x1) * dx_ + (qy - y1) * dy_) / ll))
                        if ((qx - (x1 + tt * dx_)) ** 2
                                + (qy - (y1 + tt * dy_)) ** 2) < (w_ / 2 + 0.35) ** 2:
                            return True
                    return False

                nr = near_road(x, y)
                if nr:
                    _d2, ang, w, px, py = nr
                    nx_, ny_ = -math.sin(ang), math.cos(ang)
                    side0 = 1.0 if (x - px) * nx_ + (y - py) * ny_ >= 0 else -1.0
                    for off, side in [(w / 2 + o, s)
                                      for o in (0.7, 1.6, 2.6, 3.8)
                                      for s in (side0, -side0)]:
                        qx, qy = px + nx_ * side * off, py + ny_ * side * off
                        if not _in_any_road(qx, qy):
                            x, y = qx, qy
                            break
                    else:
                        x, y = px + nx_ * side0 * (w / 2 + 0.7), py + ny_ * side0 * (w / 2 + 0.7)
                out["signals"].append({"x": round(x, 2), "y": round(y, 2)})
            elif hw == "crossing":
                nr = near_road(x, y)
                if nr and nr[0] < 15.0 ** 2:
                    out["crossings"].append(
                        {"x": round(nr[3], 2), "y": round(nr[4], 2),
                         "ang": round(nr[1], 3), "w": nr[2]})
            elif hw == "bus_stop":
                # orient the shelter along the road it serves
                nr = near_road(x, y)
                out["bus_stops"].append({"x": round(x, 2), "y": round(y, 2),
                                         "ang": round(nr[1], 3) if nr else 0.0})
            elif am == "telephone":
                out["phones"].append({"x": round(x, 2), "y": round(y, 2)})
            elif am == "post_box":
                out["posts"].append({"x": round(x, 2), "y": round(y, 2)})
            elif tags.get("barrier") == "bollard":
                out["bollards"].append({"x": round(x, 2), "y": round(y, 2)})
            continue
        pts = [[round((g["lon"] - anchor["lon0"]) * kx, 2),
                round((g["lat"] - anchor["lat0"]) * ky, 2)]
               for g in el.get("geometry") or []]
        if len(pts) < 2:
            continue
        bar = tags.get("barrier")
        if bar in ("fence", "railing"):
            for run in _clip_runs(pts, anchor, margin=10.0):
                out["fences"].append({"pts": run})
            continue
        elif bar == "wall":
            for run in _clip_runs(pts, anchor, margin=10.0):
                out["walls"].append({"pts": run})
            continue
        elif bar == "bollard":                     # a bollard LINE -> points
            for i in range(len(pts) - 1):
                (x1, y1), (x2, y2) = pts[i], pts[i + 1]
                n_ = max(1, int(math.hypot(x2 - x1, y2 - y1) / 1.5))
                for k in range(n_ + 1):
                    t = k / n_
                    out["bollards"].append({"x": round(x1 + (x2 - x1) * t, 2),
                                            "y": round(y1 + (y2 - y1) * t, 2)})
    return out


def _merc_y(lat):
    """Normalised Web-Mercator y in [0,1] (0 = north pole)."""
    r = math.radians(lat)
    return (1.0 - math.log(math.tan(r) + 1.0 / math.cos(r)) / math.pi) / 2.0


def _inv_merc_y(y):
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y))))


def _point_in_poly(x, y, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def keep_trees_off_roads(trees, roads, buildings, margin=0.6):
    """Supervisor feedback 07-28: trees stood in the middle of the street.
    DeepForest centres a kerbside tree's OVERHANGING crown, which often lands on
    the carriageway (and junction shadows detect as trees outright). A trunk
    inside a drivable ribbon is snapped out to the kerb -- nearest clear spot,
    both sides, growing offsets, never into a building footprint (the traffic-
    signal recipe) -- or dropped when nothing within ~4 m is clear (junction
    interior = false positive). Runs on the cached detections at load time, so
    fixing placement never re-runs the detector."""
    segs = []
    for r in roads:
        if r["class"] not in DRIVABLE:
            continue
        for i in range(len(r["pts"]) - 1):
            segs.append((r["pts"][i], r["pts"][i + 1], r["width"]))

    def nearest(x, y):
        best = None
        for (x1, y1), (x2, y2), w in segs:
            dx, dy = x2 - x1, y2 - y1
            ll = dx * dx + dy * dy
            if ll < 1e-9:
                continue
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / ll))
            px, py = x1 + t * dx, y1 + t * dy
            d2 = (x - px) ** 2 + (y - py) ** 2
            if best is None or d2 < best[0]:
                best = (d2, math.atan2(dy, dx), w, px, py)
        return best

    def in_road(x, y):
        for (x1, y1), (x2, y2), w in segs:
            dx, dy = x2 - x1, y2 - y1
            ll = dx * dx + dy * dy
            if ll < 1e-9:
                continue
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / ll))
            if ((x - (x1 + t * dx)) ** 2
                    + (y - (y1 + t * dy)) ** 2) < (w / 2 + margin) ** 2:
                return True
        return False

    kept, snapped, dropped = [], 0, 0
    for t in trees:
        if not in_road(t["x"], t["y"]):
            kept.append(t)
            continue
        _d2, ang, w, px, py = nearest(t["x"], t["y"])
        nx, ny = -math.sin(ang), math.cos(ang)
        side0 = 1.0 if (t["x"] - px) * nx + (t["y"] - py) * ny >= 0 else -1.0
        for off, side in [(w / 2 + margin + o, s)
                          for o in (0.4, 1.2, 2.2, 3.4)
                          for s in (side0, -side0)]:
            qx, qy = px + nx * side * off, py + ny * side * off
            if in_road(qx, qy):
                continue
            if any(_point_in_poly(qx, qy, b["pts"]) for b in buildings):
                continue
            kept.append(dict(t, x=round(qx, 2), y=round(qy, 2)))
            snapped += 1
            break
        else:
            dropped += 1
    if snapped or dropped:
        print(f"[trees] road clearance: {snapped} snapped to kerb, "
              f"{dropped} dropped (junction interior)")
    return kept


def detect_trees(sat_png, bbox, buildings, anchor, cache, force=False,
                 min_score=0.3, patch_size=400):
    """DeepForest tree crowns on the bbox-cropped satellite -> [{x, y, r, score}]
    in scene metres, cached to JSON. Detections centred inside a building footprint
    are dropped (roof clutter reads as canopy to the detector). Crown radius r is
    half the mean detected box side, converted to metres."""
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    from PIL import Image
    from deepforest import main as df_main                    # lazy: heavy import
    s, w, n, e = bbox
    W, H = Image.open(sat_png).size
    m = df_main.deepforest()
    m.load_model("weecology/deepforest-tree")
    boxes = m.predict_tile(sat_png, patch_size=patch_size, patch_overlap=0.15)
    if boxes is None:                 # DeepForest returns None, not an empty
        return []                     # frame, when a tile has no detections
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0
    my0, my1 = _merc_y(n), _merc_y(s)                # crop is linear in mercator y
    mppx = (e - w) * kx / W                          # metres per pixel (x)
    trees, dropped = [], 0
    for _, b in boxes.iterrows():
        if b["score"] < min_score:
            continue
        px = (b["xmin"] + b["xmax"]) / 2.0
        py = (b["ymin"] + b["ymax"]) / 2.0
        lon = w + (px / W) * (e - w)
        lat = _inv_merc_y(my0 + (py / H) * (my1 - my0))
        x = (lon - anchor["lon0"]) * kx
        y = (lat - anchor["lat0"]) * ky
        if any(_point_in_poly(x, y, bl["pts"]) for bl in buildings):
            dropped += 1
            continue
        r = ((b["xmax"] - b["xmin"]) + (b["ymax"] - b["ymin"])) / 4.0 * mppx
        trees.append({"x": round(x, 2), "y": round(y, 2),
                      "r": round(max(1.5, min(r, 9.0)), 2),
                      "score": round(float(b["score"]), 3)})
    print(f"[trees] {len(trees)} kept, {dropped} dropped inside footprints, "
          f"{int((boxes['score'] < min_score).sum())} below score {min_score}")
    with open(cache, "w") as f:
        json.dump(trees, f)
    return trees


def load_or_build(out, force=False):
    """The one entry point city_generate uses: (trees, roads, green, hedges) for
    the block in scene metres, built from caches under `out` (satellite crop
    fetched via city.compare_top; buildings.json written by city_pilot). trees include
    the deterministic park in-fill (scatter_park_trees)."""
    d = json.load(open(os.path.join(out, "buildings.json")))
    anchor, buildings = d["anchor"], d["buildings"]
    bbox = anchor["bbox"]
    roads = roads_to_local(
        fetch_roads(bbox, os.path.join(out, "roads_raw.json"), force), anchor)
    green, hedges = green_to_local(
        fetch_green(bbox, os.path.join(out, "green_raw.json"), force), anchor)
    sat = os.path.join(out, "block_sat_bbox.png")
    if not os.path.exists(sat):
        # the bbox-cropped satellite tile is shared with the alignment figure;
        # fetch it here so the tree layer never depends on running that first
        try:
            from img2city.city.compare_top import fetch_bbox_satellite
            fetch_bbox_satellite(bbox, sat)
        except Exception as e:
            print(f"[trees] could not fetch {sat} ({str(e)[:80]})")
    trees = []
    if os.path.exists(sat):
        trees = detect_trees(sat, bbox, buildings, anchor,
                             os.path.join(out, "trees.json"), force)
    else:
        print(f"[trees] {sat} missing -- skipping trees")
    extra = scatter_park_trees(green, trees, buildings)
    if extra:
        print(f"[green] +{len(extra)} in-fill park trees")
    trees = keep_trees_off_roads(trees + extra, roads, buildings)
    # DETECTED trees can land on water too (DeepForest reads boat wakes and
    # dock-edge shadows as crowns) -- same containment rule as footprints
    water = [g["pts"] for g in green if g.get("kind") == "water"]
    if water:
        n0 = len(trees)
        trees = [t for t in trees
                 if not any(_point_in_poly(t["x"], t["y"], w) for w in water)]
        if n0 - len(trees):
            print(f"[trees] {n0 - len(trees)} dropped from water")
    furniture = furniture_to_local(
        fetch_furniture(bbox, os.path.join(out, "furniture_raw.json"), force),
        anchor, roads)
    # transport rides in the furniture dict (additive keys -- no caller change)
    try:
        rails, bridges = transport_to_local(
            fetch_transport(bbox, os.path.join(out, "transport_raw.json"), force),
            anchor, water=[g["pts"] for g in green if g.get("kind") == "water"])
        furniture["rails"] = rails
        furniture["bridges"] = bridges
        if rails or bridges:
            print(f"[transport] {len(rails)} rail ways "
                  f"({sum(1 for r in rails if r['bridge'])} elevated), "
                  f"{len(bridges)} bridge decks")
    except Exception as e:
        print(f"[transport] skipped: {e}")
    return trees, roads, green, hedges, furniture


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    trees, roads, green, hedges, furn = load_or_build(a.out, a.force)
    km = sum(math.dist(r["pts"][i], r["pts"][i + 1])
             for r in roads for i in range(len(r["pts"]) - 1)) / 1000.0
    gm2 = sum(_poly_area(g["pts"]) for g in green)
    print(f"[scene] {len(trees)} trees, {len(roads)} road ways ({km:.1f} km), "
          f"{len(green)} green areas ({gm2/1e4:.1f} ha), {len(hedges)} hedges, "
          + ", ".join(f"{len(v)} {k}" for k, v in furn.items() if v))


if __name__ == "__main__":
    main()
