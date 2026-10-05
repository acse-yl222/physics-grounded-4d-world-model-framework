"""img2city/scene/vehicles.py -- reconstruct the VEHICLES visible in the imagery
(supervisor request 2026-07-28: "reconstruct the cars visible in the imagery",
suggested detectors YOLO / Grounding DINO, noting Google imagery can be a few
years old -- positions are a plausible historical snapshot, not live traffic).

Deterministic pipeline, cached like every scene layer:

  1. tiles    zoom-19 scale-2 Static Maps satellite tiles over the block bbox
              (~9 cm/px; the block crop is 37 cm/px -- a car is 12 px there,
              far too small to detect). Cached under vehicle_tiles/.
  2. detect   Grounding DINO (IDEA-Research/grounding-dino-tiny, zero-shot,
              prompt "car") per tile -> boxes -> cross-tile NMS in scene
              metres. Needs torch/transformers (run with IMG2CITY_TORCH_PYTHON,
              the same interpreter DeepForest uses).
  3. place    keep detections ON the road network (within a drivable ribbon
              + verge margin, never inside a building footprint); heading
              from the NEAREST DIRECTED ARC of road_graph.py -- UK keep-left
              picks the arc whose travel direction puts the car on its left
              side, so parked/moving cars face the way traffic flows.
  4. colour   body colour sampled from the tile pixels inside the box
              (median), same photo-derived-appearance rule as facades.

Output vehicles.json: [{x, y, ang, len, wid, color, score, arc}] -- an
editable semantic layer (each car = typed params, regenerable geometry);
city_generate builds low-poly parametric cars from it.

  python -m img2city.scene.vehicles --out data/city_sk            # cached
  python -m img2city.scene.vehicles --out data/city_sk --force
"""
from __future__ import annotations
import argparse
import json
import math
import os
import urllib.parse
import urllib.request

MERC = 156543.03392          # Web-Mercator m/px at zoom 0, equator
ZOOM = 19
SCALE = 2
TILE_PX = 640                # request size (scale doubles delivered pixels)
# detected boxes are AXIS-ALIGNED, so a diagonal car's box inflates to ~
# (l+w)/sqrt(2) per side -- classify on box AREA + max side, not raw l/w
# (the first cut used strict l/w bounds and rejected every diagonal car)
CAR_AREA, CAR_MAX = (6.0, 26.0), 8.0       # real car 8 m2 -> AABB 8..~20
BUS_AREA, BUS_MAX = (24.0, 110.0), 16.0    # double-decker 27 m2 -> AABB up to ~90


def _key():
    k = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not k:
        raise SystemExit("Set GOOGLE_MAPS_API_KEY first (maps_fetch.py rule).")
    return k


def fetch_tiles(bbox, out_dir, force=False):
    """Cover bbox with zoom-19 scale-2 satellite tiles; returns
    [{png, lat, lng}] (tile centres). Cached; ~20 tiles for the block."""
    os.makedirs(out_dir, exist_ok=True)
    s, w, n, e = bbox
    lat_mid = (s + n) / 2
    res = MERC * math.cos(math.radians(lat_mid)) / (2 ** ZOOM)   # m/px @ size
    cover = TILE_PX * res * 0.92                                 # 8% overlap
    kx = 111320.0 * math.cos(math.radians(lat_mid))
    nx = max(1, math.ceil((e - w) * kx / cover))
    ny = max(1, math.ceil((n - s) * 110540.0 / cover))
    tiles = []
    for iy in range(ny):
        for ix in range(nx):
            lng = w + (ix + 0.5) * (e - w) / nx
            lat = s + (iy + 0.5) * (n - s) / ny
            png = os.path.join(out_dir, f"tile_{ix}_{iy}.png")
            if not os.path.exists(png) or force:
                q = urllib.parse.urlencode(
                    {"center": f"{lat},{lng}", "zoom": ZOOM,
                     "size": f"{TILE_PX}x{TILE_PX}", "scale": SCALE,
                     "maptype": "satellite", "key": _key()})
                with urllib.request.urlopen(
                        "https://maps.googleapis.com/maps/api/staticmap?" + q,
                        timeout=60) as r, open(png, "wb") as f:
                    f.write(r.read())
            tiles.append({"png": png, "lat": lat, "lng": lng})
    print(f"[vehicles] {len(tiles)} tiles ({nx}x{ny}, {res*100:.0f} cm/px)")
    return tiles


def detect_cars(tiles, anchor, score_min=0.22):
    """Grounding DINO 'car. bus.' boxes on every tile -> scene-metre detections
    [{x, y, kind, len, wid, score, color}] with cross-tile NMS. London's red
    double-deckers are as visible as the cars, so bus is its own class."""
    import numpy as np
    import torch
    from PIL import Image
    from transformers import (AutoModelForZeroShotObjectDetection,
                              AutoProcessor)
    mid = "IDEA-Research/grounding-dino-tiny"
    proc = AutoProcessor.from_pretrained(mid)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(mid)
    model.eval()
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    dets = []
    for t in tiles:
        img = Image.open(t["png"]).convert("RGB")
        Wpx = img.size[0]
        res = MERC * math.cos(math.radians(t["lat"])) / (2 ** ZOOM) / SCALE
        with torch.no_grad():
            inp = proc(images=img, text="car. bus.", return_tensors="pt")
            out = model(**inp)
            r = proc.post_process_grounded_object_detection(
                out, inp.input_ids, threshold=score_min,
                text_threshold=score_min,
                target_sizes=[img.size[::-1]])[0]
        arr = np.asarray(img)
        for box, score, label in zip(r["boxes"].tolist(),
                                     r["scores"].tolist(), r["labels"]):
            x0, y0, x1, y1 = box
            l_m = max(x1 - x0, y1 - y0) * res
            w_m = min(x1 - x0, y1 - y0) * res
            area = l_m * w_m
            if "bus" in label and BUS_AREA[0] <= area <= BUS_AREA[1] \
                    and 8.0 <= l_m <= BUS_MAX:
                kind = "bus"
            elif CAR_AREA[0] <= area <= CAR_AREA[1] and l_m <= CAR_MAX:
                kind = "car"
            else:
                continue
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            # tile-local px -> lat/lon around the tile centre
            lng = t["lng"] + (cx - Wpx / 2) * res / (111320.0 * math.cos(math.radians(t["lat"])))
            lat = t["lat"] - (cy - Wpx / 2) * res / 110540.0
            px = arr[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)]
            color = [round(float(v) / 255.0, 3)
                     for v in np.median(px.reshape(-1, 3), axis=0)] if px.size else [0.4, 0.4, 0.42]
            dets.append({"x": round((lng - anchor["lon0"]) * kx, 2),
                         "y": round((lat - anchor["lat0"]) * 110540.0, 2),
                         "kind": kind,
                         "len": round(l_m, 2), "wid": round(w_m, 2),
                         "score": round(score, 3), "color": color})
    dets.sort(key=lambda d: -d["score"])
    kept = []
    for d in dets:                                     # cross-tile NMS
        r2 = (4.5 if d["kind"] == "bus" else 2.2) ** 2
        if all((d["x"] - k["x"]) ** 2 + (d["y"] - k["y"]) ** 2 > r2
               for k in kept):
            kept.append(d)
    print(f"[vehicles] {len(dets)} raw detections -> {len(kept)} after NMS")
    return kept


def place_on_roads(dets, graph, buildings, verge=2.5):
    """Keep detections on the drivable network; heading = nearest directed arc
    whose travel direction puts the car on its LEFT side (UK). Cars inside a
    building footprint or off the network (private forecourts, roofs
    misdetected) are dropped."""
    from img2city.scene.assets import _point_in_poly
    segs = []
    for arc in graph["arcs"]:
        for i in range(len(arc["pts"]) - 1):
            segs.append((arc["pts"][i], arc["pts"][i + 1], arc))
    placed = []
    for d in dets:
        if any(_point_in_poly(d["x"], d["y"], b["pts"]) for b in buildings):
            continue
        best = None
        for (x1, y1), (x2, y2), arc in segs:
            dx, dy = x2 - x1, y2 - y1
            ll = dx * dx + dy * dy
            if ll < 1e-9:
                continue
            t = max(0.0, min(1.0, ((d["x"] - x1) * dx + (d["y"] - y1) * dy) / ll))
            px, py = x1 + t * dx, y1 + t * dy
            d2 = (d["x"] - px) ** 2 + (d["y"] - py) ** 2
            if d2 > (arc["width"] / 2 + verge) ** 2:
                continue
            ang = math.atan2(dy, dx)
            # signed side: +1 = car left of travel direction (UK correct)
            side = math.copysign(
                1.0, -math.sin(ang) * (d["x"] - px) + math.cos(ang) * (d["y"] - py))
            rank = (d2, -side)          # nearest arc first, prefer left side
            if best is None or rank < best[0]:
                best = (rank, ang, arc["id"])
        if best is None:
            continue
        placed.append(dict(d, ang=round(best[1], 3), arc=best[2]))
    print(f"[vehicles] {len(placed)} placed on the network "
          f"({len(dets) - len(placed)} off-road/in-footprint dropped)")
    return placed


def _lateral_dist(v, arc):
    """Min perpendicular distance from a vehicle to its arc's polyline."""
    best = float("inf")
    pts = arc["pts"]
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        dx, dy = x2 - x1, y2 - y1
        ll = dx * dx + dy * dy
        if ll < 1e-9:
            continue
        t = max(0.0, min(1.0, ((v["x"] - x1) * dx + (v["y"] - y1) * dy) / ll))
        best = min(best, math.hypot(v["x"] - (x1 + t * dx),
                                    v["y"] - (y1 + t * dy)))
    return best


def drop_vehicles_in_water(cars, out, graph=None):
    """Boats and sun-glint on canals detect as 'car' and, being too far off
    the quay street's centreline to drive, get PARKED at their detected spot
    -- in the canal (08-14: cars were landing in the water; ams 9,
    cw 1). Drop any vehicle inside a water polygon unless it sits within its
    arc's carriageway half-width (a real car crossing a bridge). Same
    load-time-on-cached-detections pattern as keep_trees_off_roads."""
    from img2city.scene.assets import fetch_green, green_to_local, _point_in_poly
    d = json.load(open(os.path.join(out, "buildings.json")))
    els = fetch_green(d["anchor"]["bbox"], os.path.join(out, "green_raw.json"))
    areas, _hedges = green_to_local(els, d["anchor"])
    waters = [g["pts"] for g in areas
              if g.get("kind") == "water" and len(g["pts"]) >= 3]
    if not waters:
        return cars
    from img2city.scene import road_graph
    arcs = {a["id"]: a for a in (graph or road_graph.load_or_build(out))["arcs"]}
    kept = []
    for v in cars:
        if any(_point_in_poly(v["x"], v["y"], w) for w in waters):
            a = arcs.get(v.get("arc"))
            if a is None or _lateral_dist(v, a) > a["width"] / 2:
                continue
        kept.append(v)
    if len(kept) != len(cars):
        print(f"[vehicles] {len(cars) - len(kept)} in-water detections "
              "dropped (boats/glint; bridge traffic kept)")
    return kept


# ---- collision clean-up (08-19: "some cars are crashed into shops, some
# into each other -- clean this up and write it down so it never recurs").
# Root cause: place_on_roads tested only the detection CENTRE against the OSM
# polygon; 45/56 SK hosts are built as an OBB RECTANGLE that can reach past the
# OSM edge, shop units add ~0.3 m, and the rendered body is a fixed 4.4 x 1.8 m
# box (10.9 x 2.52 bus) around that centre -- so a kerbside car hugging a
# frontage renders into the shopfront. Cross-tile NMS was done on the raw
# detections, not on the rendered bodies, so two detections of one car (or
# queued cars in a bumper-to-bumper row) render as one interpenetrating clump.
# Rule: the RENDERED BODY, with clearance, must not touch the BUILT outline
# (shop_assets.built_outlines: OBB or polygon, whichever is actually raised) nor
# another body. Body inside a building -> nudge laterally towards the arc
# centreline (<= NUDGE m, the photo position is kept within detection error);
# still inside -> drop. Body-body overlap -> keep the higher score. Kerbside
# bodies intruding into the running lane (keep-side lane centre w/4, the lane
# traffic_sim drives in) -> nudge out to the kerb so animated cars do not clip
# parked ones. Pure python (runs in the base env at assembly time too).
BODY = {"car": (4.4, 1.8), "bus": (10.9, 2.52)}
CLEAR_BLDG = 0.6     # m body-to-wall clearance (shop units + awnings)
CLEAR_VEH = 0.3      # m body-to-body clearance
NUDGE = 2.0          # m max lateral correction before dropping
LANE_CLEAR = 0.4     # m between a parked body and a moving body's lane edge


def _rect(x, y, ang, L, W, pad=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    hl, hw = L / 2 + pad, W / 2 + pad
    return [(x + ca * sx * hl - sa * sy * hw, y + sa * sx * hl + ca * sy * hw)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _seg_x(p1, p2, p3, p4):
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(p3, p4, p1), o(p3, p4, p2), o(p1, p2, p3), o(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def _poly_hit(a, b):
    """Convex-or-not polygon overlap: shared point, or an edge crossing."""
    from img2city.scene.assets import _point_in_poly
    if any(_point_in_poly(x, y, b) for x, y in a) or \
       any(_point_in_poly(x, y, a) for x, y in b):
        return True
    for i in range(len(a)):
        for j in range(len(b)):
            if _seg_x(a[i], a[(i + 1) % len(a)], b[j], b[(j + 1) % len(b)]):
                return True
    return False


def _bbox(p):
    xs = [q[0] for q in p]; ys = [q[1] for q in p]
    return min(xs), min(ys), max(xs), max(ys)


def _bb_touch(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _arc_frame(v, arc):
    """(lateral offset to the LEFT of travel, unit left-normal) at the nearest
    point of the vehicle's arc."""
    best = None
    pts = arc["pts"]
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        dx, dy = x2 - x1, y2 - y1
        ll = dx * dx + dy * dy
        if ll < 1e-9:
            continue
        t = max(0.0, min(1.0, ((v["x"] - x1) * dx + (v["y"] - y1) * dy) / ll))
        px, py = x1 + t * dx, y1 + t * dy
        d = math.hypot(v["x"] - px, v["y"] - py)
        if best is None or d < best[0]:
            ang = math.atan2(dy, dx)
            nx, ny = -math.sin(ang), math.cos(ang)
            lat = nx * (v["x"] - px) + ny * (v["y"] - py)
            best = (d, lat, (nx, ny))
    return best[1], best[2]


def clean_vehicles(cars, out, graph=None, buildings=None, verbose=True):
    from img2city.scene.shops import built_outlines
    from img2city.scene import road_graph
    d = json.load(open(os.path.join(out, "buildings.json")))
    bl = buildings or d["buildings"]
    outl = built_outlines(out, bl)
    polys = [p for p, _m in outl.values()] + \
            [[tuple(q) for q in b["pts"]] for b in bl if b["id"] not in outl]
    pbb = [_bbox(p) for p in polys]
    arcs = {a["id"]: a for a in (graph or road_graph.load_or_build(out))["arcs"]}
    sgn = 1.0 if road_graph.drive_side(out) == "left" else -1.0

    def in_building(v):
        r = _rect(v["x"], v["y"], v["ang"], *BODY.get(v["kind"], BODY["car"]),
                  pad=CLEAR_BLDG)
        rb = _bbox(r)
        return any(_bb_touch(rb, pb) and _poly_hit(r, p)
                   for p, pb in zip(polys, pbb))

    # stale arc ids (vehicles cached against an older graph -- e.g. before the
    # motor_access filter) are re-snapped to the current network or dropped
    stale = [v for v in cars if v.get("arc") not in arcs]
    if stale:
        g = graph or road_graph.load_or_build(out)
        placed = place_on_roads(stale, g, bl)
        byxy = {(round(p["x"], 2), round(p["y"], 2)): p for p in placed}
        cars = [byxy.get((round(v["x"], 2), round(v["y"], 2)), None)
                if v.get("arc") not in arcs else v for v in cars]
        n_stale_drop = sum(1 for v in cars if v is None)
        cars = [v for v in cars if v is not None]
        print(f"[vehicles] {len(stale)} vehicles on arcs no longer in the graph: "
              f"{len(stale) - n_stale_drop} re-snapped, {n_stale_drop} dropped")
    kept, n_nudge, n_drop_b, n_lane = [], 0, 0, 0
    for v in cars:
        v = dict(v)
        a = arcs.get(v.get("arc"))
        if a is not None:
            lat, (nx, ny) = _arc_frame(v, a)
            # (1) kerbside body must clear the running lane traffic_sim uses
            W = BODY.get(v["kind"], BODY["car"])[1]
            lane_c = (a["width"] / 4.0 if not a["oneway"]
                      else a["width"] / (2 * max(1, a["lanes"])) * 0.5) * sgn
            parked = abs(lat) > a["width"] / 4.0 + 1.0       # traffic_sim rule
            need = abs(lane_c) + BODY["car"][1] / 2 + W / 2 + LANE_CLEAR
            # ...but never past the kerb: a parked car belongs on the
            # carriageway. Where the street is too narrow to hold a parked row
            # AND a running lane, traffic_sim shifts/blocks the lane instead.
            kerb = a["width"] / 2 + 0.3 - W / 2
            if parked and lat * sgn > 0 and abs(lat) + 0.02 < min(need, kerb):
                sh = min(need, kerb) - abs(lat)
                v["x"] += nx * sh * sgn; v["y"] += ny * sh * sgn
                lat = min(need, kerb) * sgn
                n_lane += 1
            # (2) body must clear the built outline: nudge towards centreline
            if in_building(v):
                ok = False
                for k in range(1, int(NUDGE / 0.25) + 1):
                    sh = 0.25 * k
                    vx = dict(v, x=v["x"] - nx * sh * math.copysign(1, lat),
                              y=v["y"] - ny * sh * math.copysign(1, lat))
                    if not in_building(vx):
                        v, ok = vx, True
                        n_nudge += 1
                        break
                if not ok:
                    n_drop_b += 1
                    continue
        elif in_building(v):
            n_drop_b += 1
            continue
        v["x"], v["y"] = round(v["x"], 2), round(v["y"], 2)
        kept.append(v)
    # (3) body-body overlap: keep the higher score
    rects = [_rect(v["x"], v["y"], v["ang"], *BODY.get(v["kind"], BODY["car"]),
                   pad=CLEAR_VEH / 2) for v in kept]
    bbs = [_bbox(r) for r in rects]
    order = sorted(range(len(kept)), key=lambda i: -kept[i].get("score", 0))
    alive, n_drop_v = [], 0
    for i in order:
        if any(_bb_touch(bbs[i], bbs[j]) and _poly_hit(rects[i], rects[j])
               for j in alive):
            n_drop_v += 1
            continue
        alive.append(i)
    final = [kept[i] for i in sorted(alive)]
    if verbose:
        print(f"[vehicles] clean: {len(cars)} -> {len(final)}; "
              f"{n_nudge} nudged off buildings, {n_drop_b} dropped in-building, "
              f"{n_lane} kerbside pushed clear of the running lane, "
              f"{n_drop_v} overlapping bodies dropped")
    return final


def load_or_build(out, force=False):
    cache = os.path.join(out, "vehicles.json")
    if os.path.exists(cache) and not force:
        cars = json.load(open(cache))
        kept = clean_vehicles(drop_vehicles_in_water(cars, out), out)
        if kept != cars:                  # persist: sim + assembly read the
            with open(cache, "w") as f:   # cache file directly
                json.dump(kept, f)
        return kept
    from img2city.scene import road_graph
    d = json.load(open(os.path.join(out, "buildings.json")))
    tiles = fetch_tiles(d["anchor"]["bbox"],
                        os.path.join(out, "vehicle_tiles"), force)
    dets = detect_cars(tiles, d["anchor"])
    cars = place_on_roads(dets, road_graph.load_or_build(out),
                          d["buildings"])
    cars = clean_vehicles(drop_vehicles_in_water(cars, out), out)
    with open(cache, "w") as f:
        json.dump(cars, f)
    return cars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    cars = load_or_build(a.out, a.force)
    print(f"[vehicles] {len(cars)} cars; "
          f"mean len {sum(c['len'] for c in cars)/max(1,len(cars)):.1f} m")


if __name__ == "__main__":
    main()
