import unittest
import torch
from urban_flow.solvers.rans.stress import velocity_gradient,stress_tensor,stress_divergence


class StressTests(unittest.TestCase):
    def test_linear_shear_exact_with_physical_boundary_values(self):
        shape=(5,6,7);h=(.2,.3,.4)
        y=(torch.arange(6,dtype=torch.float64)+.5)*h[1]
        u=(2*y[None,:,None]).expand(shape);zero=torch.zeros_like(u)
        grad=velocity_gradient([u,zero,zero],h,[{1:(0.,2*6*h[1])},{},{}])
        torch.testing.assert_close(grad[...,0,1],torch.full_like(u,2.))
        stress=stress_tensor(grad,torch.full_like(u,.1))
        torch.testing.assert_close(stress[...,0,1],torch.full_like(u,.2))
        for value in stress_divergence(stress,h):
            self.assertLess(float(value.abs().max()),1e-13)

    def test_variable_viscosity_shear_interior(self):
        shape=(5,6,7);h=(.2,.3,.4)
        y=(torch.arange(6,dtype=torch.float64)+.5)*h[1]
        viscosity=(1+y[None,:,None]).expand(shape)
        grad=torch.zeros((*shape,3,3),dtype=torch.float64);grad[...,0,1]=2
        acceleration=stress_divergence(stress_tensor(grad,viscosity),h)
        torch.testing.assert_close(acceleration[0][:,1:-1],torch.full_like(acceleration[0][:,1:-1],2.))
        self.assertEqual(float(acceleration[1].abs().max()),0)

    def test_rigid_rotation_has_zero_stress(self):
        grad=torch.zeros((2,2,2,3,3),dtype=torch.float64)
        grad[...,0,1]=3;grad[...,1,0]=-3
        stress=stress_tensor(grad,torch.ones((2,2,2),dtype=torch.float64))
        self.assertEqual(float(stress.abs().max()),0)


if __name__=='__main__':unittest.main()
