import unittest
import torch
from urban_flow.solvers.rans.terrain import TerrainRANS

class TerrainTests(unittest.TestCase):
    def test_voxel_obstacle_mass_and_turbulence(self):
        f=torch.ones((8,12,24),dtype=torch.bool);f[:2]=False;f[2:5,5:7,10:12]=False
        m=TerrainRANS(f,2.,dtype=torch.float64)
        for _ in range(4):info=m.advance(min(.02,m.stable_dt()))
        self.assertLess(info['divergence_rms'],1e-5)
        self.assertGreater(info['k_min'],0)
        self.assertGreater(info['epsilon_min'],0)
        for c in range(3):self.assertEqual(float(m.mac.vel[c][~m.mac.opened(c)].abs().max()),0.)
        flux=m.faces()
        self.assertAlmostEqual(float(flux[0][...,-1].sum()),float(flux[0][...,0].sum()),places=3)

    def test_scalar_no_flux_through_solid(self):
        f=torch.ones((8,8,16),dtype=torch.bool);f[:2]=False
        m=TerrainRANS(f,1.,dtype=torch.float64)
        q=torch.ones_like(m.k);q[~f]=999.
        rhs=m.scalar_rhs(q,1.,[torch.zeros_like(x) for x in m.faces()],1.)
        self.assertLess(float(rhs.abs().max()),1e-12)

if __name__=='__main__':unittest.main()
