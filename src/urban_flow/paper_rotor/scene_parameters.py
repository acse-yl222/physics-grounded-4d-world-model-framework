"""Explicit rotor-size scaling; never infer full-scale parameters from a label."""
import math


def rotor_parameters(config, radius):
    diameter=2*radius
    sigma=config['sigma_over_diameter']*diameter if 'sigma_over_diameter' in config else config['sigma_m']
    inner_radius=config.get('inner_diameter_ratio',0.)*radius
    if not (math.isfinite(sigma) and sigma>0 and 0<=inner_radius<radius):
        raise ValueError('Invalid scaled rotor support')
    return dict(sigma_m=sigma,inner_radius_m=inner_radius,
                thickness_m=2*config['cutoff_sigma']*sigma)
