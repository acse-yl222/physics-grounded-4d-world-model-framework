import json, struct
from detailed_common import BuildingContext
import bpy


def build(root):
    data = json.loads((root / "context.json").read_text())
    col = bpy.data.collections.new("Site | roads parks water")
    bpy.context.scene.collection.children.link(col)
    ctx = BuildingContext(col, {"name": "Site"})
    mats = {
        k: ctx.material("site " + k, c, 0.9)
        for k, c in {
            "ground": (0.53, 0.53, 0.47),
            "park": (0.23, 0.34, 0.19),
            "water": (0.09, 0.26, 0.32),
            "road": (0.24, 0.26, 0.26),
            "path": (0.62, 0.57, 0.46),
        }.items()
    }
    items = [{"id": "ground", "kind": "ground", "geometry": data["ground"]}] + data["features"]
    objects = []
    for f in items:
        path_edges = {}
        m = ctx.mesh(f["id"])
        z = {"ground": -0.05, "park": -0.02, "water": -0.01, "road": 0.0, "path": 0.015}[f["kind"]]
        for part in f["geometry"]:
            for tri in part["triangles"]:
                t = [tuple(struct.unpack("f", struct.pack("f", c))[0] for c in v) for v in tri]
                area = (
                    abs(
                        (t[1][0] - t[0][0]) * (t[2][1] - t[0][1])
                        - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0])
                    )
                    / 2
                )
                if area >= 1e-10:
                    m.face([(x, y, z) for x, y in tri], mats[f["kind"]])
                    if f["kind"] == "path":
                        # Close the new path below both nominal and boundary-blended ground.
                        # Count triangulation edges so internal diagonals receive no side faces.
                        points = [tuple(v) for v in t]
                        if (
                            sum(
                                points[i][0] * points[(i + 1) % 3][1]
                                - points[(i + 1) % 3][0] * points[i][1]
                                for i in range(3)
                            )
                            < 0
                        ):
                            points.reverse()
                        m.face([(x, y, -0.07) for x, y in reversed(points)], mats["path"])
                        for a, b in zip(points, points[1:] + points[:1]):
                            key = tuple(sorted((a, b)))
                            if key in path_edges:
                                path_edges[key][0] += 1
                            else:
                                path_edges[key] = [1, a, b]
        if f["kind"] == "path":
            for count, a, b in path_edges.values():
                assert count in (1, 2), "Nonmanifold path triangulation"
                if count == 1:
                    m.face(
                        [
                            (a[0], a[1], z),
                            (a[0], a[1], -0.07),
                            (b[0], b[1], -0.07),
                            (b[0], b[1], z),
                        ],
                        mats["path"],
                    )
        ob = m.done()
        if ob:
            ob["research_object_id"] = "context::" + f["id"]
            ob["semantic_type"] = f["kind"]
            objects.append(ob)
    return objects
