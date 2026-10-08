import unittest
import torch
from urban_flow.solvers.rans.pressure import RectangularPressure,cosine_transform,project
from urban_flow.solvers.rans.transport import transport,divergence


class PressureTests(unittest.TestCase):
    def test_transform_inverse_odd_and_even_sizes(self):
        for n in (5,6):
            x=torch.arange(3*n,dtype=torch.float64).reshape(3,n).sin()
            restored=cosine_transform(cosine_transform(x,1),1,True)
            torch.testing.assert_close(restored,x,atol=1e-13,rtol=1e-13)

    def test_manufactured_pressure_on_anisotropic_grid(self):
        shape=(5,7,10); spacing=(.2,.3,.4)
        p=torch.arange(350,dtype=torch.float64).reshape(shape).sin()
        faces=[]
        for c in range(3):
            dims=list(shape);dims[2-c]+=1
            faces.append(torch.zeros(dims,dtype=p.dtype))
        rhs=-transport(p,faces,1.,spacing,{0:(None,0.)})
        actual=RectangularPressure(shape,spacing).solve(rhs)
        torch.testing.assert_close(actual,p,atol=2e-12,rtol=2e-12)

    def test_projection_removes_divergence_preserves_inlet(self):
        shape=(5,7,10); spacing=(.2,.3,.4); faces=[]
        generator=torch.Generator().manual_seed(18)
        for c in range(3):
            dims=list(shape);dims[2-c]+=1
            faces.append(torch.randn(dims,dtype=torch.float64,generator=generator))
        corrected,_=project(faces,spacing,RectangularPressure(shape,spacing))
        self.assertLess(float(divergence(corrected,spacing).abs().max()),1e-11)
        torch.testing.assert_close(corrected[0][...,0],faces[0][...,0])


if __name__=='__main__':unittest.main()
