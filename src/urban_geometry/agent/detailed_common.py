"""Small, side-effect-free Blender authoring API for independent building modules.

All inputs are metres in the shared campus frame. No decimation, compression,
global preference edits, file IO or automatic scene clearing occurs here.
"""

import math
import bpy
from mathutils import Vector


class Mesh:
    def __init__(self, name, collection):
        self.name, self.collection = name, collection
        self.v, self.f, self.mi, self.mats = [], [], [], []

    def _material(self, material):
        if material not in self.mats:
            self.mats.append(material)
        return self.mats.index(material)

    def face(self, vertices, material):
        start = len(self.v)
        self.v.extend(tuple(v) for v in vertices)
        self.f.append(tuple(range(start, len(self.v))))
        self.mi.append(self._material(material))

    def box(self, x, y, z, w, d, h, material, angle=0):
        if min(w, d, h) <= 0:
            return
        start = len(self.v)
        co, si = math.cos(angle), math.sin(angle)
        corners = [
            (-w / 2, -d / 2, -h / 2),
            (w / 2, -d / 2, -h / 2),
            (w / 2, d / 2, -h / 2),
            (-w / 2, d / 2, -h / 2),
            (-w / 2, -d / 2, h / 2),
            (w / 2, -d / 2, h / 2),
            (w / 2, d / 2, h / 2),
            (-w / 2, d / 2, h / 2),
        ]
        self.v.extend((x + a * co - b * si, y + a * si + b * co, z + c) for a, b, c in corners)
        mi = self._material(material)
        for face in [
            (0, 3, 2, 1),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
            (4, 5, 6, 7),
        ]:
            self.f.append(tuple(start + i for i in face))
            self.mi.append(mi)

    def beam(self, a, b, r, material, n=12):
        a, b = Vector(a), Vector(b)
        if (b - a).length < 1e-8:
            return
        direction = (b - a).normalized()
        u = direction.cross(Vector((0, 0, 1)))
        if u.length < 0.001:
            u = Vector((1, 0, 0))
        u.normalize()
        w = direction.cross(u).normalized()
        rings = [
            [
                p + r * (u * math.cos(j * math.tau / n) + w * math.sin(j * math.tau / n))
                for j in range(n)
            ]
            for p in [a, b]
        ]
        for j in range(n):
            self.face(
                [rings[0][j], rings[0][(j + 1) % n], rings[1][(j + 1) % n], rings[1][j]], material
            )
        self.face(list(reversed(rings[0])), material)
        self.face(rings[1], material)

    def lathe(self, x, y, z, profile, material, n=32):
        rings = [
            [
                (x + r * math.cos(j * math.tau / n), y + r * math.sin(j * math.tau / n), z + h)
                for j in range(n)
            ]
            for r, h in profile
        ]
        for a, b in zip(rings, rings[1:]):
            for j in range(n):
                self.face([a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]], material)
        self.face(list(reversed(rings[0])), material)
        self.face(rings[-1], material)

    def surface(self, parts, z, material):
        for part in parts:
            for tri in part["triangles"]:
                self.face([(x, y, z) for x, y in tri], material)

    def shell(self, parts, z0, z1, material):
        for part in parts:
            for ring in [part["outer"]] + part.get("holes", []):
                for a, b in zip(ring, ring[1:] + ring[:1]):
                    self.face(
                        [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)],
                        material,
                    )
        self.surface(parts, z1, material)

    def done(self):
        if not self.v:
            return None
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.v, [], self.f)
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        self.collection.objects.link(obj)
        for material in self.mats:
            mesh.materials.append(material)
        for poly, index in zip(mesh.polygons, self.mi):
            poly.material_index = index
        # World-space, metre-based planar UV projection; keeps independent
        # components on the same material scale without altering geometry.
        uv = mesh.uv_layers.new(name="Metric_Surface_UV")
        for poly in mesh.polygons:
            axis = max(range(3), key=lambda i: abs(poly.normal[i]))
            axes = ((1, 2), (0, 2), (0, 1))[axis]
            material = self.mats[poly.material_index]
            scale = material.get("uv_tile_m", material.get("tile_size_m", (2.0, 2.0)))
            if not isinstance(scale, (list, tuple)) and not hasattr(scale, "__len__"):
                scale = (2.0, 2.0)
            for index in poly.loop_indices:
                co = mesh.vertices[mesh.loops[index].vertex_index].co
                uv.data[index].uv = (co[axes[0]] / float(scale[0]), co[axes[1]] / float(scale[1]))
        mesh.uv_layers.active = uv
        uv.active_render = True
        obj["authoring_method"] = (
            "Independent building module; full authored geometry; no decimation"
        )
        return obj


class BuildingContext:
    def __init__(self, collection, feature):
        self.collection = collection
        self.feature = feature

    def mesh(self, label):
        return Mesh(self.feature["name"] + " | " + label, self.collection)

    def existing(self, name):
        return bpy.data.materials.get(name + " | PBR") or bpy.data.materials.get(name)

    def material(self, key, color=(0.5, 0.5, 0.5), rough=0.5, metal=0, transmission=0):
        name = "Detailed | " + key
        material = bpy.data.materials.get(name)
        if material:
            return material
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        rgba = tuple(color[:3]) + (1.0,)
        material.diffuse_color = rgba
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = rgba
        shader.inputs["Roughness"].default_value = rough
        shader.inputs["Metallic"].default_value = metal
        shader.inputs["Transmission Weight"].default_value = transmission
        shader.inputs["IOR"].default_value = 1.45
        material["physical_properties"] = (
            "Visual parameters; not calibrated optical or thermal measurements"
        )
        return material
