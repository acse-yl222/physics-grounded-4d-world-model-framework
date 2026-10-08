"""Single flat-wall k-epsilon functions matching OF2312 default stepwise forms.

No corner averaging is needed for the wind tunnel's single bottom wall.
The default epsilonWallFunction has lowReCorrection=false; preserve that
choice explicitly rather than substituting a different low-Re closure.
"""
import math
import torch


def kepsilon_wall(k, tangential_speed, distance, nu, low_re_correction=False):
    if distance <= 0 or nu <= 0:
        raise ValueError('Positive wall distance and viscosity required')
    if (k < 0).any() or not torch.isfinite(k).all():
        raise ValueError('Finite nonnegative wall-cell k required')
    cmu, kappa, e = .09, .41, 9.8
    transition=11.
    for _ in range(10):
        transition=math.log(max(e*transition,1.))/kappa
    friction=cmu**.25*torch.sqrt(k)
    yplus=friction*distance/nu
    nut=torch.where(yplus>transition,
        nu*(yplus*kappa/torch.log((e*yplus).clamp_min(1.0001))-1),
        torch.zeros_like(k))
    epsilon=cmu**.75*k.pow(1.5)/(kappa*distance)
    production=(nu+nut)*(tangential_speed.abs()/distance)*friction/(kappa*distance)
    if low_re_correction:
        epsilon=torch.where(yplus<transition,2*k*nu/distance**2,epsilon)
        production=torch.where(yplus>transition,production,torch.zeros_like(production))
    return dict(nut=nut,epsilon=epsilon,production=production,yplus=yplus)
