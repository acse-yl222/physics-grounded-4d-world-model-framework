import unittest
import numpy as np
import torch
from urban_flow.solvers.rans.terrain import TerrainRANS
from urban_flow.paper_rotor.run_torch_windfarm import FarmRotors

class FarmForceTests(unittest.TestCase):
    def test_yawed_rotor_total_face_force_with_solid_exclusion(self):
        f=torch.ones((16,16,32),dtype=torch.bool);f[7:9,7:9,15:17]=False
        m=TerrainRANS(f,2.,dtype=torch.float64)
        axis=np.array([.94,.34,0.]);axis/=np.linalg.norm(axis)
        g={'origin_xyz_m':[0,0,0],'turbines':[{'id':'test','hub_xyz_m':[32,16,16],'radius_m':6.,'normal_xyz':axis.tolist()}]}
        cfg={'sigma_m':1.,'cutoff_sigma':2.,'ct':.75,'rho_kg_m3':1.225}
        force,rows=FarmRotors(m,g,cfg).loads(.8)
        actual=np.array([float(v.sum())*8*1.225 for v in force])
        np.testing.assert_allclose(actual,-rows[0]['thrust_N']*axis,rtol=1e-12,atol=1e-10)
        for c in range(3):self.assertEqual(float(force[c][~m.mac.opened(c)].abs().max()),0)
        self.assertGreater(rows[0]['disc_speed_m_s'],0.)

if __name__=='__main__':unittest.main()
