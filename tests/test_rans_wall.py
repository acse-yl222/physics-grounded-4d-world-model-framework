import unittest
import torch
from urban_flow.solvers.rans.wall import kepsilon_wall


class WallTests(unittest.TestCase):
    def test_log_layer_equilibrium_production_equals_dissipation(self):
        k=torch.tensor([1.],dtype=torch.float64);y=.1;nu=1e-5
        friction=.09**.25*k.sqrt();yplus=friction*y/nu
        speed=friction*torch.log(9.8*yplus)/.41
        state=kepsilon_wall(k,speed,y,nu)
        torch.testing.assert_close(state['production'],state['epsilon'])
        self.assertGreater(float(state['nut']),0)

    def test_viscous_sublayer_and_explicit_low_re_switch(self):
        k=torch.tensor([1e-6],dtype=torch.float64);y=.001;nu=1e-5
        default=kepsilon_wall(k,k*0,y,nu)
        corrected=kepsilon_wall(k,k*0,y,nu,True)
        self.assertEqual(float(default['nut']),0)
        torch.testing.assert_close(corrected['epsilon'],2*k*nu/y**2)
        self.assertNotEqual(float(default['epsilon']),float(corrected['epsilon']))


if __name__=='__main__':unittest.main()
