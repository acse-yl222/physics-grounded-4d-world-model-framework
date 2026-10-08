"""FFT diagonalization of a uniform rectangular finite-volume Poisson operator.

Cell-centred fields, XYZ spacings, tensor ZYX. Zero Neumann at inlet and
four lateral walls, zero Dirichlet at the east outlet. Pressure is the
projection potential (dt*p/rho), not physical pressure. No immersed solids.
"""
import math
import torch


def cosine_transform(x, axis, inverse=False):
    n=x.shape[axis]
    angle=torch.arange(n,device=x.device,dtype=x.dtype)*math.pi/(2*n)
    phase=torch.polar(torch.ones_like(angle),angle)
    shape=[1]*x.ndim;shape[axis]=n;phase=phase.reshape(shape)
    if not inverse:
        extended=torch.cat((x,x.flip((axis,))),axis)
        spectrum=torch.fft.rfft(extended,dim=axis).narrow(axis,0,n)
        return .5*(spectrum*phase.conj()).real
    spectrum=2*x*phase
    zero_shape=list(x.shape);zero_shape[axis]=1
    spectrum=torch.cat((spectrum,torch.zeros(zero_shape,device=x.device,dtype=spectrum.dtype)),axis)
    return torch.fft.irfft(spectrum,n=2*n,dim=axis).narrow(axis,0,n)


class RectangularPressure:
    def __init__(self, shape, spacing_xyz, device='cpu', dtype=torch.float64):
        if len(shape)!=3 or len(spacing_xyz)!=3 or min(shape)<2 or min(spacing_xyz)<=0:
            raise ValueError('Three positive spacings and dimensions >=2 required')
        self.shape=tuple(shape)
        extended=(shape[0],shape[1],2*shape[2])
        denominator=torch.zeros(extended,device=device,dtype=dtype)
        for axis,(n,h) in enumerate(zip(extended,spacing_xyz[::-1])):
            eigen=4*torch.sin(torch.arange(n,device=device,dtype=dtype)*math.pi/(2*n)).square()/h**2
            view=[1]*3;view[axis]=n
            denominator+=eigen.reshape(view)
        denominator[0,0,0]=1
        self.denominator=denominator

    def solve(self, rhs):
        """Solve -laplacian(potential)=rhs without a periodic wrap boundary."""
        if tuple(rhs.shape)!=self.shape:
            raise ValueError('Pressure RHS shape mismatch')
        # Odd reflection across outlet converts N/D into N/N on doubled x.
        value=torch.cat((rhs,-rhs.flip((-1,))),-1)
        for axis in range(3):value=cosine_transform(value,axis)
        value=value/self.denominator
        value[0,0,0]=0
        for axis in reversed(range(3)):value=cosine_transform(value,axis,inverse=True)
        return value[...,:self.shape[-1]]


def project(face_velocity, spacing_xyz, solver):
    """Return divergence-free faces, preserving prescribed inlet/wall fluxes."""
    from .transport import divergence
    potential=solver.solve(-divergence(face_velocity,spacing_xyz))
    result=[]
    for component,(velocity,h) in enumerate(zip(face_velocity,spacing_xyz)):
        axis=2-component
        edge_shape=list(potential.shape);edge_shape[axis]=1
        low=torch.zeros(edge_shape,device=potential.device,dtype=potential.dtype)
        high=-2*potential.narrow(axis,potential.shape[axis]-1,1)/h if component==0 else low
        gradient=torch.cat((low,torch.diff(potential,dim=axis)/h,high),axis)
        result.append(velocity-gradient)
    return result,potential
