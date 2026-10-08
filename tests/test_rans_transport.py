import unittest
import torch
from urban_flow.solvers.rans.transport import transport


class TransportTests(unittest.TestCase):
    def faces(self, shape):
        result=[]
        for c in range(3):
            dims=list(shape); dims[2-c]+=1
            result.append(torch.zeros(dims,dtype=torch.float64))
        return result

    def test_closed_diffusion_conserves_mass(self):
        q=torch.arange(120,dtype=torch.float64).reshape(4,5,6).sin()
        result=transport(q,self.faces(q.shape),.1+q.square(),(.2,.3,.4))
        self.assertLess(abs(float(result.sum())),1e-10)
        self.assertLess(float((q*result).sum()),0)

    def test_linear_dirichlet_profile_has_zero_laplacian(self):
        q=(torch.arange(6,dtype=torch.float64)+.5)[None,None,:].expand(4,5,6)*.2
        result=transport(q,self.faces(q.shape),1.,(.2,.3,.4),{0:(0.,1.2)})
        self.assertLess(float(result.abs().max()),1e-12)

    def test_advection_mass_matches_boundary_flux(self):
        q=torch.ones((4,5,6),dtype=torch.float64)*2
        faces=self.faces(q.shape); faces[0].fill_(3.)
        result=transport(q,faces,0.,(.2,.3,.4),{0:(1.,None)})
        self.assertAlmostEqual(float(result.sum())*.2*.3*.4,3*(1-2)*(5*.3)*(4*.4))


if __name__=='__main__': unittest.main()
