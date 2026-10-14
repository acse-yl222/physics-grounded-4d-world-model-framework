import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from urban_geometry.voxelization.context_buildings import clean_ring
from urban_geometry.voxelization.georef_roads import enu_basis, to_latlon
from urban_geometry.voxelization.glb_plan import local_bounds, plan_grid, read_glb_header

SCRIPT = ROOT / "src/urban_geometry/voxelization/context_buildings.py"
ORIGIN = (28.65, 77.19)


def write_base(path, parts):
    """Baked GLB of (name, physics_class, local xyz vertices, triangles)."""
    blob, views, accessors, meshes, nodes = b"", [], [], [], []
    for name, cls, local, tris in parts:
        local = np.asarray(local, float)
        verts = np.stack([local[:, 0], local[:, 2], -local[:, 1]], 1).astype(np.float32)
        for array, component, kind in (
            (verts, 5126, "VEC3"),
            (np.asarray(tris, np.uint32).reshape(-1), 5125, "SCALAR"),
        ):
            data = array.tobytes()
            views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)})
            acc = {"bufferView": len(views) - 1, "componentType": component, "count": len(array)}
            acc["type"] = kind
            if kind == "VEC3":
                acc["min"], acc["max"] = array.min(0).tolist(), array.max(0).tolist()
            accessors.append(acc)
            blob += data
        prim = {"attributes": {"POSITION": len(accessors) - 2}, "indices": len(accessors) - 1}
        meshes.append({"primitives": [prim]})
        nodes.append({"name": name, "mesh": len(meshes) - 1, "extras": {"physics_class": cls}})
    doc = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(blob)}],
    }
    js = json.dumps(doc).encode()
    js += b" " * (-len(js) % 4)
    total = 28 + len(js) + len(blob)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<II", len(js), 0x4E4F534A)
        + js
        + struct.pack("<II", len(blob), 0x004E4942)
        + blob
    )


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]


def geometry(ring, frame):
    lat, lon = to_latlon(np.asarray(ring, float), frame)
    return [{"lat": a, "lon": b} for a, b in zip(lat, lon)]


class ContextBuildingsTests(unittest.TestCase):
    def test_filters_extrudes_and_keeps_grid_plan(self):
        frame = enu_basis(*ORIGIN)
        box = [[-20, -20, 0], [20, -20, 0], [20, 20, 0], [-20, 20, 0]]
        top = [[x, y, 12] for x, y, _ in box]
        base_parts = [
            (
                "Ground",
                "ground",
                [[-300, -300, 0], [300, -300, 0], [300, 300, 0], [-300, 300, 0]],
                [[0, 1, 2], [0, 2, 3]],
            ),
            (
                "Road_9",
                "asphalt",
                [[-300, 96, 0], [300, 96, 0], [300, 104, 0], [-300, 104, 0]],
                [[0, 1, 2], [0, 2, 3]],
            ),
            ("Agent_1", "building", box + top, [[4, 5, 6], [4, 6, 7]]),
        ]
        ways = {
            1: (square(-20, -20, 20, 20), {"building": "yes"}),
            2: (square(200, -200, 230, -170), {"building": "yes"}),
            3: (square(0, 95, 20, 115), {"building": "yes"}),
            4: (square(440, 0, 460, 20), {"building": "yes"}),
            5: (square(-250, 200, -220, 230), {"building": "yes", "building:levels": "5"}),
            6: (square(5, 5, 10, 10), {"building": "yes"}),
        }
        elements = [
            {"type": "way", "id": k, "tags": t, "geometry": geometry(r, frame)}
            for k, (r, t) in ways.items()
        ]
        halves = (
            [[-250, -250], [-200, -250], [-200, -200]],
            [[-200, -200], [-250, -200], [-250, -250]],
        )
        elements.append(
            {
                "type": "relation",
                "id": 7,
                "tags": {"building": "yes", "height": "9 m"},
                "members": [
                    *(
                        {"type": "way", "role": "outer", "geometry": geometry(h, frame)}
                        for h in halves
                    ),
                    {
                        "type": "way",
                        "role": "inner",
                        "geometry": geometry(square(-235, -235, -215, -215), frame),
                    },
                ],
            }
        )
        georef = {
            "tangent_plane_origin_latlon": list(ORIGIN),
            "similarity": {
                "scale": 1.0,
                "rotation_deg_ccw_local_to_enu": 0.0,
                "translation_enu_m": [0, 0],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_base(tmp / "solver.glb", base_parts)
            (tmp / "georef.json").write_text(json.dumps(georef))
            (tmp / "osm.json").write_text(json.dumps({"elements": elements}))
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--base",
                    str(tmp / "solver.glb"),
                    "--georef",
                    str(tmp / "georef.json"),
                    "--osm-json",
                    str(tmp / "osm.json"),
                    "--out",
                    str(tmp / "out"),
                    "--merge-into",
                    str(tmp / "solver.glb"),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            report = json.loads((tmp / "out/context-report.json").read_text())
            ctx, _ = read_glb_header(tmp / "out/context.glb")
            merged, _ = read_glb_header(tmp / "out/solver.glb")
            base, _ = read_glb_header(tmp / "solver.glb")

        self.assertEqual(report["kept"], 3)
        self.assertEqual(
            report["dropped"],
            {"overlaps modelled road": 1, "crosses context extent": 1, "inside detailed zone": 1},
        )
        extras = {n["extras"].get("osm"): n["extras"] for n in ctx["nodes"]}
        self.assertEqual(extras["way/2"]["height_m"], 12.0)
        self.assertAlmostEqual(extras["way/5"]["height_m"], 16.0)
        self.assertEqual(extras["relation/7#0"]["height_m"], 9.0)
        self.assertIn("note", extras["relation/7#0"])
        positions = {
            n["extras"].get("osm"): ctx["accessors"][
                ctx["meshes"][n["mesh"]]["primitives"][0]["attributes"]["POSITION"]
            ]
            for n in ctx["nodes"]
        }
        self.assertEqual(positions["way/2"]["count"], 4 + 4 * 4)  # square roof + four walls
        self.assertEqual(positions["way/2"]["min"][0], 200.0)
        self.assertEqual(positions["way/2"]["max"][0], 230.0)
        self.assertEqual(len(merged["nodes"]), len(base["nodes"]) + len(ctx["nodes"]))
        before, after = plan_grid(local_bounds(base), 2), plan_grid(local_bounds(merged), 2)
        self.assertTrue(np.array_equal(before["size_xy_m"], after["size_xy_m"]))
        self.assertTrue(np.array_equal(before["origin_xy"], after["origin_xy"]))
        self.assertGreater(after["bounds"][1, 0], 400)

    def test_clean_ring_keeps_every_corner(self):
        open_ring = np.array(square(0, 0, 10, 10)[:-1], float)
        for ring in (
            open_ring,
            np.vstack([open_ring, open_ring[:1]]),
            np.vstack([open_ring, open_ring[:1], open_ring[:1]]),
        ):
            cleaned = clean_ring(ring)
            self.assertEqual(len(cleaned), 4)
            area = 0.5 * np.sum(
                cleaned[:, 0] * np.roll(cleaned[:, 1], -1)
                - np.roll(cleaned[:, 0], -1) * cleaned[:, 1]
            )
            self.assertAlmostEqual(area, 100.0)
        midpoint = np.array([[0, 0], [5, 0], [10, 0], [10, 10], [0, 10], [0, 0]], float)
        self.assertEqual(len(clean_ring(midpoint)), 4)
        self.assertEqual(len(clean_ring(midpoint[::-1])), 4)


if __name__ == "__main__":
    unittest.main()
