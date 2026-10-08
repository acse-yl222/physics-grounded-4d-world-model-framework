import unittest
import torch
from urban_flow.paper_rotor.torch_profiles import sample_cells


class ProfileTests(unittest.TestCase):
    def test_linear_field_exact_on_anisotropic_cells(self):
        h=(.2,.3,.4)
        z,y,x=torch.meshgrid((torch.arange(6,dtype=torch.float64)+.5)*h[2],
            (torch.arange(7,dtype=torch.float64)+.5)*h[1],
            (torch.arange(8,dtype=torch.float64)+.5)*h[0],indexing='ij')
        points=torch.tensor([[.31,.61,.81],[1.2,1.7,1.9],[.1,.15,.2]],dtype=x.dtype)
        actual=sample_cells(2*x-3*y+4*z,points,h)
        torch.testing.assert_close(actual,2*points[:,0]-3*points[:,1]+4*points[:,2])

    def test_extrapolation_rejected(self):
        with self.assertRaises(ValueError):sample_cells(torch.ones(4,4,4),[[0,1,1]],(1,1,1))


if __name__=='__main__':unittest.main()
