"""Coordinator-owned fixture grounding; source frame baked once after build."""

import json
import bpy
from public_realm_ground import allowed
from mathutils import Matrix, Vector
from public_realm_fixtures import build


def integrate(root, transform):
    records = json.loads(
        (root / "references/public_realm/fixture_module/placement_checks.json").read_text()
    )["records"]
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    checks = []
    for row in records:
        x, y = row["position_authoring_xy_m"]
        p = transform @ Vector((x, y, 1.0))
        hit, location, normal, index, obj, matrix = bpy.context.scene.ray_cast(
            graph, p, Vector((0, 0, -1)), distance=3.0
        )
        assert hit and normal.z > 0.9 and -0.2 <= location.z <= 0.2, (
            "Unexpected fixture ground " + row["id"]
        )
        assert allowed(obj), "Unapproved fixture support " + row["id"] + " " + obj.name
        row["ground_z"] = float(location.z)
        row["ground_status"] = "native master downward ray checked"
        checks.append(
            {
                "id": row["id"],
                "campus_base_xyz": [p.x, p.y, float(location.z)],
                "support_object": obj.name,
                "support_research_id": obj.get("research_object_id"),
                "ray_passed": True,
            }
        )
    col = bpy.data.collections.new("Extension | mapped lighting and bollard")
    bpy.context.scene.collection.children.link(col)
    old = set(bpy.data.objects)
    objects = build(col, records)
    assert set(bpy.data.objects) - old == set(objects)
    for ob in objects:
        ob.data.transform(transform @ ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
    return objects, {
        "created": [o.name for o in objects],
        "ground_checks": checks,
        "master_visual_reviewed": False,
    }
