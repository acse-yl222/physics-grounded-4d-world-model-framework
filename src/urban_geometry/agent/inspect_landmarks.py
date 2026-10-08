"""Small independent landmark render/geometry inspection, before full integration."""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root, agent_src, authoring_path
import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector

root = authoring_path()
sys.path.insert(0, str(agent_src()))
from detailed_common import BuildingContext
import importlib

rows = {f["id"]: f for f in json.loads((root / "geometry.json").read_text())["buildings"]}
mods = {"way-27765411": "science_museum"}
if "--all" in sys.argv:
    mods.update(
        {
            "way-372860405": "royal_albert_hall",
            "way-27765400": "royal_college_music",
            "way-24436446": "natural_history",
            "relation-29795": "victoria_albert",
        }
    )
out = root / "renders/isolated"
out.mkdir(parents=True, exist_ok=True)
for oid, slug in mods.items():
    if not (agent_src() / "buildings" / f"{slug}.py").exists():
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    col = bpy.data.collections.new(slug)
    scene.collection.children.link(col)
    report = importlib.import_module("buildings." + slug).build(
        BuildingContext(col, rows[oid]), rows[oid]
    )
    obs = list(col.all_objects)
    assert set(report["created"]) == {o.name for o in obs}
    degenerate = 0
    triangles = 0
    for ob in obs:
        ob.data.calc_loop_triangles()
        triangles += len(ob.data.loop_triangles)
        degenerate += sum(t.area < 1e-10 for t in ob.data.loop_triangles)
        assert all(math.isfinite(v) for p in ob.data.vertices for v in p.co)
    vs = [o.matrix_world @ Vector(p) for o in obs for p in o.bound_box]
    lo = Vector([min(p[i] for p in vs) for i in range(3)])
    hi = Vector([max(p[i] for p in vs) for i in range(3)])
    centre = (lo + hi) / 2
    span = max(hi.x - lo.x, hi.y - lo.y)
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.clip_end = 10000
    scene.camera = cam
    bpy.ops.object.light_add(type="SUN")
    bpy.context.object.data.energy = 3.0
    bpy.context.object.rotation_euler = (0.45, 0.5, -0.5)
    scene.world = bpy.data.worlds.new("Inspection world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.39, 0.46, 1)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    entries = report.get("interfaces", {}).get("entrances", [])
    front = (
        Vector((1, 0.16, 0))
        if slug == "science_museum"
        else Vector((0, 1, 0))
        if slug == "royal_college_music"
        else Vector((0, -1, 0))
    )
    views = [
        ("overview", centre, centre + Vector((span * 0.6, -span, span * 0.7)), span * 1.3),
        ("front", centre, centre + front * span + Vector((0, 0, span * 0.12)), span * 1.18),
        ("roof", centre, centre + Vector((0, -1, span * 1.4)), span * 1.2),
        ("rear", centre, centre - front * span + Vector((0, 0, span * 0.25)), span * 1.2),
    ]
    if slug == "science_museum":
        fc = Vector((901.68, -295.2, 13))
        views[1] = ("front", fc, fc + front * 100 + Vector((0, 0, 5)), 85.0)
    if entries:
        e = entries[0]
        target = Vector(e["threshold_xyz"]) + Vector((0, 0, 4.5))
        views.append(
            (
                "entrance",
                target,
                target + Vector(e["outward_normal"]) * 20 + Vector((0, 0, 3)),
                17.0,
            )
        )
    for name, target, loc, scale in views:
        cam.location = loc
        cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = scale
        scene.render.filepath = str(out / (slug + "_" + name + ".png"))
        bpy.ops.render.render(write_still=True)
    report.update(
        triangles=triangles, degenerate_triangles=degenerate, isolated=True, visual_reviewed=False
    )
    (out / (slug + ".json")).write_text(json.dumps(report, indent=2))
    print("LANDMARK_INSPECT", slug, triangles, degenerate, flush=True)
