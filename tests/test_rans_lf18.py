import unittest
import torch
from urban_flow.solvers.rans.lf18 import viscosity_ratio


class LimiterTests(unittest.TestCase):
    def test_shear_unaffected_potential_strain_suppressed(self):
        grad=torch.zeros(2,3,3,dtype=torch.float64)
        grad[0,0,1]=1.
        grad[1,0,0]=1.;grad[1,1,1]=-1.
        state=torch.ones(2,dtype=grad.dtype)
        ratio=viscosity_ratio(state,state,state,1.5e-5,grad)
        self.assertEqual(float(ratio[0]),1.)
        self.assertLess(float(ratio[1]),1e-10)
        torch.testing.assert_close(viscosity_ratio(state,state,state,1.5e-5,grad,0),state)

    def test_stabilized_omega_source_is_not_standard_limiter(self):
        from urban_flow.solvers.rans.sst import step
        shape=(3,3,3);k=torch.full(shape,.001,dtype=torch.float64);w=torch.ones_like(k)
        faces=[torch.zeros((3,3,4),dtype=k.dtype),torch.zeros((3,4,3),dtype=k.dtype),torch.zeros((4,3,3),dtype=k.dtype)]
        grad=torch.zeros(*shape,3,3,dtype=k.dtype);grad[...,0,1]=100
        distance=torch.full_like(k,1e7);dt=1e-6
        _,actual=step(k,w,faces,grad,1.5e-5,(1,1,1),dt,distance,lf18=True)
        expected=(w+dt*.44*10000)/(1+dt*.0828*w)
        torch.testing.assert_close(actual,expected)
        _,standard=step(k,w,faces,grad,1.5e-5,(1,1,1),dt,distance)
        self.assertTrue((actual>standard).all())


if __name__=='__main__':unittest.main()
