"""Cell-centred velocity gradients and deviatoric stress on rectangular grids.

Boundary values are prescribed at physical faces. Flux divergence is conservative.
Pressure absorbs the isotropic turbulent kinetic energy term, as in incompressible
eddy-viscosity solvers. Domain adapters supply wall stress flux overrides.
"""
import torch
from .transport import face_pair, divergence


def gradient(q, spacing_xyz, boundaries=None):
    boundaries=boundaries or {}
    components=[]
    for c,h in enumerate(spacing_xyz):
        axis=2-c; low,high=boundaries.get(c,(None,None))
        left,right=face_pair(q,axis)
        faces=.5*(left+right)
        if low is not None:faces.narrow(axis,0,1).copy_(torch.ones_like(faces.narrow(axis,0,1))*low)
        if high is not None:faces.narrow(axis,q.shape[axis],1).copy_(torch.ones_like(faces.narrow(axis,0,1))*high)
        components.append(torch.diff(faces,dim=axis)/h)
    return torch.stack(components,-1)


def velocity_gradient(velocity,spacing_xyz,boundaries=None):
    boundaries=boundaries or [{} for _ in range(3)]
    return torch.stack([gradient(u,spacing_xyz,b) for u,b in zip(velocity,boundaries)],-2)


def stress_tensor(grad, viscosity):
    trace=grad.diagonal(dim1=-2,dim2=-1).sum(-1)
    eye=torch.eye(3,device=grad.device,dtype=grad.dtype)
    return viscosity[...,None,None]*(grad+grad.transpose(-1,-2)-(2/3)*trace[...,None,None]*eye)


def stress_divergence(stress,spacing_xyz,boundary_flux=None):
    """boundary_flux[(velocity_component,normal_component)] = (low, high)."""
    boundary_flux=boundary_flux or {}
    result=[]
    for i in range(3):
        flux=[]
        for j in range(3):
            axis=2-j
            left,right=face_pair(stress[...,i,j],axis)
            value=.5*(left+right)
            low,high=boundary_flux.get((i,j),(None,None))
            if low is not None:value.narrow(axis,0,1).copy_(torch.ones_like(value.narrow(axis,0,1))*low)
            if high is not None:value.narrow(axis,value.shape[axis]-1,1).copy_(torch.ones_like(value.narrow(axis,0,1))*high)
            flux.append(value)
        result.append(divergence(flux,spacing_xyz))
    return result


def viscous_acceleration(velocity,viscosity,spacing_xyz,boundaries,boundary_flux=None):
    """Direct two-point normal gradients avoid an odd/even diffusion nullspace."""
    grad=velocity_gradient(velocity,spacing_xyz,boundaries)
    trace=grad.diagonal(dim1=-2,dim2=-1).sum(-1)
    result=[];boundary_flux=boundary_flux or {}
    for i,q in enumerate(velocity):
        fluxes=[]
        for j,h in enumerate(spacing_xyz):
            axis=2-j;lo,hi=boundaries[i].get(j,(None,None))
            left,right=face_pair(q,axis,lo,hi);normal=(right-left)/h
            if lo is not None:normal.narrow(axis,0,1).mul_(2)
            if hi is not None:normal.narrow(axis,q.shape[axis],1).mul_(2)
            cross=grad[...,j,i]-(2/3)*trace if i==j else grad[...,j,i]
            cl,cr=face_pair(cross,axis);vl,vr=face_pair(viscosity,axis)
            value=.5*(vl+vr)*(normal+.5*(cl+cr))
            low,high=boundary_flux.get((i,j),(None,None))
            if low is not None:value.narrow(axis,0,1).copy_(low)
            if high is not None:value.narrow(axis,q.shape[axis],1).fill_(high)
            fluxes.append(value)
        result.append(divergence(fluxes,spacing_xyz))
    return result
