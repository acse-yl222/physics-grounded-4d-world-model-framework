"""An interrupted SCALED wind run must not be reported complete by `p4d run`."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from common.pipeline.run_scene import status_of

CELL, FACTOR, STEPS = 2, 4, 3
FINAL = f"velocity_final_{CELL}m_raw_czyx_float16.npy"
LAST = f"wind{CELL * FACTOR}m_{STEPS:03d}.npz"


class WindStageStatusTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.run_dir = Path(tmp.name) / "scaled_latent"
        (self.run_dir / "wind").mkdir(parents=True)
        self.cfg = {
            "domain": {"cell_m": CELL},
            "wind": {"coarse_factor": FACTOR, "steps": STEPS, "step_seconds": 50},
        }

    def write(self, name):
        (self.run_dir / "wind" / name).write_bytes(b"x")

    def record(self, value):
        (self.run_dir / "status.json").write_text(json.dumps(value))

    def state(self):
        return status_of("wind", self.cfg, {"run": self.run_dir}, {"geometry"})[0]

    def test_outputs_without_completion_record_are_not_done(self):
        self.write(FINAL)
        self.write(LAST)
        self.assertEqual(self.state(), "ready")

    def test_outputs_with_incomplete_record_are_not_done(self):
        # Killed while writing the final field: the record still names the previous step.
        self.write(FINAL)
        self.write(LAST)
        self.record({"stage": "wind", "completed_steps": STEPS - 1, "total_steps": STEPS})
        self.assertEqual(self.state(), "ready")

    def test_complete_record_is_done(self):
        self.write(FINAL)
        self.write(LAST)
        self.record({"stage": "wind", "completed_steps": STEPS, "total_steps": STEPS})
        self.assertEqual(self.state(), "done")

    def test_record_rewritten_by_temperature_stage_is_done(self):
        self.write(FINAL)
        self.write(LAST)
        self.record({"stage": "wind_temperature_complete", "wind_steps": STEPS})
        self.assertEqual(self.state(), "done")

    def test_leftover_partial_final_is_not_done(self):
        self.write(Path(FINAL).with_suffix(".partial").name)
        self.write(LAST)
        self.record({"stage": "wind", "completed_steps": STEPS - 1, "total_steps": STEPS})
        self.assertEqual(self.state(), "ready")
        self.record({"stage": "wind", "completed_steps": STEPS, "total_steps": STEPS})
        self.assertEqual(self.state(), "ready")


class InterruptedChannels:
    """Channel-first source whose second channel read fails, as if the process stopped."""

    shape = (3, 2, 4, 4)

    def __getitem__(self, c):
        if c == 1:
            raise KeyboardInterrupt("stopped mid-copy")
        return np.full(self.shape[1:], 1.5, np.float32)


@unittest.skipUnless(importlib.util.find_spec("torch"), "Requires the flow environment")
class FinalFieldWriteTests(unittest.TestCase):
    def setUp(self):
        from common.pipeline.scene_scaled_latent import save_npy

        self.save_npy = save_npy
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.final = Path(tmp.name) / FINAL

    def test_interrupted_write_leaves_no_final_field(self):
        with self.assertRaises(KeyboardInterrupt):
            self.save_npy(self.final, InterruptedChannels(), np.float16)
        self.assertFalse(self.final.exists())

    def test_complete_write_is_loadable_float16(self):
        field = np.random.default_rng(0).normal(size=(3, 2, 4, 4)).astype(np.float32)
        self.save_npy(self.final, field, np.float16)
        loaded = np.load(self.final)
        self.assertEqual(loaded.dtype, np.float16)
        np.testing.assert_array_equal(loaded, field.astype(np.float16))
        self.assertFalse(self.final.with_suffix(".partial").exists())


if __name__ == "__main__":
    unittest.main()
