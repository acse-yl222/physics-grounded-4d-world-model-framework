import bpy, sys, json, time, math
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1 :]
(
    REGION,
    SCOPE,
    GEOMJSON,
    GLB008,
    OUT_GLB,
    REPORT,
    RENDER_DIR,
    TRAFFIC_ROADS,
    TRAFFIC_VEH,
    TRAFFIC_PRED,
    REGION_ROADS,
    BIRDS_NPZ,
) = argv[:12]
ZLIFT = 0.05
t0 = time.time()


def log(*a):
    print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == "MESH" else 0


def bounds(objs):
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return [round(v, 3) for v in lo], [round(v, 3) for v in hi]


bpy.ops.wm.open_mainfile(filepath=REGION)
log("opened region", len(bpy.data.objects))
scope = json.load(open(SCOPE))
ids = set(scope["building_ids"])
rec = {b["id"]: b for b in json.load(open(GEOMJSON))["buildings"]}
region_before = {
    "objects": len([o for o in bpy.data.objects if o.type == "MESH"]),
    "triangles": sum(tris(o) for o in bpy.data.objects),
}
removed = []
for o in list(bpy.data.objects):
    bid = str(o.get("building_id") or "")
    if not bid:
        continue
    r = rec.get(bid, {})
    why = None
    if bid in ids:
        why = "in_central_scope"
    elif str(r.get("parent_building_id") or "") in ids:
        why = "part_of_central_scope_building"
    elif str(r.get("represented_by_id") or "") in ids:
        why = "represented_by_central_scope_id"
    if why:
        removed.append({"name": o.name, "building_id": bid, "reason": why, "triangles": tris(o)})
        bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    if m.users == 0:
        bpy.data.meshes.remove(m)
for c in list(bpy.data.collections):
    if not c.objects and not c.children:
        bpy.data.collections.remove(c)
log("removed region objects", len(removed), "tris", sum(r["triangles"] for r in removed))

before = set(bpy.data.objects.keys())
bpy.ops.import_scene.gltf(filepath=GLB008)
new = [o for o in bpy.data.objects if o.name not in before]
log(
    "imported 008 objects",
    len(new),
    "meshes",
    sum(1 for o in new if o.type == "MESH"),
    "tris",
    sum(tris(o) for o in new),
)
col = bpy.data.collections.new(
    "Central core 008 | central-preview-007 + nhm-polish-001 (web light)"
)
bpy.context.scene.collection.children.link(col)
for o in new:
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    o["central_core_version"] = "008"
    o["source_frame"] = (
        "campus local -> region EPSG:32630 local via inverse coordinate_contract affine"
    )

A = np.array(
    [[0.9971372878088512, 0.03850621238135248], [-0.03860679068166115, 0.9997417959287375]]
)
t = np.array([-700.1750108416061, 238.94679349918735])
Mi = np.linalg.inv(A)
tt = -Mi @ t
T = Matrix(
    ((Mi[0, 0], Mi[0, 1], 0, tt[0]), (Mi[1, 0], Mi[1, 1], 0, tt[1]), (0, 0, 1, ZLIFT), (0, 0, 0, 1))
)
roots = [o for o in new if o.parent is None or o.parent.name in before]
for o in roots:
    o.matrix_world = T @ o.matrix_world
bpy.context.view_layer.update()
log("transformed roots", len(roots))
b008 = bounds(new)
log("008 bounds in region frame", b008)
checks = {}
for o in new:
    if o.type == "MESH" and any(
        k in o.name
        for k in ["Dana Research Centre", "Royal Albert Hall |", "Site | flat ground datum"]
    ):
        checks[o.name] = bounds([o])
log("checks", json.dumps(checks)[:1500])


# ---- tree simplification: replace sparse simplified leaf-card trees with solid low-poly trunk + canopy ----
import bmesh, re, hashlib


def world_bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), Vector(
        (max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))
    )


groups = {}
for o in new:
    if o.type != "MESH":
        continue
    nm = o.name
    if re.match(r"Tree \d+ \|", nm) or nm.startswith("Estimated planting"):
        groups.setdefault(nm, []).append(o)
    else:
        m = re.match(r"Public realm \| (node-\d+) (trunk and branches|editable leaf canopy)", nm)
        if m:
            groups.setdefault("Public realm tree | " + m.group(1), []).append(o)
canopy_mats = sorted(
    [m for m in bpy.data.materials if m.name.startswith("Detailed vegetation | generic broadleaf")],
    key=lambda m: m.name,
)
bark_mat = next(
    (m for m in bpy.data.materials if m.name.startswith("Site detail | mottled plane-tree bark")),
    None,
)
if not canopy_mats:
    cm = bpy.data.materials.new("Simplified tree | canopy")
    cm.use_nodes = True
    cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.2, 0.03, 1)
    canopy_mats = [cm]
if bark_mat is None:
    bark_mat = bpy.data.materials.new("Simplified tree | bark")
    bark_mat.use_nodes = True
    bark_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        0.23,
        0.19,
        0.14,
        1,
    )
canopy_meshes = []
for i, m in enumerate(canopy_mats):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
    me = bpy.data.meshes.new(f"Simplified tree | canopy {i:02d}")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(m)
    canopy_meshes.append(me)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=1.0, radius2=0.75, depth=1.0)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.5))
trunk_mesh = bpy.data.meshes.new("Simplified tree | trunk")
bm.to_mesh(trunk_mesh)
bm.free()
trunk_mesh.materials.append(bark_mat)
created = []
tree_log = []
orig_tris = 0
orig_objs = 0
tree_obj_names = {o.name for objs in groups.values() for o in objs}
keep_names = [o.name for o in new if o.name not in tree_obj_names]
for key, objs in groups.items():
    lo, hi = world_bounds(objs)
    H = hi.z - lo.z
    r = max(hi.x - lo.x, hi.y - lo.y) / 2
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    if H < 1.5:
        continue
    r = min(max(r, 0.8), 0.6 * H)
    trunk_h = 0.45 * H
    trunk_r = min(max(0.035 * H, 0.12), 0.6)
    props = {k: objs[0][k] for k in objs[0].keys() if not k.startswith("_")}
    h = int(hashlib.sha1(key.encode()).hexdigest(), 16)
    canopy = bpy.data.objects.new(
        key + " | simplified canopy", canopy_meshes[h % len(canopy_meshes)]
    )
    canopy.location = (cx, cy, lo.z + 0.675 * H)
    canopy.scale = (r, r, 0.325 * H)
    trunk = bpy.data.objects.new(key + " | simplified trunk", trunk_mesh)
    trunk.location = (cx, cy, lo.z)
    trunk.scale = (trunk_r, trunk_r, trunk_h)
    for ob in (canopy, trunk):
        for k, v in props.items():
            ob[k] = v
        ob["simplified_tree"] = True
        ob["tree_height_m"] = round(H, 2)
        ob["canopy_radius_m"] = round(r, 2)
        col.objects.link(ob)
        created.append(ob)
    orig_tris += sum(tris(o) for o in objs)
    orig_objs += len(objs)
    tree_log.append(
        {
            "tree": key,
            "height_m": round(H, 2),
            "radius_m": round(r, 2),
            "xy": [round(cx, 2), round(cy, 2)],
            "original_objects": len(objs),
        }
    )
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    if m.users == 0:
        bpy.data.meshes.remove(m)
new = [bpy.data.objects[n] for n in keep_names if n in bpy.data.objects] + created
tree_stats = {
    "trees_replaced": len(tree_log),
    "original_objects": orig_objs,
    "original_triangles": orig_tris,
    "new_objects": len(created),
    "new_triangles": sum(tris(o) for o in created),
    "shape": "8-segment tapered trunk cylinder (0-45% height) + 12x8 ellipsoid canopy (35-100% height), radius from original bounds, 6 broadleaf shades kept",
    "trees": tree_log,
}
log(
    "trees simplified",
    tree_stats["trees_replaced"],
    "objs",
    orig_objs,
    "->",
    len(created),
    "tris",
    orig_tris,
    "->",
    tree_stats["new_triangles"],
)

# ---- ground unification: extend the 008 authored ground tiles (stone 4.8 m, asphalt 2.4 m, grass 6 m) to the region site meshes ----
TILE = {"paving": 4.8, "asphalt": 2.4, "grass": 6.0}


def find_mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = next((x for x in bpy.data.materials if x.name.startswith(name)), None)
    if m is None:
        raise RuntimeError("008 material not found: " + name)
    return m


MAT = {
    "paving": find_mat("Unified campus and district | paving"),
    "asphalt": find_mat("Central preview | asphalt | authored tile"),
    "grass": find_mat("Central preview | grass | authored tile"),
}
ROLE = {"ground": "paving", "path": "paving", "road": "asphalt", "park": "grass"}


def planar_uv(o, tile):
    me = o.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    me.uv_layers.active = uv
    uv.active_render = True
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    idx = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", idx)
    M = np.array(o.matrix_world)
    world = co @ M[:3, :3].T + M[:3, 3]
    uv.data.foreach_set("uv", (world[idx, :2] / tile).astype(np.float32).ravel())


unified = []
for o in bpy.data.objects:
    if o.type != "MESH" or o.name not in before or o.get("building_id"):
        continue
    kind = ROLE.get(str(o.get("semantic_type") or ""))
    if not kind:
        continue
    old = [m.name for m in o.data.materials if m]
    planar_uv(o, TILE[kind])
    o.data.materials.clear()
    o.data.materials.append(MAT[kind])
    unified.append(
        {
            "object": o.name,
            "semantic_type": o.get("semantic_type"),
            "old_materials": old,
            "new_material": MAT[kind].name,
            "uv_tile_m": TILE[kind],
        }
    )
plinth = bpy.data.materials.get("Campus | presentation base")
if plinth and plinth.use_nodes:
    bs = next((n for n in plinth.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bs:
        bs.inputs["Base Color"].default_value = (
            0.364,
            0.352,
            0.304,
            1.0,
        )  # linear mean of stone_albedo, hides the plinth edge at the seam
log("ground unified", len(unified), [u["object"] for u in unified][:6])

# ---- traffic layer: OSM road attributes (75 ways) + simulated vehicle tracks, both already in the region frame ----
road_json = json.load(open(TRAFFIC_ROADS))
veh_json = json.load(open(TRAFFIC_VEH))
tcol = bpy.data.collections.new("Traffic | OSM roads and simulated vehicles (South Kensington)")
bpy.context.scene.collection.children.link(tcol)
HW_COL = {
    "trunk": (0.80, 0.20, 0.12, 1),
    "trunk_link": (0.80, 0.20, 0.12, 1),
    "primary": (0.90, 0.50, 0.12, 1),
    "primary_link": (0.90, 0.50, 0.12, 1),
    "secondary": (0.90, 0.75, 0.20, 1),
    "tertiary": (0.85, 0.85, 0.25, 1),
    "residential": (0.85, 0.85, 0.85, 1),
    "unclassified": (0.65, 0.65, 0.65, 1),
    "service": (0.45, 0.55, 0.70, 1),
    "living_street": (0.45, 0.70, 0.45, 1),
}
tmats = {}


def traffic_mat(name, col, emit=0.35):
    if name in tmats:
        return tmats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = col
    bs.inputs["Roughness"].default_value = 0.6
    m.diffuse_color = col  # viewport/Workbench colour so review renders match the glTF base colour
    try:
        bs.inputs["Emission Color"].default_value = col
        bs.inputs["Emission Strength"].default_value = emit
    except KeyError:
        pass
    tmats[name] = m
    return m


def ribbon_mesh(name, pts, width, z):
    P = np.array(pts, float)
    n = len(P)
    verts = []
    faces = []
    for i in range(n):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, n - 1)]
        d = b - a
        L = float(np.hypot(*d)) or 1.0
        nx, ny = -d[1] / L, d[0] / L
        verts.append((P[i, 0] + nx * width / 2, P[i, 1] + ny * width / 2, z))
        verts.append((P[i, 0] - nx * width / 2, P[i, 1] - ny * width / 2, z))
    for i in range(n - 1):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return me


ROAD_Z = ZLIFT + 0.20
road_objs = []
region_roads = json.load(open(REGION_ROADS))
road_json["roads"] = region_roads["roads"]
for r in road_json["roads"]:
    hw = r["highway"]
    m = traffic_mat("Traffic | road class | " + hw, HW_COL.get(hw, (0.7, 0.7, 0.7, 1)))
    me = ribbon_mesh(
        f"Traffic road | {r.get('name') or 'unnamed'} | osm-{r['osm_id']}",
        r["xy"],
        1.2 if r["highway"] in ("service", "living_street") else 1.6,
        ROAD_Z,
    )
    me.materials.append(m)
    ob = bpy.data.objects.new(me.name, me)
    tcol.objects.link(ob)
    for k in [
        "osm_id",
        "name",
        "highway",
        "lanes",
        "lanes_basis",
        "lanes_forward",
        "lanes_backward",
        "maxspeed",
        "oneway",
        "surface",
        "lit",
        "width_m",
        "length_m",
        "in_traffic_simulation",
        "sim_mean_vehicles_present",
        "sim_mean_speed_mps",
        "sim_vehicle_samples",
    ]:
        if r.get(k) is not None:
            ob[k] = r[k]
    ob["layer"] = "traffic_road"
    ob["semantic_type"] = "traffic_road_centreline"
    road_objs.append(ob)
# vehicles: shared box mesh, animated location/heading, scale 0 when absent
FPS = int(round(1.0 / veh_json["meta"]["dt_s"]))
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = 0
scene.frame_end = int(round(veh_json["meta"]["duration_s"] * FPS))
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.scale(bm, vec=(4.4, 1.8, 1.5), verts=bm.verts)
bmesh.ops.translate(bm, vec=(0, 0, 0.75), verts=bm.verts)
car_mesh = bpy.data.meshes.new("Traffic | vehicle box 4.4x1.8x1.5")
bm.to_mesh(car_mesh)
bm.free()
palette = [
    (0.85, 0.85, 0.88, 1),
    (0.15, 0.15, 0.17, 1),
    (0.6, 0.62, 0.65, 1),
    (0.55, 0.1, 0.1, 1),
    (0.1, 0.2, 0.5, 1),
    (0.8, 0.8, 0.8, 1),
]
car_meshes = []
for i, c in enumerate(palette):
    me = car_mesh.copy()
    me.name = f"Traffic | vehicle box {i}"
    me.materials.append(traffic_mat(f"Traffic | vehicle paint {i}", c, 0.0))
    car_meshes.append(me)
bpy.data.meshes.remove(car_mesh)
veh_objs = []
for v in veh_json["vehicles"]:
    tr = v["track"]
    ob = bpy.data.objects.new(
        f"Traffic vehicle | sim-{v['id']:03d}", car_meshes[v["id"] % len(car_meshes)]
    )
    tcol.objects.link(ob)
    ob["layer"] = "traffic_vehicle"
    ob["vehicle_id"] = v["id"]
    ob["entry"] = v["entry"]
    ob["t_start_s"] = tr[0]["t_s"]
    ob["t_end_s"] = tr[-1]["t_s"]
    ob["source"] = "simulated (IDM + signals), not observed"
    ob.rotation_mode = "XYZ"
    f0 = int(round(tr[0]["t_s"] * FPS))
    f1 = int(round(tr[-1]["t_s"] * FPS))
    ob.scale = (0, 0, 0)
    if f0 > 0:
        ob.keyframe_insert("scale", frame=f0 - 1)
    ob.scale = (1, 1, 1)
    ob.keyframe_insert("scale", frame=f0)
    ob.keyframe_insert("scale", frame=f1)
    if f1 < scene.frame_end:
        ob.scale = (0, 0, 0)
        ob.keyframe_insert("scale", frame=f1 + 1)
    prev = None
    for p in tr:
        f = int(round(p["t_s"] * FPS))
        ob.location = (p["x"], p["y"], ZLIFT + 0.10)
        h = p["heading_rad"]
        if prev is not None:
            while h - prev > math.pi:
                h -= 2 * math.pi
            while h - prev < -math.pi:
                h += 2 * math.pi
        prev = h
        ob.rotation_euler = (0, 0, h)
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("rotation_euler", frame=f)
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR" if not fc.data_path.startswith("scale") else "CONSTANT"
    veh_objs.append(ob)
traffic_stats = {
    "roads": len(road_objs),
    "roads_meta": region_roads["meta"],
    "vehicles": len(veh_objs),
    "fps": FPS,
    "frames": scene.frame_end,
    "duration_s": veh_json["meta"]["duration_s"],
    "meta": veh_json["meta"],
    "road_band_width_m": 1.6,
    "road_band_z_m": ROAD_Z,
}
log(
    "traffic layer",
    len(road_objs),
    "roads",
    len(veh_objs),
    "vehicles",
    scene.frame_end,
    "frames @",
    FPS,
    "fps",
)

# ---- traffic model predictions: per vehicle per 5 s window, 3 s horizon, shown only during their window ----
pred_json = json.load(open(TRAFFIC_PRED))
pm = pred_json["meta"]
pred_mat = traffic_mat("Traffic | model prediction (3 s horizon)", (0.95, 0.15, 0.75, 1), 0.8)
PRED_Z = ZLIFT + 1.6
pred_objs = []
for p in pred_json["predictions"]:
    pts = [[p["anchor"]["x"], p["anchor"]["y"]]] + [[q["x"], q["y"]] for q in p["predicted"]]
    if len(pts) < 2:
        continue
    me = ribbon_mesh(
        f"Traffic prediction | sim-{p['vehicle_id']:03d} | t={p['t_last_s']:.1f}s", pts, 0.6, PRED_Z
    )
    me.materials.append(pred_mat)
    ob = bpy.data.objects.new(me.name, me)
    tcol.objects.link(ob)
    ob["layer"] = "traffic_prediction"
    ob["vehicle_id"] = p["vehicle_id"]
    ob["window_t_start_s"] = p["window_t_start_s"]
    ob["t_last_s"] = p["t_last_s"]
    ob["horizon_s"] = pm["horizon_s"]
    ob["model"] = pm["model"]
    if p.get("ade_m") is not None:
        ob["ade_m_vs_simulator"] = p["ade_m"]
        ob["fde_m_vs_simulator"] = p["fde_m"]
    f0 = int(round(p["t_last_s"] * FPS))
    f1 = int(round((p["t_last_s"] + pm["horizon_s"]) * FPS))
    ob.scale = (0, 0, 0)
    if f0 > 0:
        ob.keyframe_insert("scale", frame=f0 - 1)
    ob.scale = (1, 1, 1)
    ob.keyframe_insert("scale", frame=f0)
    ob.keyframe_insert("scale", frame=f1)
    if f1 < scene.frame_end:
        ob.scale = (0, 0, 0)
        ob.keyframe_insert("scale", frame=f1 + 1)
    for fc in ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"
    pred_objs.append(ob)
traffic_stats["predictions"] = {
    "objects": len(pred_objs),
    "windows": pm["windows"],
    "horizon_s": pm["horizon_s"],
    "model": pm["model"],
    "training": pm["training"],
    "ade_m_overall_vs_simulator": pm["ade_m_overall"],
    "consistency": pm.get("consistency_with_embedded_vehicle_tracks_m"),
}
log("traffic predictions", len(pred_objs))

# ---- birds layer: flock simulation (src/urban_geometry/birds) on the merged city grid, subsampled to the scene fps ----
bnpz = np.load(BIRDS_NPZ, allow_pickle=True)
bpos = bnpz["pos"]
btimes = bnpz["frame_times"]
bstate = bnpz["bstate"]
bdt = float(bnpz["dt"])
nb = bpos.shape[1]
bcol = bpy.data.collections.new("Birds | flock simulation (src/urban_geometry/birds)")
bpy.context.scene.collection.children.link(bcol)
step = max(1, int(round((1.0 / FPS) / bdt)))
sel = np.arange(0, len(btimes), step)
bt = btimes[sel]
bp = bpos[sel]
bird_mat = traffic_mat("Birds | starling body", (0.12, 0.11, 0.13, 1), 0.0)
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.scale(bm, vec=(0.45, 0.28, 0.10), verts=bm.verts)
bird_mesh = bpy.data.meshes.new("Birds | body 0.45x0.28x0.10")
bm.to_mesh(bird_mesh)
bm.free()
bird_mesh.materials.append(bird_mat)
frames = np.round(bt * FPS).astype(float)
bird_objs = []
for i in range(nb):
    ob = bpy.data.objects.new(f"Bird | sim-{i:03d}", bird_mesh)
    bcol.objects.link(ob)
    ob["layer"] = "bird"
    ob["bird_id"] = i
    ob["source"] = "src/urban_geometry/birds flock simulation (starling model), not observed"
    ob["identity_valence_disposition"] = float(bnpz["identity_valence_disposition"][i])
    ob["identity_arousal_excitability"] = float(bnpz["identity_arousal_excitability"][i])
    ob["identity_energy_drain_rate"] = float(bnpz["identity_energy_drain_rate"][i])
    ob.animation_data_create()
    act = bpy.data.actions.new(f"Bird | sim-{i:03d}")
    ob.animation_data.action = act
    for axis in range(3):
        fc = act.fcurves.new(data_path="location", index=axis)
        fc.keyframe_points.add(len(frames))
        co = np.empty(len(frames) * 2)
        co[0::2] = frames
        co[1::2] = bp[:, i, axis]
        fc.keyframe_points.foreach_set("co", co)
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.update()
    ob.location = tuple(bp[0, i])
    bird_objs.append(ob)
wl = json.loads(str(bnpz["world_layout"]))
site_objs = []
for kind, color in (("roosts", (0.9, 0.6, 0.1, 1)), ("forage_sites", (0.2, 0.8, 0.3, 1))):
    for k, s in enumerate(wl.get(kind, [])):
        c = s["center"]
        sz = s["size"]
        me = bpy.data.meshes.new(f"Bird site | {kind[:-1] if kind.endswith('s') else kind} {k}")
        me.from_pydata(
            [
                (c[0] - sz[0] / 2, c[1] - sz[1] / 2, c[2] + 0.3),
                (c[0] + sz[0] / 2, c[1] - sz[1] / 2, c[2] + 0.3),
                (c[0] + sz[0] / 2, c[1] + sz[1] / 2, c[2] + 0.3),
                (c[0] - sz[0] / 2, c[1] + sz[1] / 2, c[2] + 0.3),
            ],
            [],
            [(0, 1, 2, 3)],
        )
        me.update()
        me.materials.append(traffic_mat(f"Birds | {kind} marker", color, 0.5))
        ob = bpy.data.objects.new(me.name, me)
        bcol.objects.link(ob)
        ob["layer"] = "bird_site"
        ob["site_kind"] = kind
        ob["centre_xyz"] = [round(v, 2) for v in c]
        ob["size_m"] = sz
        ob["basis"] = (
            "auto-generated by birds/sim/world_gen.py from the voxel grid (rooftop / open ground)"
        )
        site_objs.append(ob)
scene.frame_end = max(scene.frame_end, int(frames[-1]))
states = np.unique(bstate[sel]).tolist()
bird_stats = {
    "birds": nb,
    "sim_dt_s": bdt,
    "sim_steps": int(len(btimes)),
    "duration_s": float(btimes[-1]),
    "keyframes_per_bird": int(len(frames)),
    "keyframe_dt_s": step * bdt,
    "sites": {"roosts": len(wl.get("roosts", [])), "forage_sites": len(wl.get("forage_sites", []))},
    "behaviour_states_seen": states,
    "grid": "128x128x64 voxels, 8 m XY / 1 m Z, origin (200,-700,0) region frame; buildings + solid trees only",
    "seed": int(bnpz["seed"]),
}
log("birds layer", nb, "birds", len(frames), "keyframes each; sites", bird_stats["sites"])

allm = [o for o in bpy.data.objects if o.type == "MESH"]
stats = {
    "objects": len(allm),
    "triangles": sum(tris(o) for o in allm),
    "bounds": bounds(allm),
    "materials": len(bpy.data.materials),
    "images": [(i.name, list(i.size)) for i in bpy.data.images],
}
log("merged stats", stats)

kw = dict(
    filepath=OUT_GLB,
    export_format="GLB",
    export_apply=True,
    export_extras=True,
    export_yup=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_animations=True,
    export_animation_mode="SCENE",
    export_frame_step=1,
    export_force_sampling=True,
    export_optimize_animation_size=True,
    export_skins=False,
    export_morph=False,
    export_lights=False,
    export_cameras=False,
    export_draco_mesh_compression_enable=False,
)
try:
    bpy.ops.export_scene.gltf(**kw)
except TypeError as e:
    log("export kw fallback", e)
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB,
        export_format="GLB",
        export_apply=True,
        export_extras=True,
        export_animations=True,
        export_draco_mesh_compression_enable=False,
    )
log("exported", OUT_GLB)

json.dump(
    {
        "region_source": REGION,
        "core008_source": GLB008,
        "zlift_m": ZLIFT,
        "campus_to_region_matrix": [list(map(float, row)) for row in T],
        "region_before": region_before,
        "removed": removed,
        "imported_008": {
            "objects": len(new),
            "triangles": sum(tris(o) for o in new),
            "bounds": b008,
        },
        "checks": checks,
        "merged": stats,
        "ground_unification": {
            "rule": "region site meshes re-materialed with the 008 authored tiles using world-XY planar UVs",
            "tiles_m": TILE,
            "objects": unified,
            "plinth_material_recoloured_to_stone_mean": True,
        },
        "tree_simplification": tree_stats,
        "traffic_layer": traffic_stats,
        "birds_layer": bird_stats,
    },
    open(REPORT, "w"),
    indent=1,
    ensure_ascii=False,
)
log("report written")

# ---- renders (best effort) ----
import os

os.makedirs(RENDER_DIR, exist_ok=True)
scene = bpy.context.scene
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
sun_d = bpy.data.lights.new("sun", "SUN")
sun_d.energy = 3.0
sun = bpy.data.objects.new("sun", sun_d)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
if scene.world is None:
    scene.world = bpy.data.worlds.new("w")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.75, 0.8, 0.9, 1)
    bg.inputs[1].default_value = 1.0
scene.render.resolution_x = 1800
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"


def look(cam, pos, target):
    cam.location = Vector(pos)
    d = Vector(target) - Vector(pos)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


views = {
    "seam_overview": ((675 + 450, -200 - 750, 520), (675, -200, 0)),
    "region_wide": ((0 + 900, -1900, 1300), (300, -100, 0)),
    "nhm_museums": ((755 + 180, -480 - 330, 190), (720, -420, 10)),
    "seam_sw": ((430 + 120, -560 - 420, 330), (520, -380, 0)),
    "seam_north": ((700 - 500, 150 + 500, 420), (640, 60, 0)),
    "traffic_quarter": ((960 + 120, -500 - 330, 210), (950, -460, 5)),
    "birds_campus": ((600 + 350, -150 - 500, 300), (560, -120, 20)),
}


def render_all(engine):
    scene.frame_set(int(scene.frame_end * 0.5))
    scene.render.engine = engine
    if engine == "BLENDER_WORKBENCH":
        sh = scene.display.shading
        sh.light = "STUDIO"
        sh.color_type = "TEXTURE"
        sh.show_shadows = False
        sh.show_cavity = False
        scene.view_settings.view_transform = "Standard"
    if engine == "CYCLES":
        scene.cycles.samples = 24
        scene.cycles.device = "CPU"
        scene.cycles.use_denoising = True
    for name, (p, tg) in views.items():
        look(cam, p, tg)
        cam_data.lens = 35
        cam_data.clip_end = 6000
        scene.render.filepath = os.path.join(RENDER_DIR, name + ".png")
        bpy.ops.render.render(write_still=True)
        log("rendered", engine, name)


try:
    render_all("BLENDER_WORKBENCH")
except Exception as e:
    log("workbench failed", e)
    try:
        render_all("CYCLES")
    except Exception as e2:
        log("cycles failed", e2)
log("DONE")
