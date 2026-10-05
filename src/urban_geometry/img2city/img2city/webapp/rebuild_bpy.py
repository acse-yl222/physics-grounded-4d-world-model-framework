"""img2city/webapp/rebuild_bpy.py -- ALL Blender-side building work for the web app, one tool,
three modes (consolidated 08-22; formerly rebuild_bpy / rebuild_fast_bpy /
rebuild_worker_bpy / build_desc_bpy):

  sync    Blender -b <area>_textured.blend --python -m img2city.webapp.rebuild_bpy -- --job J
          Replace Agent_<id> inside the packed city blend, save it, export a
          world-posed mini glb.  Used by the background persistence thread.

  worker  Blender -b --python -m img2city.webapp.rebuild_bpy -- --worker --components KIT
          Stay resident with the parts kit loaded once; read job-file paths
          from stdin, build each in an empty scene, export the mini glb.
          Powers the editor's interactive preview loop (seconds, not minutes).

  desc    Blender -b --python -m img2city.webapp.rebuild_bpy -- --desc J
          Build a bare build_building() description in an empty scene and
          export it (photo-upload page).

Job JSON: {entry|desc, components_src, texture_dir?, glb_out, save_blend?}.
Worker protocol: stdin line = job path (or QUIT); stdout = "DONE ..."/"FAIL ...".
"""
import json
import os
import sys
import traceback

import bpy
import mathutils as _mu

# runs inside Blender's python (no img2city install): sibling import by path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_glb  # noqa: E402

_TEX_SCALE = {"brick": (1.2, 0.9), "stucco": (1.6, 0.8), "slate": (6.0, 0.85)}
_CH_OF = {"brick": "brick", "stucco": "stucco", "slate_dark": "slate", "slate": "slate"}


def _tex_mat(bid, ch, path):
    """Per-building photo-texture material (same recipe as AGENT_TEXTURES)."""
    name = "%s_%d" % (ch, bid)
    m = bpy.data.materials.get(name)
    if m:
        return m
    metres, rough = _TEX_SCALE[ch]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.projection = 'BOX'
    tex.projection_blend = 0.25
    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.inputs["Scale"].default_value = (1.0 / metres, 1.0 / metres, 1.0 / metres)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Object"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def _build_entry(kit, entry):
    """Placement entry -> ([objects], pose matrix or None); the poly/OBB split
    mirrors city_generate.AGENT_CHUNK exactly."""
    if entry.get("poly"):
        objs = kit["polygon_terrace"]({
            "pts": entry["poly"], "floors": entry["floors"],
            "floor_h": entry["floor_h"], "wall": entry["wall"],
            "roof_tone": entry.get("roof_tone", "dark"),
            "roof_form": entry.get("roof_form", "valley"),
            "dormers": entry.get("dormers", False),
            "shopfront": entry.get("shopfront", False),
            "shop_edges": entry.get("shop_edges"),
            "podium_floors": entry.get("podium_floors", 0),
            "fins": entry.get("fins"),
            "colonnade": entry.get("colonnade"),
            "balustrade": entry.get("balustrade", False),
            "arch": entry.get("arch", False),
            "arch_row": entry.get("arch_row", 0),
            "ribbon": entry.get("ribbon"),
            "giant": entry.get("giant"),
            "holes": entry.get("holes"),
            "sat_parts": entry.get("sat_parts"),
            "roof_spec": entry.get("roof_spec"),
            "obb_frame": entry.get("obb_frame"),
            "front_edges": entry.get("front_edges"),
            "colors": entry.get("colors")}, entry["id"])
        return objs, None
    objs = kit["build_building"](entry["desc"])
    M = (_mu.Matrix.Translation((entry["cx"], entry["cy"], 0))
         @ _mu.Matrix.Rotation(entry["rot"], 4, 'Z'))
    return objs, M


def _join_as(objs, name, M):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ok = [o for o in objs if o and o.name in bpy.context.scene.objects]
    if not ok:
        raise RuntimeError("empty build")
    for o in ok:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ok[0]
    bpy.ops.object.join()
    j = bpy.context.view_layer.objects.active
    j.name = name
    if M is not None:
        j.matrix_world = M @ j.matrix_world
    return j


def _apply_textures(j, bid, tdir):
    if not (tdir and os.path.isdir(tdir)):
        return
    for sl in j.material_slots:
        base = (sl.material.name.split(".")[0] if sl.material else "")
        ch = _CH_OF.get(base)
        if ch and os.path.exists(os.path.join(tdir, ch + ".png")):
            sl.material = _tex_mat(bid, ch, os.path.join(tdir, ch + ".png"))


def _export_mini(j, glb_out):
    export_glb.box_uv(j.data)
    for sl in j.material_slots:
        if sl.material:
            export_glb.convert_material(sl.material)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    j.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=glb_out, export_format='GLB', use_selection=True,
        export_yup=True, export_apply=True, export_cameras=False,
        export_lights=False, export_animations=False, export_extras=False,
        export_image_format='JPEG')


def _clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    # orphaned meshes otherwise accumulate and slow every later build
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def mode_sync(job):
    """Inside the opened city blend: replace the building, save, export."""
    entry = job["entry"]
    bid = entry["id"]
    for ob in list(bpy.data.objects):
        if ob.name.split(".")[0] in (f"Agent_{bid}", f"Bldg_{bid}"):
            bpy.data.objects.remove(ob, do_unlink=True)
    kit = {}
    exec(open(job["components_src"]).read(), kit)
    kit["ensure_materials"]()
    objs, M = _build_entry(kit, entry)
    j = _join_as(objs, f"Agent_{bid}", M)
    _apply_textures(j, bid, job.get("texture_dir"))
    if job.get("save_blend", True):
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_mainfile(compress=True)
    _export_mini(j, job["glb_out"])
    print("REBUILD_OK id=%d glb=%s" % (bid, job["glb_out"]))


def mode_worker(components_path):
    """Resident preview worker: kit loaded once, jobs streamed on stdin."""
    kit = {}
    exec(open(components_path).read(), kit)
    print("WORKER_READY", flush=True)
    for line in sys.stdin:
        jp = line.strip()
        if not jp:
            continue
        if jp == "QUIT":
            break
        try:
            job = json.load(open(jp))
            _clear_scene()
            # the kit is resident but its MAT cache now points at materials
            # _clear_scene just removed (palette variants are created once per
            # name and reused by name) -- drop the cache or the second build
            # of any building with a measured palette silently degenerates
            # into a stub (found by the edit benchmark, 2026-08-23)
            kit["MAT"].clear()
            kit["ensure_materials"]()
            if "desc" in job:
                objs, M = kit["build_building"](job["desc"]), None
                j = _join_as(objs, "Agent_1", M)
            else:
                entry = job["entry"]
                objs, M = _build_entry(kit, entry)
                j = _join_as(objs, f"Agent_{entry['id']}", M)
                _apply_textures(j, entry["id"], job.get("texture_dir"))
            _export_mini(j, job["glb_out"])
            print("DONE " + job["glb_out"], flush=True)
        except Exception as e:
            traceback.print_exc()
            print("FAIL " + str(e)[:200], flush=True)


def mode_desc(job):
    """Photo page: one description in an empty scene."""
    _clear_scene()
    kit = {}
    exec(open(job["components_src"]).read(), kit)
    kit["ensure_materials"]()
    j = _join_as(kit["build_building"](job["desc"]), "Agent_1", None)
    _export_mini(j, job["glb_out"])
    print("BUILD_OK glb=%s" % job["glb_out"])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--worker" in argv:
        mode_worker(argv[argv.index("--components") + 1])
    elif "--desc" in argv:
        mode_desc(json.load(open(argv[argv.index("--desc") + 1])))
    else:
        mode_sync(json.load(open(argv[argv.index("--job") + 1])))


main()
