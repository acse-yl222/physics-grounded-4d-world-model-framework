"""img2city/city/lod1.py -- bounded London area -> OSM footprints -> LoD1 Blender scene.

The city-scenario pilot (supervisor direction, 2026-06-30): building positions come
from OpenStreetMap (the footprint is the placement CONTRACT -- geometry snapped to
the real polygon is correctly placed, plausibly massed and watertight by
construction), heights from OSM tags where present, and per-building imagery is
fetched with the existing maps_fetch.py (Google Static Maps + Street View) so the
single-building agent can replace the most prominent LoD1 blocks with generated
parametric models later.

Pipeline:
  1. fetch_osm      Overpass bbox query -> building ways (+ tags), cached to JSON
  2. to_local       lat/lon -> local metres around the bbox centre (stored in the
                    scene metadata so any point maps back to WGS84)
  3. build_scene    LoD1 extrusion per footprint in live Blender (BlenderMCP) +
                    aerial and top renders
  4. --imagery N    fetch satellite + street view for the N largest buildings via
                    maps_fetch.fetch  (needs GOOGLE_MAPS_API_KEY)

Usage (Blender + BlenderMCP server open):
  python -m img2city.city.lod1 --out data/city_sk                  # default SK bbox
  python -m img2city.city.lod1 --out data/city_sk --imagery 6      # + per-building imagery
"""
from __future__ import annotations
import argparse
import json
import math
import os
import urllib.parse
import urllib.request

from img2city import config
from img2city.imagery import maps_fetch
from img2city.building.generate import _send, RENDER_OUT

# default pilot area: ~400 m x 390 m around South Kensington station -- terraces,
# a square, the station block: varied but no monster museum footprints
BBOX = (51.4922, -0.1772, 51.4958, -0.1716)   # (s, w, n, e)

OVERPASS = tuple(config.OVERPASS_URLS)      # mirrors, tried in order (IMG2CITY_OVERPASS_URLS)

FLOOR_H = 3.2          # metres per storey when only building:levels is tagged
DEFAULT_H = 11.0       # typical 3-4 storey London terrace when nothing is tagged


def fetch_osm(bbox, cache):
    """Building ways (with geometry + tags) in bbox; cached to JSON."""
    if os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)
    s, w, n, e = bbox
    # ways AND relations: multipolygon `relation["building"]` (mansion blocks,
    # courtyard buildings -- Melton Court, the Ismaili Centre) were silently
    # dropped when we queried ways only, so those buildings went missing from the
    # whole scene (2026-07-27). Each relation's OUTER rings become footprints.
    q = ('[out:json][timeout:60];('
         'way["building"](%f,%f,%f,%f);'
         'relation["building"](%f,%f,%f,%f););out body geom;'
         % (s, w, n, e, s, w, n, e))
    last = None
    for ep in OVERPASS:
        try:
            req = urllib.request.Request(
                ep, data=urllib.parse.urlencode({"data": q}).encode(),
                headers={"User-Agent": "img2city/0.1"})
            with urllib.request.urlopen(req, timeout=90) as r:
                j = json.loads(r.read())
            break
        except Exception as exc:
            last = exc
    else:
        raise SystemExit(f"Overpass failed on all mirrors: {last}")
    out = []
    for el in j.get("elements", []):
        if el.get("type") == "relation":
            # one footprint per OUTER ring; INNER rings are courtyards and are
            # kept as holes on the outer ring that contains them (08-17:
            # V&A rendered as a solid blob — its Madejski Garden courtyard is
            # an inner ring this loop used to throw away)
            inners = [[[g["lat"], g["lon"]] for g in (m.get("geometry") or [])]
                      for m in el.get("members", []) if m.get("role") == "inner"
                      and len(m.get("geometry") or []) >= 4]
            for i, mem in enumerate(m for m in el.get("members", [])
                                    if m.get("role") == "outer"):
                geom = mem.get("geometry") or []
                if len(geom) < 4:
                    continue
                ring = [[g["lat"], g["lon"]] for g in geom]

                def _inside(pt, poly):
                    x, y = pt[1], pt[0]
                    ok = False
                    for a, b in zip(poly, poly[1:] + poly[:1]):
                        if (a[0] > y) != (b[0] > y):
                            t = (y - a[0]) / (b[0] - a[0])
                            if x < a[1] + t * (b[1] - a[1]):
                                ok = not ok
                    return ok
                holes = [h for h in inners if _inside(h[0], ring)]
                ent = {"id": el["id"] * 10 + i, "tags": el.get("tags", {}),
                       "coords": ring}
                if holes:
                    ent["holes"] = holes
                out.append(ent)
            continue
        geom = el.get("geometry") or []
        if len(geom) < 4:          # need a closed ring
            continue
        out.append({"id": el["id"], "tags": el.get("tags", {}),
                    "coords": [[g["lat"], g["lon"]] for g in geom]})
    with open(cache, "w") as f:
        json.dump(out, f)
    return out


def height_of(tags):
    """OSM height hierarchy: height tag -> levels x FLOOR_H -> default."""
    h = tags.get("height") or tags.get("building:height")
    if h:
        try:
            return max(3.0, float(str(h).replace("m", "").strip())), "tag:height"
        except ValueError:
            pass
    lv = tags.get("building:levels")
    if lv:
        try:
            return max(3.0, float(lv) * FLOOR_H), "tag:levels"
        except ValueError:
            pass
    return DEFAULT_H, "default"


def to_local(buildings, bbox):
    """Equirectangular projection around the bbox centre -- accurate to ~cm at this
    scale, dependency-free. The (lat0, lon0) anchor is stored in the metadata so any
    scene point maps back to WGS84 (Blosm's scene-anchor convention)."""
    lat0 = (bbox[0] + bbox[2]) / 2
    lon0 = (bbox[1] + bbox[3]) / 2
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0
    metas = []
    for b in buildings:
        pts = [[(lon - lon0) * kx, (lat - lat0) * ky] for lat, lon in b["coords"]]
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) < 3:
            continue
        holes = []
        for h in b.get("holes") or []:
            hp = [[(lon - lon0) * kx, (lat - lat0) * ky] for lat, lon in h]
            if hp[0] == hp[-1]:
                hp = hp[:-1]
            if len(hp) >= 3:
                holes.append([[round(x, 2), round(y, 2)] for x, y in hp])
        h, hsrc = height_of(b["tags"])
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        area = abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1]
                       - pts[(i + 1) % len(pts)][0] * pts[i][1]
                       for i in range(len(pts)))) / 2
        metas.append({"id": b["id"], "pts": [[round(x, 2), round(y, 2)] for x, y in pts],
                      "height": round(h, 1), "height_src": hsrc,
                      "area_m2": round(area, 1),
                      "center_latlng": [round(cy / ky + lat0, 6), round(cx / kx + lon0, 6)],
                      "name": b["tags"].get("name", ""),
                      "btype": b["tags"].get("building", "yes"),
                      **({"holes": holes} if holes else {})})
    return metas, {"lat0": lat0, "lon0": lon0, "bbox": list(bbox), "proj": "equirect"}


# LoD1 builder: one solid, watertight prism per footprint (bottom ring, top ring,
# side quads, top/bottom ngons), named by OSM id so scene objects map back to OSM.
BUILD_SCENE = r'''
import bpy, json
for _o in list(bpy.data.objects):
    bpy.data.objects.remove(_o, do_unlink=True)
for _m in list(bpy.data.materials):
    bpy.data.materials.remove(_m)

def _mat(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m
M_B = _mat("bldg", (0.82, 0.79, 0.72))
M_R = _mat("roofc", (0.55, 0.53, 0.50))
M_G = _mat("ground", (0.35, 0.37, 0.35))

DATA = json.loads(%r)
for b in DATA:
    pts, h = b["pts"], b["height"]
    n = len(pts)
    verts = [(x, y, 0.0) for x, y in pts] + [(x, y, h) for x, y in pts]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) %% n, n + (i + 1) %% n, n + i) for i in range(n)]
    me = bpy.data.meshes.new("m%%d" %% b["id"])
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new("Bldg_%%d" %% b["id"], me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(M_B); ob.data.materials.append(M_R)
    for p in me.polygons:
        p.material_index = 1 if all(me.vertices[v].co.z > 0.1 for v in p.vertices) else 0

import mathutils
mn = [1e18]*3; mx = [-1e18]*3
for o in bpy.data.objects:
    if o.type == 'MESH':
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
g = bpy.data.objects.new("Ground", bpy.data.meshes.new("g"))
g.data.from_pydata([(mn[0]-40, mn[1]-40, -0.1), (mx[0]+40, mn[1]-40, -0.1),
                    (mx[0]+40, mx[1]+40, -0.1), (mn[0]-40, mx[1]+40, -0.1)],
                   [], [(0, 1, 2, 3)])
bpy.context.scene.collection.objects.link(g); g.data.materials.append(M_G)
'''

CITY_RENDER = r'''
import bpy, math, mathutils
# recompute the scene bbox HERE, over everything actually built: the BUILD_SCENE-
# time mn/mx only saw the LoD1 buildings, and with an all-agent scene (min-area 0)
# that set is EMPTY -- the stale +-1e18 bounds aimed the camera at nothing and
# every whole-block render came out blank (2026-07-26)
mn = [1e18]*3; mx = [-1e18]*3
_skip = ("Ground", "Road", "Pave", "Line", "Tree", "Green", "Hedge")
for _o in bpy.data.objects:
    if _o.type == 'MESH' and not _o.name.startswith(_skip):
        for _c in _o.bound_box:
            _w = _o.matrix_world @ mathutils.Vector(_c)
            for _i in range(3):
                mn[_i] = min(mn[_i], _w[_i]); mx[_i] = max(mx[_i], _w[_i])
_g = bpy.data.objects.get("Ground")
if _g and (mx[0] - mn[0]) < 1e17:
    _gm = _g.data
    _co = [(mn[0]-40, mn[1]-40, -0.1), (mx[0]+40, mn[1]-40, -0.1),
           (mx[0]+40, mx[1]+40, -0.1), (mn[0]-40, mx[1]+40, -0.1)]
    for _v, _q in zip(_gm.vertices, _co):
        _v.co = _q
cx, cy, cz = [(mn[i]+mx[i])/2 for i in range(3)]
tgt = bpy.data.objects.new("Tgt", None); bpy.context.scene.collection.objects.link(tgt)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); bpy.context.scene.collection.objects.link(cam)
tgt.location = (cx, cy, 0)
_dir = mathutils.Vector((0.45, -0.75, 0.55)); _dir.normalize()
_rad = 0.5*math.sqrt((mx[0]-mn[0])**2 + (mx[1]-mn[1])**2)
cam.data.lens = 40
# the whole-block camera stands >1 km out; the default 1000 m clip_end sliced
# the far side of the scene off (blank/partial whole-block renders, 2026-07-26)
cam.data.clip_end = 100000.0
_d = _rad / math.tan(math.atan(18.0/cam.data.lens)) * 1.1
cam.location = (cx + _dir.x*_d, cy + _dir.y*_d, _dir.z*_d)
con = cam.constraints.new('TRACK_TO'); con.target = tgt
con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
bpy.context.scene.camera = cam
sc = bpy.context.scene
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); bpy.context.scene.collection.objects.link(sun)
# tamed exposure: the old sun 2.8 + full-strength sky blew out the white stucco band
# (the judge kept scoring "can't count storeys" on washed-out renders, not on wrong
# geometry). AgX view transform + a negative exposure roll the highlights back.
sun.data.energy = 1.9; sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(30))
sun.data.angle = math.radians(2.5)                  # soften shadow edges a touch
w = bpy.context.scene.world or bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
# realism pass (2026-07-26): Nishita sky drives the LIGHTING (graded ambient,
# warm sun side) while CAMERA rays see a clean pale-blue backdrop -- the raw
# Nishita zenith renders near-black under AgX -0.7EV on aerial framings.
try:
    _nt = w.node_tree
    for _n in list(_nt.nodes):
        _nt.nodes.remove(_n)
    _out = _nt.nodes.new("ShaderNodeOutputWorld")
    _sky = _nt.nodes.new("ShaderNodeTexSky")
    _sky.sky_type = 'NISHITA'
    _sky.sun_elevation = math.radians(45)
    _sky.sun_rotation = math.radians(120)
    _sky.sun_intensity = 0.4
    _sky.altitude = 10
    _bg1 = _nt.nodes.new("ShaderNodeBackground")
    _nt.links.new(_sky.outputs[0], _bg1.inputs[0]); _bg1.inputs[1].default_value = 0.55
    _bg2 = _nt.nodes.new("ShaderNodeBackground")
    _bg2.inputs[0].default_value = (0.74, 0.81, 0.90, 1); _bg2.inputs[1].default_value = 1.0
    _lp = _nt.nodes.new("ShaderNodeLightPath")
    _mx = _nt.nodes.new("ShaderNodeMixShader")
    _nt.links.new(_lp.outputs["Is Camera Ray"], _mx.inputs[0])
    _nt.links.new(_bg1.outputs[0], _mx.inputs[1])
    _nt.links.new(_bg2.outputs[0], _mx.inputs[2])
    _nt.links.new(_mx.outputs[0], _out.inputs[0])
except Exception:
    if bg: bg.inputs[0].default_value = (0.75, 0.82, 0.90, 1); bg.inputs[1].default_value = 0.7
try: sc.view_settings.view_transform = 'AgX'
except Exception: pass
try: sc.view_settings.exposure = -0.7
except Exception: pass
'''

CITY_TOP = r'''
tgt.location = (cx, cy, 0)
cam.location = (cx, cy + 0.001, _rad / math.tan(math.atan(18.0/cam.data.lens)) * 1.05)
'''


def build_scene(metas, out_dir):
    code = (BUILD_SCENE % json.dumps(metas)) + CITY_RENDER \
        + (RENDER_OUT % os.path.join(out_dir, "city_aerial.png")) \
        + CITY_TOP + (RENDER_OUT % os.path.join(out_dir, "city_top.png"))
    return _send(code, timeout=300)


def main():
    ap = argparse.ArgumentParser(description="OSM bbox -> LoD1 city scene in Blender")
    ap.add_argument("--bbox", default=",".join(str(v) for v in BBOX),
                    help="s,w,n,e (default: South Kensington pilot area)")
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--imagery", type=int, default=0,
                    help="also fetch satellite+street view for the N largest buildings "
                         "(needs GOOGLE_MAPS_API_KEY; uses maps_fetch.py)")
    a = ap.parse_args()
    bbox = tuple(float(v) for v in a.bbox.split(","))
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    raw = fetch_osm(bbox, os.path.join(out, "osm_raw.json"))
    metas, anchor = to_local(raw, bbox)
    tagged = sum(1 for m in metas if m["height_src"] != "default")
    print(f"[osm] {len(metas)} footprints ({tagged} with tagged height/levels, "
          f"{len(metas) - tagged} default {DEFAULT_H} m)")
    with open(os.path.join(out, "buildings.json"), "w") as f:
        json.dump({"anchor": anchor, "buildings": metas}, f, indent=1)

    _res, err = build_scene(metas, out)
    if err:
        raise SystemExit(f"Blender build failed: {err}")
    print(f"[blender] LoD1 scene built -> {out}/city_aerial.png, city_top.png")

    if a.imagery:
        from img2city.imagery.maps_fetch import fetch
        big = sorted(metas, key=lambda m: -m["area_m2"])[:a.imagery]
        for m in big:
            lat, lng = m["center_latlng"]
            d = os.path.join(out, "buildings", str(m["id"]))
            print(f"[imagery] {m['id']} ({maps_fetch.latin_only(m['name']) if m['name'] else m['btype']}, "
                  f"{m['area_m2']:.0f} m2) -> {d}")
            try:
                fetch(lat, lng, d, pitch=20)
            except SystemExit as e:
                print(f"  skipped: {e}")
                break


if __name__ == "__main__":
    main()
