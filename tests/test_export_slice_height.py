import contextlib
import io
import json
import shutil
import struct
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common.export import package_export
from common.pipeline import export_scene_web
from common.pipeline.run_scene import load_config
from common.storage import Storage

CELL, FACTOR, LAYER = 2, 4, 1
COARSE = CELL * FACTOR
# Coarse layer 1 spans z = 8-16 m; its cell centres, where the solvers sample, are at 12 m.
SLICE_CENTRE_M = (LAYER + 0.5) * COARSE


def glb(path):
    payload = json.dumps({"asset": {"version": "2.0"}, "scenes": [{"nodes": []}], "scene": 0})
    payload = payload.encode() + b" " * ((-len(payload)) % 4)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, 28 + len(payload))
        + struct.pack("<I4s", len(payload), b"JSON")
        + payload
        + struct.pack("<II", 0, 0x004E4942)
    )


class SliceHeightTests(unittest.TestCase):
    """A synthetic finished trial exported for the legacy viewer and packaged as a protocol bundle."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "AGENTS.md").write_text("fixture")
        shutil.copytree(ROOT / "schemas", self.root / "schemas")
        env = mock.patch.dict("os.environ", {"P4D_ROOT": str(self.root), "UWM_RUN_ID": "trial"})
        env.start()
        self.addCleanup(env.stop)
        glb(self.root / "city.glb")
        config = self.root / "pipeline.json"
        config.write_text(
            json.dumps(
                {
                    "scene": "test",
                    "source": str(self.root / "city.glb"),
                    "domain": {"cell_m": CELL, "wind_layers": 2 * FACTOR},
                    "georeference": {"latitude_deg": 0, "longitude_deg": 0},
                    "wind": {"steps": 2, "step_seconds": 50, "coarse_factor": FACTOR},
                    "visualize": {"layer": LAYER},
                }
            )
        )
        self.cfg, self.p = load_config(str(config))
        ny = nx = 2 * FACTOR
        zc, yc, xc = 2, ny // FACTOR, nx // FACTOR
        g = self.p["geometry"]
        g.mkdir(parents=True)
        (g / "metadata.json").write_text(
            json.dumps(
                {"shape_zyx": [2 * FACTOR, ny, nx], "source_region_origin_xyz_m": [-8, -16, 0]}
            )
        )
        np.save(g / f"footprint_{CELL}m_yx.npy", np.zeros((ny, nx), bool))
        np.save(g / "height_m.npy", np.zeros((ny, nx), np.float32))
        np.save(g / f"footprint_{COARSE}m_yx.npy", np.zeros((yc, xc), bool))
        np.save(g / "solid.npy", np.zeros((2 * FACTOR, ny, nx), bool))
        run = self.p["run"]
        (run / "wind").mkdir(parents=True)
        (run / "pollution").mkdir()
        for k in range(3):
            np.savez(run / f"wind/wind{COARSE}m_{k:03d}.npz", uvw=np.ones((3, zc, yc, xc), "<f4"))
        for k in (1, 2):
            np.savez(
                run / f"pollution/concentration_{k:03d}.npz",
                concentration=np.ones((zc, yc, xc), "<f4"),
            )
        (run / "pollution/status.json").write_text(json.dumps({"complete": True}))
        self.p["status"].write_text(json.dumps({"stages": {"wind": {"status": "done"}}}))
        t = self.p["temperature3d"]
        t.mkdir(parents=True)
        np.save(t / "temperature_c_tzyx.npy", np.full((3, zc, yc, xc), 26, "<f4"))
        (t / "run_config.json").write_text(
            json.dumps(
                {"duration_seconds": 100, "ambient_c": 26.0, "surface_c": 30.0, "cell_m": COARSE}
            )
        )
        (t / "summary.json").write_text(json.dumps({"complete": True}))
        argv = ["export_scene_web", "--config", str(config), "--no-frames"]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            export_scene_web.main()
        self.scene = json.loads((self.p["scene_web"] / "scene.json").read_text())
        snapshot = self.root / "snapshot.tar.gz"
        with tarfile.open(snapshot, "w:gz"):
            pass
        self.package = lambda: package_export(
            Storage.load(self.root), self.p["scene_web"], self.cfg, "trial", snapshot, "rev"
        )
        self.bundle = self.package()

    def origin(self, key):
        manifest = json.loads((self.bundle / f"trial_{key}/manifest.json").read_text())
        return manifest["layers"][0]["encoding"]["origin_m"]

    def test_protocol_layers_sit_at_the_physical_slice_height(self):
        for key in ("wind", "temp", "poll"):
            with self.subTest(layer=key):
                self.assertEqual(self.origin(key), [-8, -16, SLICE_CENTRE_M])

    def test_legacy_scene_keeps_its_display_heights(self):
        layers = self.scene["layers"]
        self.assertEqual(layers["wind"]["y"], SLICE_CENTRE_M)
        self.assertEqual(layers["temp"]["y"], 0.6)
        self.assertEqual(layers["poll"]["y"], SLICE_CENTRE_M + 2)

    def test_export_without_recorded_height_is_refused(self):
        shutil.rmtree(self.bundle)
        path = self.p["scene_web"] / "physics/manifest.json"
        manifest = json.loads(path.read_text())
        for entry in manifest["arrays"].values():
            entry.pop("z_m", None)
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "temp has no recorded sample height"):
            self.package()
        self.assertFalse(self.bundle.exists())


if __name__ == "__main__":
    unittest.main()
