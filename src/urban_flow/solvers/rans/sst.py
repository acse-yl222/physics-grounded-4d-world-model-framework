"""Incompressible SST closure, OF2312 defaults, explicit uniform-grid transport.

F3 and ambient decay are disabled. This is standard single-phase SST, without
Larsen--Fuhrman stabilization unless lf18=True is explicitly selected. Time discretization differs from
OpenFOAM SIMPLE; agreement must be established with flow comparisons.
"""
import math
import torch
from .transport import transport
from .stress import gradient
from .kepsilon import production_per_viscosity
from .wall import kepsilon_wall

BETA_STAR, A1 = .09, .31


def blending(k, omega, distance, nu, cross_diffusion):
    root=k.sqrt()
    viscous=500*nu/(distance.square()*omega)
    arg1=torch.minimum(torch.maximum(root/(BETA_STAR*omega*distance),viscous),
                       4*.856*k/(cross_diffusion.clamp_min(1e-10)*distance.square()))
    arg2=torch.maximum(2*root/(BETA_STAR*omega*distance),viscous)
    return torch.tanh(arg1.clamp_max(10).pow(4)),torch.tanh(arg2.clamp_max(100).square())


def strain_squared(grad):
    return .5*(grad+grad.transpose(-1,-2)).square().sum((-1,-2))


def eddy_viscosity(k,omega,distance,nu,grad,lf18=False):
    _,f2=blending(k,omega,distance,nu,torch.zeros_like(k))
    nut=A1*k/torch.maximum(A1*omega,f2*strain_squared(grad).sqrt())
    if lf18:
        from .lf18 import viscosity_ratio
        nut=nut*viscosity_ratio(k,omega,distance,nu,grad)
    return nut


def omega_wall(k,speed,distance,nu):
    # omegaWallFunction dictionary default: binomial blending, n=2.
    wall=kepsilon_wall(k,speed,distance,nu)
    viscous=6*nu/(.075*distance**2)
    log=k.sqrt()/(.09**.25*.41*distance)
    wall['omega']=torch.sqrt(viscous**2+log.square())
    return wall


def step(k,omega,face_velocity,grad,nu,spacing_xyz,dt,distance,
         k_boundaries=None,omega_boundaries=None,wall=None,lf18=False):
    if not math.isfinite(dt) or dt<=0 or not math.isfinite(nu) or nu<=0:
        raise ValueError('Positive finite timestep and viscosity required')
    if not torch.isfinite(k).all() or not torch.isfinite(omega).all() or (k<=0).any() or (omega<=0).any():
        raise ValueError('Finite positive turbulence state required')
    nut=eddy_viscosity(k,omega,distance,nu,grad,lf18=lf18)
    production=nut*production_per_viscosity(grad)
    if wall is not None:
        omega=omega.clone();omega[0]=wall['omega']
        production[0]=wall['production']
    cd=2*.856*(gradient(k,spacing_xyz,k_boundaries)*gradient(omega,spacing_xyz,omega_boundaries)).sum(-1)/omega
    f1,f2=blending(k,omega,distance,nu,cd)
    alpha_k=1.+f1*(.85-1.)
    alpha_w=.856+f1*(.5-.856)
    beta=.0828+f1*(.075-.0828)
    gamma=.44+f1*(5/9-.44)
    g_limit=(10/A1)*BETA_STAR*omega*torch.maximum(A1*omega,f2*strain_squared(grad).sqrt())
    # Authors' stabilized SST uses unbounded gamma*S2 omega production.
    # Constant density makes their additional buoyancy term identically zero.
    g=strain_squared(grad) if lf18 else torch.minimum(production_per_viscosity(grad),g_limit)
    cross=(1-f1)*cd
    rhs=transport(omega,face_velocity,nu+alpha_w*nut,spacing_xyz,omega_boundaries)+gamma*g+cross.clamp_min(0)
    omega_new=(omega+dt*rhs)/(1+dt*(beta*omega+(-cross).clamp_min(0)/omega))
    if wall is not None:omega_new[0]=wall['omega']
    pk=torch.minimum(production,10*BETA_STAR*k*omega_new)
    k_new=(k+dt*(transport(k,face_velocity,nu+alpha_k*nut,spacing_xyz,k_boundaries)+pk))/(1+dt*BETA_STAR*omega_new)
    if not torch.isfinite(k_new).all() or not torch.isfinite(omega_new).all() or (k_new<=0).any() or (omega_new<=0).any():
        raise RuntimeError('SST transport lost positivity or finiteness; reduce timestep')
    return k_new,omega_new
