"""LF18 SST viscosity limiter from the authors' public implementation.

Source: BjarkeEltardLarsen/stabRAS_v1712 at
46be844dcd54524c75a3ecdda381c66e1e6a0279, kOmegaSSTStabBase.C.
This helper alone is not the full stabilized closure: that implementation also
changes omega production. Keep standard SST and diagnostic use distinct.
"""
import math
import torch
from .sst import A1,BETA_STAR,strain_squared,blending


def viscosity_ratio(k,omega,distance,nu,grad,lambda2=.05):
    """Return proposed nut / standard SST nut on the same supplied state."""
    if not math.isfinite(lambda2) or lambda2<0:raise ValueError('Invalid lambda2')
    strain=strain_squared(grad)
    rotation=.5*(grad-grad.transpose(-1,-2)).square().sum((-1,-2))
    _,f2=blending(k,omega,distance,nu,torch.zeros_like(k))
    base=torch.maximum(A1*omega,f2*strain.sqrt())
    extra=A1*lambda2*.075/(BETA_STAR*(5/9))*strain/(rotation+1e-15)*omega
    return base/torch.maximum(base,extra)
