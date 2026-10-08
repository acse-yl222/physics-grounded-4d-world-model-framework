"""Render the actual full expansion master, without hiding inherited geometry."""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root, agent_src, authoring_path
import bpy, json, sys, argparse
from pathlib import Path
from mathutils import Vector

ROOT = authoring_path()
p = argparse.ArgumentParser()
p.add_argument("--run", required=True)
p.add_argument("--names", default="")
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
out = ROOT / "exports" / args.run
bpy.ops.wm.open_mainfile(filepath=str(out / "expanded_region.blend"))
scene = bpy.context.scene
cam = scene.camera
scene.render.resolution_x = 1800
scene.render.resolution_y = 1400
scene.render.resolution_percentage = 100
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.use_persistent_data = True
build = json.loads((out / "build.json").read_text())
views = []


def bounds(obs):
    vs = [o.matrix_world @ Vector(p) for o in obs for p in o.bound_box]
    lo = Vector([min(v[i] for v in vs) for i in range(3)])
    hi = Vector([max(v[i] for v in vs) for i in range(3)])
    return (lo + hi) / 2, hi - lo


c, s = bounds([o for o in scene.objects if o.type == "MESH"])
span = max(s)
views.extend(
    [
        ("overview", c, c + Vector((0.85, -1.1, 0.95)) * span, span * 1.48),
        ("plan", c, c + Vector((0, 0, span * 2)), max(s.x, s.y * 1800 / 1400) * 1.12),
    ]
)
for oid, slug in [
    ("way-372860405", "royal_albert_hall"),
    ("way-27765400", "royal_college_music"),
    ("way-24436446", "natural_history"),
    ("way-27765411", "science_museum"),
    ("relation-29795", "victoria_albert"),
    ("way-4959880", "dana_research"),
]:
    obs = [o for o in scene.objects if o.get("building_id") == oid]
    c, s = bounds(obs)
    span = max(s.x, s.y)
    n = (
        Vector((-1, -0.15, 0))
        if slug == "dana_research"
        else Vector((1, 0.13, 0))
        if slug == "science_museum"
        else Vector((-0.12, 1, 0))
        if slug in ("royal_college_music", "royal_albert_hall")
        else Vector((0.1, -1, 0))
    )
    entries = build["buildings"][oid].get("interfaces", {}).get("entrances", [])
    # Elevated oblique full-scene view gives context and avoids most opposite buildings.
    views.append(
        (
            slug + "_context",
            c,
            c + n * span * 0.85 + Vector((span * 0.12, 0, span * 0.8)),
            span * 1.24,
        )
    )
    if entries and "campus_threshold_xyz" in entries[0]:
        e = entries[0]
        t = Vector(e["campus_threshold_xyz"]) + Vector((0, 0, 4.5))
        n = Vector(e["campus_outward_normal"])
        views.append((slug + "_entrance", t, t + n * 14 + Vector((0, 0, 3)), 18.0))
    # Roof and rear both shown from the opposite elevated approach.
    views.append((slug + "_rear_roof", c, c - n * span * 0.85 + Vector((0, 0, span)), span * 1.25))
selection = set(args.names.split(",")) if args.names else None
renderdir = out / "renders"
renderdir.mkdir(exist_ok=True)
manifest = []
for name, target, loc, scale in views:
    if selection and name not in selection:
        continue
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = scale
    cam.data.clip_end = 20000
    scene.render.filepath = str(renderdir / (name + ".png"))
    bpy.ops.render.render(write_still=True)
    manifest.append(
        {
            "name": name,
            "file": str((renderdir / (name + ".png")).relative_to(ROOT)),
            "target": list(target),
            "camera": list(loc),
            "scale": scale,
            "master_mtime_ns": (out / "expanded_region.blend").stat().st_mtime_ns,
            "all_geometry_visible": True,
            "visually_reviewed": False,
        }
    )
    print("EXPANSION_RENDERED", name, flush=True)
manifestpath = out / "render_manifest.json"
previous = json.loads(manifestpath.read_text()) if manifestpath.exists() else []
combined = {v["name"]: v for v in previous}
combined.update({v["name"]: v for v in manifest})
manifestpath.write_text(json.dumps(list(combined.values()), indent=2))
