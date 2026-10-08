"""Standard incompressible k-epsilon bulk equations in PyTorch.

Constants and source ordering follow OpenFOAM 2312 RAS/kEpsilon.
Transport is explicit, destruction is locally implicit. Wall functions must be
applied by the domain adapter; this module alone is not a wind-tunnel solver.
"""
import math
import torch
from .transport import transport

CMU, C1, C2 = .09, 1.44, 1.92
SIGMA_K, SIGMA_EPSILON = 1., 1.3


def eddy_viscosity(k, epsilon):
    return CMU*k.square()/epsilon.clamp_min(1e-20)


def production_per_viscosity(gradient):
    """grad[..., i,j] = d U_i/d x_j; contract with deviatoric 2S."""
    twice_strain = gradient+gradient.transpose(-1,-2)
    trace = gradient.diagonal(dim1=-2,dim2=-1).sum(-1)
    eye = torch.eye(3, dtype=gradient.dtype, device=gradient.device)
    return (gradient*(twice_strain-(2/3)*trace[...,None,None]*eye)).sum((-1,-2))


def step(k, epsilon, face_velocity, g_by_nu, nu, spacing_xyz, dt,
         k_boundaries=None, epsilon_boundaries=None, wall=None):
    """Advance divergence-free bulk transport; return new fields and diagnostics.

    Caller must enforce advective/diffusive CFL and wall production/epsilon.
    Positivity violations from transport are rejected, not silently clipped.
    """
    if not math.isfinite(dt) or dt <= 0 or not math.isfinite(nu) or nu <= 0:
        raise ValueError('Positive finite timestep and molecular viscosity required')
    if not torch.isfinite(k).all() or not torch.isfinite(epsilon).all():
        raise ValueError('Nonfinite turbulence state')
    if (k <= 0).any() or (epsilon <= 0).any():
        raise ValueError('Positive turbulence state required')
    nut = eddy_viscosity(k, epsilon)
    epsilon_rhs = transport(epsilon,face_velocity,nu+nut/SIGMA_EPSILON,
                            spacing_xyz,epsilon_boundaries)+C1*CMU*k*g_by_nu
    epsilon_new = (epsilon+dt*epsilon_rhs)/(1+dt*C2*epsilon/k)
    production=nut*g_by_nu
    if wall is not None:
        epsilon_new[0]=wall["epsilon"]
        production[0]=wall["production"]
    k_rhs = transport(k,face_velocity,nu+nut/SIGMA_K,spacing_xyz,k_boundaries)+production
    k_new = (k+dt*k_rhs)/(1+dt*epsilon_new/k)
    if not torch.isfinite(k_new).all() or not torch.isfinite(epsilon_new).all():
        raise RuntimeError('Nonfinite turbulence update')
    if (k_new <= 0).any() or (epsilon_new <= 0).any():
        raise RuntimeError('Turbulence transport lost positivity; reduce timestep')
    return k_new, epsilon_new
