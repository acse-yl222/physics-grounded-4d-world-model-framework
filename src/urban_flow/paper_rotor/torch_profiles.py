"""Diagnostic profiles at physical cell-centre coordinates; no extrapolation."""
import torch
from common.export import write


def sample_cells(field,positions,spacing_xyz):
    """Trilinearly interpolate ZYX scalar cells at XYZ physical positions."""
    spacing=torch.as_tensor(spacing_xyz,device=field.device,dtype=field.dtype)
    points=torch.as_tensor(positions,device=field.device,dtype=field.dtype)
    extent=torch.tensor(field.shape[::-1],device=field.device,dtype=field.dtype)-1
    index=points/spacing-.5
    if not torch.isfinite(index).all() or (index<0).any() or (index>extent).any():
        raise ValueError('Profile points outside cell-centre support')
    lower=index.floor().long()
    upper=torch.minimum(lower+1,extent.long())
    fraction=index-lower
    result=torch.zeros(points.shape[0],device=field.device,dtype=field.dtype)
    for z in (0,1):
        for y in (0,1):
            for x in (0,1):
                ix=upper[:,0] if x else lower[:,0]
                iy=upper[:,1] if y else lower[:,1]
                iz=upper[:,2] if z else lower[:,2]
                weight=(fraction[:,0] if x else 1-fraction[:,0])
                weight=weight*(fraction[:,1] if y else 1-fraction[:,1])
                weight=weight*(fraction[:,2] if z else 1-fraction[:,2])
                result+=weight*field[iz,iy,ix]
    return result


def export_profiles(solver,out):
    config=solver.config
    hx,hy,hz=config['hub_xyz_m'];diameter=config['rotor_diameter_m']
    velocity=solver.centred()[0]
    y=torch.linspace(hy-1.5*diameter,hy+1.5*diameter,121,device=velocity.device,dtype=velocity.dtype)
    for distance in (1,3,5):
        positions=torch.stack((torch.full_like(y,hx+distance*diameter),y,torch.full_like(y,hz)),-1)
        u=sample_cells(velocity,positions,solver.h)
        write(out/f'data/wake_{distance}d.json',{
            'positions':positions.cpu().tolist(),'values':(1-u/solver.inlet).cpu().tolist(),
            'time_s':solver.time,'steady_convergence_verified':False,
            'sampling':'trilinear cell-centred streamwise velocity'})
