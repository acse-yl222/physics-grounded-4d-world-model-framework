"""Run: blender --background --python src/urban_geometry/uav/generate_models.py"""

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent


def material(name, color, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = 0.32
    return m


def finish(obj, name, mat):
    obj.name = name
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def ellipsoid(name, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=loc)
    o = bpy.context.object
    o.scale = scale
    return finish(o, name, mat)


def box(name, loc, scale, mat, bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = o.modifiers.new("Rounded edges", "BEVEL")
    mod.width = bevel
    mod.segments = 3
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o, name, mat)


def rod(name, a, b, radius, mat):
    d = Vector(b) - Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=20, radius=radius, depth=d.length, location=(Vector(a) + Vector(b)) / 2
    )
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return finish(o, name, mat)


def rotor(name, loc, radius, angle=0, vertical=False):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = loc
    if vertical:
        root.rotation_euler.x = math.pi / 2
    root.rotation_euler.z = angle
    hub = ellipsoid(name + "_hub", (0, 0, 0), (0.027, 0.027, 0.022), metal)
    hub.parent = root
    for i in range(2):
        o = ellipsoid(
            name + "_blade_" + str(i),
            ((-1 if i else 1) * radius * 0.49, 0, 0),
            (radius * 0.51, radius * 0.105, 0.006),
            carbon,
        )
        o.rotation_euler.x = 0.13
        o.parent = root


def camera(loc, size=1):
    x, y, z = loc
    rod("Gimbal_mount", (x, y, z + 0.08 * size), loc, 0.018 * size, metal)
    ellipsoid("Camera_gimbal", loc, (0.06 * size, 0.052 * size, 0.046 * size), carbon)
    rod("Camera_lens", (x, y - 0.04 * size, z), (x, y - 0.065 * size, z), 0.028 * size, glass)


def multirotor(count, arm, prop):
    ellipsoid(
        "Upper_shell",
        (0, 0, 0.34),
        (0.15 if count == 4 else 0.23, 0.20 if count == 4 else 0.26, 0.075),
        white if count == 4 else orange,
    )
    box("Lower_chassis", (0, 0, 0.29), (0.23, 0.29, 0.065), carbon)
    box("Battery", (0, 0.035, 0.407), (0.115, 0.19, 0.045), carbon, 0.012)
    for i in range(count):
        t = 2 * math.pi * i / count + math.pi / 4 if count == 4 else 2 * math.pi * i / count
        x, y = arm * math.cos(t), arm * math.sin(t)
        rod(
            "Arm_%02d" % i,
            (x * 0.22, y * 0.22, 0.32),
            (x, y, 0.34),
            0.022 if count == 4 else 0.03,
            carbon,
        )
        rod("Motor_%02d" % i, (x, y, 0.325), (x, y, 0.389), 0.034, metal)
        rotor("Rotor_%02d" % i, (x, y, 0.408), prop, t + 0.25)
        ellipsoid(
            "Navigation_light_%02d" % i,
            (x, y, 0.321),
            (0.018, 0.018, 0.01),
            red if y < 0 else green,
        )
    for side in [-1, 1]:
        for y in [-0.10, 0.10]:
            rod("Landing_strut", (side * 0.10, y, 0.28), (side * 0.19, y, 0.055), 0.012, metal)
        rod("Landing_skid", (side * 0.19, -0.24, 0.04), (side * 0.19, 0.24, 0.04), 0.015, carbon)
    if count == 4:
        camera((0, -0.13, 0.20))
    else:
        box("Cargo_case", (0, 0, 0.16), (0.27, 0.30, 0.17), white)
        for x in [-0.09, 0.09]:
            box("Cargo_strap", (x, 0, 0.16), (0.023, 0.307, 0.178), carbon, 0.003)
        camera((0, -0.27, 0.27), 0.8)
        rod("GPS_mast", (0, 0.12, 0.42), (0, 0.12, 0.52), 0.008, metal)
        ellipsoid("GPS_receiver", (0, 0.12, 0.53), (0.04, 0.04, 0.012), white)


def wing(name, sections, mat):
    verts = []
    for x, front, back, z, thick in sections:
        verts.extend(
            [
                (x, front, z),
                (x, front + (back - front) * 0.3, z + thick),
                (x, back, z),
                (x, front + (back - front) * 0.3, z - thick * 0.4),
            ]
        )
    faces = [(3, 2, 1, 0)]
    for i in range(len(sections) - 1):
        for j in range(4):
            a = i * 4 + j
            b = i * 4 + (j + 1) % 4
            faces.append((a, b, b + 4, a + 4))
    n = len(verts)
    faces.append(tuple(range(n - 4, n)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat)


def fixedwing():
    ellipsoid("Fuselage", (0, 0, 0.30), (0.115, 0.73, 0.12), white)
    ellipsoid("Canopy", (0, -0.29, 0.385), (0.078, 0.23, 0.055), glass)
    for side in [-1, 1]:
        wing(
            "Main_wing",
            [
                (side * 0.065, -0.25, 0.23, 0.32, 0.037),
                (side * 0.85, -0.09, 0.23, 0.36, 0.023),
                (side * 1.18, 0.03, 0.21, 0.40, 0.012),
            ],
            white,
        )
        wing(
            "Wingtip_marking",
            [(side * 1.08, -0.006, 0.216, 0.387, 0.016), (side * 1.18, 0.03, 0.21, 0.40, 0.012)],
            orange,
        )
        wing(
            "Tailplane",
            [(side * 0.035, 0.43, 0.69, 0.34, 0.018), (side * 0.40, 0.54, 0.70, 0.365, 0.009)],
            white,
        )
    fin = wing(
        "Vertical_stabilizer", [(0, 0.37, 0.70, 0, 0.021), (0.36, 0.59, 0.71, 0, 0.008)], orange
    )
    fin.rotation_euler.y = -math.pi / 2
    fin.location.z = 0.36
    rod("Nose_motor", (0, -0.68, 0.30), (0, -0.78, 0.30), 0.045, metal)
    rotor("Nose_propeller", (0, -0.79, 0.30), 0.24, vertical=True)
    camera((0, -0.25, 0.16), 0.7)
    for x, y in [(-0.21, 0.12), (0.21, 0.12), (0, -0.48)]:
        rod("Wheel_strut", (x * 0.3, y, 0.25), (x, y, 0.065), 0.009, metal)
        rod("Wheel", (x - 0.018, y, 0.048), (x + 0.018, y, 0.048), 0.047, carbon)


report = []
for name, builder in [
    ("quadcopter", lambda: multirotor(4, 0.30, 0.145)),
    ("hexacopter_cargo", lambda: multirotor(6, 0.48, 0.20)),
    ("fixed_wing", fixedwing),
]:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    white = material("Pearl shell", (0.72, 0.79, 0.84), 0.2)
    carbon = material("Graphite", (0.024, 0.033, 0.043), 0.3)
    metal = material("Motor aluminium", (0.25, 0.29, 0.33), 0.8)
    orange = material("Safety orange", (0.95, 0.19, 0.035), 0.15)
    glass = material("Lens blue", (0.018, 0.10, 0.17), 0.7)
    red = material("Red navigation", (0.85, 0.025, 0.018))
    green = material("Green navigation", (0.025, 0.75, 0.16))
    builder()
    bpy.context.scene.unit_settings.system = "METRIC"
    path = OUT / (name + ".glb")
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_yup=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    assert meshes and all(len(o.data.polygons) > 0 for o in meshes)
    coords = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    dims = [round(max(v[i] for v in coords) - min(v[i] for v in coords), 3) for i in range(3)]
    report.append(
        dict(
            file=path.name,
            bytes=path.stat().st_size,
            mesh_objects=len(meshes),
            triangles=sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons),
            dimensions_blender_xyz_m=dims,
            reimport_verified=True,
        )
    )
    # Render the imported asset so the preview also verifies the actual deliverable.
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.world.color = (0.3, 0.3, 0.3)
    span = max(dims)
    bpy.ops.object.camera_add(location=(span * 1.3, -span * 1.65, span * 1.1))
    cam = bpy.context.object
    cam.rotation_euler = (Vector((0, 0, 0.25)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = span * 1.35
    scene.camera = cam
    for loc, power, size in [((1, -2, 4), 450, 4), ((-3, -1, 2), 300, 3), ((0, 3, 3), 500, 2)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (
            (Vector((0, 0, 0.25)) - light.location).to_track_quat("-Z", "Y").to_euler()
        )
    scene.render.resolution_x = 900
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.render.filepath = str(OUT / (name + ".png"))
    bpy.ops.render.render(write_still=True)
(OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
