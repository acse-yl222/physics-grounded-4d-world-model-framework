import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
try:
    from urban_flow.physics.conservative_tracer import SteadyTracer
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'SciPy optional simulation dependency unavailable')
class ConservativeTracerTests(unittest.TestCase):
    def solver(self, shape=(3,4,8), speed=1., h=1., k=.3, blocked=None):
        f=np.ones(shape,dtype=bool)
        if blocked is not None:
            f[blocked]=False
        faces=[np.zeros(shape) for _ in range(3)]
        faces[0][:]=speed
        return SteadyTracer(f,faces,np.full(shape[:2],speed),h,k,open_top=False)

    def test_zero_source(self):
        s=self.solver()
        field,check=s.solve(np.zeros(s.fluid.shape))
        np.testing.assert_array_equal(field,0)
        self.assertEqual(check['emitted_au_s'],0)

    def test_conservation_nonnegative_and_superposition(self):
        s=self.solver()
        a=np.zeros(s.fluid.shape);b=a.copy()
        a[1,1,2]=1;b[1,2,5]=2
        ca,qa=s.solve(a);cb,qb=s.solve(b);total,qt=s.solve(a+b)
        np.testing.assert_allclose(total,ca+cb,rtol=1e-12,atol=1e-12)
        self.assertGreaterEqual(total.min(),-1e-14)
        self.assertLess(qt['mass_balance_relative_error'],1e-12)
        np.testing.assert_allclose(np.asarray(s.matrix.sum(axis=0)).ravel(),s.out_coeff,atol=1e-14)

    def test_closed_solid_wall(self):
        s=self.solver(speed=0,blocked=(slice(None),slice(None),4))
        q=np.zeros(s.fluid.shape);q[1,1,2]=1
        c,_=s.solve(q)
        np.testing.assert_allclose(c[:,:,5:],0,atol=1e-14)
        q[1,1,4]=1
        with self.assertRaisesRegex(ValueError,'solid'):
            s.solve(q)

    def test_pure_diffusion_second_order_refinement(self):
        errors=[]
        for n in [10,20]:
            h=10/n
            s=self.solver((1,1,n),speed=0,h=h,k=1)
            q=np.full(s.fluid.shape,h**3)
            c,_=s.solve(q)
            x=(np.arange(n)+.5)*h
            exact=.5*x*(10-x)
            errors.append(np.max(np.abs(c[0,0]-exact)))
        self.assertAlmostEqual(errors[0]/errors[1],4.,places=8)

    def test_invalid_inputs(self):
        s=self.solver()
        for value in [-1,np.nan,np.inf]:
            q=np.zeros(s.fluid.shape);q[0,0,0]=value
            with self.assertRaises(ValueError):
                s.solve(q)

    def test_changed_flow_changes_response(self):
        q=np.zeros((3,4,8));q[1,1,3]=1
        slow,_=self.solver(speed=.5).solve(q)
        fast,_=self.solver(speed=2).solve(q)
        self.assertGreater(slow.mean(),fast.mean())


if __name__=='__main__':
    unittest.main()

