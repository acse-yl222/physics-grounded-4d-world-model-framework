"""img2city/scene/road_graph.py -- traffic-system SEMANTICS for the road network (supervisor
request 2026-07-28: make the road network meaningful rather than decorative --
direction of travel per side, turn restrictions at branches -- so vehicles can
then be simulated on it).

Deterministic, zero-LLM, cached like every scene layer. Reads the SAME
roads_raw.json cache scene_assets uses (way node ids + geometry), plus one new
Overpass fetch for type=restriction relations. Output traffic.json:

  nodes         junction/endpoint nodes {id, x, y, ways} (scene metres,
                same equirect anchor as the buildings)
  arcs          DIRECTED carriageway arcs between junctions -- a two-way
                street yields two arcs, one per travel direction, pts always
                running IN the travel direction:
                {id, way, name, class, a, b, pts, width, lanes, lanes_src,
                 oneway, maxspeed_mph}
  restrictions  turn restrictions {id, type, from_way, via, via_type,
                 to_way, x, y}

lanes carries per-DIRECTION lane count with provenance (`lanes_src`:
"osm" when tagged, "default" otherwise) -- same value+source pattern as the
building parameter schema. The JSON is the editable semantic layer (a routing
graph); city_generate draws direction arrows + lane dividers from the arcs so
the semantics are visible in the model.

  python -m img2city.scene.road_graph --out data/city_sk           # build + validate (cached)
  python -m img2city.scene.road_graph --out data/city_sk --force
"""
from __future__ import annotations
import argparse
import json
import math
import os

from img2city.scene.assets import ROAD_WIDTH, DRIVABLE, _overpass

# default per-direction lane count when OSM has no lanes tag
DEFAULT_LANES = {"trunk": 2, "trunk_link": 1, "primary": 1, "primary_link": 1}


def fetch_restrictions(bbox, cache, force=False):
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    s, w, n, e = bbox
    els = _overpass(f'[out:json][timeout:60];'
                    f'relation["type"="restriction"]({s},{w},{n},{e});out body;')
    with open(cache, "w") as f:
        json.dump(els, f)
    return els


def _mph(v):
    try:
        return int(str(v).split()[0])
    except (ValueError, AttributeError):
        return None


def motor_access(tags):
    """Who may DRIVE here: 'yes' | 'destination' | 'bus_only' | 'private' |
    'no' — from OSM access tags (motor_vehicle > vehicle > access) + class
    defaults. 08-17: which roads are drivable must be pinned down —
    the sk2 export was handing the vehicle-sim partner 8 private mews as
    ordinary carriageways, and our own arrows/sim used them too."""
    hw = (tags or {}).get("highway")
    v = tags.get("motor_vehicle") or tags.get("vehicle") or tags.get("access")
    if v == "private":
        return "private"
    if v == "no":
        return "no"
    if hw == "busway":
        return "bus_only"
    if v == "destination":
        return "destination"
    if hw == "living_street":
        return "destination"          # shared space: access, not through-route
    if hw == "pedestrian":
        return "no"
    return "yes"


def build_graph(elements, restrictions, anchor):
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0

    def loc(g):
        return (round((g["lon"] - anchor["lon0"]) * kx, 2),
                round((g["lat"] - anchor["lat0"]) * ky, 2))

    ways = [el for el in elements
            if (el.get("tags") or {}).get("highway") in DRIVABLE
            and motor_access(el.get("tags") or {}) not in ("no", "private")
            and (el.get("tags") or {}).get("area") != "yes"
            and len(el.get("nodes") or []) >= 2
            and len(el.get("nodes")) == len(el.get("geometry") or [])]

    # a node is a graph node when >1 drivable way uses it, or at a way end
    use = {}
    for el in ways:
        for nid in el["nodes"]:
            use[nid] = use.get(nid, 0) + 1
    node_xy, node_ways = {}, {}
    arcs = []
    for el in ways:
        tags = el["tags"]
        cls = tags["highway"]
        oneway = tags.get("oneway") in ("yes", "-1", "1", "true")
        nds, geo = el["nodes"], el["geometry"]
        if tags.get("oneway") == "-1":              # mapped against travel dir
            nds, geo = nds[::-1], geo[::-1]
        total = _mph(tags.get("lanes"))
        if total:
            lanes, lanes_src = (total if oneway else max(1, total // 2)), "osm"
        else:
            lanes, lanes_src = DEFAULT_LANES.get(cls, 1), "default"
        cuts = [i for i in range(len(nds))
                if i in (0, len(nds) - 1) or use[nds[i]] > 1]
        for a, b in zip(cuts, cuts[1:]):
            pts = [loc(g) for g in geo[a:b + 1]]
            if sum(math.dist(pts[i], pts[i + 1])
                   for i in range(len(pts) - 1)) < 1.0:
                continue
            for nid, (x, y) in ((nds[a], pts[0]), (nds[b], pts[-1])):
                node_xy[nid] = (x, y)
                node_ways.setdefault(nid, set()).add(el["id"])
            base = dict(way=el["id"], name=tags.get("name", ""), **{"class": cls},
                        width=ROAD_WIDTH[cls], lanes=lanes, lanes_src=lanes_src,
                        oneway=oneway, maxspeed_mph=_mph(tags.get("maxspeed")))
            arcs.append(dict(base, id=f"{el['id']}:{a}:f",
                             a=nds[a], b=nds[b], pts=pts))
            if not oneway:
                arcs.append(dict(base, id=f"{el['id']}:{a}:r",
                                 a=nds[b], b=nds[a], pts=pts[::-1]))

    way_ids = {el["id"] for el in ways}
    rests = []
    for rel in restrictions:
        m = {r: [mm["ref"] for mm in rel["members"] if mm["role"] == r]
             for r in ("from", "via", "to")}
        via_type = next((mm["type"] for mm in rel["members"]
                         if mm["role"] == "via"), None)
        if not (m["from"] and m["to"] and m["via"]):
            continue
        x, y = node_xy.get(m["via"][0], (None, None))
        rests.append({"id": rel["id"], "type": rel["tags"].get("restriction"),
                      "from_way": m["from"][0], "via": m["via"][0],
                      "via_type": via_type, "to_way": m["to"][0],
                      "x": x, "y": y,
                      "in_graph": m["from"][0] in way_ids
                                  and m["to"][0] in way_ids})
    return {"nodes": [{"id": n, "x": xy[0], "y": xy[1],
                       "ways": sorted(node_ways.get(n, ()))}
                      for n, xy in sorted(node_xy.items())],
            "arcs": arcs, "restrictions": rests}


# ---- render helpers: the marks city_generate instantiates -------------------

ARROW_CLASSES = DRIVABLE - {"service", "living_street"}   # keep clutter down


def drive_side(out):
    """'left' or 'right' from region.json {"drive": ...}; default LEFT because
    sk/cw predate the field. Wrong side = head-on traffic + arrows against the
    flow (the 08-13 generality audit: Amsterdam/Paris drive on the right), so
    make_city writes this at bootstrap from the geocoded country."""
    try:
        return json.load(open(os.path.join(out, "region.json"))).get(
            "drive", "left")
    except Exception:
        return "left"


def traffic_marks(graph, arrow_step=28.0, dash_step=4.0, side="left"):
    """Directed arcs -> {arrows: [{x,y,ang}], dashes: [{x,y,ang}]} in scene
    metres. A two-way arc's arrow row sits w/4 to the DRIVING side of the
    centreline in the travel direction (left in the UK, right elsewhere); a
    one-way carriageway centres its rows on the lanes. Lane dividers (dashes)
    between lanes on multi-lane carriageways."""
    sgn = 1.0 if side == "left" else -1.0
    arrows, dashes = [], []
    for arc in graph["arcs"]:
        if arc["class"] not in ARROW_CLASSES:
            continue
        pts, w = arc["pts"], arc["width"]
        if arc["oneway"]:
            offs = [((k + 0.5) / arc["lanes"] - 0.5) * w * 0.8
                    for k in range(arc["lanes"])]
        else:
            offs = [sgn * w / 4.0]
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        if L < 6.0:
            continue
        n_arrows = max(1, int(L / arrow_step))
        for off in offs:
            for k in range(n_arrows):
                d = (k + 0.5) * L / n_arrows
                p = _along(pts, d)
                if p:
                    x, y, ang = p
                    arrows.append({"x": round(x - math.sin(ang) * off, 2),
                                   "y": round(y + math.cos(ang) * off, 2),
                                   "ang": round(ang, 3)})
        if arc["oneway"] and arc["lanes"] >= 2:
            for k in range(1, arc["lanes"]):
                off = (k / arc["lanes"] - 0.5) * w * 0.8
                d = dash_step / 2
                while d < L:
                    p = _along(pts, d)
                    if p:
                        x, y, ang = p
                        dashes.append({"x": round(x - math.sin(ang) * off, 2),
                                       "y": round(y + math.cos(ang) * off, 2),
                                       "ang": round(ang, 3)})
                    d += dash_step
    return {"arrows": arrows, "dashes": dashes}


def _along(pts, dist):
    """Point + bearing at arc-length dist along a polyline."""
    run = 0.0
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg < 1e-9:
            continue
        if run + seg >= dist:
            t = (dist - run) / seg
            return (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t,
                    math.atan2(y2 - y1, x2 - x1))
        run += seg
    return None


def load_or_build(out, force=False):
    cache = os.path.join(out, "traffic.json")
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    d = json.load(open(os.path.join(out, "buildings.json")))
    anchor = d["anchor"]
    elements = json.load(open(os.path.join(out, "roads_raw.json")))
    rest = fetch_restrictions(anchor["bbox"],
                              os.path.join(out, "restrictions_raw.json"), force)
    graph = build_graph(elements, rest, anchor)
    with open(cache, "w") as f:
        json.dump(graph, f)
    return graph


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    g = load_or_build(a.out, a.force)
    ow = [r for r in g["arcs"] if r["oneway"]]
    km = sum(math.dist(r["pts"][i], r["pts"][i + 1])
             for r in g["arcs"] for i in range(len(r["pts"]) - 1)) / 1000.0
    deg = {}
    for arc in g["arcs"]:
        deg[arc["a"]] = deg.get(arc["a"], 0) + 1
        deg[arc["b"]] = deg.get(arc["b"], 0) + 1
    junctions = sum(1 for n in g["nodes"] if deg.get(n["id"], 0) > 2)
    marks = traffic_marks(g)
    print(f"[traffic] {len(g['nodes'])} nodes ({junctions} junctions), "
          f"{len(g['arcs'])} directed arcs ({km:.1f} arc-km, {len(ow)} oneway), "
          f"{len(g['restrictions'])} turn restrictions "
          f"({sum(1 for r in g['restrictions'] if r['in_graph'])} fully in graph)")
    for r in g["restrictions"]:
        print(f"  {r['type']:<18} from {r['from_way']} via {r['via']} "
              f"to {r['to_way']}" + ("" if r["in_graph"] else "  [edge of bbox]"))
    print(f"[traffic] marks: {len(marks['arrows'])} arrows, "
          f"{len(marks['dashes'])} lane dashes")


if __name__ == "__main__":
    main()
