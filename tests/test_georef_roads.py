import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
from itertools import pairwise
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from urban_geometry.voxelization.georef_roads import enu_basis, to_latlon

SCRIPT = ROOT / "src/urban_geometry/voxelization/georef_roads.py"


def write_glb(path, roads):
    """Minimal GLB with one float32 POSITION strip per named road."""
    blob, views, accessors, meshes, nodes = b"", [], [], [], []
    for name, verts in roads.items():
        data = np.asarray(verts, np.float32).tobytes()
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)})
        accessors.append(
            {
                "bufferView": len(views) - 1,
                "componentType": 5126,
                "count": len(verts),
                "type": "VEC3",
                "min": np.min(verts, 0).tolist(),
                "max": np.max(verts, 0).tolist(),
            }
        )
        meshes.append({"primitives": [{"attributes": {"POSITION": len(accessors) - 1}}]})
        nodes.append({"name": name, "mesh": len(meshes) - 1})
        blob += data
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
    blob += b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<II", len(js), 0x4E4F534A)
        + js
        + struct.pack("<II", len(blob), 0x004E4942)
        + blob
    )


class GeorefRoadsTests(unittest.TestCase):
    def test_recovers_known_similarity(self):
        scale, deg, shift = 1.002, 7.0, np.array([40.0, -15.0])
        a = math.radians(deg)
        rot = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        frame = enu_basis(28.65, 77.19)
        lines = {
            101: [[-400, -300], [-380, 0], [-390, 350]],
            102: [[-100, -350], [-90, 360]],
            103: [[250, -320], [260, 0], [240, 340]],
            104: [[-420, -200], [0, -180], [420, -210]],
            105: [[-410, 120], [430, 140]],
            106: [[-200, 300], [100, 280], [380, 310]],
        }
        roads, elements = {}, []
        for wid, enu in lines.items():
            enu = np.asarray(enu, float)
            lat, lon = to_latlon(enu, frame)
            elements.append(
                {
                    "type": "way",
                    "id": wid,
                    "geometry": [{"lat": y, "lon": x} for y, x in zip(lat, lon)],
                }
            )
            dense = np.concatenate(
                [
                    p + np.linspace(0, 1, 12, endpoint=False)[:, None] * (q - p)
                    for p, q in pairwise(enu)
                ]
            )
            local = (dense - shift) @ rot / scale
            d = np.gradient(local, axis=0)
            normal = np.stack([-d[:, 1], d[:, 0]], 1) / np.linalg.norm(d, axis=1)[:, None]
            strip = np.empty((2 * len(local), 3))
            for side, k in ((3.0, 0), (-3.0, 1)):
                xy = local + side * normal
                strip[k::2] = np.stack([xy[:, 0], np.zeros(len(xy)), -xy[:, 1]], 1)
            roads[f"Road_{wid}"] = strip

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_glb(tmp / "scene.glb", roads)
            (tmp / "osm.json").write_text(json.dumps({"elements": elements}))
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(tmp / "scene.glb"),
                    "--osm-json",
                    str(tmp / "osm.json"),
                    "--out",
                    str(tmp / "report.json"),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            report = json.loads((tmp / "report.json").read_text())

        sim = report["similarity"]
        self.assertAlmostEqual(sim["scale"], scale, places=5)
        self.assertAlmostEqual(sim["rotation_deg_ccw_local_to_enu"], deg, places=3)
        self.assertLess(sim["residual"]["max_m"], 0.01)
        lat0, lon0 = to_latlon(shift[None], frame)
        self.assertAlmostEqual(report["local_origin_latlon"][0], lat0[0], places=7)
        self.assertAlmostEqual(report["local_origin_latlon"][1], lon0[0], places=7)
        self.assertEqual(report["osm"]["ways_missing"], [])


if __name__ == "__main__":
    unittest.main()
