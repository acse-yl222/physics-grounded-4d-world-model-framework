import unittest
import torch
from urban_flow.solvers.rans import sst
from urban_flow.solvers.rans.tunnel import Tunnel


class SSTTests(unittest.TestCase):
    def test_wall_and_free_stream_limits(self):
        k=torch.ones(2,dtype=torch.float64)
        omega=torch.ones_like(k)
        y=torch.tensor([1e-7,1e7],dtype=k.dtype)
        f1,f2=sst.blending(k,omega,y,1e-5,torch.zeros_like(k))
        self.assertAlmostEqual(float(f1[0]),1.)
        self.assertLess(float(f1[1]),1e-15)
        self.assertAlmostEqual(float(f2[0]),1.)
        self.assertLess(float(f2[1]),1e-10)

    def test_shear_limiter(self):
        k=torch.ones(2,dtype=torch.float64);omega=k.clone();y=k*.001
        grad=torch.zeros(2,3,3,dtype=k.dtype);grad[:,0,1]=100
        nut=sst.eddy_viscosity(k,omega,y,1e-5,grad)
        torch.testing.assert_close(nut,torch.full_like(k,.0031))
        self.assertTrue((nut<k/omega).all())

    def test_homogeneous_decay(self):
        shape=(4,4,4);k=torch.ones(shape,dtype=torch.float64);omega=k*2
        faces=[torch.zeros((4,4,5),dtype=k.dtype),torch.zeros((4,5,4),dtype=k.dtype),torch.zeros((5,4,4),dtype=k.dtype)]
        grad=torch.zeros(*shape,3,3,dtype=k.dtype);y=torch.full_like(k,1e7);dt=.01
        kn,wn=sst.step(k,omega,faces,grad,1e-5,(1,1,1),dt,y)
        expected=omega/(1+dt*.0828*omega)
        torch.testing.assert_close(wn,expected)
        torch.testing.assert_close(kn,k/(1+dt*.09*expected))

    def test_coupled_tunnel_conserves_mass_and_wall_slows_flow(self):
        solver=Tunnel((8,8,16),(.1,.1,.1),10,1.5e-5,.003,.03,model='kOmegaSST')
        for _ in range(12):result=solver.advance(min(.001,solver.stable_dt()))
        self.assertLess(result['divergence_rms'],1e-10)
        self.assertLess(float(solver.centred()[0][0,:,2:-2].mean()),10.)
        self.assertTrue((solver.omega>0).all())
        self.assertTrue(torch.equal(solver.faces[0][...,0],torch.full((8,8),10.,dtype=torch.float64)))


if __name__=='__main__':unittest.main()
