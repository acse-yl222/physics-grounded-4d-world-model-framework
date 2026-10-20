"""UAV route compute validates inputs and output identity before writing any file."""

import dataclasses
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _routing_started(*args, **kwargs):
    raise AssertionError("routing started; validation must fail first")


def _wave_config(**fields):
    return dataclasses.make_dataclass("WaveConfig", list(fields))(**fields)


@unittest.skipUnless(importlib.util.find_spec("scipy"), "Requires SciPy")
class ComputeIdentityTests(unittest.TestCase):
    def setUp(self):
        import numpy as np

        self.np = np
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.geometry = self.base / "geometry"
        self.geometry.mkdir()
        (self.geometry / "metadata.json").write_text(
            json.dumps({"source_region_origin_xyz_m": [0.0, 0.0, 0.0]})
        )
        # 16 x 16 cells of 2 m pool to a free 4 x 4 grid of 8 m cells.
        np.save(self.geometry / "height_m.npy", np.zeros((16, 16)))
        self.framework = self.base / "framework"
        self.framework.mkdir()
        self.output = self.base / "run"

    def stations(self, *east_north):
        # Viewer coordinates: (east, up, south).
        path = self.base / "stations.json"
        stations = [
            {"label": f"S{i}", "xyz": [east, 0.0, -north]}
            for i, (east, north) in enumerate(east_north)
        ]
        path.write_text(json.dumps(stations))
        return path

    def run_compute(self, station_file):
        backend = types.ModuleType("wavepde.torch_backend")
        backend.WaveConfig = _wave_config
        backend.plan_paths = _routing_started
        backend.waveform_samples = MagicMock()
        geometry = types.ModuleType("wavepde.torch_backend.geometry")
        geometry.segment_free = geometry.segment_time = _routing_started
        stubs = {
            "torch": MagicMock(),
            "wavepde": types.ModuleType("wavepde"),
            "wavepde.torch_backend": backend,
            "wavepde.torch_backend.geometry": geometry,
        }
        argv = [
            "compute",
            "--output",
            str(self.output),
            "--geometry",
            str(self.geometry),
            "--station-file",
            str(station_file),
            "--framework",
            str(self.framework),
            "--sources",
            "2",
            "--ground-mode",
        ]
        # Import real dependencies first; patch.dict removes modules first imported inside it.
        import scipy.ndimage  # noqa: F401

        import common.storage  # noqa: F401

        spec = importlib.util.spec_from_file_location(
            "uav_compute_under_test", ROOT / "src/uav_routing/compute.py"
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, stubs), patch.object(sys, "argv", argv):
            spec.loader.exec_module(module)
            module.main()

    def test_foreign_output_directory_is_left_untouched(self):
        station_file = self.stations((4.0, 4.0), (20.0, 20.0))
        old = {
            "domain_8m.npz": b"previous run domain",
            "stations_enu.json": b"previous run stations\n",
            "source_00.json": b"[]\n",
        }
        cases = {
            "different identity": {"station_sha256": "previous run"},
            "missing identity": None,
        }
        for label, identity in cases.items():
            with self.subTest(label):
                self.output.mkdir(exist_ok=True)
                for name, data in old.items():
                    (self.output / name).write_bytes(data)
                identity_path = self.output / "input_identity.json"
                identity_path.unlink(missing_ok=True)
                if identity is not None:
                    identity_path.write_text(json.dumps(identity))
                before = {p.name: p.read_bytes() for p in self.output.iterdir()}
                with self.assertRaisesRegex(ValueError, "different inputs|no input identity"):
                    self.run_compute(station_file)
                after = {p.name: p.read_bytes() for p in self.output.iterdir()}
                self.assertEqual(after, before)

    def test_station_outside_height_map_is_rejected(self):
        for index, east_north in enumerate(((-4.0, 4.0), (4.0, -4.0), (40.0, 4.0), (4.0, 40.0))):
            with self.subTest(east_north=east_north):
                self.output = self.base / f"run_{index}"
                station_file = self.stations((4.0, 4.0), east_north)
                with self.assertRaisesRegex(ValueError, "outside the height map: S1"):
                    self.run_compute(station_file)
                self.assertFalse((self.output / "domain_8m.npz").exists())


if __name__ == "__main__":
    unittest.main()
