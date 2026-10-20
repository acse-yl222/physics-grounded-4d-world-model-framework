"""Jacobi refinement must keep predicted positions anchored to the observed frame."""

import importlib
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

MODELS = ("traffic.models.particle_mlp", "traffic.verification.particle_mlp_london")
VEHICLES = ((0, 55), (10, 12), (11, 13))  # grid edge, then two neighbours; row-major order


@unittest.skipUnless(importlib.util.find_spec("torch"), "Requires the traffic environment")
class JacobiAnchorTests(unittest.TestCase):
    def setUp(self):
        import torch
        from torch import nn

        from traffic.configs import default as C

        self.torch, self.C = torch, C
        steps = torch.arange(1, C.PRED_STEPS + 1, dtype=torch.float32)[:, None]
        velocity = torch.tensor([[0.5, -0.25]]).expand(C.PRED_STEPS, 2)
        self.disp = torch.cat([steps * torch.tensor([0.01, -0.02]), velocity], dim=-1)
        self.grid = torch.zeros(C.HIST_STEPS, C.GRID_SIZE, C.GRID_SIZE, C.TOTAL_FEAT_DIM)
        for r, c in VEHICLES:
            state = [(r + 0.3) / C.GRID_SIZE, (c + 0.6) / C.GRID_SIZE, 0.2, 0.1]
            self.grid[:, r, c, : C.VEHICLE_DIM] = torch.tensor(state)

        class ConstantDisplacement(nn.Module):
            """Predicts the same displacement for every vehicle and records its inputs."""

            def __init__(self, disp):
                super().__init__()
                self.disp, self.inputs = disp, []

            def forward(self, x):
                self.inputs.append(x.clone())
                return self.disp.expand(x.shape[0], -1, -1).clone()

        self.stub = ConstantDisplacement

    def model(self, name):
        model = importlib.import_module(name).ParticleTrafficModel()
        model.interaction_mlp = self.stub(self.disp)
        return model.eval()

    def test_positions_equal_observed_last_position_plus_displacement(self):
        for name in MODELS:
            model = self.model(name)
            for iters in (1, 2, 3):
                with self.subTest(model=name, iters=iters):
                    pred = model.predict_full_grid(self.grid, n_iters=iters)
                    for r, c in VEHICLES:
                        observed = self.grid[-1, r, c, :2]
                        self.torch.testing.assert_close(
                            pred[:, r, c, :2], observed + self.disp[:, :2]
                        )
                        self.torch.testing.assert_close(pred[:, r, c, 2:], self.disp[:, 2:])

    def test_london_scales_displacement_around_observed_position(self):
        model = self.model(MODELS[1])
        pred = model.predict_full_grid(self.grid, n_iters=3, disp_scale=0.5)
        for r, c in VEHICLES:
            expected = self.grid[-1, r, c, :2] + 0.5 * self.disp[:, :2]
            self.torch.testing.assert_close(pred[:, r, c, :2], expected)

    def test_blended_state_still_feeds_later_windows(self):
        alpha, half = 0.3, self.C.WINDOW_SIZE // 2
        for name in MODELS:
            with self.subTest(model=name):
                model = self.model(name)
                model.predict_full_grid(self.grid, n_iters=2, alpha=alpha)
                first, second = model.interaction_mlp.inputs
                ego = VEHICLES.index((10, 12))
                # Ego cell and its (11, 13) neighbour, as seen from the (10, 12) window.
                for dr, dc in ((0, 0), (1, 1)):
                    observed = self.grid[-1, 10 + dr, 12 + dc, : self.C.VEHICLE_DIM]
                    step = self.torch.cat([self.disp[0, :2], self.disp[0, 2:] - observed[2:]])
                    window = first[ego, -1, half + dr, half + dc, : self.C.VEHICLE_DIM]
                    self.torch.testing.assert_close(window, observed)
                    window = second[ego, -1, half + dr, half + dc, : self.C.VEHICLE_DIM]
                    self.torch.testing.assert_close(window, observed + alpha * step)


if __name__ == "__main__":
    unittest.main()
