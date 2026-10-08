import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common.contract import validate


class BinaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "manifest.json"
        self.manifest = json.loads((ROOT / "examples/contract-v1/manifest.json").read_text())
        self.manifest["schema_version"] = "1.1.0"
        self.layer = {
            "id": "flow",
            "kind": "vector_field",
            "format": "npy",
            "asset": "flow.npy",
            "sampling": "linear",
            "field": {"name": "velocity", "unit": "m/s"},
            "encoding": {
                "coordinate_frame": "ENU",
                "dtype": "<f4",
                "shape": [2, 3, 4, 5],
                "axes": "TCYX",
                "origin_m": [0, 0, 1],
                "spacing_m": [2, 2],
                "sample_location": "cell_center",
                "byte_order": "little",
                "compression": "none",
            },
            "display": {"widget": "vector_field", "capabilities": ["pick"]},
        }
        self.manifest["layers"] = [self.layer]
        np.save(self.root / "flow.npy", np.ones((2, 3, 4, 5), dtype="<f4"))

    def check(self):
        self.path.write_text(json.dumps(self.manifest))
        return validate(self.path)

    def test_full_binary_array(self):
        self.assertEqual(self.check(), 1)

    def test_mismatched_axes(self):
        self.layer["encoding"]["axes"] = "TYX"
        with self.assertRaises(ValueError):
            self.check()

    def test_mismatched_dtype(self):
        self.layer["encoding"]["dtype"] = "<f2"
        with self.assertRaises(ValueError):
            self.check()

    def test_late_frame_nonfinite(self):
        data = np.ones((2, 3, 4, 5), dtype="<f4")
        data[-1, -1, -1, -1] = np.nan
        np.save(self.root / "flow.npy", data)
        with self.assertRaises(ValueError):
            self.check()

    def test_frame_series_with_terrain(self):
        self.layer["format"] = "npy_frames"
        self.layer["encoding"]["frame_assets"] = ["a.npy", "b.npy"]
        self.layer["encoding"].update(height_asset="height.npy", height_dtype="<f4")
        for name in ("a.npy", "b.npy"):
            np.save(self.root / name, np.ones((1, 3, 4, 5), dtype="<f4"))
        np.save(self.root / "height.npy", np.ones((4, 5), dtype="<f4"))
        self.assertEqual(self.check(), 1)
        self.layer["encoding"]["shape"][0] = 3
        with self.assertRaisesRegex(ValueError, "frame count"):
            self.check()
        self.layer["encoding"]["shape"][0] = 2
        self.layer["encoding"]["frame_assets"][1] = "../outside.npy"
        with self.assertRaisesRegex(ValueError, "asset path"):
            self.check()

    def test_missing_values_require_explicit_mask(self):
        data = np.ones((2, 3, 4, 5), dtype="<f4")
        data[:, :, 1, 2] = np.nan
        np.save(self.root / "flow.npy", data)
        mask = np.zeros((4, 5), dtype="u1")
        mask[1, 2] = 1
        np.save(self.root / "mask.npy", mask)
        self.layer["encoding"].update(
            mask_asset="mask.npy", mask_dtype="|u1", mask_semantics="invalid_nonzero"
        )
        self.assertEqual(self.check(), 1)
        data[1, 0, 2, 2] = np.nan
        np.save(self.root / "flow.npy", data)
        with self.assertRaisesRegex(ValueError, "non-finite"):
            self.check()

    def test_glb_rejects_external_buffers(self):
        payload = json.dumps(
            {"asset": {"version": "2.0"}, "buffers": [{"uri": "https://external/file.bin"}]}
        ).encode()
        payload += b" " * ((-len(payload)) % 4)
        data = (
            struct.pack("<4sII", b"glTF", 2, 20 + len(payload))
            + struct.pack("<I4s", len(payload), b"JSON")
            + payload
        )
        (self.root / "mesh.glb").write_bytes(data)
        self.manifest["time"]["samples"] = []
        self.manifest["layers"] = [
            {
                "id": "city",
                "kind": "mesh",
                "format": "glb",
                "asset": "mesh.glb",
                "sampling": "static",
                "encoding": {"coordinate_frame": "glTF-y-up"},
                "display": {"widget": "mesh", "capabilities": []},
            }
        ]
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
