"""Physical invariants for the 10 m/s rotor experiment; Torch is optional."""
import json
import math
from pathlib import Path
import unittest

try:
    import torch
    from urban_flow.paper_rotor.rotor import WeightedRotor
    from urban_flow.paper_rotor.wind_tunnel import axial_faces, check_config
except ImportError:
    torch = None


@unittest.skipIf(torch is None, 'Torch experiment environment required')
class PaperRotorTests(unittest.TestCase):
    def grid(self):
        h = .02
        q = torch.arange(-.4, .4, h, dtype=torch.float64)+h/2
        z, y, x = torch.meshgrid(q, q, q, indexing='ij')
        return torch.stack((x, y, z), -1), h

    def test_ideal_ten_ms_load_and_reaction(self):
        xyz, h = self.grid()
        rotor = WeightedRotor(.4647/2, .02, ct=.95, inner_radius=.045)
        u = torch.zeros_like(xyz)
        u[..., 0] = 10*(1-rotor.a)
        result = rotor(xyz, u, h**3, [0, 0, 0], [1, 0, 0])
        expected = .5*1.225*math.pi*(.4647/2)**2*.95*10**2
        self.assertAlmostEqual(float(result['thrust']), expected, places=10)
        reaction = result['acceleration'].sum((0, 1, 2))*1.225*h**3
        torch.testing.assert_close(reaction, -result['body_force'])
        faces = axial_faces(result['acceleration'][..., 0])
        self.assertAlmostEqual(float(faces.sum())*1.225*h**3, -expected, places=10)

    def test_relative_motion_yaw_and_platform_moment(self):
        xyz, h = self.grid()
        rotor = WeightedRotor(.2, .02, ct=.95)
        u = torch.zeros_like(xyz); u[..., 0] = 10
        axis = [math.sqrt(.5), math.sqrt(.5), 0]
        result = rotor(xyz, u, h**3, [0, 0, .1], axis,
                       hub_velocity=[2, 0, 0], com=[0, 0, 0])
        self.assertAlmostEqual(float(result['disc_speed']), 8*math.sqrt(.5), places=10)
        expected = torch.linalg.cross(torch.tensor([0, 0, .1], dtype=torch.float64), result['body_force'])
        torch.testing.assert_close(result['body_torque'], expected)
        reaction = result['acceleration'].sum((0, 1, 2))*1.225*h**3
        torch.testing.assert_close(reaction, -result['body_force'])

    def test_translation_and_signed_thruster(self):
        xyz, h = self.grid()
        rotor = WeightedRotor(.2, .02, ct=.95, inner_radius=.045)
        u = torch.zeros_like(xyz); u[..., 0] = 10
        loads = [rotor(xyz, u, h**3, [offset, 0, 0], [1, 0, 0])
                 for offset in (0., h/2)]
        self.assertAlmostEqual(float(loads[0]['thrust']), float(loads[1]['thrust']), places=10)
        result = rotor(xyz, u, h**3, [0, 0, 0], [1, 0, 0], thrust=-5.4)
        self.assertAlmostEqual(float(result['body_force'][0]), -5.4, places=10)
        self.assertGreater(float(result['acceleration'][..., 0].sum()), 0)
        self.assertEqual(float(result['weight'][(xyz[..., 1]**2+xyz[..., 2]**2)<.045**2].sum()), 0)

    def test_config_and_refinement_preserve_physical_support(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root/'project/actuator_lab/configs/paper_rotor_10ms.json').read_text())
        self.assertEqual(config['inlet_m_s'], 10)
        self.assertEqual(check_config(config), (64, 64, 128))
        self.assertEqual(check_config(dict(config, cell_m=.02)), (128, 128, 256))
        for patch in ({'cell_m': .03}, {'sigma_m': .04}, {'hub_xyz_m': [0, 1, 1]}, {'end_s': -1}):
            with self.assertRaises(ValueError):
                check_config(dict(config, **patch))


if __name__ == '__main__':
    unittest.main()
