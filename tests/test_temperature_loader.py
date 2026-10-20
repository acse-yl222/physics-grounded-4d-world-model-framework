"""The packaged temperature stage must load the teacher surrogate without legacy paths."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A fresh interpreter keeps earlier imports from masking a missing flat module.
SCRIPT = """
import sys
sys.path.insert(0, sys.argv[1])
import torch
from common.pipeline import scene_scaled_latent
from urban_flow.physics.wind_temperature_teacher.code.temperature_model import UNet3D

assert "temperature_model" not in sys.modules
before = list(sys.path)
config = {
    "in_channels": 15, "history_steps": 3, "base_channels": 2, "depth": 1,
    "patch_size": [4, 4, 4],
}
stats = {
    key: 1.0
    for key in (
        "temp_mean", "temp_std", "velocity_scale", "surface_temp_mean", "surface_temp_std",
        "surface_exchange_scale", "height_scale",
    )
}
torch.manual_seed(0)
state = UNet3D(in_channels=15, base_channels=2, depth=1).state_dict()
torch.save({"config": config, "stats": stats, "model_state_dict": state}, sys.argv[2])
model, loaded_stats, patch = scene_scaled_latent.load_temperature(sys.argv[2], "cpu")
assert isinstance(model, UNet3D), type(model)
assert not model.training
assert all(torch.equal(model.state_dict()[k], v) for k, v in state.items())
assert loaded_stats == stats and patch == (4, 4, 4)
assert sys.path == before, sys.path
"""


@unittest.skipUnless(
    all(importlib.util.find_spec(name) for name in ("torch", "h5py", "tqdm")),
    "Install the flow extras for the temperature surrogate",
)
class TemperatureLoaderTests(unittest.TestCase):
    def test_scene_stage_loads_teacher_checkpoint_from_package(self):
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run(
                [sys.executable, "-I", "-c", SCRIPT, str(ROOT / "src"), str(Path(cwd) / "t.pt")],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
