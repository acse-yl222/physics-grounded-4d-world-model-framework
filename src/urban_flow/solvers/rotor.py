"""Davidson et al. 2026, doi:10.1016/j.joes.2026.07.020, §2.2.
Pure torch weighted body-force ADM. Force density/acceleration explicitly
separated from volume-integrated cell force (paper Eq.6 notation ambiguous).
Axis points along force ON BODY; fluid always gets opposite reaction.
"""
import math
import torch
from torch import nn

class WeightedRotor(nn.Module):
 def __init__(self,radius,sigma,ct=.75,inner_radius=0.,cutoff=2.,rho=1.225):
  super().__init__()
  if not (0<=ct<=1 and radius>inner_radius>=0 and sigma>0 and cutoff>0 and rho>0):raise ValueError('Invalid rotor parameters')
  self.radius=radius;self.sigma=sigma;self.ct=ct;self.inner_radius=inner_radius;self.cutoff=cutoff;self.rho=rho
  self.a=(1-math.sqrt(1-ct))/2
  # Swept area includes hub hole; hole excludes force-support cells only.
  self.area=math.pi*radius**2
 def forward(self,xyz,velocity,cell_volume,hub,axis,hub_velocity=None,com=None,thrust=None):
  axis=torch.as_tensor(axis,device=xyz.device,dtype=xyz.dtype);axis=axis/torch.linalg.vector_norm(axis)
  hub=torch.as_tensor(hub,device=xyz.device,dtype=xyz.dtype)
  relative=xyz-hub;axial=(relative*axis).sum(-1);radial2=(relative**2).sum(-1)-axial**2
  support=(radial2<=self.radius**2)&(radial2>=self.inner_radius**2)&(axial.abs()<=self.cutoff*self.sigma)
  weight=torch.exp(-axial**2/(2*self.sigma**2))*support
  weighted_volume=(weight*cell_volume).sum()
  if float(weighted_volume)<=0:raise ValueError('Rotor has no resolved cells')
  mean=(velocity*(weight*cell_volume)[...,None]).sum(tuple(range(velocity.ndim-1)))/weighted_volume
  if hub_velocity is not None:mean=mean-torch.as_tensor(hub_velocity,device=xyz.device,dtype=xyz.dtype)
  ud=(mean*axis).sum().abs()
  T=2*self.rho*self.area*self.a/(1-self.a)*ud**2 if thrust is None else torch.as_tensor(thrust,device=xyz.device,dtype=xyz.dtype)
  body_force=T*axis
  acceleration=-body_force*weight[...,None]/(self.rho*weighted_volume)
  torque=torch.zeros_like(body_force) if com is None else torch.linalg.cross(hub-torch.as_tensor(com,device=xyz.device,dtype=xyz.dtype),body_force)
  return dict(acceleration=acceleration,body_force=body_force,body_torque=torque,disc_speed=ud,thrust=T,weight=weight)
