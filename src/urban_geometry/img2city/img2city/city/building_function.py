"""img2city/city/building_function.py -- resolve a real-world FUNCTION for each footprint
(direction decision 2026-07-27: the agent should determine what a building IS, not
blindly extrude the OSM polygon).

Three cross-checked sources, in order of trust:
  1. Places API (New) POI landing inside/near the footprint (subway_station,
     museum, place_of_worship, school, ...);
  2. OSM building tag (btype: train_station, church, ...);
  3. (future) the building's own street view, agent-classified.

Writes `func` + `func_src` + `func_conf` into each building in buildings.json
(a .bak is kept) and prints a summary. Special forms drive dedicated builders
in assembly (train_station -> glazed shed, building=roof -> canopy).

Usage:  python -m img2city.city.building_function --out data/city_sk
"""
import argparse
import json
import math
import os

from img2city.imagery.maps_fetch import places_nearby

# Places primaryType / type -> our coarse FUNCTION label (priority order matters:
# a footprint tagged by several POIs takes the highest-priority one)
# bus_station is deliberately absent: a bus stop is street furniture, not a
# building function -- including it tagged whole streets as "station".
TYPE_FUNC = [
    (("subway_station", "light_rail_station", "train_station",
      "transit_station"), "station"),
    (("place_of_worship", "church", "hindu_temple", "mosque", "synagogue"),
     "worship"),
    (("museum",), "museum"),
    (("university", "school", "primary_school", "secondary_school"), "education"),
    (("hospital",), "hospital"),
    (("stadium", "arena"), "stadium"),
    (("library",), "library"),
    (("city_hall", "local_government_office", "courthouse"), "civic"),
    (("hotel",), "hotel"),
    (("movie_theater", "theater"), "theatre"),
    (("gas_station",), "fuel"),
]
FUNC_PRIORITY = [f for _, f in TYPE_FUNC]

# OSM building= tag -> function (fallback when no POI matched)
OSM_FUNC = {"train_station": "station", "church": "worship",
            "cathedral": "worship", "chapel": "worship", "mosque": "worship",
            "temple": "worship", "museum": "museum", "school": "education",
            "university": "education", "college": "education",
            "hospital": "hospital", "hotel": "hotel", "stadium": "stadium",
            "civic": "civic", "roof": "canopy"}


def _point_in_poly(x, y, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _poi_func(poi):
    allt = [poi.get("primary_type", "")] + list(poi.get("types", []))
    for types, func in TYPE_FUNC:
        if any(t in types for t in allt):
            return func
    return None


def gather_pois(buildings, anchor):
    """A small grid of searchNearby calls covering the block (Places(New) caps
    each call at 20 results), deduped by name+coord."""
    if not buildings:
        return []          # a valid extent can still hold no buildings (a park,
                           # a rail yard); min() on the empty list used to raise
    lats = [m["center_latlng"][0] for m in buildings]
    lngs = [m["center_latlng"][1] for m in buildings]
    lo_la, hi_la = min(lats), max(lats)
    lo_ln, hi_ln = min(lngs), max(lngs)
    # 3x3 grid of query centres, each radius ~180 m -> full coverage w/ overlap
    seen, pois = set(), []
    for i in range(3):
        for j in range(3):
            la = lo_la + (hi_la - lo_la) * (i + 0.5) / 3
            ln = lo_ln + (hi_ln - lo_ln) * (j + 0.5) / 3
            for p in places_nearby(la, ln, radius=180.0, max_results=20):
                if p["lat"] is None:
                    continue
                k = (round(p["lat"], 5), round(p["lng"], 5), p["name"])
                if k in seen:
                    continue
                seen.add(k)
                pois.append(p)
    return pois


def resolve(out):
    d = json.load(open(os.path.join(out, "buildings.json")))
    anchor, buildings = d["anchor"], d["buildings"]
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0
    # idempotent: clear any prior resolution so a re-run can't accumulate stale
    # labels (the first-cut over-match left tags that a stricter re-run kept)
    for m in buildings:
        for k in ("func", "func_src", "func_conf"):
            m.pop(k, None)

    pois = gather_pois(buildings, anchor)
    print(f"[func] {len(pois)} POIs from Places(New)")

    # project POIs to scene metres, keep only ones we can map to a function
    fpois = []
    for p in pois:
        f = _poi_func(p)
        if not f:
            continue
        x = (p["lng"] - anchor["lon0"]) * kx
        y = (p["lat"] - anchor["lat0"]) * ky
        fpois.append({"x": x, "y": y, "func": f, "name": p["name"]})

    # centroids
    for m in buildings:
        xs = [q[0] for q in m["pts"]]; ys = [q[1] for q in m["pts"]]
        m["_cx"], m["_cy"] = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2

    # each POI belongs to ONE building: the footprint that CONTAINS it, else the
    # single nearest centroid within 18 m. Assigning to every building in a radius
    # mislabels a whole street from one bus-stop point (the first-cut bug).
    poi_hit = {}                                   # building id -> (func, conf)
    for fp in fpois:
        # CONTAINMENT ONLY: a POI tags the footprint it sits inside. A station
        # entrance / hotel pin on the street does NOT tag a random nearby house
        # (a centroid-distance fallback mislabelled residential rows next to the
        # Tube exits -- exactly the "don't guess" rule this stage exists for). Buildings
        # whose POI pin sits just outside are left to OSM / street-view instead.
        home = None
        for m in buildings:
            if _point_in_poly(fp["x"], fp["y"], m["pts"]):
                home = m
                break
        if home is None:
            continue
        prev = poi_hit.get(home["id"])
        if prev is None or FUNC_PRIORITY.index(fp["func"]) < FUNC_PRIORITY.index(prev[0]):
            poi_hit[home["id"]] = (fp["func"], 0.92)

    import collections
    counts = collections.Counter()
    for m in buildings:
        func = func_src = None
        conf = 0.0
        hit = poi_hit.get(m["id"])
        if hit:
            func, conf, func_src = hit[0], hit[1], "places"
        osm_f = OSM_FUNC.get(m.get("btype"))
        if osm_f:
            if func is None:
                func, func_src, conf = osm_f, "osm", 0.7
            elif func == osm_f:
                conf = min(0.97, conf + 0.1)      # both agree -> boost
        if func:
            m["func"], m["func_src"], m["func_conf"] = func, func_src, round(conf, 2)
            counts[func] += 1
        for k in ("_cx", "_cy"):
            m.pop(k, None)

    if not os.path.exists(os.path.join(out, "buildings.json.func.bak")):
        json.dump(d, open(os.path.join(out, "buildings.json.func.bak"), "w"))
    json.dump(d, open(os.path.join(out, "buildings.json"), "w"))
    print(f"[func] resolved: {dict(counts)}")
    for m in buildings:
        if m.get("func") in ("station", "worship", "museum", "canopy"):
            print(f"  {m['id']} {m.get('name') or m['btype']}: "
                  f"{m['func']} ({m['func_src']} {m['func_conf']})")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    a = ap.parse_args()
    resolve(os.path.abspath(a.out))


if __name__ == "__main__":
    main()
