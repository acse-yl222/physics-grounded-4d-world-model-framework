"""Preserve recovered campus and assemble the bounded museum district in its frame."""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root, agent_src, authoring_path
import bpy, json, sys, math, hashlib, argparse, importlib, shutil
from pathlib import Path
from mathutils import Matrix, Vector
import numpy as np

ROOT = authoring_path()
sys.path.insert(0, str(agent_src()))
from detailed_common import BuildingContext

p = argparse.ArgumentParser()
p.add_argument("--run", required=True)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
from common.storage import Storage, identifier

out = Storage.load().scratch("south_ken", "geometry", identifier(args.run, run=True))
if out.exists():
    raise RuntimeError("Refusing existing run")
rows = {f["id"]: f for f in json.loads((ROOT / "geometry.json").read_text())["buildings"]}
mods = json.loads((agent_src() / "modules.json").read_text())
assert set(mods) == {oid for oid, f in rows.items() if not f.get("assembly_only")}
ledger = {s["id"]: s for s in json.loads((ROOT / "references/sources.json").read_text())}
for oid in mods:
    assert (agent_src() / "buildings" / f"{mods[oid]}.py").exists(), mods[oid]
    for sid in rows[oid]["evidence_source_ids"]:
        s = ledger[sid]
        assert s["geometry_derivation"] == "allowed" or (
            s["kind"] == "text" and s["geometry_derivation"] == "not_used"
        ), sid
        if s["kind"] in ["image", "street_photo", "aerial"]:
            assert s.get("actually_inspected") is True
files = [
    authoring_path(n)
    for n in [
        "geometry.json",
        "context.json",
        "coordinate_contract.json",
        "region.json",
        "interfaces.json",
        "references/sources.json",
        "src/modules.json",
    ]
] + [
    f
    for f in (agent_src()).rglob("*.py")
    if f.parent.name != "buildings" or f.stem in set(mods.values()) | {"__init__"}
]


def snapshot():
    return {
        str(f.relative_to(repo_root())): hashlib.sha256(f.read_bytes()).hexdigest() for f in files
    }


files.extend(
    [
        ROOT / "references/public_realm/tree_module/inputs.json",
        ROOT / "references/public_realm/fixture_module/placement_checks.json",
    ]
)
files.extend(
    ROOT / n
    for n in [
        "references/public_realm/tree_module/position_checks.json",
        "references/public_realm/campus_tree_inventory.json",
        "references/public_realm/fixture_dedup.json",
    ]
)
files.append(ROOT / "references/public_realm/crossing_module/inputs.json")
sources = snapshot()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "references/campus_phase4_recovered.blend"))
scene = bpy.context.scene
campus = [o for o in scene.objects if o.type == "MESH"]
base_ids = {o["research_object_id"] for o in campus}
assert len(base_ids) == len(campus)
# Make the old multi-object buildings easy to edit without changing geometry/materials.
campus_metadata = ROOT / "references/campus/campus_geometry.json"
cdata = json.loads(campus_metadata.read_text()) if campus_metadata.exists() else {"buildings": []}
ctypes = {str(b["id"]): b.get("osm_type", "unknown") for b in cdata["buildings"]}
for ob in campus:
    if ob.get("osm_type"):
        ctypes.setdefault(str(ob.get("osm_id", "")), str(ob["osm_type"]))
cg = bpy.data.collections.new("01 | Inherited Imperial campus")
scene.collection.children.link(cg)
groups = {}
for ob in campus:
    oid = str(ob.get("osm_id", ""))
    key = oid or "site"
    if key not in groups:
        groups[key] = bpy.data.collections.new(
            ("Campus " + ctypes.get(oid, "unknown") + "-" + oid)
            if oid
            else "Campus site and vegetation"
        )
        cg.children.link(groups[key])
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    groups[key].objects.link(ob)
    if oid:
        ob["building_id"] = ctypes.get(oid, "unknown") + "-" + oid
    ob["expansion_status"] = "inherited Phase4 GLB recovery; original geometric detail retained"


def campus_signature():
    return {
        o.name: (
            o.data.as_pointer(),
            len(o.data.vertices),
            len(o.data.polygons),
            tuple(v for r in o.matrix_world for v in r),
            tuple(m.name for m in o.data.materials),
        )
        for o in campus
    }


before = campus_signature()
coef = json.loads((ROOT / "coordinate_contract.json").read_text())["source_xy_to_campus_affine"]
M = Matrix(
    (
        (coef[0][0], coef[0][1], 0, coef[0][2]),
        (coef[1][0], coef[1][1], 0, coef[1][2]),
        (0, 0, 1, 0),
        (0, 0, 0, 1),
    )
)
reports = {}
new = []
for i, (oid, slug) in enumerate(mods.items()):
    if i % 50 == 0:
        print("BUILD_EXPANSION", i, len(mods), flush=True)
    f = rows[oid]
    col = bpy.data.collections.new("Extension " + oid + " | " + f["name"])
    scene.collection.children.link(col)
    old = set(bpy.data.objects)
    r = importlib.import_module("buildings." + slug).build(BuildingContext(col, f), f)
    obs = list(col.all_objects)
    assert set(r["created"]) == {o.name for o in obs}
    assert set(bpy.data.objects) - old == set(obs)
    assert old <= set(bpy.data.objects)
    for ob in obs:
        assert (
            ob.type == "MESH"
            and ob.data.materials
            and all(m is not None for m in ob.data.materials)
        )
        assert all(math.isfinite(x) for v in ob.data.vertices for x in v.co)
        ob.data.transform(M @ ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        ob["research_object_id"] = oid + "::" + ob.name
        ob["building_id"] = oid
        ob["expansion_status"] = (
            "source-informed landmark; unverified details recorded"
            if slug != "urban"
            else "mapped procedural baseline; individual refinement pending"
        )
        if f.get("part_ids"):
            ob["source_part_ids"] = f["part_ids"]
    for e in r.get("interfaces", {}).get("entrances", []):
        if "threshold_xyz" in e:
            e["campus_threshold_xyz"] = list(M @ Vector(e["threshold_xyz"]))
        if "outward_normal" in e:
            e["campus_outward_normal"] = list(
                (M.to_3x3() @ Vector(e["outward_normal"])).normalized()
            )
    reports[oid] = r
    new.extend(obs)
assert campus_signature() == before, "Campus objects changed by independent module"
from site_context import build as site_build

site = site_build(ROOT)
for ob in site:
    if ob.get("semantic_type") in ["road", "ground"]:
        xmin, ymin, xmax, ymax = cdata["site_bounds"]
        for v in ob.data.vertices:
            q = M @ v.co
            dist = math.hypot(max(xmin - q.x, 0, q.x - xmax), max(ymin - q.y, 0, q.y - ymax))
            if dist < 1.0:
                v.co.z = (
                    (0.045 * (1 - dist))
                    if ob["semantic_type"] == "road"
                    else (-0.05 + 0.02 * (1 - dist))
                )
    ob.data.transform(M @ ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    ob["research_object_id"] = "extension::" + ob["research_object_id"]
from public_realm_seam_patch import build as repair_public_seam

seam_report = repair_public_seam(ROOT)
assert campus_signature() == before, "Inherited campus changed during seam repair"
# Coordinator supports use campus coordinates and exact unions of overlapping patches.
from entry_supports import build as build_entry_supports

col = bpy.data.collections.new("Extension | estimated entry support patches")
scene.collection.children.link(col)
ctx = BuildingContext(col, {"name": "Entry approaches"})
support_report = build_entry_supports(ctx, reports)
assert not support_report.get("deferred_group_indices"), "Unresolved entry support groups"
approaches = support_report["approaches"]
site.extend(bpy.data.objects[name] for name in support_report["created"])
from integrate_public_trees import integrate as integrate_trees

tree_objects, tree_report = integrate_trees(ROOT, M)
site.extend(tree_objects)
from integrate_public_fixtures import integrate as integrate_fixtures

fixture_objects, fixture_report = integrate_fixtures(ROOT, M)
site.extend(fixture_objects)
from integrate_public_crossings import integrate as integrate_crossings

crossing_objects, crossing_report = integrate_crossings(ROOT, M)
site.extend(crossing_objects)
assert campus_signature() == before, "Campus changed during public realm integration"
bpy.context.view_layer.update()
allobs = campus + new + site
assert len({o["research_object_id"] for o in allobs}) == len(allobs)
# Scene setup with actual full geometry and east/south light; no detail suppression.
vs = [o.matrix_world @ Vector(c) for o in allobs for c in o.bound_box]
lo = Vector([min(v[i] for v in vs) for i in range(3)])
hi = Vector([max(v[i] for v in vs) for i in range(3)])
centre = (lo + hi) / 2
span = max(hi - lo)
bpy.ops.object.camera_add(location=centre + Vector((0.8, -1.1, 1.0)) * span)
cam = bpy.context.object
cam.name = "Expansion overview camera"
cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type = "ORTHO"
cam.data.ortho_scale = span * 1.48
cam.data.clip_end = 10000
scene.camera = cam
bpy.ops.object.light_add(type="SUN")
sun = bpy.context.object
sun.data.energy = 3.0
sun.rotation_euler = (0.45, 0.5, -0.5)
scene.world = bpy.data.worlds.new("Expansion daylight")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs["Strength"].default_value = 0.8
bg.inputs["Color"].default_value = (0.35, 0.39, 0.46, 1)
scene.render.engine = "CYCLES"
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = 1800
scene.render.resolution_y = 1400
scene.render.resolution_percentage = 100
scene.unit_settings.system = "METRIC"
scene["georeference"] = json.dumps(json.loads((ROOT / "coordinate_contract.json").read_text()))
scene["all_buildings_at_RSM_standard"] = False
out.mkdir(parents=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(out / "expanded_region.blend"), compress=False)
assert snapshot() == sources, "Sources changed during build"
for source_file in files:
    dest = out / "source_snapshot" / source_file.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, dest)
assert snapshot() == sources, "Sources changed while archiving snapshot"
report = {
    "run": args.run,
    "campus_objects_preserved": len(campus),
    "new_building_objects": len(new),
    "site_objects": len(site),
    "new_inventory_records": len(rows),
    "new_integrated_modules": len(mods),
    "campus_inherited_buildings": len(ctypes),
    "sources_sha256": sources,
    "buildings": reports,
    "approaches": approaches,
    "entry_supports": support_report,
    "public_trees": tree_report,
    "public_fixtures": fixture_report,
    "public_crossings": crossing_report,
    "public_road_seam": seam_report,
    "native_compression": False,
    "master_mtime_ns": (out / "expanded_region.blend").stat().st_mtime_ns,
    "numerical_export_verified": False,
    "visual_reviewed": False,
    "all_buildings_at_RSM_standard": False,
    "fully_refined_delivered": False,
}
(out / "build.json").write_text(json.dumps(report, indent=2))
print("EXPANSION_MASTER_SAVED", out, flush=True)
