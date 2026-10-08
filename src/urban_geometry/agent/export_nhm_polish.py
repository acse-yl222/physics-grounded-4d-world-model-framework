from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root, agent_src, authoring_path
import bpy, sys, json, math, importlib
from pathlib import Path
from mathutils import Matrix, Vector

root = authoring_path()
sys.path.insert(0, str(agent_src()))
from detailed_common import BuildingContext

out = root / "exports/nhm-polish-001"
out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
f = next(
    f
    for f in json.loads((root / "geometry.json").read_text())["buildings"]
    if f["id"] == "way-24436446"
)
col = bpy.data.collections.new("NHM polished")
bpy.context.scene.collection.children.link(col)
r = importlib.import_module("buildings.natural_history").build(BuildingContext(col, f), f)
coef = json.loads((root / "coordinate_contract.json").read_text())["source_xy_to_campus_affine"]
M = Matrix(
    (
        (coef[0][0], coef[0][1], 0, coef[0][2]),
        (coef[1][0], coef[1][1], 0, coef[1][2]),
        (0, 0, 1, 0),
        (0, 0, 0, 1),
    )
)
tris = 0
degenerate = 0
for o in col.objects:
    o.data.transform(M @ o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    o["building_id"] = f["id"]
    o["research_object_id"] = f["id"] + "::" + o.name
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
    degenerate += sum(t.area < 1e-10 for t in o.data.loop_triangles)
    assert all(math.isfinite(x) for v in o.data.vertices for x in v.co)
assert degenerate == 0, degenerate
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / "natural_history.blend"), compress=False)
bpy.ops.export_scene.gltf(
    filepath=str(out / "natural_history.glb"), export_format="GLB", export_extras=True
)
r.update(triangles=tris, degenerate_triangles=degenerate)
(out / "build_report.json").write_text(json.dumps(r, indent=2))
# Independent round trip before current renders.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(out / "natural_history.glb"))
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
assert len(obs) == len(r["created"])
points = [o.matrix_world @ Vector(v) for o in obs for v in o.bound_box]
lo = Vector([min(v[i] for v in points) for i in range(3)])
hi = Vector([max(v[i] for v in points) for i in range(3)])
c = (lo + hi) / 2
span = max(hi.x - lo.x, hi.y - lo.y)
s = bpy.context.scene
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.clip_end = 10000
s.camera = cam
bpy.ops.object.light_add(type="SUN")
bpy.context.object.data.energy = 2.5
bpy.context.object.rotation_euler = (0.45, 0.5, -0.5)
s.world = bpy.data.worlds.new("Daylight")
s.world.use_nodes = True
s.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
s.render.engine = "CYCLES"
s.cycles.samples = 8
s.cycles.use_denoising = True
s.render.resolution_x = 1400
s.render.resolution_y = 900
s.render.resolution_percentage = 100
entry = M @ Vector((756.600893, -480.770048, 18))
for name, target, offset, scale in [
    ("overview", c, Vector((span * 0.5, -span, span * 0.65)), span * 1.15),
    ("front", c, Vector((span * 0.13, -span, span * 0.10)), span * 1.1),
    ("roof", c, Vector((0, 0, span)), span * 1.15),
    ("rear", c, Vector((0, span, span * 0.4)), span * 1.15),
    ("entrance", entry, Vector((10, -90, 15)), 75),
]:
    cam.location = target + offset
    cam.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = scale
    s.render.filepath = str(out / (name + ".png"))
    bpy.ops.render.render(write_still=True)
print("NHM_VERIFIED", len(obs), tris, flush=True)
