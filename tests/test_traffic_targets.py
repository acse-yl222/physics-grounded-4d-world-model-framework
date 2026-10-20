"""Missing future traffic frames must be masked, never scored or trained as positions."""

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def leaving_track(t_last):
    # Observed at the anchor frame and one future frame, then the vehicle leaves the grid.
    positions = [(t_last - 1, 20.0, 30.0, 0.1, 0.0), (t_last, 21.0, 30.0, 0.1, 0.0)]
    positions.append((t_last + 1, 22.0, 30.0, 0.1, 0.0))
    return {"entry": "road0", "positions": positions}


def complete_track(t_last, pred_steps):
    positions = [(t_last + k, 40.0, 10.0 + k, 0.0, 0.1) for k in range(pred_steps + 1)]
    return {"entry": "road1", "positions": positions}


@unittest.skipUnless(importlib.util.find_spec("torch"), "Requires the traffic environment")
class TrafficTargetMaskTests(unittest.TestCase):
    def test_track_ending_after_one_future_frame_has_one_valid_step(self):
        from traffic.configs.default import GRID_SIZE, PRED_STEPS
        from traffic.evaluate import vehicle_gt_from_tracks

        t_last = 9
        ((r, c, target, valid),) = vehicle_gt_from_tracks({7: leaving_track(t_last)}, t_last)
        self.assertEqual((r, c), (21, 30))
        self.assertEqual(valid.tolist(), [True] + [False] * (PRED_STEPS - 1))
        self.assertAlmostEqual(target[0, 0].item(), 22.0 / GRID_SIZE, places=6)

    def test_metrics_ignore_invalid_steps(self):
        import torch

        from traffic.configs.default import PRED_STEPS
        from traffic.evaluate import compute_metrics, vehicle_gt_from_tracks

        t_last = 9
        tracks = {7: leaving_track(t_last), 8: complete_track(t_last, PRED_STEPS)}
        gts = vehicle_gt_from_tracks(tracks, t_last)
        targets = torch.stack([target for _, _, target, _ in gts])
        valid = torch.stack([mask for _, _, _, mask in gts])
        self.assertEqual(int(valid.sum()), 1 + PRED_STEPS)

        preds = targets.clone()
        preds[~valid] = torch.randn(int((~valid).sum()), targets.shape[-1]) * 100.0
        ade, fde = compute_metrics(preds, targets, valid)
        self.assertEqual((ade, fde), (0.0, 0.0))

        # FDE counts only the vehicle whose final step was observed.
        complete = valid[:, -1].nonzero().item()
        preds[complete, -1, :2] += torch.tensor([0.3, 0.4])
        ade, fde = compute_metrics(preds, targets, valid)
        self.assertAlmostEqual(fde, 0.5, places=6)
        self.assertAlmostEqual(ade, 0.5 / (1 + PRED_STEPS), places=6)

    def test_training_targets_and_loss_ignore_invalid_steps(self):
        import torch

        from traffic.configs.default import (
            GRID_SIZE,
            HIST_STEPS,
            PRED_STEPS,
            TOTAL_FEAT_DIM,
            VEHICLE_DIM,
        )
        from traffic.train import WindowDataset, masked_mse

        t_last = HIST_STEPS - 1
        inputs = torch.zeros(1, HIST_STEPS, GRID_SIZE, GRID_SIZE, TOTAL_FEAT_DIM)
        dataset = WindowDataset(inputs, [{7: leaving_track(t_last)}], [0])
        _window, target, valid = dataset[0]
        self.assertEqual(valid.tolist(), [True] + [False] * (PRED_STEPS - 1))
        self.assertAlmostEqual(target[0, 0].item(), 1.0 / GRID_SIZE, places=6)

        pred = target.clone()
        pred[1:] = 5.0
        pred.requires_grad_(True)
        loss = masked_mse(pred[None], target[None], valid[None])
        loss.backward()
        self.assertEqual(loss.item(), 0.0)
        self.assertEqual(pred.grad[1:].abs().sum().item(), 0.0)

        # Valid steps keep the plain MSE: mean over every component of the valid steps.
        with torch.no_grad():
            pred[0, 0] += 0.2
        loss = masked_mse(pred[None], target[None], valid[None])
        self.assertAlmostEqual(loss.item(), 0.04 / VEHICLE_DIM, places=6)

        # A batch without an observed future step contributes no loss and no NaN.
        none_valid = torch.zeros_like(valid)[None]
        self.assertEqual(masked_mse(pred[None], target[None], none_valid).item(), 0.0)

        # With every step observed the loss is unchanged from the previous MSE.
        all_valid = torch.ones_like(valid)[None]
        expected = torch.nn.functional.mse_loss(pred[None], target[None])
        self.assertAlmostEqual(
            masked_mse(pred[None], target[None], all_valid).item(), expected.item()
        )


if __name__ == "__main__":
    unittest.main()
