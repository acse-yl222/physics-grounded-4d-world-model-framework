import unittest
import torch
from urban_flow.solvers.rans.kepsilon import step, production_per_viscosity


class KEpsilonTests(unittest.TestCase):
    def test_shear_production_and_rigid_rotation(self):
        gradient=torch.zeros((3,3),dtype=torch.float64)
        gradient[0,1]=2
        self.assertAlmostEqual(float(production_per_viscosity(gradient)),4)
        gradient[1,0]=-2
        self.assertAlmostEqual(float(production_per_viscosity(gradient)),0)

    def test_homogeneous_decay_matches_analytic_solution(self):
        k=torch.ones((2,2,2),dtype=torch.float64)
        epsilon=k*.1
        velocity=[]
        for c in range(3):
            dims=[2,2,2];dims[2-c]+=1
            velocity.append(torch.zeros(dims,dtype=k.dtype))
        for _ in range(100):
            k,epsilon=step(k,epsilon,velocity,torch.zeros_like(k),1.5e-5,(1,1,1),.01)
        # dk/dt=-epsilon, de/dt=-C2*epsilon^2/k.
        expected_k=(1+.92*.1)**(-1/.92)
        expected_e=.1*(1+.92*.1)**(-1.92/.92)
        self.assertLess(abs(float(k.mean())-expected_k),2e-4)
        self.assertLess(abs(float(epsilon.mean())-expected_e),2e-5)


if __name__=='__main__':unittest.main()
