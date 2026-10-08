import unittest
import torch
from urban_flow.solvers.rans.tunnel import Tunnel


class TunnelTests(unittest.TestCase):
    def test_coupled_wall_flow_preserves_inlet_and_mass(self):
        solver=Tunnel((6,8,12),(.1,.13,.08),10.,1.5e-5,.003,.03)
        for _ in range(12):
            result=solver.advance(solver.stable_dt())
        self.assertLess(result['divergence_rms'],1e-10)
        self.assertGreater(result['k_min'],0)
        self.assertGreater(result['epsilon_min'],0)
        torch.testing.assert_close(solver.faces[0][...,0],torch.full_like(solver.faces[0][...,0],10.))
        self.assertEqual(float(solver.faces[2][0].abs().max()),0)
        u=solver.centred()[0]
        self.assertLess(float(u[0,:,2:-2].mean()),float(u[-1,:,2:-2].mean()))


if __name__=='__main__':unittest.main()
