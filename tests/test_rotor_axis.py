import unittest
import torch
from urban_flow.paper_rotor.rotor import WeightedRotor

class RotorAxisTests(unittest.TestCase):
    def test_oblique_axis_does_not_exclude_points_on_centreline(self):
        xyz=torch.tensor([[1.,1.,1.]],dtype=torch.float64)
        axis=xyz[0]/torch.linalg.vector_norm(xyz[0])
        velocity=10*axis[None,:]
        rotor=WeightedRotor(2.,2.)
        result=rotor(xyz,velocity,torch.ones(1,dtype=torch.float64),[0,0,0],[1,1,1])
        self.assertAlmostEqual(float(result['disc_speed']),10.)
        self.assertGreater(float(result['weight'][0]),0.)
        reaction=-result['acceleration'].sum(0)*rotor.rho
        torch.testing.assert_close(reaction,result['body_force'])

    def test_zero_and_nonfinite_axes_fail_instead_of_returning_nan(self):
        xyz=torch.zeros((1,3),dtype=torch.float64)
        for axis in ([0,0,0],[float('nan'),0,0],[float('inf'),0,0]):
            with self.assertRaises(ValueError):
                WeightedRotor(1,1)(xyz,xyz,torch.ones(1),[0,0,0],axis)
