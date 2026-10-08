"""Coordinator-owned tree grounding and one-time coordinate transformation."""

import json
import bpy
from public_realm_ground import allowed
from mathutils import Matrix, Vector
from detailed_common import BuildingContext
from public_realm_trees import build


def integrate(root, transform):
    inputs = json.loads((root / "references/public_realm/tree_module/inputs.json").read_text())
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    ground_checks = []
    for row in inputs["trees"]:
        if row["status"] != "build":
            continue
        x, y = row["position_authoring_xy_m"]
        p = transform @ Vector((x, y, 1.0))
        hit, location, normal, index, obj, matrix = bpy.context.scene.ray_cast(
            graph, p, Vector((0, 0, -1)), distance=3.0
        )
        assert hit, "No ground below " + row["id"]
        assert normal.z > 0.9 and -0.2 <= location.z <= 0.2, "Unexpected tree support " + row["id"]
        assert allowed(obj), "Unapproved tree support " + row["id"] + " " + obj.name
        old_z = row["base_z_m"]
        row["base_z_m"] = float(location.z)
        ground_checks.append(
            {
                "id": row["id"],
                "campus_root_xyz": [p.x, p.y, float(location.z)],
                "previous_estimated_z": old_z,
                "support_object": obj.name,
                "support_research_id": obj.get("research_object_id"),
                "normal": list(normal),
                "ray_passed": True,
            }
        )
    col = bpy.data.collections.new("Extension | mapped trees")
    bpy.context.scene.collection.children.link(col)
    old = set(bpy.data.objects)
    report = build(BuildingContext(col, {"name": "Public realm"}), inputs)
    obs = list(col.all_objects)
    assert set(report["created"]) == {o.name for o in obs}
    assert set(bpy.data.objects) - old == set(obs)
    for ob in obs:
        ob.data.transform(transform @ ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        ob["authoring_frame"] = "campus affine baked once"
        ob["expansion_status"] = (
            "mapped tree position; estimated species and dimensions; ground ray checked"
        )
    for interface in report["interfaces"]["tree_roots"]:
        interface["ground_verification"] = (
            "native master downward ray checked against explicit ground surfaces"
        )
    report["ground_checks"] = ground_checks
    report["master_visual_reviewed"] = False
    return obs, report
