import tempfile
import unittest
from pathlib import Path

import torch

from inference import load_predictor
from model import DigitUNet3D


class InferenceTest(unittest.TestCase):
    def test_checkpoint_load_and_physical_prediction(self):
        model = DigitUNet3D((16, 32, 64, 128, 256))
        checkpoint = {
            "model": model.state_dict(),
            "config": {
                "architecture": "digit4wide",
                "stats": {"mean": 0.1, "std": 0.2},
                "stats_meta": {"clip_target": True, "clip_value": 0.5},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "best.pt"
            torch.save(checkpoint, path)
            predictor = load_predictor(path)

        pollution = torch.zeros(1, 1, 16, 16, 16)
        boundary = torch.zeros(1, 2, 16, 16, 16)
        wind = torch.zeros(1, 4, 4, 4, 4)
        prediction = predictor(pollution, boundary, wind)

        self.assertEqual(prediction.shape, pollution.shape)
        self.assertGreaterEqual(float(prediction.min()), 0.0)
        self.assertLessEqual(float(prediction.max()), 0.5)


if __name__ == "__main__":
    unittest.main()
