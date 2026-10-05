"""img2city/webapp/export_glb.py -- headless .blend -> .glb for the web viewer.

Usage:
  /Applications/Blender.app/Contents/MacOS/Blender -b <area>_textured.blend \
      --python -m img2city.webapp.export_glb -- --out scene.glb --map scene_map.json \
      [--animations]    # keep the traffic keyframes as glTF clips

The city scenes texture buildings with OBJECT-coordinate BOX projection
(city_generate.AGENT_TEXTURES) which glTF cannot represent.  This script
converts every image-textured mesh to a real per-face dominant-axis UV in
object-space METRES (exactly what BOX projection samples, minus the 25%%
edge blend), leaves each material's Mapping scale in place so the glTF
exporter emits it as KHR_texture_transform, and flattens procedural
(noise-driven) materials to their average colour so roads/grass don't come
out white.  Also writes a pick map: mesh name -> {osmid, kind, bbox}.
"""
import argparse
import json
import sys

import bpy


def merge_animation_clips(path, name="traffic"):
    """Rewrite a .glb so all animation clips become ONE clip.

    Blender emits one glTF animation per animated object (even in SCENE
    mode on 4.x); most viewers auto-play only the first clip, so a street of
    keyframed cars shows a single car moving. Channels/samplers are merged
    with sampler indices re-based; accessors and the binary chunk are
    untouched."""
    import struct
    with open(path, "rb") as f:
        magic, ver, _ln = struct.unpack("<III", f.read(12))
        jl, jt = struct.unpack("<II", f.read(8))
        js = json.loads(f.read(jl))
        rest = f.read()
    an = js.get("animations", [])
    if len(an) <= 1:
        return len(an)
    chans, samps = [], []
    for a in an:
        base = len(samps)
        samps.extend(a["samplers"])
        for c in a["channels"]:
            c = dict(c); c["sampler"] += base
            chans.append(c)
    js["animations"] = [{"name": name, "channels": chans, "samplers": samps}]
    jb = json.dumps(js, separators=(",", ":")).encode()
    jb += b" " * ((4 - len(jb) % 4) % 4)
    body = struct.pack("<II", len(jb), jt) + jb + rest
    with open(path, "wb") as f:
        f.write(struct.pack("<III", magic, ver, 12 + len(body)) + body)
    return len(an)


def _arg_list():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


UVNAME = "BoxUV"


def box_uv(me):
    """Per-face dominant-axis planar UV in object-space metres."""
    if UVNAME in me.uv_layers:
        return me.uv_layers[UVNAME]
    uv = me.uv_layers.new(name=UVNAME)
    data = uv.data
    loops, verts = me.loops, me.vertices
    for poly in me.polygons:
        n = poly.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        if az >= ax and az >= ay:
            pick = 2
        elif ax >= ay:
            pick = 0
        else:
            pick = 1
        for li in poly.loop_indices:
            co = verts[loops[li].vertex_index].co
            if pick == 2:
                u, v = co.x, co.y
            elif pick == 0:
                u, v = -co.y if n.x > 0 else co.y, co.z
            else:
                u, v = co.x if n.y > 0 else -co.x, co.z
            data[li].uv = (u, v)
    return uv


def _chain_colors(base):
    """Colour constants feeding the Base Color link chain (Mix A/B, brick
    colours, ColorRamp stops) -- NOT the BSDF's own sockets, whose white
    Specular Tint default would wash the average out."""
    cols = []
    seen = set()
    stack = [lk.from_node for lk in base.links]
    while stack:
        n = stack.pop()
        if n.name in seen:
            continue
        seen.add(n.name)
        for s in n.inputs:
            if s.type == 'RGBA' and not s.is_linked:
                cols.append(tuple(s.default_value)[:3])
            for lk in s.links:
                stack.append(lk.from_node)
        if n.type == 'VALTORGB':
            cols.extend(tuple(e.color)[:3] for e in n.color_ramp.elements)
    return cols


def convert_material(mat):
    """Return True if the material ends up glTF-friendly."""
    if not mat or not mat.use_nodes:
        return
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        return
    base = bsdf.inputs["Base Color"]
    if base.is_linked:
        src = base.links[0].from_node
        # walk back through at most Mix/Mapping style chains to find an image
        seen = set()
        img = None
        stack = [src]
        while stack:
            n = stack.pop()
            if n.name in seen:
                continue
            seen.add(n.name)
            if n.type == 'TEX_IMAGE' and n.image:
                img = n
                break
            for s in n.inputs:
                for lk in s.links:
                    stack.append(lk.from_node)
        if img is not None:
            # rewire: UVMap(BoxUV) -> [existing Mapping if any] -> image (FLAT)
            img.projection = 'FLAT'
            vec_in = img.inputs["Vector"]
            mapping = None
            if vec_in.is_linked and vec_in.links[0].from_node.type == 'MAPPING':
                mapping = vec_in.links[0].from_node
            uvn = nt.nodes.new("ShaderNodeUVMap")
            uvn.uv_map = UVNAME
            if mapping is not None:
                mv = mapping.inputs["Vector"]
                for lk in list(mv.links):
                    nt.links.remove(lk)
                nt.links.new(uvn.outputs["UV"], mv)
            else:
                for lk in list(vec_in.links):
                    nt.links.remove(lk)
                nt.links.new(uvn.outputs["UV"], vec_in)
            # direct image -> base colour (drop hue-shift middlemen the
            # exporter cannot express; palette variants keep their own image)
            if base.links[0].from_node is not img:
                for lk in list(base.links):
                    nt.links.remove(lk)
                nt.links.new(img.outputs["Color"], base)
            return
        # procedural (noise mixes etc.) -> flatten to the average constant
        cols = _chain_colors(base)
        for lk in list(base.links):
            nt.links.remove(lk)
        if cols:
            r = sum(c[0] for c in cols) / len(cols)
            g = sum(c[1] for c in cols) / len(cols)
            b = sum(c[2] for c in cols) / len(cols)
            base.default_value = (r, g, b, 1.0)
    # glass: carry transparency into glTF alpha
    trans = bsdf.inputs.get("Transmission Weight")
    alpha = bsdf.inputs.get("Alpha")
    if trans is not None and not trans.is_linked and trans.default_value > 0.3:
        if alpha is not None and not alpha.is_linked:
            alpha.default_value = 0.35
            mat.blend_method = 'BLEND'
    elif mat.name.split(".")[0].split("_")[0] in ("glass", "vault", "interior"):
        if alpha is not None and not alpha.is_linked and "interior" not in mat.name:
            alpha.default_value = 0.45
            mat.blend_method = 'BLEND'


def building_of(name):
    """(osmid, kind) from a scene object name, else (None, layer-kind)."""
    for pre, kind in (("Agent_", "agent"), ("Bldg_", "lod1")):
        if name.startswith(pre):
            tail = name[len(pre):].split(".")[0]
            try:
                return int(tail), kind
            except ValueError:
                return None, kind
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--usdz", default=None,
                    help="also write a .usdz (Apple Quick Look / Preview play "
                         "multi-object animation from USDZ; their glTF import "
                         "animates only the first node)")
    ap.add_argument("--animations", action="store_true",
                    help="keep the traffic keyframes (VehRoot_<i> object "
                         "animation) as glTF animation clips; the viewer plays "
                         "them with an AnimationMixer")
    a = ap.parse_args(_arg_list())

    # UV pass: only meshes that use an image-textured material need BoxUV
    n_uv = 0
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        needs = False
        for sl in ob.material_slots:
            m = sl.material
            if m and m.use_nodes and any(
                    n.type == 'TEX_IMAGE' and n.image for n in m.node_tree.nodes):
                needs = True
                break
        if needs:
            box_uv(ob.data)
            n_uv += 1

    for mat in bpy.data.materials:
        convert_material(mat)

    # pick map + per-building world bbox
    entries = {}
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        osmid, kind = building_of(ob.name)
        if kind is None:
            continue
        mn = [1e18] * 3
        mx = [-1e18] * 3
        for c in ob.bound_box:
            w = ob.matrix_world @ __import__("mathutils").Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
        entries[ob.name] = {"osmid": osmid, "kind": kind,
                            "bbox": [[round(v, 2) for v in mn],
                                     [round(v, 2) for v in mx]]}
    with open(a.map, "w") as f:
        json.dump({"buildings": entries}, f)

    bpy.ops.export_scene.gltf(
        filepath=a.out,
        export_format='GLB',
        export_yup=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
        export_animations=a.animations,
        # ONE clip for the whole scene (all VehRoot_<i> tracks together): most
        # viewers auto-play only the first clip, so per-object actions would
        # show a single car moving (user 08-22)
        **({"export_animation_mode": "SCENE"} if a.animations else {}),
        export_extras=False,
        export_image_format='JPEG',
        export_texture_dir="",
    )
    if a.usdz:
        sc = bpy.context.scene
        # no cameras/lights: Quick Look locks the view to an authored camera
        # (user 08-22: "fixed viewpoint, cannot orbit")
        bpy.ops.wm.usd_export(filepath=a.usdz, export_animation=a.animations,
                              export_textures=True, export_materials=True,
                              export_cameras=False, export_lights=False,
                              convert_orientation=True, export_global_forward_selection='NEGATIVE_Z',
                              export_global_up_selection='Y',
                              selected_objects_only=False, visible_objects_only=True,
                              evaluation_mode='RENDER')
        print("[export_glb] usdz -> %s (animation=%s, %d-%d)" % (
            a.usdz, a.animations, sc.frame_start, sc.frame_end))
    if a.animations:
        n_clips = merge_animation_clips(a.out)
        print("[export_glb] %d animation clips merged into one" % n_clips)
    print("EXPORT_OK uv_meshes=%d picked=%d out=%s" % (n_uv, len(entries), a.out))


if __name__ == "__main__":
    main()
