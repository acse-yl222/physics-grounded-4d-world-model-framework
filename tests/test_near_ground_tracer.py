import unittest
import numpy as np
from urban_flow.scenarios.near_ground_tracer import PlanarTracer


class TracerTests(unittest.TestCase):
    def test_mass_balance_and_impermeable_wall(self):
        wall = np.zeros((12, 24), bool); wall[:, 12] = True
        uv = np.zeros((2, 12, 24)); uv[0] = 2
        model = PlanarTracer(uv, wall, 4)
        source = np.zeros(wall.shape); source[4:8, 3] = .1
        emitted = outflow = 0
        for _ in range(120):
            row = model.step(min(.5, model.dt_max), source)
            emitted += row['emitted']; outflow += row['outflow']
            self.assertLess(abs(row['balance_error']), 1e-9)
        self.assertAlmostEqual(row['mass'], emitted - outflow, places=8)
        self.assertEqual(float(model.c[:, 13:].max()), 0)
        self.assertGreater(float(model.c[:, 4:12].max()), 0)

    def test_outflow_and_cfl(self):
        uv = np.zeros((2, 8, 8)); uv[0] = 4
        model = PlanarTracer(uv, np.zeros((8, 8), bool), 4, diffusion=0)
        model.c[:, 6] = 1
        with self.assertRaises(ValueError): model.step(model.dt_max * 2, np.zeros((8, 8)))
        total = 0
        for _ in range(30): total += model.step(.5, np.zeros((8, 8)))['outflow']
        self.assertAlmostEqual(total + model.c.sum() * 16, 128, places=8)
        self.assertGreater(total, 127)


if __name__ == '__main__': unittest.main()
