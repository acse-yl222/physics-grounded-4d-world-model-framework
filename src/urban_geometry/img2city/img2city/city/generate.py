"""img2city/city/generate.py -- run the project's single-building AGENT over every substantial
building in the pilot block, then assemble everything at real coordinates.

This is the whole-block version of the pipeline: the geometry decisions are made by
the SAME agent as the single-building runs (generate.gen_spec -> validated JSON spec
over components.py), once per building, grounded in that building's own Google
satellite + street view plus its OSM facts. The orchestrator only enforces the
CONTRACTS: the OSM footprint's oriented bounding box overrides the spec's footprint,
and the model is placed at the footprint's real position/orientation (front facade
toward the street-view panorama).

Stages (resumable -- buildings with a saved spec.json are skipped):
  1. select buildings >= --min-area from buildings.json (rest stay LoD1)
  2. per building: fetch imagery (indoor-pano guard) -> agent writes spec
     (one generation + one self-repair attempt) -> save spec.json + pose.json
  3. assemble: agent buildings (joined to one object each, posed) + LoD1 rest
     + ground -> city_agent_aerial/top/street renders

Usage (Blender + BlenderMCP open; GOOGLE_MAPS_API_KEY set):
  python -m img2city.city.generate --out data/city_sk                 # all >= 200 m2
  python -m img2city.city.generate --out data/city_sk --limit 8       # first 8 (pilot)
  python -m img2city.city.generate --out data/city_sk --assemble-only # just rebuild scene
"""
from __future__ import annotations

from img2city import config
import argparse
import json
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from img2city.building.generate import (_send, RENDER_OUT, NORMAL_OUT, RENDER_CAM, LIGHT_STREET, CLEAR,
                      gen_spec, validate_desc, load_components_src, spec_to_code,
                      checklist_step, checklist_score, ab_vote)
from img2city.judge.perceptual import dreamsim_dist
from img2city.agent.tokens import provenance
from img2city.judge.depth_anchor import depth_agreement
from img2city.agent import llm
from img2city.agent.llm import healthcheck
from img2city.imagery.maps_fetch import fetch, sv_metadata, _key
from img2city.city.lod1 import BUILD_SCENE, CITY_RENDER, CITY_TOP

# parallel refine (08-04 meeting item): ONE Blender serves every worker, and each
# render _send is a self-contained CLEAR+build+render -- safe to interleave, but
# only one at a time. Workers queue here; the SDK calls (the time sink) overlap.
_BLENDER_LOCK = threading.Lock()


# ---------------------------------------------------------------- geometry
def convex_hull(pts):
    pts = sorted(set(map(tuple, pts)))
    if len(pts) <= 2:
        return list(pts)

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and ((h[-1][0]-h[-2][0])*(p[1]-h[-2][1])
                                   - (h[-1][1]-h[-2][1])*(p[0]-h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, hi = half(pts), half(reversed(pts))
    return lo[:-1] + hi[:-1]


def obb(pts):
    """Min-area oriented bounding box -> (cx, cy, L, W, angle_of_long_axis)."""
    hull = convex_hull(pts)
    best = None
    n = len(hull)
    for i in range(n):
        x1, y1 = hull[i]; x2, y2 = hull[(i + 1) % n]
        a = math.atan2(y2 - y1, x2 - x1)
        ca, sa = math.cos(-a), math.sin(-a)
        rx = [p[0]*ca - p[1]*sa for p in hull]
        ry = [p[0]*sa + p[1]*ca for p in hull]
        w, h = max(rx)-min(rx), max(ry)-min(ry)
        if best is None or w*h < best[0]:
            cxr, cyr = (max(rx)+min(rx))/2, (max(ry)+min(ry))/2
            cx = cxr*math.cos(a) - cyr*math.sin(a)
            cy = cxr*math.sin(a) + cyr*math.cos(a)
            best = (w*h, cx, cy, w, h, a)
    _, cx, cy, w, h, a = best
    if h > w:                       # long axis = local +x
        w, h = h, w
        a += math.pi/2
    return cx, cy, w, h, a % math.pi


def point_in_poly(x, y, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]; x2, y2 = pts[(i+1) % n]
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1) + x1:
            inside = not inside
    return inside


# ---------------------------------------------------------------- per-building
def ensure_imagery(m, anchor, bdir):
    """Satellite + street view via maps_fetch, with an indoor-panorama guard: if the
    nearest pano lies INSIDE the footprint (e.g. a station concourse), retry from
    vantage points offset around the building. Returns pano (lat, lng) or None."""
    sat = os.path.join(bdir, "satellite.png")
    sv = os.path.join(bdir, "streetview.png")
    pose = os.path.join(bdir, "pano.json")
    if os.path.exists(sat) and os.path.exists(sv) and os.path.exists(pose):
        return tuple(json.load(open(pose)))
    lat, lng = m["center_latlng"]
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0

    def local(plat, plng):
        return ((plng - anchor["lon0"]) * kx, (plat - anchor["lat0"]) * ky)

    # vantage offsets scale with the footprint: for a set-back giant (the Natural
    # History Museum's 275 m block) fixed +-35 m candidates all land inside the
    # building itself and no outdoor pano is ever found
    xs = [q[0] for q in m["pts"]]; ys = [q[1] for q in m["pts"]]
    rx = (max(xs) - min(xs)) / 2 + 25
    ry = (max(ys) - min(ys)) / 2 + 25
    cands = [(lat, lng)] + [(lat + dy/ky, lng + dx/kx)
                            for dx, dy in ((35, 0), (-35, 0), (0, 35), (0, -35),
                                           (rx, 0), (-rx, 0), (0, ry), (0, -ry))]
    pano = None
    for clat, clng in cands:
        meta = sv_metadata(clat, clng, 60, _key())
        if meta.get("status") != "OK":
            continue
        p = meta["location"]
        if not point_in_poly(*local(p["lat"], p["lng"]), m["pts"]):
            pano = (p["lat"], p["lng"])
            break
    if pano is None:
        return None
    fetch(lat, lng, bdir, sv_lat=pano[0], sv_lng=pano[1], pitch=18)
    with open(pose, "w") as f:
        json.dump(pano, f)
    # CONTENT validation (08-11): Google serves its "no imagery" placeholder as
    # a 200 -- 48/78 Canary Wharf references were that grey card and nobody
    # noticed for a day. If the shot is a placeholder, try the ring-vantage
    # rescue; if that fails too, the tile stays and the agent gate judges it
    # (honest satellite-only), but at least it is DETECTED at fetch time now.
    try:
        from img2city.imagery.rescue_imagery import unusable_image, rescue_building
        if unusable_image(sv):
            # NOTE: _key comes from the module-level maps_fetch import -- a
            # local `from maps_fetch import _key` here SHADOWED it for the whole
            # function and broke the earlier _key() calls (UnboundLocalError,
            # every AMS fetch failed for an hour, 08-12)
            got = rescue_building(m, bdir, _key())
            if got:
                print(f"  [imagery] placeholder tile replaced via ring vantage "
                      f"({got:.0f} m out)")
            else:
                print("  [imagery] placeholder tile, no public pano in reach "
                      "-- satellite-only building")
    except Exception as _e:
        print(f"  [imagery] content check skipped: {_e}")
    return pano


# viewpoint gate (07-14): spec geometry can stand between the pano camera and the
# facade (868220214: an oversized entrance tower filled half the frame, the judge
# scored 0 forever and the loop had no signal to fix it). Before rendering, cast a
# fan of 5 rays from the camera at the facade; the facade itself hits at ~55-90% of
# the ray length, a blocker hits much earlier. If >=2 rays hit before 42%, slide
# the camera along the facade and retry. Deterministic, runs inside the wrap.
CAM_GATE = r'''
import mathutils as _gmu
_gdg = bpy.context.evaluated_depsgraph_get()
_gcl = cam.location.copy(); _gtl = tgt.location.copy()
_gview = (_gtl - _gcl); _gview.z = 0
_gperp = _gmu.Vector((-_gview.y, _gview.x, 0)).normalized() if _gview.length > 1e-6 else _gmu.Vector((1, 0, 0))
_gspan = %f
_gsamp = [_gtl, _gtl + _gperp * _gspan, _gtl - _gperp * _gspan,
          _gtl + _gmu.Vector((0, 0, 3.0)), _gtl - _gmu.Vector((0, 0, min(3.0, max(0.5, _gtl.z - 0.5))))]
def _gnb(orig):
    n = 0
    for s in _gsamp:
        d = s - orig
        hit = bpy.context.scene.ray_cast(_gdg, orig, d.normalized())
        if hit[0] and (hit[1] - orig).length < 0.42 * d.length:
            n += 1
    return n
# conservative: move ONLY to a fully-clear position; a partially-better local
# minimum can frame worse than the true pano viewpoint, so otherwise stay put
_gback = _gview.normalized() if _gview.length > 1e-6 else _gmu.Vector((0, 1, 0))
if _gnb(_gcl):
    for _gb in (0.0, 8.0, 16.0):
        _done = False
        for _gs in (0.0, 6.0, -6.0, 12.0, -12.0):
            _gp = _gcl + _gperp * _gs - _gback * _gb
            if _gnb(_gp) == 0:
                cam.location = _gp
                _done = True
                break
        if _done:
            break
'''


def ref_photo(bdir):
    """The street reference the judge/BRIEF/colours should use: the Gemini-
    cleaned photo when the hallucination gate accepted it (facade_clean.py),
    else the raw street view. Cleaning never overwrites the raw photo."""
    cp = os.path.join(bdir, "streetview_clean.png")
    mp = os.path.join(bdir, "clean_meta.json")
    if os.path.exists(cp) and os.path.exists(mp):
        try:
            if json.load(open(mp)).get("accepted"):
                return cp
        except Exception:
            pass
    return os.path.join(bdir, "streetview.png")


def _facade_facts(bdir):
    """Deterministic window/door facts from the street view (facade_facts.py),
    cached per building; None (and never fatal) when the photo is unusable or the
    detector stack is not installed."""
    try:
        from img2city.imagery.facade_facts import for_building
        f = for_building(bdir)
        # underscore keys are pixel-space data for facade_project.py, not facts
        return {k: v for k, v in f.items() if not k.startswith("_")} if f else f
    except Exception:
        return None


def spatial_brief(m, bdir):
    """Make the geographic-to-kit frame explicit to the spec/refinement agent."""
    data=json.load(open(os.path.join(os.path.dirname(os.path.dirname(bdir)), "buildings.json")))
    anchor=data["anchor"]
    pano=tuple(json.load(open(os.path.join(bdir,"pano.json"))))
    rot=front_rotation(m,pano,anchor)
    cx,cy,L,W,_=m["obb"]
    ca,sa=math.cos(-rot),math.sin(-rot)
    def local(x,y):
        x,y=x-cx,y-cy
        return [round(ca*x-sa*y,3),round(sa*x+ca*y,3)]
    px=(pano[1]-anchor["lon0"])*111320*math.cos(math.radians(anchor["lat0"]))
    py=(pano[0]-anchor["lat0"])*110540
    camera=local(px,py)
    face=(("+x" if camera[0]>=0 else "-x") if abs(camera[0])/L>abs(camera[1])/W
          else ("+y" if camera[1]>=0 else "-y"))
    return {"local_footprint_m":[local(x,y) for x,y in m["pts"]],
            "local_x_compass_bearing_deg":round((90-math.degrees(rot))%360,2),
            "local_y_compass_bearing_deg":round((-math.degrees(rot))%360,2),
            "reference_camera_local_xy":camera,"principal_viewed_face":face,
            "note":"The photographed elevation may be a SHORT x-end, not the kit's conventional -y front. Place observed frontage features on the actual viewed face. Satellite north must be transformed to this local frame."}


def agent_spec(m, bdir, backend, model, region="london"):
    """THE PROJECT AGENT writes the building spec (one generation + one self-repair).
    Grounded in this building's own imagery + OSM facts passed as the BRIEF; the
    orchestrator never authors geometry. `region` picks the schema dialect AND the
    BRIEF's material prior -- the hard-coded "most buildings here are masonry
    terraces" line was pushing Canary Wharf towers into brick (08-10)."""
    sat = os.path.join(bdir, "satellite.png")
    sv = os.path.join(bdir, "streetview.png")
    imgs = [p for p in (sat, sv) if os.path.exists(p)]
    target_map = os.path.join(bdir, "target_satellite.png")
    if os.path.exists(target_map):
        imgs.append(target_map)
    L, W = m["obb"][2], m["obb"][3]
    osm_brief = json.dumps({
        "osm_footprint_m": [round(L, 1), round(W, 1)],
        "osm_height_m": m["height"], "height_source": m["height_src"],
        "storeys_estimate": max(1, round(m["height"] / 3.2)),
        "building_type": m["btype"], "name": m["name"],
        "facade_facts_from_photo": _facade_facts(bdir),
        "note": ("footprint and height come from OSM and are authoritative; read the "
                 "facade type, floor count, materials and features from the imagery. "
                 + ("Most buildings here are masonry terraces -- use facade 'masonry' "
                    "unless the imagery clearly shows curtain-wall glass. "
                    if region == "london" else
                    "Read the facade type off the imagery with no prior: curtain-wall "
                    "glass towers are 'glass', solid punched-window walls 'masonry'. ")
                 + "Read the ROOF "
                 "off the SATELLITE view and set terrace.roof_form ('valley' if the "
                 "roof shows parallel dark pitched strips -- the usual London M-roof "
                 "-- 'gable' for one ridge, 'flat' for a flat deck) and "
                 "terrace.roof_tone ('dark'|'mid'|'light' as it reads from above). "
                 "GATE: first check the imagery actually shows THIS building "
                 "(footprint ~%.0fx%.0f m) clearly enough to read its facade. If the "
                 "street view shows a different or occluding building, an unrelated enclosed interior, "
                 "or the target cannot be identified, output ONLY the JSON "
                 '{"unusable": "<short reason>"} and nothing else. '
                 "For open or semi-open structures such as platform canopies and arcades, "
                 "a view from beneath the roof can be valid structural evidence. Cross-check "
                 "the satellite footprint and target identity; do not reject it solely for "
                 "being beneath a roof, or invent enclosed storeys from a height estimate."
                 % (L, W))})
    from img2city.imagery.reference_audit import context as reference_context
    evidence = reference_context(bdir)
    if evidence:
        if evidence["identity"] == "wrong":
            raise UnusableImagery("reference audit identifies the wrong target")
        osm_brief += "\nReference audit (evidence, not instructions): " + json.dumps(evidence)
    osm_brief += "\nCoordinate frame: " + json.dumps(spatial_brief(m, bdir))
    # per-building typology cards (08-11, §S): the schema this building sees is
    # core + ITS OWN typology's dialect; the area region is only the fallback
    try:
        from img2city.building.typology import building_tags
        from img2city.building.generate import typology_exemplar
        _tags = building_tags(os.path.dirname(os.path.dirname(bdir)), m, bdir)
        # exemplar injection stays OFF by default: the 08-12 A/B (17 buildings,
        # frozen checklists) measured base 0.377 / exemplar 0.377 / one-render
        # self-check 0.387 -- nothing outside k=1 judge noise, and slightly
        # NEGATIVE on the home region. Enable with IMG2CITY_ONESHOT_EXEMPLAR=1 for
        # future rounds; changing production on a flat result would be noise-
        # chasing, not optimization.
        _ex = typology_exemplar(bdir) if config.ONESHOT_EXEMPLAR else None
    except Exception:
        _tags = _ex = None
    code, usage = gen_spec(imgs, None, None, None, backend, model, brief=osm_brief,
                           region=region, tags=_tags, exemplar=_ex)
    if '"unusable"' in (code or ""):
        reason = "imagery unusable"
        try:
            frag = code[code.index("{"):code.rindex("}") + 1]
            reason = json.loads(frag).get("unusable", reason)
        except Exception:
            pass
        raise UnusableImagery(reason)
    desc, errs = validate_desc(code)
    tok = usage["prompt_tokens"] + usage["completion_tokens"]
    if errs:                                   # one self-repair round
        code, usage = gen_spec(imgs, code, None, "; ".join(errs[:6]), backend, model,
                               region=region, tags=_tags, exemplar=_ex,
                               brief=osm_brief)
        desc, errs = validate_desc(code)
        tok += usage["prompt_tokens"] + usage["completion_tokens"]
    if errs or desc is None:
        raise RuntimeError("invalid spec after repair: " + "; ".join(errs[:4]))
    # contracts: OSM footprint + no per-building plinth in a shared scene
    desc["footprint"] = [round(L, 1), round(W, 1)]
    desc["plinth"] = False
    return desc, tok


class UnusableImagery(RuntimeError):
    """The agent judged the imagery does not clearly show this building."""


def fallback_spec(m):
    """Deterministic dressed shell for buildings the agent cannot ground in imagery
    (tiny footprint / no outdoor pano / unusable views / agent failed): brick masonry
    walls + dark valley roof via the terrace kit, floors from OSM height. Zero-LLM --
    an honest default instead of a white LoD1 box or a hallucinated facade."""
    L, W = m["obb"][2], m["obb"][3]
    if m.get("height_src") != "default":
        floors = max(1, round(m["height"] / 3.2))
    else:
        floors = 1 if m["area_m2"] < 60 else 2
    return {"footprint": [round(L, 1), round(W, 1)], "floor_h": 3.0,
            "masses": [{"x": [0, 1], "y": [0, 1], "floors": floors,
                        "facade": "masonry", "wall": "brick"}],
            "terrace": {"roof_form": "valley", "roof_tone": "dark"},
            "plinth": False}


def front_rotation(m, pano_latlng, anchor):
    """Rotation (rad) so local +x runs along the OBB long axis and local -y (the
    front facade) faces the street-view panorama."""
    cx, cy, _L, _W, ang = m["obb"]
    if not pano_latlng:
        return ang
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0
    px = (pano_latlng[1] - anchor["lon0"]) * kx
    py = (pano_latlng[0] - anchor["lat0"]) * ky
    vx, vy = px - cx, py - cy
    for th in (ang, ang + math.pi):
        if math.sin(th) * vx - math.cos(th) * vy > 0:   # local -y . v > 0
            return th
    return ang


# ---------------------------------------------------------------- assembly
AGENT_CHUNK = r'''
exec(_COMPONENTS_SRC)
ensure_materials()      # polygon_terrace is called directly (not via assemble())
import json as _json
import mathutils as _mu
for _b in _json.loads(%r):
    if _b.get("poly"):
        # true-footprint terrace (already in scene coords -- no transform)
        _objs = polygon_terrace({"pts": _b["poly"], "floors": _b["floors"],
                                 "floor_h": _b["floor_h"], "wall": _b["wall"],
                                 "roof_tone": _b.get("roof_tone", "dark"),
                                 "roof_form": _b.get("roof_form", "valley"),
                                 # library-learning knobs were silently dropped
                                 # here while the refine render (poly_params)
                                 # showed them -- the 07-14 poly-gap defect
                                 "dormers": _b.get("dormers", False),
                                 "shopfront": _b.get("shopfront", False),
                                 # per-edge parade layer (scene/shops.py)
                                 "shop_edges": _b.get("shop_edges"),
                                 "podium_floors": _b.get("podium_floors", 0),
                                 "fins": _b.get("fins"),
                                 "colonnade": _b.get("colonnade"),
                                 "balustrade": _b.get("balustrade", False),
                                 "arch": _b.get("arch", False),
                                 "arch_row": _b.get("arch_row", 0),
                                 "ribbon": _b.get("ribbon"),
                                 "giant": _b.get("giant"),
                                 "holes": _b.get("holes"),
                                 "sat_parts": _b.get("sat_parts"),
                                 "roof_spec": _b.get("roof_spec"),
                                 "obb_frame": _b.get("obb_frame"),
                                 "front_edges": _b.get("front_edges"),
                                 "colors": _b.get("colors")},
                                _b["id"])
        _M = None
        if _b.get("extra_parts_frame"):
            _f = _b['extra_parts_frame']
            _E = (_mu.Matrix.Translation((_f['cx'], _f['cy'], 0))
                  @ _mu.Matrix.Rotation(_f['rotation_rad'], 4, 'Z'))
            for _part in _b.get('framed_extra_parts') or []:
                _new = BUILDERS[_part['type']](_part, _b['id'])
                for _obj in _new: _obj.matrix_world = _E @ _obj.matrix_world
                _objs.extend(_new)
    else:
        _objs = build_building(_b["desc"])
        # pose about the WORLD origin: geometry is built around (0,0) but the joined
        # object's origin lands on its first part's centre (a wall at z=H/2) -- setting
        # .location directly dragged every building down by half its height
        _M = (_mu.Matrix.Translation((_b["cx"], _b["cy"], 0))
              @ _mu.Matrix.Rotation(_b["rot"], 4, 'Z'))
    for _o in bpy.context.selected_objects:
        _o.select_set(False)
    _ok = [o for o in _objs if o and o.name in bpy.context.scene.objects]
    for _o in _ok:
        _o.select_set(True)
    if _ok:
        bpy.context.view_layer.objects.active = _ok[0]
        bpy.ops.object.join()
        _j = bpy.context.view_layer.objects.active
        _j.name = "Agent_%%d" %% _b["id"]
        if _M is not None:
            _j.matrix_world = _M @ _j.matrix_world
'''

CITY_STREET = r'''
tgt.location = (%f, %f, 7)
cam.location = (%f, %f, 2.5); cam.data.lens = 35
'''

# per-building photo-derived textures (texture_assets.py): replace the shared
# brick/stucco/slate materials on each joined Agent_<id> object with per-building
# image-textured copies. OBJECT-coordinate BOX projection at true metric scale --
# no UV unwrap, geometry untouched, materials stay swappable.
AGENT_TEXTURES = r'''
import bpy, os as _to, json as _tjson
_TEX_SCALE = {"brick": (1.2, 0.9), "stucco": (1.6, 0.8), "slate": (6.0, 0.85)}

def _tex_mat(bid, ch, path):
    name = "%%s_%%d" %% (ch, bid)
    m = bpy.data.materials.get(name)
    if m: return m
    metres, rough = _TEX_SCALE[ch]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.projection = 'BOX'; tex.projection_blend = 0.25
    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.inputs["Scale"].default_value = (1.0/metres, 1.0/metres, 1.0/metres)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Object"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m

_CH_OF = {"brick": "brick", "stucco": "stucco", "slate_dark": "slate", "slate": "slate"}
for _e in _tjson.loads(%r):
    _ob = bpy.data.objects.get("Agent_%%d" %% _e["id"])
    if not _ob or _ob.type != 'MESH':
        continue
    for _sl in _ob.material_slots:
        _base = (_sl.material.name.split(".")[0] if _sl.material else "")
        _ch = _CH_OF.get(_base)
        if not _ch:
            continue
        _p = _to.path.join(_e["dir"], _ch + ".png")
        if _to.path.exists(_p):
            _sl.material = _tex_mat(_e["id"], _ch, _p)
'''

# appearance-channel eval (research pass §Q item 3): retexture the shared kit
# materials from the building's own extracted tiles -- used ONLY for the final
# textured eval render, never inside the judge loop (colored renders hide geometry
# defects from VLM judges, §P)
TEX_OVERRIDE = r'''
import bpy, os as _xo
_XT = %r
def _xtex(matname, fname, metres, rough=0.9):
    m = bpy.data.materials.get(matname)
    p = _xo.path.join(_XT, fname)
    if not m or not _xo.path.exists(p):
        return
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(p, check_existing=True)
    tex.projection = 'BOX'; tex.projection_blend = 0.25
    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.inputs["Scale"].default_value = (1.0/metres, 1.0/metres, 1.0/metres)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Object"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
_xtex("brick", "brick.png", 1.2)
_xtex("stucco", "stucco.png", 1.6, 0.8)
_xtex("slate_dark", "slate.png", 6.0, 0.85)
'''

# non-building scene layer (scene/assets.py): trees at DeepForest-detected satellite
# positions + OSM roads as flat ribbons. Runs after BUILD_SCENE in the same exec, so
# _mat() is in scope. Low-poly by construction: one shared trunk/canopy mesh pair,
# per-tree objects only carry location/scale, so the whole layer stays lightweight.
SCENE_ASSETS = r'''
import bpy, math, json as _sa_json, mathutils as _sa_mu
_SA = _sa_json.loads(%r)
M_ASPH = _mat("asphalt", (0.16, 0.16, 0.17), rough=0.95)
M_PATH = _mat("pathway", (0.44, 0.42, 0.39), rough=0.95)
M_TRUNK = _mat("trunk", (0.22, 0.16, 0.11))
M_LEAF = _mat("leaf", (0.20, 0.34, 0.15))

# realism pass (2026-07-26): procedural surface detail on the big flat colour
# fields -- asphalt mottle, paving flags, grass mottle, ground dirt. Object
# coordinates so every ribbon/polygon sharing the material lines up.
def _noise_into(mat, c1, c2, scale, rough_lo=None, rough_hi=None):
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs["A"].default_value = (*c1, 1)
    mix.inputs["B"].default_value = (*c2, 1)
    nt.links.new(nz.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    if rough_lo is not None:
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough_lo
        mr.inputs["To Max"].default_value = rough_hi
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])

_noise_into(M_ASPH, (0.115, 0.115, 0.125), (0.165, 0.165, 0.175), 0.45, 0.82, 0.98)
def _flag_mat(mat):
    """pavement: ~1.2 m paving flags via a brick texture + wear noise."""
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 0.8
    br.inputs["Color1"].default_value = (0.45, 0.435, 0.40, 1)
    br.inputs["Color2"].default_value = (0.40, 0.385, 0.355, 1)
    br.inputs["Mortar"].default_value = (0.28, 0.27, 0.255, 1)
    br.inputs["Mortar Size"].default_value = 0.012
    br.squash = 1.0
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.3
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(br.outputs["Color"], mix.inputs["A"])
    nt.links.new(nz.outputs["Color"], mix.inputs["B"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = 'RGBA'
    mix2.inputs["Factor"].default_value = 0.18
    nt.links.new(br.outputs["Color"], mix2.inputs["A"])
    nt.links.new(mix.outputs["Result"], mix2.inputs["B"])
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
_flag_mat(M_PATH)
_FOOT = {"footway", "path", "cycleway", "pedestrian", "living_street"}

M_LINE = _mat("roadline", (0.85, 0.84, 0.80), rough=0.7)

def _ribbon(pts, w, mat, name, z=0.02, off=0.0):
    n = len(pts)
    dirs = []
    for i in range(n):
        a = _sa_mu.Vector(pts[max(0, i - 1)]); b = _sa_mu.Vector(pts[min(n - 1, i + 1)])
        d = (b - a)
        dirs.append(d.normalized() if d.length > 1e-6 else _sa_mu.Vector((1, 0)))
    verts, faces = [], []
    for i, (p, d) in enumerate(zip(pts, dirs)):
        nx, ny = -d.y, d.x
        cxx, cyy = p[0] + nx * off, p[1] + ny * off
        verts += [(cxx + nx * w / 2, cyy + ny * w / 2, z),
                  (cxx - nx * w / 2, cyy - ny * w / 2, z)]
        if i:
            k = 2 * i
            faces.append((k - 2, k - 1, k + 1, k))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob

# junction clipping (07-28 feedback: "streets unclear"): pavements, centre
# lines and footways used to draw FULL-LENGTH through every junction, so raised
# pavement bands and lines lay on top of the crossing carriageway. Anything but
# the asphalt itself now stops at another drivable ribbon. Same-street
# continuations (one road split into several OSM ways) are excluded by bearing
# -- under ~35 deg is a continuation, not a junction -- or every way joint
# would open a gap.
_DSEGS = []
for _r in _SA.get("roads", []):
    if _r["class"] not in _FOOT:
        for _si in range(len(_r["pts"]) - 1):
            _DSEGS.append((_r["id"], _r["pts"][_si], _r["pts"][_si + 1],
                           _r["width"]))

def _road_block(x, y, ang, own_id, pad):
    for _oid, (_x1, _y1), (_x2, _y2), _w in _DSEGS:
        if _oid == own_id:
            continue
        _dx, _dy = _x2 - _x1, _y2 - _y1
        _ll = _dx * _dx + _dy * _dy
        if _ll < 1e-9:
            continue
        _da = abs((math.atan2(_dy, _dx) - ang + math.pi / 2) %% math.pi
                  - math.pi / 2)
        if _da < 0.6:
            continue
        _t = max(0.0, min(1.0, ((x - _x1) * _dx + (y - _y1) * _dy) / _ll))
        if ((x - (_x1 + _t * _dx)) ** 2
                + (y - (_y1 + _t * _dy)) ** 2) < (_w / 2 + pad) ** 2:
            return True
    return False

def _offset_path(pts, off):
    if abs(off) < 1e-9:
        return [tuple(p) for p in pts]
    n = len(pts); out = []
    for i in range(n):
        a = _sa_mu.Vector(pts[max(0, i - 1)]); b = _sa_mu.Vector(pts[min(n - 1, i + 1)])
        d = b - a
        d = d.normalized() if d.length > 1e-6 else _sa_mu.Vector((1, 0))
        out.append((pts[i][0] - d.y * off, pts[i][1] + d.x * off))
    return out

def _resample_dir(pts, step=1.5):
    out = []
    for i in range(len(pts) - 1):
        (_x1, _y1), (_x2, _y2) = pts[i], pts[i + 1]
        _L = math.hypot(_x2 - _x1, _y2 - _y1)
        if _L < 1e-6:
            continue
        _a = math.atan2(_y2 - _y1, _x2 - _x1)
        _k = max(1, int(_L / step))
        for _j in range(0 if i == 0 else 1, _k + 1):
            out.append((_x1 + (_x2 - _x1) * _j / _k,
                        _y1 + (_y2 - _y1) * _j / _k, _a))
    return out

def _clipped_ribbon(pts, w, mat, name, z, off, own_id, pad):
    run, ri = [], 0
    for _s in _resample_dir(_offset_path(pts, off)) + [None]:
        if _s is not None and not _road_block(_s[0], _s[1], _s[2], own_id, pad):
            run.append((_s[0], _s[1]))
            continue
        if len(run) >= 2:
            _ribbon(run, w, mat, "%%s_c%%d" %% (name, ri), z=z); ri += 1
        run = []

# roads v2 (07-14 meeting: "improve the road visualisation"): drivable roads get
# flanking raised PAVEMENTS (kerb reads as the height step) and main roads a
# centre line; footways stay single light ribbons
for _r in _SA.get("roads", []):
    if _r["class"] in _FOOT:
        _clipped_ribbon(_r["pts"], _r["width"], M_PATH, "Road_%%d" %% _r["id"],
                        0.03, 0.0, _r["id"], _r["width"] / 2)
        continue
    _ribbon(_r["pts"], _r["width"], M_ASPH, "Road_%%d" %% _r["id"])
    _pw = 2.0 if _r["width"] >= 6.0 else 1.4
    for _sfx, _sgn in (("L", 1.0), ("R", -1.0)):
        _clipped_ribbon(_r["pts"], _pw, M_PATH, "Pave%%s_%%d" %% (_sfx, _r["id"]),
                        0.045, _sgn * (_r["width"] / 2 + _pw / 2), _r["id"],
                        _pw / 2 - 0.1)
    if _r["class"] in ("trunk", "primary", "primary_link", "secondary",
                       "tertiary"):
        _clipped_ribbon(_r["pts"], 0.15, M_LINE, "Line_%%d" %% _r["id"],
                        0.028, 0.0, _r["id"], 0.4)

# traffic semantics made visible (07-28 supervisor request): direction arrows
# per travel direction (UK keep-left placement) + lane-divider dashes on multi-
# lane carriageways, all computed from the directed road graph (road_graph.py).
# One shared chevron mesh; per-arrow objects only place/rotate it.
_TRF = _SA.get("traffic") or {}
_me_arrow = bpy.data.meshes.get("_traffic_arrow")
if _me_arrow is None:
    _me_arrow = bpy.data.meshes.new("_traffic_arrow")
    _me_arrow.from_pydata(
        [(1.1, 0.0, 0), (-1.1, 0.55, 0), (-0.5, 0.0, 0), (-1.1, -0.55, 0)],
        [], [(0, 1, 2), (0, 2, 3)])
    _me_arrow.materials.append(M_LINE)
elif not _me_arrow.materials or _me_arrow.materials[0] is not M_LINE:
    _me_arrow.materials.clear(); _me_arrow.materials.append(M_LINE)
for _i, _a in enumerate(_TRF.get("arrows", [])):
    _ob = bpy.data.objects.new("Arrow_%%d" %% _i, _me_arrow)
    _ob.location = (_a["x"], _a["y"], 0.027)
    _ob.rotation_euler = (0, 0, _a["ang"])
    bpy.context.scene.collection.objects.link(_ob)
_me_dash = bpy.data.meshes.get("_traffic_dash")
if _me_dash is None:
    _me_dash = bpy.data.meshes.new("_traffic_dash")
    _me_dash.from_pydata(
        [(-0.7, -0.06, 0), (0.7, -0.06, 0), (0.7, 0.06, 0), (-0.7, 0.06, 0)],
        [], [(0, 1, 2, 3)])
    _me_dash.materials.append(M_LINE)
elif not _me_dash.materials or _me_dash.materials[0] is not M_LINE:
    _me_dash.materials.clear(); _me_dash.materials.append(M_LINE)
for _i, _d in enumerate(_TRF.get("dashes", [])):
    _ob = bpy.data.objects.new("Dash_%%d" %% _i, _me_dash)
    _ob.location = (_d["x"], _d["y"], 0.026)
    _ob.rotation_euler = (0, 0, _d["ang"])
    bpy.context.scene.collection.objects.link(_ob)

# green infrastructure (2026-07-26, supervisor ask): OSM parks/lawns/gardens as
# grass polygons UNDER the road layer (z=0.012 < road 0.02), hedge ways as
# extruded green ribbons. Two grass tones so adjacent lawns don't merge visually.
M_GRASS = _mat("grass", (0.24, 0.36, 0.16), rough=1.0)
M_GRASS2 = _mat("grass2", (0.29, 0.41, 0.19), rough=1.0)
M_HEDGE = _mat("hedge", (0.15, 0.27, 0.11), rough=1.0)
_noise_into(M_GRASS, (0.16, 0.27, 0.10), (0.28, 0.38, 0.15), 6.0)
_noise_into(M_GRASS2, (0.20, 0.31, 0.12), (0.32, 0.42, 0.17), 6.0)
_mg = bpy.data.materials.get("ground")
if _mg:
    _noise_into(_mg, (0.30, 0.31, 0.29), (0.40, 0.40, 0.37), 0.25)
# water plane: dock basins / rivers sit just under the grass layer, dark and
# lightly mirrored so towers reflect (the whole look of a waterfront block)
M_WATER = _mat("water", (0.030, 0.055, 0.075), rough=0.06)
M_WATER.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.35
from mathutils.geometry import tessellate_polygon as _sa_tess
for _gi, _g in enumerate(_SA.get("green", [])):
    try:
        _tris = _sa_tess([[_sa_mu.Vector((p[0], p[1])) for p in _g["pts"]]])
    except Exception:
        continue
    if not _tris:
        continue
    _wat = _g.get("kind") == "water"
    _me = bpy.data.meshes.new("Green_%%d" %% _g["id"])
    _me.from_pydata([(p[0], p[1], 0.008 if _wat else 0.012)
                     for p in _g["pts"]], [], list(_tris))
    _ob = bpy.data.objects.new("Green_%%d" %% _g["id"], _me)
    bpy.context.scene.collection.objects.link(_ob)
    _me.materials.append(M_WATER if _wat else (M_GRASS if _gi %% 2 else M_GRASS2))

_hv = [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0),
       (-0.5, -0.5, 1), (0.5, -0.5, 1), (0.5, 0.5, 1), (-0.5, 0.5, 1)]
_hf = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 1, 5, 4), (1, 2, 6, 5),
       (2, 3, 7, 6), (3, 0, 4, 7)]
_me_hedge = bpy.data.meshes.new("hedge_seg"); _me_hedge.from_pydata(_hv, [], _hf)
_me_hedge.materials.append(M_HEDGE)
for _h in _SA.get("hedges", []):
    _hp = _h["pts"]
    for _si in range(len(_hp) - 1):
        (_x1, _y1), (_x2, _y2) = _hp[_si], _hp[_si + 1]
        _sl = math.hypot(_x2 - _x1, _y2 - _y1)
        if _sl < 0.3:
            continue
        _hb = bpy.data.objects.new("Hedge_%%d_%%d" %% (_h["id"], _si), _me_hedge)
        _hb.location = ((_x1 + _x2) / 2, (_y1 + _y2) / 2, 0.0)
        _hb.scale = (_sl + 0.4, 0.75, 1.3)
        _hb.rotation_euler = (0, 0, math.atan2(_y2 - _y1, _x2 - _x1))
        bpy.context.scene.collection.objects.link(_hb)

# street furniture (2026-07-26 ask: traffic lights, railings, road furniture): OSM-positioned
# traffic signals, zebra crossings (oriented to the nearest carriageway), bus
# stops, K2 phone boxes, pillar post boxes, bollards, railings and garden
# walls. Shared template meshes, per-item objects only place/rotate them.
_FURN = _SA.get("furniture") or {}
M_POLE = _mat("pole", (0.07, 0.07, 0.08), rough=0.6)
M_SRED = _mat("sig_red", (0.75, 0.04, 0.04))
M_SAMB = _mat("sig_amber", (0.78, 0.48, 0.04))
M_SGRN = _mat("sig_green", (0.05, 0.55, 0.10))
M_KRED = _mat("k2_red", (0.42, 0.02, 0.03), rough=0.55)
M_GWALL = _mat("garden_wall", (0.19, 0.15, 0.12))

def _box_at(nm, mat, sx, sy, sz, x, y, z, ang=0.0):
    me = bpy.data.meshes.get("_fb_" + mat.name)   # one unit cube per material
    if me is None:
        me = bpy.data.meshes.new("_fb_" + mat.name)
        v = [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0),
             (-0.5, -0.5, 1), (0.5, -0.5, 1), (0.5, 0.5, 1), (-0.5, 0.5, 1)]
        f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
        me.from_pydata(v, [], f)
        me.materials.append(mat)
    elif not me.materials or me.materials[0] is not mat:
        # a mesh surviving from the previous assembly still points at the
        # DELETED material generation -- rebind or it renders default white
        me.materials.clear()
        me.materials.append(mat)
    ob = bpy.data.objects.new(nm, me)
    ob.location = (x, y, z); ob.scale = (sx, sy, sz)
    ob.rotation_euler = (0, 0, ang)
    bpy.context.scene.collection.objects.link(ob)
    return ob

for _i, _s in enumerate(_FURN.get("signals", [])):
    _box_at("Sig_%%d_p" %% _i, M_POLE, 0.09, 0.09, 3.0, _s["x"], _s["y"], 0)
    _box_at("Sig_%%d_h" %% _i, M_POLE, 0.30, 0.24, 0.85, _s["x"], _s["y"], 2.35)
    for _k, _m in ((0, M_SRED), (1, M_SAMB), (2, M_SGRN)):
        _box_at("Sig_%%d_l%%d" %% (_i, _k), _m, 0.13, 0.13, 0.14,
                _s["x"], _s["y"] - 0.13, 2.98 - _k * 0.24)
for _i, _c in enumerate(_FURN.get("crossings", [])):
    _wd = _c["w"] * 0.92
    for _k in range(6):
        _t = (_k - 2.5) * 0.85
        _box_at("Zeb_%%d_%%d" %% (_i, _k), M_LINE, 0.45, _wd, 0.012,
                _c["x"] + math.cos(_c["ang"]) * _t,
                _c["y"] + math.sin(_c["ang"]) * _t, 0.022, _c["ang"])
M_SHGLASS = _mat("shelter_glass", (0.55, 0.62, 0.66), rough=0.15)
for _i, _b in enumerate(_FURN.get("bus_stops", [])):
    _ba = _b.get("ang", 0.0)
    _ax, _ay = math.cos(_ba), math.sin(_ba)          # along the road
    # flag pole 2.4 m down-road of the shelter centre: pole + red flag + white bar
    _fx, _fy = _b["x"] + _ax * 2.9, _b["y"] + _ay * 2.9
    _box_at("Bus_%%d_p" %% _i, M_POLE, 0.08, 0.08, 3.0, _fx, _fy, 0)
    _box_at("Bus_%%d_f" %% _i, M_KRED, 0.46, 0.07, 0.34, _fx, _fy, 2.55, _ba)
    _box_at("Bus_%%d_w" %% _i, M_LINE, 0.48, 0.08, 0.09, _fx, _fy, 2.66, _ba)
    # TfL-style shelter: flat roof on four posts, glazed back + ends, bench
    _box_at("Bus_%%d_r" %% _i, M_POLE, 4.3, 1.5, 0.09, _b["x"], _b["y"], 2.35, _ba)
    for _dx, _dy in ((-2.0, -0.65), (2.0, -0.65), (-2.0, 0.65), (2.0, 0.65)):
        _px_ = _b["x"] + _ax * _dx - math.sin(_ba) * _dy
        _py_ = _b["y"] + _ay * _dx + math.cos(_ba) * _dy
        _box_at("Bus_%%d_c" %% _i, M_POLE, 0.07, 0.07, 2.35, _px_, _py_, 0)
    _bx_ = _b["x"] - math.sin(_ba) * 0.68; _by_ = _b["y"] + math.cos(_ba) * 0.68
    _box_at("Bus_%%d_b" %% _i, M_SHGLASS, 4.1, 0.04, 1.85, _bx_, _by_, 0.35, _ba)
    for _dx in (-2.0, 2.0):
        _ex = _b["x"] + _ax * _dx; _ey = _b["y"] + _ay * _dx
        _box_at("Bus_%%d_e" %% _i, M_SHGLASS, 0.04, 1.3, 1.85, _ex, _ey, 0.35, _ba)
    _box_at("Bus_%%d_s" %% _i, M_POLE, 3.0, 0.35, 0.45,
            _b["x"] - math.sin(_ba) * 0.35, _b["y"] + math.cos(_ba) * 0.35, 0, _ba)
for _i, _p in enumerate(_FURN.get("phones", [])):
    _box_at("K2_%%d" %% _i, M_KRED, 1.0, 1.0, 2.5, _p["x"], _p["y"], 0)
    _box_at("K2_%%d_c" %% _i, M_KRED, 1.08, 1.08, 0.22, _p["x"], _p["y"], 2.5)
for _i, _p in enumerate(_FURN.get("posts", [])):
    _box_at("Post_%%d" %% _i, M_KRED, 0.42, 0.42, 1.05, _p["x"], _p["y"], 0)
    _box_at("Post_%%d_c" %% _i, M_POLE, 0.46, 0.46, 0.08, _p["x"], _p["y"], 1.05)
for _i, _p in enumerate(_FURN.get("bollards", [])):
    _box_at("Bol_%%d" %% _i, M_POLE, 0.16, 0.16, 0.9, _p["x"], _p["y"], 0)
for _nm, _feat, _mat_, _h, _t in (("Fence", "fences", M_POLE, 1.1, 0.06),
                                  ("GWall", "walls", M_GWALL, 1.3, 0.24)):
    for _i, _w in enumerate(_FURN.get(_feat, [])):
        _wp = _w["pts"]
        for _si in range(len(_wp) - 1):
            (_x1, _y1), (_x2, _y2) = _wp[_si], _wp[_si + 1]
            _sl = math.hypot(_x2 - _x1, _y2 - _y1)
            if _sl < 0.3:
                continue
            _box_at("%%s_%%d_%%d" %% (_nm, _i, _si), _mat_, _sl + 0.1, _t, _h,
                    (_x1 + _x2) / 2, (_y1 + _y2) / 2, 0,
                    math.atan2(_y2 - _y1, _x2 - _x1))

# TRANSPORT: DLR viaducts + dock footbridges (08-11 review: "there are bridges
# and elevated railways"). Deterministic from OSM (scene_assets.fetch_transport):
# elevated rail = deck ribbon on piers with parapets + twin rails; grade rail =
# ballast + rails; non-rail bridges = raised deck + railings over the water.
M_VIA = _mat("viaduct", (0.42, 0.41, 0.40), rough=0.85)
M_RAILS = _mat("railsteel", (0.35, 0.33, 0.31), rough=0.4)
M_BALLAST = _mat("ballast", (0.30, 0.28, 0.26), rough=1.0)
def _seg_boxes(nm, pts, w, mat, z, th, step_pier=None, pier_h=None):
    for _k in range(len(pts) - 1):
        _x1, _y1 = pts[_k]; _x2, _y2 = pts[_k + 1]
        _sl = math.hypot(_x2 - _x1, _y2 - _y1)
        if _sl < 0.5:
            continue
        _an = math.atan2(_y2 - _y1, _x2 - _x1)
        _box_at("%%s_%%d" %% (nm, _k), mat, _sl + 0.15, w, th,
                (_x1 + _x2) / 2, (_y1 + _y2) / 2, z, _an)
        if step_pier:
            _npier = max(1, int(_sl / step_pier))
            for _pk in range(_npier):
                _t = (_pk + 0.5) / _npier
                _box_at("%%sP_%%d_%%d" %% (nm, _k, _pk), M_VIA, 1.4, 2.4, pier_h,
                        _x1 + (_x2 - _x1) * _t, _y1 + (_y2 - _y1) * _t, 0.0, _an)
for _ri, _r in enumerate(_SA.get("furniture", {}).get("rails", [])):
    _pts = _r["pts"]
    if _r["bridge"]:
        _dz = 6.5                       # layer is STACKING order, not metres
        _seg_boxes("Via%%d" %% _ri, _pts, 6.0, M_VIA, _dz, 0.7,
                   step_pier=14.0, pier_h=_dz)
        for _sgn in (-1, 1):                       # parapets
            _off = []
            for _k in range(len(_pts)):
                _k2 = min(_k, len(_pts) - 2)
                _an = math.atan2(_pts[_k2 + 1][1] - _pts[_k2][1],
                                 _pts[_k2 + 1][0] - _pts[_k2][0])
                _off.append([_pts[_k][0] - math.sin(_an) * _sgn * 2.8,
                             _pts[_k][1] + math.cos(_an) * _sgn * 2.8])
            _seg_boxes("ViaPar%%d_%%d" %% (_ri, _sgn > 0), _off, 0.25, M_VIA,
                       _dz + 0.75, 0.8)
        _rz = _dz + 0.45
    else:
        _seg_boxes("Bal%%d" %% _ri, _pts, 3.6, M_BALLAST, 0.05, 0.28)
        _rz = 0.30
    for _sgn in (-1, 1):                           # twin rails
        _off = []
        for _k in range(len(_pts)):
            _k2 = min(_k, len(_pts) - 2)
            _an = math.atan2(_pts[_k2 + 1][1] - _pts[_k2][1],
                             _pts[_k2 + 1][0] - _pts[_k2][0])
            _off.append([_pts[_k][0] - math.sin(_an) * _sgn * 0.75,
                         _pts[_k][1] + math.cos(_an) * _sgn * 0.75])
        _seg_boxes("Rail%%d_%%d" %% (_ri, _sgn > 0), _off, 0.12, M_RAILS, _rz, 0.14)
for _bi, _b in enumerate(_SA.get("furniture", {}).get("bridges", [])):
    _bz = 2.4 if _b["foot"] else 1.6
    _seg_boxes("Brg%%d" %% _bi, _b["pts"], _b["width"], M_PATH, _bz, 0.35,
               step_pier=18.0, pier_h=_bz)
    for _sgn in (-1, 1):
        _off = []
        for _k in range(len(_b["pts"])):
            _k2 = min(_k, len(_b["pts"]) - 2)
            _an = math.atan2(_b["pts"][_k2 + 1][1] - _b["pts"][_k2][1],
                             _b["pts"][_k2 + 1][0] - _b["pts"][_k2][0])
            _off.append([_b["pts"][_k][0] - math.sin(_an) * _sgn * _b["width"] / 2,
                         _b["pts"][_k][1] + math.cos(_an) * _sgn * _b["width"] / 2])
        _seg_boxes("BrgR%%d_%%d" %% (_bi, _sgn > 0), _off, 0.1, M_RAILS,
                   _bz + 0.75, 0.9)

# vehicles (07-28 supervisor request): cars + buses detected in the satellite
# imagery (scene/vehicles.py: Grounding DINO on zoom-19 tiles), heading from the
# directed road graph (UK keep-left arc), body colour photo-sampled. Standard
# body dims -- the detected axis-aligned boxes carry position, not true size.
M_CGLASS = _mat("car_glass", (0.13, 0.16, 0.20), rough=0.25)
M_TIRE = _mat("car_tire", (0.05, 0.05, 0.05), rough=0.9)
# bus bodies use the SAME photo-sampled colour as cars (08-13: Paris
# buses are not London-red -- no region-specific livery may be hardcoded; the
# imagery is the only authority on appearance)
_car_mats = {}
def _car_mat(cl):
    if cl not in _car_mats:
        _car_mats[cl] = _mat("car_body_%%.2f_%%.2f_%%.2f" %% cl, cl, rough=0.35)
    return _car_mats[cl]
# animated traffic (08-11 ask: cars should move, respecting direction): the
# deterministic sim (traffic_sim.py) walks the DIRECTED graph -- keep-left lane
# offset, one-ways, turn restrictions -- and the moving cars are keyframed here;
# kerbside cars stay parked exactly where the photo has them.
_ANIM = {r["i"]: r for r in (_SA.get("anim") or {}).get("routes", [])}
_FPS = 24
if _ANIM:
    _scn = bpy.context.scene
    _scn.render.fps = _FPS
    _scn.frame_start = 1
    _scn.frame_end = int((_SA.get("anim") or {}).get("seconds", 60) * _FPS)

def _veh_anim_root(_i, _rt):
    _e = bpy.data.objects.new("VehRoot_%%d" %% _i, None)
    bpy.context.scene.collection.objects.link(_e)
    _prev = None
    for _t, _x, _y, _ang in _rt["samples"]:
        if _prev is not None:                 # unwrap so the car never spins
            while _ang - _prev > math.pi:
                _ang -= 2 * math.pi
            while _ang - _prev < -math.pi:
                _ang += 2 * math.pi
        _prev = _ang
        _e.location = (_x, _y, 0.0)
        _e.rotation_euler = (0.0, 0.0, _ang)
        _fr = 1 + int(_t * _FPS)
        _e.keyframe_insert("location", frame=_fr)
        _e.keyframe_insert("rotation_euler", frame=_fr)
    return _e

for _i, _v in enumerate(_SA.get("vehicles", [])):
    _rt = _ANIM.get(_i)
    if _rt and _rt.get("samples"):
        _root = _veh_anim_root(_i, _rt)
        # parts built in LOCAL coords, parented -- the root carries the motion
        if _v["kind"] == "bus":
            _cl = tuple(round(min(1.0, c * 1.25) / 0.15) * 0.15 for c in _v["color"])
            _pb = [("b", _car_mat(_cl), 10.9, 2.52, 3.9, 0, 0, 0.35),
                   ("g", M_CGLASS, 10.5, 2.56, 0.8, 0, 0, 2.9)]
            _wx, _wy, _ww = (-3.6, 3.6), (-1.05, 1.05), (1.0, 0.3, 0.35)
        else:
            _cl = tuple(round(min(1.0, c * 1.25) / 0.15) * 0.15 for c in _v["color"])
            _pb = [("b", _car_mat(_cl), 4.4, 1.8, 0.55, 0, 0, 0.30),
                   ("c", M_CGLASS, 2.1, 1.62, 0.42, -0.35, 0, 0.85)]
            _wx, _wy, _ww = (-1.45, 1.45), (-0.86, 0.86), (0.62, 0.22, 0.30)
        for _tag, _mt, _sx, _sy, _sz, _ox, _oy, _oz in _pb:
            _o = _box_at("VehM%%d_%%s" %% (_i, _tag), _mt, _sx, _sy, _sz,
                         _ox, _oy, _oz, 0.0)
            _o.parent = _root
        for _sx in _wx:
            for _sy in _wy:
                _o = _box_at("VehM%%d_w" %% _i, M_TIRE, _ww[0], _ww[1], _ww[2],
                             _sx, _sy, 0.0, 0.0)
                _o.parent = _root
        continue
    _va = _v["ang"]
    _ax_, _ay_ = math.cos(_va), math.sin(_va)
    if _v["kind"] == "bus":
        _cl = tuple(round(min(1.0, c * 1.25) / 0.15) * 0.15 for c in _v["color"])
        _box_at("VBus_%%d_bd" %% _i, _car_mat(_cl), 10.9, 2.52, 3.9,
                _v["x"], _v["y"], 0.35, _va)
        _box_at("VBus_%%d_gl" %% _i, M_CGLASS, 10.5, 2.56, 0.8,
                _v["x"], _v["y"], 2.9, _va)
        _wx, _wy, _ww = (-3.6, 3.6), (-1.05, 1.05), (1.0, 0.3, 0.35)
    else:
        _cl = tuple(round(min(1.0, c * 1.25) / 0.15) * 0.15 for c in _v["color"])
        _box_at("Car_%%d_b" %% _i, _car_mat(_cl), 4.4, 1.8, 0.55,
                _v["x"], _v["y"], 0.30, _va)
        _box_at("Car_%%d_c" %% _i, M_CGLASS, 2.1, 1.62, 0.42,
                _v["x"] - _ax_ * 0.35, _v["y"] - _ay_ * 0.35, 0.85, _va)
        _wx, _wy, _ww = (-1.45, 1.45), (-0.86, 0.86), (0.62, 0.22, 0.30)
    for _sx in _wx:
        for _sy in _wy:
            _box_at("Veh_%%d_w" %% _i, M_TIRE, _ww[0], _ww[1], _ww[2],
                    _v["x"] + _ax_ * _sx - _ay_ * _sy,
                    _v["y"] + _ay_ * _sx + _ax_ * _sy, 0.0, _va)

# shared template meshes; per-tree objects just place + scale them. Canopies are
# 4 pre-built VARIANTS -- a main blob + offset side blobs, all vertices noise-
# displaced radially (seeded => deterministic) -- so crowns read as irregular
# foliage clusters, not lollipop spheres. Trees cycle variants/rotation by index.
import bmesh, random, mathutils as _mu2
M_LEAF2 = _mat("leaf2", (0.26, 0.40, 0.18))
M_LEAF3 = _mat("leaf3", (0.17, 0.30, 0.11))
M_LEAF4 = _mat("leaf4", (0.30, 0.38, 0.14))
for _lm in (M_LEAF, M_LEAF2, M_LEAF3, M_LEAF4):
    _b_ = _lm.node_tree.nodes.get("Principled BSDF")
    _b_.inputs["Roughness"].default_value = 1.0

# trunk with a flare at the base and three short BRANCH stubs reaching into the
# canopy -- the single bare cone read as a lollipop stick (realism pass)
_bm = bmesh.new()
bmesh.ops.create_cone(_bm, cap_ends=True, segments=7,
                      radius1=0.55, radius2=0.28, depth=1.0,
                      matrix=_mu2.Matrix.Translation((0, 0, 0.5)))
_rngT = random.Random(7)
for _k in range(3):
    _a = _k * 2.094 + 0.5
    _tilt = _mu2.Matrix.Rotation(0.55, 4, (math.cos(_a), math.sin(_a), 0))
    _mtx = _mu2.Matrix.Translation((math.cos(_a) * 0.18, math.sin(_a) * 0.18, 0.98)) \
        @ _tilt @ _mu2.Matrix.Scale(0.5, 4, (0, 0, 1))
    bmesh.ops.create_cone(_bm, cap_ends=True, segments=5,
                          radius1=0.16, radius2=0.05, depth=1.0,
                          matrix=_mtx @ _mu2.Matrix.Translation((0, 0, 0.5)))
_me_tr = bpy.data.meshes.new("tree_trunk"); _bm.to_mesh(_me_tr); _bm.free()
_me_tr.materials.append(M_TRUNK)

def _canopy_variant(seed):
    """Irregular multi-lobe crown: a vertically-stretched main mass, side lobes
    biased UPWARD, a top lobe, strong seeded noise displacement -- reads as a
    broadleaf street tree, not a ball on a stick."""
    rng = random.Random(seed)
    bm = bmesh.new()
    blobs = [((0, 0, 0.05), 1.0)] \
        + [((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), rng.uniform(0.0, 0.5)),
            rng.uniform(0.4, 0.65)) for _ in range(rng.randint(4, 6))] \
        + [((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(0.55, 0.75)),
            rng.uniform(0.35, 0.5))]
    for (bx, by, bz), br in blobs:
        b2 = bmesh.new()
        bmesh.ops.create_icosphere(b2, subdivisions=2, radius=br)
        for v in b2.verts:
            v.co += v.co.normalized() * br * rng.uniform(-0.18, 0.22)
            v.co.z *= 1.12
            v.co.x += bx; v.co.y += by; v.co.z += bz
        tmp = bpy.data.meshes.new("_blob"); b2.to_mesh(tmp); b2.free()
        bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new("tree_canopy_%%d" %% seed)
    bm.to_mesh(me); bm.free()
    me.materials.append((M_LEAF, M_LEAF2, M_LEAF3, M_LEAF4)[seed %% 4])
    return me

_canopies = [_canopy_variant(s) for s in range(8)]
for _i, _t in enumerate(_SA.get("trees", [])):
    _r = _t["r"]
    _h = max(4.0, min(2.2 * _r, 18.0))            # plausible height from crown size
    _tr = bpy.data.objects.new("Tree_%%d_t" %% _i, _me_tr)
    _tr.location = (_t["x"], _t["y"], 0); _tr.scale = (_r * 0.16, _r * 0.16, _h * 0.62)
    _cn = bpy.data.objects.new("Tree_%%d_c" %% _i, _canopies[_i %% 8])
    _jit = 0.9 + 0.2 * ((_i * 7) %% 5) / 4.0
    _cn.location = (_t["x"], _t["y"], _h * 0.60)
    _cn.scale = (_r * _jit, _r * (2.0 - _jit), _h * 0.36)
    _cn.rotation_euler = (0, 0, (_i * 0.9) %% 6.28)
    bpy.context.scene.collection.objects.link(_tr)
    bpy.context.scene.collection.objects.link(_cn)
'''


# street-side SHOP UNITS (scene/shops.py): the ground-floor retail parade, one
# parameterised unit per business rather than the old single boolean band. Each
# unit is drawn from its own typed params (stallriser / glazing / fascia / sign /
# awning / door), against the wall of the footprint the host was actually BUILT
# on (true polygon or OBB rectangle -- shop_assets resolves that). Runs after
# BUILD_SCENE so _mat() is in scope; the host's generic `shopfront` band is
# switched off in assemble() for exactly these buildings, so nothing doubles up.
SHOP_UNITS = r'''
import bpy, math, json as _sh_json
_SHOPS = _sh_json.loads(%r)
# shop glazing: dark, only lightly mirrored. At metallic 0.45 / rough 0.06 the
# panes turned into sky mirrors and the parade read as a pale glass strip
M_SHGLASS = _mat("shop_glass", (0.028, 0.038, 0.042), rough=0.14)
M_SHGLASS.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.18
M_SHSILL = _mat("shop_stall", (0.052, 0.052, 0.055), rough=0.75)
M_SHPIER = _mat("shop_pier", (0.30, 0.29, 0.275), rough=0.72)
M_SHDOOR = _mat("shop_door", (0.035, 0.035, 0.038), rough=0.55)
_sh_mats = {}
def _sh_mat(tag, rgb, rough=0.55):
    k = (tag, tuple(round(c, 3) for c in rgb))
    if k not in _sh_mats:
        _sh_mats[k] = _mat("%%s_%%.3f_%%.3f_%%.3f" %% (tag, rgb[0], rgb[1], rgb[2]),
                           tuple(rgb), rough=rough)
    return _sh_mats[k]

def _sh_box(nm, mat, sx, sy, sz, x, y, z, ang):
    """A box of local size (along-wall, out-of-wall, up) placed at its CENTRE and
    yawed to the wall bearing. One shared unit cube per material (the scene-layer
    convention) -- a 180-unit parade stays a handful of meshes."""
    me = bpy.data.meshes.get("_sh_" + mat.name)
    if me is None:
        me = bpy.data.meshes.new("_sh_" + mat.name)
        v = [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
             (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
        f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
        me.from_pydata(v, [], f)
        me.materials.append(mat)
    elif not me.materials or me.materials[0] is not mat:
        me.materials.clear(); me.materials.append(mat)   # rebind after a scene CLEAR
    o = bpy.data.objects.new(nm, me)
    o.location = (x, y, z); o.scale = (sx, sy, sz); o.rotation_euler = (0, 0, ang)
    bpy.context.scene.collection.objects.link(o)
    return o

_sh_n = 0
for _u in _SHOPS:
    _p = _u["params"]
    _w = _p["width"]
    _ang = _u["ang"]
    _ex, _ey = math.cos(_ang), math.sin(_ang)            # along the wall
    _nx, _ny = _u["nx"], _u["ny"]                        # out of the wall
    # the built wall's outer face: polygon_terrace raises a prism ON the footprint
    # line, build_building's block carries a 0.4-thick wall whose face sits 0.2
    # outside it -- start the shopfront at the surface that actually exists
    _d0 = 0.20 if _u.get("mode") == "obb" else 0.0
    _cx, _cy = _u["x"], _u["y"]
    def _at(_along, _out):
        return (_cx + _ex * _along + _nx * (_d0 + _out),
                _cy + _ey * _along + _ny * (_d0 + _out))
    _stall, _glaz, _fasc = _p["stall_h"], _p["glaz_h"], _p["fascia_h"]
    _pier = 0.34
    _gw = max(0.6, _w - _pier)                           # glazed width between piers
    _fm = _sh_mat("shop_fascia", _p["fascia_rgb"], rough=0.42)
    # the DOOR interrupts the glazing: a shopfront is two display windows with a
    # set-back entrance between them, not one sheet of plate with a door drawn on
    # it (the first cut buried the leaf behind the glass, invisible)
    _dw = min(_p["door_w"], _gw * 0.45)
    _dt = (_p["door_t"] - 0.5) * max(0.0, _gw - _dw)
    _dz = min(_stall + _glaz - 0.15, 2.15)               # leaf height, fanlight over
    for _s, (_a, _b) in enumerate(((-_gw / 2, _dt - _dw / 2), (_dt + _dw / 2, _gw / 2))):
        _pw = _b - _a
        if _pw < 0.3:
            continue
        _mid = (_a + _b) / 2
        # stallriser: painted in the shop's own colour, as a real one is
        _x_, _y_ = _at(_mid, 0.13)
        _sh_box("Shop_%%d_st%%d" %% (_sh_n, _s), _fm, _pw, 0.26, _stall,
                _x_, _y_, _stall / 2, _ang)
        _x_, _y_ = _at(_mid, 0.09)
        _sh_box("Shop_%%d_gl%%d" %% (_sh_n, _s), M_SHGLASS, _pw, 0.14, _glaz,
                _x_, _y_, _stall + _glaz / 2, _ang)
        # slim mullions dividing the display window (a 5 m pane is not one sheet).
        # The unit's `mullions` parameter is the authority -- shared out between
        # the two panels by width, so editing it in shops.json actually changes
        # the model (a parameter the renderer ignored would be a false claim of
        # editability)
        _nm_ = int(round(_p["mullions"] * _pw / max(0.1, _gw - _dw)))
        for _m in range(max(0, _nm_)):
            _t = _a + _pw * (_m + 1) / (_nm_ + 1)
            _x_, _y_ = _at(_t, 0.13)
            _sh_box("Shop_%%d_mu%%d_%%d" %% (_sh_n, _s, _m), M_SHPIER, 0.07, 0.16,
                    _glaz, _x_, _y_, _stall + _glaz / 2, _ang)
    # entrance: leaf set back from the glazing line, fanlight above it
    _x_, _y_ = _at(_dt, max(0.02, 0.09 - _p["recess"]))
    _sh_box("Shop_%%d_dr" %% _sh_n, M_SHDOOR, _dw, 0.08, _dz, _x_, _y_, _dz / 2, _ang)
    _x_, _y_ = _at(_dt, 0.09)
    _sh_box("Shop_%%d_fl" %% _sh_n, M_SHGLASS, _dw, 0.12,
            max(0.05, _stall + _glaz - _dz), _x_, _y_,
            (_dz + _stall + _glaz) / 2, _ang)
    # flanking piers (the party walls between neighbouring units)
    for _s in (-0.5, 0.5):
        _x_, _y_ = _at(_s * (_w - _pier / 2), 0.15)
        _sh_box("Shop_%%d_pr%%d" %% (_sh_n, _s > 0), M_SHPIER, _pier, 0.30,
                _stall + _glaz + _fasc, _x_, _y_, (_stall + _glaz + _fasc) / 2, _ang)
    # fascia board + painted lettering
    _fz = _stall + _glaz + _fasc / 2
    _x_, _y_ = _at(0.0, 0.17)
    _sh_box("Shop_%%d_fa" %% _sh_n, _fm, _w, 0.34, _fasc, _x_, _y_, _fz, _ang)
    if _p["sign_text"]:
        _txt = bpy.data.curves.new("ShopSign_%%d" %% _sh_n, type='FONT')
        _txt.body = _p["sign_text"]
        _txt.align_x = 'CENTER'; _txt.align_y = 'CENTER'
        _txt.extrude = 0.006; _txt.resolution_u = 2
        # size WITHOUT a depsgraph round-trip: the default font averages ~0.55 em
        # per glyph, so fit on character count and cap on the fascia height (180
        # dimension queries would each force a scene update)
        _sz = min(_fasc * 0.58, (_w - _pier - 0.3) / max(1, len(_p["sign_text"])) / 0.55)
        _txt.size = max(0.10, _sz)
        _to = bpy.data.objects.new("ShopSign_%%d" %% _sh_n, _txt)
        _x_, _y_ = _at(0.0, 0.35)
        _to.location = (_x_, _y_, _fz)
        # stand the glyph plane up and turn its face along the outward normal
        _to.rotation_euler = (math.pi / 2, 0, math.atan2(_nx, -_ny))
        _txt.materials.append(_sh_mat("shop_sign", _p["sign_rgb"], rough=0.5))
        bpy.context.scene.collection.objects.link(_to)
    if _p["awning"]:
        # a straight canvas awning sloping down from just under the fascia
        _pj = _p["awning_proj"]
        _am = _sh_mat("shop_awning", _p["awning_rgb"], rough=0.85)
        _x_, _y_ = _at(0.0, 0.20 + _pj / 2)
        _sh_box("Shop_%%d_aw" %% _sh_n, _am, _w - 0.2, _pj, 0.05,
                _x_, _y_, _stall + _glaz - 0.10, _ang)
        _x_, _y_ = _at(0.0, 0.20 + _pj)
        _sh_box("Shop_%%d_awv" %% _sh_n, _am, _w - 0.2, 0.04, 0.26,
                _x_, _y_, _stall + _glaz - 0.30, _ang)     # valance
    _sh_n += 1
print("[shops] %%d units built" %% _sh_n)
'''


VIEWPORT_SYNC = r"""
import bpy as _cg_bpy
# VIEWPORT display sync (08-11: no colour showed in the Blender viewport):
# SOLID shading shows material.diffuse_color, which the pipeline never set --
# the scene rendered coloured but opened GREY. Copy every Principled base
# colour to the viewport display colour. Display-layer fix only; every
# APPEARANCE value stays agent/photo-decided (direction decision 08-11: material
# looks are the agent's call, not the orchestrator's).
for _vm in _cg_bpy.data.materials:
    if not _vm.use_nodes:
        continue
    _vb = _vm.node_tree.nodes.get("Principled BSDF")
    if _vb is None:
        continue
    _c = _vb.inputs["Base Color"].default_value
    _vm.diffuse_color = (_c[0], _c[1], _c[2], 1.0)
print("[viewport] display colours synced")
"""


VESSEL_BUILD = r'''
import bpy, json as _vs_json, math as _vs_math
# floating VESSELS (Canary Wharf, 08-10): OSM maps moored boats/barges as
# building=yes (the barge church, Hawksmoor, yachts). Extruding them as houses
# put 11 m white boxes in the dock -- build hull + cabin at water level instead.
# Self-contained (no _box_at: that helper lives in the SCENE_ASSETS template,
# which runs later and is skipped entirely when Overpass is down).
_vsm_h = _mat("vessel_hull", (0.10, 0.10, 0.115))
_vsm_c = _mat("vessel_cabin", (0.78, 0.78, 0.76))
def _vs_box(nm, mat, sx, sy, sz, x, y, z, ang):
    v = [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0),
         (-.5, -.5, 1), (.5, -.5, 1), (.5, .5, 1), (-.5, .5, 1)]
    f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(nm); me.from_pydata(v, [], f)
    me.materials.append(mat)
    o = bpy.data.objects.new(nm, me)
    o.location = (x, y, z); o.scale = (sx, sy, sz)
    o.rotation_euler = (0, 0, ang)
    bpy.context.scene.collection.objects.link(o)
_vs = _vs_json.loads(%r)
for _v in _vs:
    _hl, _hw = _v["L"], min(_v["W"], _v["L"] * 0.45)
    _hh = min(2.0, 0.35 * _v["h"] + 0.9)
    _vs_box("Vessel_%%d_h" %% _v["id"], _vsm_h, _hl, _hw, _hh,
            _v["cx"], _v["cy"], 0.05, _v["ang"])
    _ch = min(2.6, max(1.4, _v["h"] - _hh))
    _vs_box("Vessel_%%d_c" %% _v["id"], _vsm_c, _hl * 0.55, _hw * 0.8, _ch,
            _v["cx"], _v["cy"], 0.05 + _hh, _v["ang"])
print("[vessels] %%d floating structures" %% len(_vs))
'''


CANOPY_BUILD = r'''
import bpy, json, mathutils as _cmu
# building=roof (2026-07-27: the station concourse is open in the middle): OSM tags these as a ROOF
# with nothing underneath (station platform canopies, covered ways). Build them
# as an open canopy -- a flat roof slab on thin perimeter columns -- NOT a solid
# extruded mass. M_R (roof) + M_B (structure) already exist from BUILD_SCENE.
for _c in json.loads(%r):
    _pts = _c["pts"]; _h = max(2.6, _c["height"]); _n = len(_pts)
    _th = 0.35
    _v = [(x, y, _h - _th) for x, y in _pts] + [(x, y, _h) for x, y in _pts]
    _f = [tuple(range(_n))[::-1], tuple(range(_n, 2 * _n))]
    _f += [(i, (i + 1) %% _n, _n + (i + 1) %% _n, _n + i) for i in range(_n)]
    _me = bpy.data.meshes.new("canopy%%d" %% _c["id"]); _me.from_pydata(_v, [], _f)
    _ob = bpy.data.objects.new("Canopy_%%d" %% _c["id"], _me)
    bpy.context.scene.collection.objects.link(_ob); _ob.data.materials.append(M_R)
    for _k in range(_n):                              # a column at each vertex
        _x, _y = _pts[_k]
        _cm = bpy.data.meshes.get("_cancol")
        if _cm is None:
            _cm = bpy.data.meshes.new("_cancol")
            _cv = [(-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0),
                   (-.5,-.5,1),(.5,-.5,1),(.5,.5,1),(-.5,.5,1)]
            _cf = [(0,1,2,3),(7,6,5,4),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
            _cm.from_pydata(_cv, [], _cf); _cm.materials.append(M_B)
        elif not _cm.materials or _cm.materials[0] is not M_B:
            # a mesh surviving the scene CLEAR still points at the DELETED
            # material generation (the 08-04 _box_at defect class) -- rebind, or
            # the columns render unbound. Found by render_regress's first run.
            _cm.materials.clear(); _cm.materials.append(M_B)
        _col = bpy.data.objects.new("CanCol_%%d_%%d" %% (_c["id"], _k), _cm)
        _col.location = (_x, _y, 0); _col.scale = (0.28, 0.28, _h - _th)
        bpy.context.scene.collection.objects.link(_col)
'''


STATION_BUILD = r'''
import bpy, math, json, mathutils as _smu
# train_station (2026-07-27: the agent should tell a station from its real form,
# not extrude it solid): the footprint's OWN street view lands INSIDE it and shows
# an OPEN glazed train-shed on iron columns (platforms below). Build that: a glazed
# gable roof over two rows of columns, OPEN underneath -- not a solid mass. The
# footprint is confirmed a station by OSM building=train_station AND by geocoding
# the station name onto this polygon (two independent sources agree).
_SGL = bpy.data.materials.get("station_glass") or bpy.data.materials.new("station_glass")
_SGL.use_nodes = True
_b = _SGL.node_tree.nodes.get("Principled BSDF")
_b.inputs["Base Color"].default_value = (0.62, 0.70, 0.72, 1)
_b.inputs["Roughness"].default_value = 0.12
try: _b.inputs["Transmission Weight"].default_value = 0.35
except Exception: pass
_SIR = bpy.data.materials.get("station_iron") or bpy.data.materials.new("station_iron")
_SIR.use_nodes = True
_SIR.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.10, 0.26, 0.15, 1)
for _s in json.loads(%r):
    cx, cy, L, W, ang = _s["cx"], _s["cy"], _s["L"], _s["W"], _s["ang"]
    He = max(5.0, _s["height"]); Hr = He + W * 0.18
    V, F, MI = [], [], []
    def _addbox(x0, y0, z0, dx, dy, dz, mi):
        i = len(V)
        V.extend([(x0-dx/2, y0-dy/2, z0), (x0+dx/2, y0-dy/2, z0),
                  (x0+dx/2, y0+dy/2, z0), (x0-dx/2, y0+dy/2, z0),
                  (x0-dx/2, y0-dy/2, z0+dz), (x0+dx/2, y0-dy/2, z0+dz),
                  (x0+dx/2, y0+dy/2, z0+dz), (x0-dx/2, y0+dy/2, z0+dz)])
        for f in [(i,i+1,i+2,i+3),(i+7,i+6,i+5,i+4),(i,i+1,i+5,i+4),
                  (i+1,i+2,i+6,i+5),(i+2,i+3,i+7,i+6),(i+3,i,i+4,i+7)]:
            F.append(f); MI.append(mi)
    def _quad(p0, p1, p2, p3, mi):
        i = len(V); V.extend([p0, p1, p2, p3]); F.append((i,i+1,i+2,i+3)); MI.append(mi)
    # two glazed roof planes meeting at the ridge (open gable ends)
    _quad((-L/2,-W/2,He),(L/2,-W/2,He),(L/2,0,Hr),(-L/2,0,Hr), 0)
    _quad((-L/2, W/2,He),(L/2, W/2,He),(L/2,0,Hr),(-L/2,0,Hr), 0)
    _addbox(0, 0, Hr-0.15, L, 0.35, 0.3, 1)                 # ridge beam
    for _sy in (-W/2, W/2):
        _addbox(0, _sy, He-0.15, L, 0.3, 0.3, 1)            # eave beams
    _ncol = max(3, int(L/5.0))
    for _c in range(_ncol+1):
        _x = -L/2 + L*_c/_ncol
        for _sy in (-W*0.42, W*0.42):
            _addbox(_x, _sy, 0, 0.35, 0.35, He, 1)          # iron columns
    _me = bpy.data.meshes.new("station%%d" %% _s["id"]); _me.from_pydata(V, [], F)
    _me.materials.append(_SGL); _me.materials.append(_SIR)
    for _p, _mi in zip(_me.polygons, MI):
        _p.material_index = _mi
    _ob = bpy.data.objects.new("Station_%%d" %% _s["id"], _me)
    _ob.rotation_euler = (0, 0, ang); _ob.location = (cx, cy, 0)
    bpy.context.scene.collection.objects.link(_ob)
'''


def assemble(metas, agent_specs, out_dir):
    """LoD1 for un-generated buildings + posed agent buildings + renders.
    Special-form builders are fallbacks only: never replace an agent spec."""
    def _is(m, kinds):
        return (m["id"] not in agent_specs and
                (m.get("func") in kinds or m.get("btype") in kinds))

    def _shed(m):
        # A Tube entrance POI inside an office/shop does not make the whole
        # host a train shed. Retain the agent's learned assembly when present.
        return m["id"] not in agent_specs and m.get("btype") == "train_station"
    canopies = [{"id": m["id"], "pts": m["pts"], "height": m["height"]}
                for m in metas if _is(m, ("canopy", "roof"))]
    stations = [{"id": m["id"], "cx": obb(m["pts"])[0], "cy": obb(m["pts"])[1],
                 "L": obb(m["pts"])[2], "W": obb(m["pts"])[3], "ang": obb(m["pts"])[4],
                 "height": m["height"]}
                for m in metas if _shed(m)]
    # floating vessels: small, low, and (almost) fully inside a water polygon --
    # OSM building=yes barges/yachts; routed like the other special forms
    vessels = []
    try:
        from img2city.scene import assets as _sa
        _d0 = json.load(open(os.path.join(out_dir, "buildings.json")))
        _green, _hh = _sa.green_to_local(
            _sa.fetch_green(_d0["anchor"]["bbox"],
                            os.path.join(out_dir, "green_raw.json")), _d0["anchor"])
        _water = [g["pts"] for g in _green if g.get("kind") == "water"]
        for m in metas:
            if m["id"] in agent_specs or m["area_m2"] >= 900 or m["height"] > 12 or not _water:
                continue
            inw = sum(1 for q in m["pts"]
                      if any(_sa._point_in_poly(q[0], q[1], w) for w in _water))
            if inw >= 0.8 * len(m["pts"]):
                o = obb(m["pts"])
                vessels.append({"id": m["id"], "cx": o[0], "cy": o[1],
                                "L": round(o[2], 1), "W": round(o[3], 1),
                                "ang": round(o[4], 3), "h": m["height"]})
    except Exception as e:
        print(f"[vessels] skipped: {e}")
    special = ({m["id"] for m in metas if _is(m, ("canopy", "roof"))}
               | {m["id"] for m in metas if _shed(m)}
               | {v["id"] for v in vessels})
    agent_specs = {k: v for k, v in agent_specs.items() if k not in special}
    lod1 = [m for m in metas if m["id"] not in agent_specs and m["id"] not in special]
    code = BUILD_SCENE % json.dumps(lod1)
    if canopies:
        code += CANOPY_BUILD % json.dumps(canopies)
        print(f"[scene] {len(canopies)} building=roof -> open canopy")
    if stations:
        code += STATION_BUILD % json.dumps(stations)
        print(f"[scene] {len(stations)} train_station -> open glazed shed")
    if vessels:
        code += VESSEL_BUILD % json.dumps(vessels)
        print(f"[scene] {len(vessels)} in-water buildings -> vessels")
    try:
        from img2city.scene.assets import load_or_build
        trees, roads, green, hedges, furn = load_or_build(out_dir)
        from img2city.scene import road_graph
        traffic = road_graph.load_or_build(out_dir)
        marks = road_graph.traffic_marks(traffic,
                                         side=road_graph.drive_side(out_dir))
        vjson = os.path.join(out_dir, "vehicles.json")
        vehicles = json.load(open(vjson)) if os.path.exists(vjson) else []
        ajson = os.path.join(out_dir, "traffic_anim.json")
        anim = json.load(open(ajson)) if os.path.exists(ajson) else None
        if anim:
            print(f"[traffic-sim] {len(anim['routes'])} vehicles animated "
                  f"({anim['seconds']:.0f}s)")
        if vehicles:
            print(f"[vehicles] {len(vehicles)} from cache "
                  f"({sum(1 for v in vehicles if v['kind'] == 'bus')} buses)")
        else:
            print("[vehicles] no vehicles.json -- run `python -m img2city.scene.vehicles` "
                  "with a torch-capable interpreter (IMG2CITY_TORCH_PYTHON) to detect them")
        code += SCENE_ASSETS % json.dumps({"trees": trees, "roads": roads,
                                           "green": green, "hedges": hedges,
                                           "furniture": furn, "traffic": marks,
                                           "vehicles": vehicles,
                                           "anim": anim})
        print(f"[scene] + {len(trees)} trees, {len(roads)} road ways, "
              f"{len(green)} green areas, {len(hedges)} hedges, "
              + ", ".join(f"{len(v)} {k}" for k, v in furn.items() if v))
        print(f"[traffic] {len(traffic['arcs'])} directed arcs, "
              f"{len(traffic['restrictions'])} turn restrictions -> "
              f"{len(marks['arrows'])} arrows, {len(marks['dashes'])} lane dashes")
    except Exception as e:                     # scene layer is additive, never fatal
        print(f"[scene] assets skipped: {e}")
    # street-side shops (scene/shops.py): a parameterised unit per business on
    # the ground-floor frontage. Hosts are flagged `shop_units` so the kit clears
    # the ground storey (no ordinary windows, no stucco over it) but does NOT
    # draw its old generic glass+fascia band -- the two would occupy the same
    # 0.3 m of wall and z-fight, and the unit layer carries strictly more
    # information. The spec on disk is untouched, so the refine loop keeps
    # judging the building it always judged (shops are a scene layer, like trees
    # and vehicles, deliberately outside the per-building refine contract).
    shop_units = []
    try:
        sj = os.path.join(out_dir, "shops.json")
        if os.path.exists(sj):
            shop_units = json.load(open(sj))["units"]
            hosts = {u["host"] for u in shop_units}
            # the flag is per EDGE (polygon) / per FACE (OBB rectangle): a corner
            # building can carry a parade on one street and plain windows on the
            # other. built_outlines() orders the OBB corners (-1,-1) (1,-1) (1,1)
            # (-1,1), so edge k maps onto the kit's face names in that order.
            OBB_FACE = ["-y", "+x", "+y", "-x"]
            edges = {}
            for u in shop_units:
                edges.setdefault(u["host"], set()).add(u["edge"])
            for it in agent_specs.values():
                ek = edges.get(it["id"])
                if not ek:
                    continue
                if "poly" in it:
                    it["shop_edges"] = sorted(ek)
                else:
                    it["desc"]["shop_faces"] = sorted(
                        {OBB_FACE[k] for k in ek if k < 4})
            print(f"[shops] {len(shop_units)} units on {len(hosts)} buildings "
                  f"({sum(1 for u in shop_units if u['name'])} named)")
        else:
            print("[shops] no shops.json -- run scene/shops.py to build it")
    except Exception as e:                     # shop layer is additive, never fatal
        print(f"[shops] skipped: {e}")

    code += "\n_COMPONENTS_SRC = %r\n" % load_components_src()
    items = list(agent_specs.values())
    # photo-sampled part colours (facade_colors.py, cached colors.json only --
    # run `python -m img2city.building.facade_colors --out <dir>` to build them). The editable
    # appearance route (2026-07-18 direction decision): colours live on the
    # parts as material values; the photo-projection quads were retired.
    try:
        from img2city.building.facade_colors import colors_for
        nc = 0
        for it in items:
            c = colors_for(out_dir, it["id"])
            if not c:
                continue
            nc += 1
            if "poly" in it:
                it["colors"] = dict(c, **(it.get("colors") or {}))
            else:
                it["desc"]["colors"] = dict(c, **(it["desc"].get("colors") or {}))
        if nc:
            print(f"[colors] {nc} buildings photo-coloured")
    except Exception as e:                     # colour layer is additive
        print(f"[colors] skipped: {e}")
    for k in range(0, len(items), 5):
        code += AGENT_CHUNK % json.dumps(items[k:k+5])
    if shop_units:
        # after AGENT_CHUNK: the units hang on walls the buildings above just built
        code += SHOP_UNITS % json.dumps(shop_units)
    ground_code = ""
    features_path = os.path.join(out_dir, "district_features.json")
    if os.path.exists(features_path):
        from img2city.city.district_features import BUILD, validate, ground_mesh, GROUND
        feature_plan = json.load(open(features_path))
        anchor = json.load(open(os.path.join(out_dir, "buildings.json")))["anchor"]
        errors = validate(feature_plan, metas, anchor)
        if errors:
            raise ValueError("invalid district features: " + str(errors))
        code += BUILD % json.dumps(feature_plan["features"])
        ground = ground_mesh(feature_plan, metas)
        if ground:
            ground_code = GROUND % json.dumps(ground)
    code += VIEWPORT_SYNC
    try:
        from img2city.building.texture_assets import run_all
        code += AGENT_TEXTURES % json.dumps(run_all(out_dir))
    except Exception as e:                     # texture layer is additive, never fatal
        print(f"[textures] skipped: {e}")
    # cameras: whole-block aerial + top, plus an OBLIQUE street-level view of the
    # largest rectangular agent building (oblique shows depth: balconies, porticos,
    # chimneys -- the frontal view flattened them away)
    rect = [b for b in items if "poly" not in b]
    big = max(rect or items, key=lambda b: b["desc"]["footprint"][0]) if items else None
    code += CITY_RENDER + ground_code + (RENDER_OUT % os.path.join(out_dir, "city_agent_aerial.png"))
    code += CITY_TOP + (RENDER_OUT % os.path.join(out_dir, "city_agent_top.png"))
    if big:
        r = big["rot"]
        nx, ny = math.sin(r), -math.cos(r)          # facade normal (front)
        ax, ay = math.cos(r), math.sin(r)           # along the facade
        fx = big["cx"] + nx * 30 + ax * 24
        fy = big["cy"] + ny * 30 + ay * 24
        code += (CITY_STREET % (big["cx"] + nx * 8, big["cy"] + ny * 8, fx, fy)) \
            + (RENDER_OUT % os.path.join(out_dir, "city_agent_street.png"))
    # 2400 s: a big-area assembly (ams, 4900+ objects) can exceed 900 s since
    # needs_poly switched dozens of buildings to polygon builders -- and a
    # CLIENT-side timeout mid-request is exactly what wedges the BlenderMCP
    # server (08-13, three wedges in one day traced to this)
    from pathlib import Path as _Path
    from img2city.city.quality import _write
    _write(_Path(out_dir) / "assembly_manifest.json", {"status": "assembling"})
    result = _send(code, timeout=2400)
    if isinstance(result, tuple) and result[1] is None:
        from img2city.city.quality import record_assembly
        record_assembly(out_dir)
    return result


# camera that REPRODUCES the street-view photo's viewpoint: the building is built at
# the origin (front = -y) and the camera stands where the panorama stood, in
# building-local coordinates, with Street View's 90-degree fov (= 18 mm lens).
# Without this, photo-vs-render comparisons are meaningless: the judge compares two
# different viewpoints and even a perfect model "looks wrong".
PANO_RENDER = r'''
import bpy, math, mathutils
tgt = bpy.data.objects.new("Tgt", None); bpy.context.scene.collection.objects.link(tgt)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); bpy.context.scene.collection.objects.link(cam)
tgt.location = (%f, %f, %f)
cam.location = (%f, %f, 2.5)
cam.data.lens = 18
'''

# appended after PANO_RENDER when the pano record carries the photo's own fov
# ([lat, lng, heading, fov, pitch], facade_clean.select_view): the render must
# match the photo's lens or the comparison punishes framing, not the model
PANO_LENS = '''
cam.data.lens = %f
'''


def pano_cam(pano, dist):
    """(lens_mm, target_z) for the pano-matched render camera. Empirically
    calibrated (2026-07-20, 3x3 sweep vs the cleaned photo): the Street View
    fov PARAMETER does not map onto Blender's rectilinear lens (fov 120 ->
    10.4 mm rendered the building as a distant strip, ds 0.58 vs 0.47), so the
    lens stays 18 mm regardless of the recorded fov; the sweep preferred a
    slightly higher aim than the old H*0.55 heuristic (best zt ~0.75H)."""
    return 18.0, None

# second render per iteration: straight-down ortho of the single building, judged
# against the SATELLITE reference (roof form / plan features are invisible or
# unreliable in the street view -- same lesson as generate.CAM_TOP)
TOP_CAM = r'''
camT = bpy.data.objects.new("CamT", bpy.data.cameras.new("CamT")); bpy.context.scene.collection.objects.link(camT)
camT.data.type = 'ORTHO'; camT.data.ortho_scale = %f; camT.data.clip_end = 1000
camT.location = (%f, %f, 300)
bpy.context.scene.camera = camT
'''

# refine render for a POLYGON-MODE building: the scene shows these on their TRUE
# footprint (polygon_terrace), so the refine loop must render the same thing -- the
# old loop skipped them because it could only render the OBB box, leaving 9 of the
# block's largest buildings permanently unrefined
POLY_BUILD = r'''
import json as _json
ensure_materials()
_poly_parameters = _json.loads(%r)
polygon_terrace(_poly_parameters, 0)
import mathutils as _pxm
if _poly_parameters.get('extra_parts_frame'):
    _pf = _poly_parameters['extra_parts_frame']
    _pm = (_pxm.Matrix.Translation((_pf['cx'], _pf['cy'], 0))
           @ _pxm.Matrix.Rotation(_pf['rotation_rad'], 4, 'Z'))
    for _pp in _poly_parameters.get('framed_extra_parts') or []:
        for _po in BUILDERS[_pp['type']](_pp, 0):
            _po.matrix_world = _pm @ _po.matrix_world
'''


def front_edges(pts, pano_xy):
    """Indices of the polygon edges that make up the building's PRIMARY (street /
    photographed) facade, given the pano's scene position. Only these get the rich
    facade treatment (giant order, ribbon, colonnade, full window relief); the
    other edges (ends, back walls that face the campus interior and are never
    photographed) get a plain default -- otherwise the kit stamps the grand front
    onto blank flank walls (RSM's blank rusticated end wrongly grew giant-order
    windows). The primary facade = the longest edge whose outward normal faces the
    pano's side, plus any other long edge (>=0.6x) on that same side."""
    n = len(pts)
    px, py = pano_xy

    def _seg_x(a, b, c, d):
        """do segments a-b and c-d cross?"""
        def ccw(u, v, w):
            return (w[1] - u[1]) * (v[0] - u[0]) > (v[1] - u[1]) * (w[0] - u[0])
        return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)

    lens, vis = [], []
    for k in range(n):
        x1, y1 = pts[k]; x2, y2 = pts[(k + 1) % n]
        el = math.hypot(x2 - x1, y2 - y1)
        lens.append(el)
        # pull the sample point slightly OUTWARD off the wall so the edge's own
        # endpoints don't count as an occluder
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        cx = sum(p[0] for p in pts) / n; cy = sum(p[1] for p in pts) / n
        ox, oy = mx - cx, my - cy
        on = math.hypot(ox, oy) or 1.0
        sx, sy = mx + ox / on * 0.5, my + oy / on * 0.5
        # SELF-occlusion: the pano can only photograph this facade if the sightline
        # to it does not pass through the building (the back walls are hidden by
        # the mass, so facing angle alone can't tell front from back on a corner
        # shot -- visibility can)
        blocked = False
        for j in range(n):
            if j == k or (j + 1) % n == k or j == (k + 1) % n:
                continue
            if _seg_x((px, py), (sx, sy), pts[j], pts[(j + 1) % n]):
                blocked = True
                break
        vis.append(not blocked)
    maxlen = max(lens) if lens else 0.0
    if maxlen < 1e-6:
        return []
    # front = visible (unoccluded) edges long enough to be a real facade
    cand = [k for k in range(n) if vis[k] and lens[k] >= 0.35 * maxlen]
    if not cand:
        cand = [max(range(n), key=lambda k: lens[k])]
    return sorted(cand)


def poly_params(spec, pts=None, pano_xy=None):
    """Map an agent spec onto polygon_terrace parameters -- the single place where
    the spec->true-polygon contract lives (assembly and the refine render must
    build the SAME thing or the refined spec would be judged on geometry the scene
    never shows). pano_xy (scene coords) restricts the rich facade treatment to the
    photographed front edges (front_edges); without it, every edge is treated as
    front (backward-compatible)."""
    masses = spec.get("masses") or [{}]
    # wall material: the LARGEST masonry mass decides (one small glass wing used
    # to flip the whole polygon building to glass -- RSM rendered as a pale
    # glass slab and its stone colonnade was invisible against it)
    mas = [mm for mm in masses if mm.get("facade", spec.get("facade", "glass")) != "glass"]
    if mas:
        big = max(mas, key=lambda mm: (mm.get("x", [0, 1])[1] - mm.get("x", [0, 1])[0])
                  * (mm.get("y", [0, 1])[1] - mm.get("y", [0, 1])[0]))
        wall = big.get("wall", "brick" if spec.get("typology", "terrace") == "terrace"
                       else "stone")
    else:
        wall = "glass"
    tr = spec.get("terrace") or {}
    p = {"floors": max(int(mm.get("floors", spec.get("floors", 4))) for mm in masses),
         "floor_h": float(spec.get("floor_h", 3.2)),
         "wall": wall,
         "roof_tone": tr.get("roof_tone", "dark"),
         "roof_form": tr.get("roof_form") or (
             "valley" if spec.get("typology", "terrace") == "terrace" else "flat"),
         "dormers": bool(tr.get("dormers")),
         "shopfront": bool(tr.get("shopfront")),
         # library round 3 knobs (campus institutional typology)
         "podium_floors": int((spec.get("podium") or {}).get("floors", 0)),
         "fins": spec.get("fins"),
         # institutional fidelity round
         "colonnade": spec.get("colonnade"),
         "balustrade": bool(spec.get("balustrade")),
         "arch": bool(spec.get("arch_windows")),
         "arch_row": int(spec.get("arch_row", 0)),
         # library round 4: ribbon facade (continuous glazing strips + spandrel
         # bands + mullion rhythm -- post-war modernist slabs)
         "ribbon": spec.get("ribbon"),
         # photo-measured editable part colours (facade_colors.py); polygon_terrace
         # aliases the kit materials to these per-colour variants
         "colors": spec.get("colors"),
         # library round 4: giant-order fenestration (tall piano-nobile windows
         # spanning storeys) for grand institutional stone fronts
         "giant": spec.get("giant"),
         # roof parity (08-17 review: "the roofs feel simplified"): the agent's
         # roof list (ridges/sawtooth/plant) was silently dropped on the poly
         # path — NHM specced 7 ridges + a sawtooth range and rendered flat
         "roof_spec": spec.get("roof"),
         "extra_parts_frame": spec.get("extra_parts_frame"),
         "framed_extra_parts": spec.get("extra_parts") if spec.get("extra_parts_frame") else None}
    if pts is not None and pano_xy is not None:
        p["front_edges"] = front_edges([tuple(q) for q in pts], pano_xy)
    if pts is not None:
        p["pts"] = pts
    return p


_NP_CACHE = {}


def needs_poly(m, out):
    """True when this building must build on its TRUE OSM polygon instead of
    the OBB rectangle: bad fill (L-shapes/wedges, the original rule) OR the
    rectangle INTRUDES into a neighbour's footprint (08-13: dense
    party-wall parcels -- Paris/AMS -- had buildings growing into each other;
    28/86 Paris OBB placements overlapped a neighbour, worst 597 m2). The OSM
    footprint is the placement contract; the rectangle is only a convenience
    that must never leak across it. Same rule for assembly AND refine renders."""
    fill = m["area_m2"] / max(1.0, m["obb"][2] * m["obb"][3])
    if fill < 0.72:
        return True
    try:
        from shapely.geometry import Polygon
    except ImportError:
        return False
    if out not in _NP_CACHE:
        d = json.load(open(os.path.join(out, "buildings.json")))
        _NP_CACHE[out] = [(mm["id"], Polygon(mm["pts"]))
                          for mm in d["buildings"]]
    cx, cy, L, W, ang = m["obb"]
    ca, sa = math.cos(ang), math.sin(ang)
    rect = Polygon([(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)
                    for dx, dy in ((L/2, W/2), (L/2, -W/2),
                                   (-L/2, -W/2), (-L/2, W/2))])
    # allowance: 6% of own area for party-wall jitter, but capped ABSOLUTELY —
    # the percentage rule handed the Natural History Museum a 1614 m2 licence
    # to overlap its neighbours by 595 m2 (08-16: building spacing looked
    # wrong; V&A likewise 510 m2). No building may overlap neighbours by more
    # than a mews-house worth of area before switching to its true polygon.
    lim = max(10.0, min(0.06 * m["area_m2"], 25.0))
    rb = rect.bounds
    intr = 0.0
    for bid, p in _NP_CACHE[out]:
        if bid == m["id"]:
            continue
        b = p.bounds
        if b[0] > rb[2] or b[2] < rb[0] or b[1] > rb[3] or b[3] < rb[1]:
            continue
        try:
            intr += rect.intersection(p).area
        except Exception:
            continue
        if intr > lim:
            return True
    return False


def spec_render_ctx(out, osmid, use_view2=True):
    """Load ONE building's refine context and return its render function --
    the PANO-MATCHED street camera(s) + ortho top, standoff guards, poly/obb
    routing -- factored out of refine_building so other callers (library_grow's
    paired A/B gate above all) score candidate geometry from the IDENTICAL
    viewpoints; a lift measured from a different camera would be meaningless.
    Returns {render, m, anchor, spec, photo, photo2, sat, refs, pano, pano2,
    dist, lx, ly, poly_mode, L, W, cam_moved, bdir, comp}."""
    d = json.load(open(os.path.join(out, "buildings.json")))
    metas, anchor = d["buildings"], d["anchor"]
    m = next(mm for mm in metas if mm["id"] == osmid)
    m["obb"] = obb(m["pts"])
    bdir = os.path.join(out, "buildings", str(osmid))
    photo = ref_photo(bdir)          # cleaned reference when gate-accepted
    sat = os.path.join(bdir, "satellite.png")
    # optional SECOND street viewpoint (facade_clean --select --second): its
    # render is judged by street2-tagged checks, so the sides the primary photo
    # cannot see stop being unconstrained guesses (multi-view, 2026-07-20)
    v2dir = os.path.join(bdir, "view2")
    photo2 = pano2 = None
    if (use_view2 and os.path.exists(os.path.join(v2dir, "pano.json"))
            and os.path.exists(os.path.join(v2dir, "streetview.png"))):
        photo2 = ref_photo(v2dir)
        pano2 = tuple(json.load(open(os.path.join(v2dir, "pano.json"))))
    refs = [photo] + ([photo2] if photo2 else []) \
        + ([sat] if os.path.exists(sat) else [])
    target_map = os.path.join(bdir, "target_satellite.png")
    if os.path.exists(target_map):
        refs.append(target_map)
    spec = json.load(open(os.path.join(bdir, "spec.json")))
    pano = tuple(json.load(open(os.path.join(bdir, "pano.json"))))
    rot = front_rotation(m, pano, anchor)
    cx, cy = m["obb"][0], m["obb"][1]
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    dx = (pano[1] - anchor["lon0"]) * kx - cx
    dy = (pano[0] - anchor["lat0"]) * 110540.0 - cy
    lx = math.cos(-rot) * dx - math.sin(-rot) * dy      # pano in building-local coords
    ly = math.sin(-rot) * dx + math.cos(-rot) * dy
    dist = math.hypot(lx, ly)
    # pano position in scene coords BEFORE any standoff push -- front_edges must
    # judge visibility from where the photo was actually taken, not the render cam
    pano_scene = (cx + dx, cy + dy)
    dx2 = dy2 = lx2 = ly2 = None
    if pano2:
        dx2 = (pano2[1] - anchor["lon0"]) * kx - cx
        dy2 = (pano2[0] - anchor["lat0"]) * 110540.0 - cy
        lx2 = math.cos(-rot) * dx2 - math.sin(-rot) * dy2
        ly2 = math.sin(-rot) * dx2 + math.cos(-rot) * dy2
    L, W = m["obb"][2], m["obb"][3]
    poly_mode = needs_poly(m, out)
    comp = load_components_src()
    from img2city.imagery.camera import recorded_pose, blender_override, recorded_top, top_override
    recorded = recorded_pose(bdir, anchor, rot, (cx, cy), poly_mode)
    pose_override = blender_override(recorded)
    top_pose = recorded_top(bdir, anchor, rot, (cx, cy), poly_mode)
    top_correction = top_override(top_pose)

    # minimum-standoff guard (07-14): some panoramas sit almost against -- or, for
    # concave footprints, INSIDE -- the polygon. Every render is then a wall
    # closeup no judge can score (the eval subset's ds~0.85 cluster). Push such
    # cameras out along the nearest edge's outward normal to a sane distance;
    # CAM_GATE still handles protruding parts after this.
    _hs = max(int(mm.get("floors", spec.get("floors", 4))) for mm in
              (spec.get("masses") or [{}])) * float(spec.get("floor_h", 3.2))
    stand = max(12.0, 1.1 * _hs)
    # when the guard moves the camera, the render viewpoint no longer matches the
    # photo's, so the depth anchor compares two different perspectives -- record it
    # (850052662 post-mortem: v4's da=0.82 on a wall-closeup was spurious agreement
    # of two smooth depth gradients; v5's honest reframe "collapsed" to 0.03)
    cam_moved = False

    def _stand_poly(dxi, dyi):
        """Push a pano that stands against/inside the TRUE footprint out to a
        sane standoff along the nearest edge's outward normal."""
        from img2city.scene.assets import _point_in_poly
        px, py = cx + dxi, cy + dyi
        dmin, qbest = 1e9, (px, py)
        n_ = len(m["pts"])
        for k in range(n_):
            x1, y1 = m["pts"][k]
            x2, y2 = m["pts"][(k + 1) % n_]
            ex, ey = x2 - x1, y2 - y1
            t = max(0.0, min(1.0, ((px - x1) * ex + (py - y1) * ey) / max(1e-9, ex * ex + ey * ey)))
            qx, qy = x1 + t * ex, y1 + t * ey
            dq = math.hypot(px - qx, py - qy)
            if dq < dmin:
                dmin, qbest = dq, (qx, qy)
        if _point_in_poly(px, py, m["pts"]) or dmin < 5.0:
            ccx = sum(q[0] for q in m["pts"]) / n_
            ccy = sum(q[1] for q in m["pts"]) / n_
            nx_, ny_ = qbest[0] - ccx, qbest[1] - ccy
            nn = math.hypot(nx_, ny_) or 1.0
            return (qbest[0] + nx_ / nn * stand - cx,
                    qbest[1] + ny_ / nn * stand - cy, True)
        return dxi, dyi, False

    if poly_mode:
        dx, dy, cam_moved = _stand_poly(dx, dy)
        if cam_moved:
            print(f"[refine {osmid}] pano against/inside footprint -- camera pushed "
                  f"to {stand:.0f} m standoff")
        if pano2:
            dx2, dy2, _m2 = _stand_poly(dx2, dy2)
            if _m2:
                print(f"[refine {osmid}] view2 pano pushed to {stand:.0f} m standoff")
    elif ly > -(W / 2 + 4.0) or dist < 8.0:
        lx = max(-L / 2, min(L / 2, lx))
        ly = -(W / 2 + stand)
        cam_moved = True
        print(f"[refine {osmid}] pano against facade -- camera pushed to "
              f"{stand:.0f} m standoff")
    if (not poly_mode) and pano2:
        # generic min-distance guard only: which facade view2 faces is unknown
        _d2 = math.hypot(lx2, ly2)
        if _d2 < 8.0:
            _s = stand / max(1e-6, _d2)
            lx2, ly2 = lx2 * _s, ly2 * _s

    def render(sp, out_png, top_png, nrm_png=None, textured=False, out2_png=None):
        H = max(int(mm.get("floors", sp.get("floors", 4))) for mm in
                (sp.get("masses") or [{}])) * float(sp.get("floor_h", 3.2))
        lens1, zt_p = pano_cam(pano, dist)
        zt = zt_p if zt_p is not None else min(H * 0.72, 4.0 + 0.32 * dist)
        if pano2:
            d2r = math.hypot(dx2, dy2) if poly_mode else math.hypot(lx2, ly2)
            lens2, zt2_p = pano_cam(pano2, d2r)
            zt2 = zt2_p if zt2_p is not None else min(H * 0.72, 4.0 + 0.32 * d2r)
        nrm = (NORMAL_OUT % nrm_png) if nrm_png else ""
        tex = (TEX_OVERRIDE % os.path.join(bdir, "textures")) if textured else ""
        if poly_mode:
            # true-footprint build in SCENE coordinates; the camera stands at the
            # panorama's scene position, exactly like the assembled block
            xs = [q[0] for q in m["pts"]]; ys = [q[1] for q in m["pts"]]
            scale = 1.25 * max(max(xs) - min(xs), max(ys) - min(ys))
            build = POLY_BUILD % json.dumps(
                poly_params(sp, pts=m["pts"], pano_xy=pano_scene))
            wrap = (PANO_RENDER % (cx, cy, zt, cx + dx, cy + dy)) \
                + (PANO_LENS % lens1) + RENDER_CAM \
                + (CAM_GATE % min(20.0, scale / 5.0)) \
                + pose_override + LIGHT_STREET + tex + (RENDER_OUT % out_png) + nrm
            if out2_png and pano2:
                wrap += (PANO_RENDER % (cx, cy, zt2, cx + dx2, cy + dy2)) \
                    + (PANO_LENS % lens2) + RENDER_CAM \
                    + (CAM_GATE % min(20.0, scale / 5.0)) \
                    + (RENDER_OUT % out2_png)
            wrap += (TOP_CAM % (scale, cx, cy)) + top_correction + (RENDER_OUT % top_png)
            with _BLENDER_LOCK:
                return _send(CLEAR + "\n" + comp + "\n" + build + "\n" + wrap,
                             timeout=600)
        wrap = (PANO_RENDER % (0, 0, zt, lx, ly)) + (PANO_LENS % lens1) \
            + RENDER_CAM + (CAM_GATE % (L / 4.0)) + pose_override + LIGHT_STREET + tex \
            + (RENDER_OUT % out_png) + nrm
        if out2_png and pano2:
            wrap += (PANO_RENDER % (0, 0, zt2, lx2, ly2)) + (PANO_LENS % lens2) \
                + RENDER_CAM + (CAM_GATE % (L / 4.0)) + (RENDER_OUT % out2_png)
        wrap += (TOP_CAM % (max(L, W) * 1.25, 0, 0)) + top_correction + (RENDER_OUT % top_png)
        with _BLENDER_LOCK:
            return _send(CLEAR + "\n" + spec_to_code(json.dumps(sp), comp)
                         + "\n" + wrap, timeout=600)

    return {"render": render, "m": m, "anchor": anchor, "spec": spec,
            "photo": photo, "photo2": photo2, "sat": sat, "refs": refs,
            "pano": pano, "pano2": pano2, "dist": dist, "lx": lx, "ly": ly,
            "poly_mode": poly_mode, "L": L, "W": W, "cam_moved": cam_moved,
            "bdir": bdir, "comp": comp, "recorded_pose": recorded, "recorded_top": top_pose}


def refine_building(out, osmid, iters, backend, model, jmodel, inspector_k=3,
                    use_view2=True, frozen_checks=None):
    """Run the verified single-building refinement loop (checklist judge + pairwise
    vote) on ONE city building. Every iteration renders TWO views -- the PANO-MATCHED
    street camera (same viewpoint as the street-view photo) and a straight-down ortho
    top (same viewpoint as the satellite tile) -- so the checklist can hold the model
    to BOTH references. The refined spec replaces spec.json, so the next
    --assemble-only upgrades the scene. Returns (best_pass_rate, tokens_spent).

    Judge v2 (2026-07-11, related_work_methods.md §J/§O): checks carry a "view" tag
    and are judged one-view-per-question; the inspector is sampled `inspector_k`
    times with per-check majority voting; the pairwise tie-break is swap-consistent;
    DreamSim (street render vs street photo) is logged every iteration and breaks
    residual ties. Polygon-mode buildings (OBB fill < 0.72) refine on their TRUE footprint
    via polygon_terrace -- previously they were skipped entirely."""
    from img2city.building.generate import area_region
    region = area_region(out)
    ctx = spec_render_ctx(out, osmid, use_view2)
    try:
        from img2city.building.typology import building_tags
        _tags = building_tags(out, ctx["m"],
                              os.path.join(out, "buildings", str(osmid)))
    except Exception:
        _tags = None
    m, spec, render = ctx["m"], ctx["spec"], ctx["render"]
    photo, photo2, refs = ctx["photo"], ctx["photo2"], ctx["refs"]
    L, W, poly_mode = ctx["L"], ctx["W"], ctx["poly_mode"]
    lx, ly, dist = ctx["lx"], ctx["ly"], ctx["dist"]
    cam_moved, bdir = ctx["cam_moved"], ctx["bdir"]
    tok = [0]

    def _use(u):
        tok[0] += u.get("prompt_tokens", 0) + u.get("completion_tokens", 0)

    poly_note = (" The model is built on the building's TRUE footprint polygon; the "
                 "spec controls floors, floor_h, facade material and the terrace "
                 "options (roof_form/roof_tone/stucco), NOT the footprint shape."
                 if poly_mode else "")
    imgs_note = "reference image 1 is a STREET-LEVEL photo"
    if photo2:
        imgs_note += (", the next image a SECOND street-level photo of the SAME "
                      "building from a different side")
    imgs_note += (", the last image (if present) a SATELLITE top view of the "
                  "same building")
    osm_brief = json.dumps({
        "osm_footprint_m": [round(L, 1), round(W, 1)], "osm_height_m": m["height"],
        "facade_facts_from_photo": _facade_facts(bdir),
        "note": (imgs_note + ". The candidate model is rendered from EACH of "
                 "those viewpoints; every check must be answerable from one of "
                 "those renders" + poly_note)})
    osm_brief += "\nCoordinate frame: " + json.dumps(spatial_brief(m, bdir))
    from img2city.imagery.reference_audit import context as reference_context
    evidence = reference_context(bdir)
    camera_verified = bool(evidence and evidence.get("camera_verified") and not cam_moved)
    if evidence:
        osm_brief += "\nReference evidence audit: " + json.dumps(evidence)
        osm_brief += ("\nCamera match is NOT verified. Use observable structural features; "
                      "do not make pixel alignment, framing, apparent left/right placement "
                      "or occluded interiors acceptance criteria. If a feature cannot be "
                      "observed from the candidate views, report insufficient evidence.")
    rdir = os.path.join(bdir, "refine")
    os.makedirs(rdir, exist_ok=True)
    if frozen_checks is not None:
        # paired / repeated experiments: the measuring stick is supplied and
        # must not move between arms or replicates (no re-derivation noise)
        checks = frozen_checks
    else:
        checks, _u = checklist_step(
            refs, osm_brief, backend, model,
            views=[("street", "a street-level render from the photo's own viewpoint")]
            + ([("street2", "a street-level render from the second photo's own "
                            "viewpoint (a different side of the building)")]
               if photo2 else [])
            + [("top", "a straight-down orthographic roof/plan view")])
        _use(_u)
        with open(os.path.join(rdir, "checklist.json"), "w") as f:
            json.dump(checks, f, indent=1)
    print(f"[refine {osmid}] {len(checks)} checks ({'poly' if poly_mode else 'obb'}); "
          f"pano at local ({lx:.0f},{ly:.0f}), dist {dist:.0f} m")

    best, best_spec, best_render, crit = -1.0, spec, None, None
    best_failed = []
    best_ds, iter_log = None, []
    best_render2, best_ds2 = None, None
    agent_iters, agent_errs = 0, 0
    for it in range(iters):
        if it > 0:
            agent_iters += 1
            try:
                code, _u = gen_spec(refs + [best_render], json.dumps(best_spec), crit,
                                    None, backend, model, brief=osm_brief,
                                    region=region, tags=_tags)
                _use(_u)
                sp, errs = validate_desc(code)
                if errs:
                    code, _u = gen_spec(refs + [best_render], code, None,
                                        "; ".join(errs[:6]), backend, model,
                                        brief=osm_brief, region=region, tags=_tags)
                    _use(_u)
                    sp, errs = validate_desc(code)
                if errs or sp is None:
                    print(f"  iter {it}: invalid spec, skipping")
                    continue
                sp["footprint"] = [round(L, 1), round(W, 1)]   # OSM contract
                sp["plinth"] = False
            except Exception as e:
                agent_errs += 1
                print(f"  iter {it}: agent error, skipping: {str(e)[:80]}")
                continue
        else:
            sp = dict(spec); sp["plinth"] = False
        png = os.path.join(rdir, f"r{it:02d}.png")
        top = os.path.join(rdir, f"t{it:02d}.png")
        nrm = os.path.join(rdir, f"n{it:02d}.png")
        png2 = os.path.join(rdir, f"s{it:02d}.png") if photo2 else None
        _res, err = render(sp, png, top, nrm_png=nrm, out2_png=png2)
        if err:
            print(f"  iter {it}: blender error: {err[:80]}")
            crit = err[:200]
            continue
        s2 = png2 if png2 and os.path.exists(png2) else None
        passed, failed, _u = checklist_score(png, checks, backend, model,
                                             top=top if os.path.exists(top) else None,
                                             normal=nrm if os.path.exists(nrm) else None,
                                             street2=s2,
                                             k=inspector_k)
        _use(_u)
        ds = dreamsim_dist(png, photo) if camera_verified else None
        da = depth_agreement(png, photo) if camera_verified else None
        ds2 = dreamsim_dist(s2, photo2) if s2 and camera_verified else None
        accepted = passed > best
        if camera_verified and not accepted and best_render and abs(passed - best) < 1e-9:
            try:
                w, _why, _u2 = ab_vote(photo, best_render, png, backend, jmodel, votes=2)
                _use(_u2)
                accepted = (w == "B") or (
                    w == "tie" and ds is not None and best_ds is not None
                    and ds < best_ds - 0.01)
            except Exception:
                pass
        if accepted:
            best, best_spec, best_render, best_ds = passed, sp, png, ds
            best_render2, best_ds2 = s2, ds2
            best_failed = failed
        crit = ("; ".join((f["note"] or f["q"]) for f in best_failed)
                or "all checks pass -- refine proportions")
        # PERSIST the failed checks, not just how many there were. These are the
        # only record of what the model was ASKED for and could not deliver, and
        # they are the input to library learning (07-14 round 1 mined exactly this
        # by hand: dormers 13/34, mansard 10/34, pediment 7/34, shopfront 6/34).
        # Counting them and throwing the text away destroys the evidence at the
        # moment it is produced.
        iter_log.append({"iter": it, "pass": passed, "ds": ds, "da": da,
                         "ds2": ds2, "accepted": accepted,
                         "failed": [{"q": f.get("q"), "cat": f.get("cat"),
                                     "view": f.get("view"),
                                     "note": (f.get("note") or "")[:200]}
                                    for f in failed]})
        print(f"  iter {it}: pass={passed:.3f} ds={ds} "
              f"{'<- best' if accepted else ''}  {crit[:60]}")
    # every agent iteration errored (and there was at least one): the backend is down,
    # not the model failing to improve -- raise so a batch run counts this as a failure
    # and does NOT write a result.json (so a re-run retries this building)
    if agent_iters and agent_errs == agent_iters:
        raise llm.BackendDownError(f"all {agent_iters} agent iterations errored on {osmid}")
    with open(os.path.join(bdir, "spec.json"), "w") as f:
        json.dump(best_spec, f, indent=1)
    ds_tex = None
    if best_render:
        import shutil
        shutil.copy(best_render, os.path.join(rdir, "best.png"))
        if best_render2 and os.path.exists(best_render2):
            shutil.copy(best_render2, os.path.join(rdir, "best2.png"))
        # appearance channel (§Q item 3): DreamSim photo-vs-TEXTURED render of the
        # final best spec -- measured once at the end, never inside the loop
        if os.path.isdir(os.path.join(bdir, "textures")):
            btex = os.path.join(rdir, "best_textured.png")
            _tmp = os.path.join(rdir, "_tex_top.png")
            _res, terr = render(best_spec, btex, _tmp, textured=True)
            if not terr:
                ds_tex = dreamsim_dist(btex, photo) if camera_verified else None
            if os.path.exists(_tmp):
                os.remove(_tmp)
    with open(os.path.join(rdir, "result.json"), "w") as f:
        json.dump({"best_pass_rate": best, "best_ds": best_ds,
                   "best_ds2": best_ds2, "views": 2 if photo2 else 1,
                   "best_ds_textured": ds_tex, "iters": iters,
                   "tokens": tok[0], "checks": len(checks), "mode":
                   ("poly" if poly_mode else "obb"), "cam_moved": cam_moved, "camera_verified": camera_verified,
                   # what the BEST spec still could not satisfy: the demands that
                   # survived refinement are the "the kit cannot express this"
                   # evidence, as opposed to a proportion the loop simply had not
                   # tuned yet
                   "unmet": [{"q": f.get("q"), "cat": f.get("cat"),
                              "view": f.get("view"),
                              "note": (f.get("note") or "")[:200]}
                             for f in best_failed],
                   "iter_log": iter_log,
                   "provenance": provenance(model=model, judge_model=jmodel,
                                            backend=backend)}, f, indent=1)
    print(f"[refine {osmid}] best pass-rate {best:.3f} (~{tok[0]/1000:.0f}k tokens) "
          "-> spec.json updated")
    return best, tok[0]


def refine_todo(out, min_area, limit):
    """List of (osmid, area) still needing refinement -- every agent building with a
    spec.json but no refine/result.json (polygon-mode buildings refine on their true
    footprint since judge v2). Used by the overnight driver to know when the batch
    is actually complete."""
    d = json.load(open(os.path.join(out, "buildings.json")))
    todo = []
    # LANDMARK-FIRST (08-13 decision: deliverable = roads + basic landmarks
    # correct): named buildings carry the recognisability of the block, so a
    # budget-capped or interrupted batch must have spent its tokens on them
    # before anonymous stock; within each class, largest first as before
    for m in sorted(d["buildings"],
                    key=lambda m: (not m.get("name"), -m["area_m2"])):
        if m["area_m2"] < min_area:
            continue
        bdir = os.path.join(out, "buildings", str(m["id"]))
        if not os.path.exists(os.path.join(bdir, "spec.json")):
            continue
        if os.path.exists(os.path.join(bdir, "refine", "result.json")):
            continue
        # no street-view panorama = the pano-matched refine loop cannot run
        # (NHM stall 2026-07-19: missing pano.json crashed every driver pass);
        # skip rather than stall -- re-fetching imagery clears the skip
        if not os.path.exists(os.path.join(bdir, "pano.json")):
            print(f"[refine-todo] {m['id']} skipped: no street-view pano")
            continue
        # fallback shells (2026-07-27): the gate judged this building's imagery
        # unusable (interior/occluded/tiny) -- refining against a useless photo
        # burns tokens AND degrades the honest default; skip them
        gp = os.path.join(bdir, "gate.json")
        try:
            if os.path.exists(gp) and json.load(open(gp)).get("fallback"):
                continue
        except Exception:
            pass
        todo.append((m["id"], m["area_m2"]))
    return todo[:limit] if limit else todo


def refine_all(out, iters, backend, model, jmodel, min_area, limit, inspector_k=3,
               workers=8):
    """Scale the per-building refinement loop to EVERY agent-generated building
    (largest first) -- since judge v2 that includes polygon-mode buildings, which
    refine on their true footprint. Resumable: buildings with refine/result.json are
    skipped, so an interrupted run continues where it left off. NOTE: each render
    CLEARS the Blender scene -- re-run --assemble-only afterwards to rebuild."""
    d = json.load(open(os.path.join(out, "buildings.json")))
    metas = d["buildings"]
    sel = []
    for m in sorted(metas, key=lambda m: -m["area_m2"]):
        if m["area_m2"] < min_area:
            continue
        bdir = os.path.join(out, "buildings", str(m["id"]))
        if not os.path.exists(os.path.join(bdir, "spec.json")):
            continue
        # fallback shells (2026-07-27): imagery judged unusable at spec time --
        # refining against that photo mutates an honest default toward garbage
        # (697869263 was refined against a pedestrian-tunnel interior). Same
        # skip as refine_todo, which the driver uses for its remaining-count.
        gp = os.path.join(bdir, "gate.json")
        try:
            if os.path.exists(gp) and json.load(open(gp)).get("fallback"):
                continue
        except Exception:
            pass
        m["obb"] = obb(m["pts"])
        sel.append(m)
    if limit:
        sel = sel[:limit]
    done = [m for m in sel if os.path.exists(
        os.path.join(out, "buildings", str(m["id"]), "refine", "result.json"))]
    todo = [m for m in sel if m not in done]
    print(f"[refine-all] {len(todo)} to refine ({len(done)} already done, "
          f"{workers} workers)")

    # preflight: a whole run that silently errors every call (usage limit / expired
    # auth) burned time on 9 buildings for nothing before -- fail fast with the reason
    ok, why = healthcheck(model, backend)
    if not ok:
        raise SystemExit(f"[refine-all] backend not ready ({model}): {why}\n"
                         "  Fix the limit/auth, or point IMG2CITY_LLM_PROVIDER / --model "
                         "(<provider>:<model>) at another model, and re-run; "
                         "already-refined buildings are skipped.")

    # parallel workers (08-04 meeting item: ~10 agents at once). Safe because a
    # refine touches only its own building dir, each Blender render _send is
    # atomic behind _BLENDER_LOCK, and the torch anchors (DreamSim / depth) are
    # lock-guarded. On persistent failures a healthcheck decides between "keep
    # going" (transient) and "stop taking new work" (backend down / capped) --
    # the overnight shell driver then waits for quota and relaunches; progress
    # stays per-building resumable either way.
    lock = threading.Lock()
    stop = threading.Event()
    state = {"tok": 0, "scores": [], "fail": 0, "done": 0}

    def one(k, m):
        if stop.is_set():
            return
        print(f"[refine-all] start {k + 1}/{len(todo)} -- {m['id']} "
              f"({m['area_m2']:.0f} m2)")
        try:
            best, tk = refine_building(out, m["id"], iters, backend, model, jmodel,
                                       inspector_k=inspector_k)
            with lock:
                state["scores"].append(best)
                state["tok"] += tk
                state["fail"] = 0
                state["done"] += 1
                print(f"[refine-all] {m['id']} done (best {best:.2f}) -- "
                      f"{state['done']}/{len(todo)}, ~{state['tok'] / 1000:.0f}k tokens")
        except Exception as e:
            print(f"  [{m['id']}] refine failed: {str(e)[:100]}")
            with lock:
                state["fail"] += 1
                nf = state["fail"]
            if nf >= max(2, workers):
                ok, why = healthcheck(model, backend)
                if ok:
                    with lock:
                        state["fail"] = 0
                elif not stop.is_set():
                    print(f"[refine-all] backend down/capped ({why}) -- "
                          "stopping new work; progress is saved per building")
                    stop.set()

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for f in as_completed([ex.submit(one, k, m) for k, m in enumerate(todo)]):
            f.result()
    if stop.is_set():
        raise SystemExit("[refine-all] stopped early -- backend down or capped; "
                         "re-run (or let overnight_refine.sh wait) to resume.")
    if state["scores"]:
        print(f"[refine-all] done: {len(state['scores'])} buildings, mean best "
              f"pass-rate {sum(state['scores']) / len(state['scores']):.3f}, "
              f"~{state['tok'] / 1000:.0f}k tokens. "
              "Re-run with --assemble-only to rebuild the scene with refined specs.")


def main():
    ap = argparse.ArgumentParser(description="Whole-block agent generation")
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--min-area", type=float, default=200.0)
    ap.add_argument("--extra-ids", type=int, nargs="*", default=[],
                    help="building ids to include in agent generation regardless "
                         "of --min-area (small-building trial subset)")
    ap.add_argument("--limit", type=int, default=0, help="cap building count (0 = all)")
    ap.add_argument("--backend", choices=llm.BACKEND_CHOICES, default=None,
                    help="override IMG2CITY_LLM_PROVIDER (.env) for this run")
    ap.add_argument("--model", default=config.SPEC_MODEL,
                    help="spec model; '<provider>:<model>' pins the provider")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--refine-workers", type=int, default=8,
                    help="concurrent refine loops (one Blender render at a time "
                         "behind a lock; SDK calls overlap)")
    ap.add_argument("--assemble-only", action="store_true")
    ap.add_argument("--no-assemble", action="store_true", help="write specs/placements; defer assembly to district controller")
    ap.add_argument("--refine", type=int, default=None, metavar="OSMID",
                    help="run the checklist refinement loop on ONE building with the "
                         "pano-matched camera, update its spec.json, then exit")
    ap.add_argument("--refine-all", action="store_true",
                    help="run the refinement loop on EVERY agent building (largest "
                         "first, resumable; respects --min-area and --limit)")
    ap.add_argument("--refine-status", action="store_true",
                    help="print how many buildings still need refinement, then exit "
                         "(prints 'REMAINING <n>' for the overnight driver)")
    ap.add_argument("--refine-iters", type=int, default=4)
    ap.add_argument("--judge-model", default=config.JUDGE_MODEL)
    ap.add_argument("--inspector-k", type=int, default=3,
                    help="checklist inspector samples per iteration (per-check "
                         "majority vote; 1 = old single-sample behaviour)")
    ap.add_argument("--no-view2", action="store_true",
                    help="ignore a prepared second viewpoint (single-view "
                         "baseline arm of the multi-view experiment)")
    a = ap.parse_args()
    if a.refine:
        refine_building(os.path.abspath(a.out), a.refine, a.refine_iters,
                        a.backend, a.model, a.judge_model, inspector_k=a.inspector_k,
                        use_view2=not a.no_view2)
        return
    if a.refine_status:
        todo = refine_todo(os.path.abspath(a.out), a.min_area, a.limit)
        print("REMAINING %d" % len(todo))
        return
    if a.refine_all:
        refine_all(os.path.abspath(a.out), a.refine_iters, a.backend, a.model,
                   a.judge_model, a.min_area, a.limit, inspector_k=a.inspector_k,
                   workers=a.refine_workers)
        return
    out = os.path.abspath(a.out)
    d = json.load(open(os.path.join(out, "buildings.json")))
    metas, anchor = d["buildings"], d["anchor"]
    for m in metas:
        m["obb"] = obb(m["pts"])
    extra = set(a.extra_ids or [])
    sel = sorted((m for m in metas
                  if m["area_m2"] >= a.min_area or m["id"] in extra),
                 key=lambda m: -m["area_m2"])
    if a.limit:
        sel = sel[:a.limit]
    from img2city.building.generate import area_region
    region = area_region(out)
    print(f"[city] region {region}; {len(sel)} buildings >= {a.min_area} m2 for agent generation "
          f"({len(metas) - len(sel)} stay LoD1)")

    done, failed, total_tok = {}, [], 0

    def one(m):
        bdir = os.path.join(out, "buildings", str(m["id"]))
        os.makedirs(bdir, exist_ok=True)
        sf = os.path.join(bdir, "spec.json")
        pano = None
        try:
            pano = ensure_imagery(m, anchor, bdir)
        except Exception as e:
            print(f"  [{m['id']}] imagery failed: {str(e)[:70]}")
        if os.path.exists(sf):                     # resume: agent already ran
            spec = json.load(open(sf))
            return m, spec, pano, 0
        if not a.assemble_only:
            def _fallback(reason):
                spec = fallback_spec(m)
                with open(sf, "w") as f:
                    json.dump(spec, f, indent=1)
                with open(os.path.join(bdir, "gate.json"), "w") as f:
                    json.dump({"fallback": True, "reason": reason}, f)
                print(f"  [{m['id']}] fallback shell ({reason[:60]})")
                return m, spec, pano, 0
            if m["area_m2"] < 40:                  # sheds: no evidence worth reading
                return _fallback("tiny footprint (<40 m2)")
            if pano is None:                       # satellite-only: don't hallucinate
                return _fallback("no outdoor panorama")
            attempts = 0
            while attempts < 2:                    # ride out transient SDK blips
                try:
                    spec, tok = agent_spec(m, bdir, a.backend, a.model,
                                           region=region)
                    with open(sf, "w") as f:
                        json.dump(spec, f, indent=1)
                    return m, spec, pano, tok
                except UnusableImagery as e:       # agent-judged: views don't show it
                    return _fallback(f"imagery unusable: {str(e)[:70]}")
                except Exception as e:
                    # usage-limit guard (same policy as overnight_refine.sh): a
                    # capped subscription must WAIT for quota, never degrade the
                    # building to a fallback shell -- quota waits don't consume
                    # an attempt
                    capped = False
                    try:
                        ok, why = healthcheck(a.model, a.backend)
                        capped = (not ok) and "limit" in why.lower()
                    except Exception:
                        pass
                    if capped:
                        print(f"  [{m['id']}] usage limit reached -- waiting 20m "
                              "for quota (no fallback)")
                        time.sleep(1200)
                        continue
                    attempts += 1
                    print(f"  [{m['id']}] agent attempt {attempts} failed: {str(e)[:80]}")
                    time.sleep(25)
            return _fallback("agent failed twice")
        return m, None, pano, 0

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for m, spec, pano, tok in ex.map(one, sel):
            total_tok += tok
            if spec is None:
                failed.append(m["id"])
                continue
            rot = front_rotation(m, pano, anchor)
            entry = {"id": m["id"], "desc": spec, "cx": m["obb"][0],
                     "cy": m["obb"][1], "rot": rot}
            # L-shapes / wedges / neighbour-intruding rectangles: build on the
            # TRUE polygon instead (agent keeps floors/floor_h/material; the
            # polygon is OSM's, same contract as the rectangle case)
            if needs_poly(m, out):
                entry["poly"] = m["pts"]
                if m.get("holes"):
                    entry["holes"] = m["holes"]   # courtyards (OSM inner rings
                                                  # or satellite agent reads)
                if m.get("sat_parts"):
                    entry["sat_parts"] = m["sat_parts"]
                entry["obb_frame"] = m["obb"][:5]    # roof_spec placement frame
                entry.update(poly_params(spec))   # same contract as the refine render
                if pano:
                    # rich facade only on the photographed edges (front_edges);
                    # scene coords of the pano, same math as refine_building
                    kx_ = 111320.0 * math.cos(math.radians(anchor["lat0"]))
                    entry["front_edges"] = front_edges(
                        [tuple(q) for q in m["pts"]],
                        ((pano[1] - anchor["lon0"]) * kx_,
                         (pano[0] - anchor["lat0"]) * 110540.0))
            done[m["id"]] = entry
            print(f"  [{m['id']}] spec ok ({m['area_m2']:.0f} m2, "
                  f"{'poly' if 'poly' in entry else 'obb'} · {len(done)}/{len(sel)})")

    print(f"[city] agent specs: {len(done)} ok, {len(failed)} failed {failed[:8]}, "
          f"~{total_tok/1000:.0f}k tokens this pass")
    with open(os.path.join(out, "agent_placements.json"), "w") as f:
        json.dump(list(done.values()), f, indent=1)

    if a.no_assemble:
        print("[city] specs ready; assembly deferred")
        return
    _res, err = assemble(metas, done, out)
    if err:
        raise SystemExit(f"assembly failed: {err}")
    print(f"[city] scene assembled -> {out}/city_agent_aerial.png / _top / _street")


if __name__ == "__main__":
    main()
