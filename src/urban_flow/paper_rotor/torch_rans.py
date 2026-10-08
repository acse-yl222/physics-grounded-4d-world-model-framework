"""Rotor coupling for the rectangular PyTorch RANS tunnel (under validation)."""
import math
import torch
from urban_flow.solvers.rans.tunnel import Tunnel
from .rotor import WeightedRotor


class RotorTunnel(Tunnel):
    def __init__(self,config,device='cpu',dtype=torch.float64,model='kEpsilon'):
        counts=config['mesh_counts_xyz']
        spacing=[length/count for length,count in zip(config['domain_xyz_m'],counts)]
        super().__init__(tuple(counts[::-1]),spacing,config['inlet_m_s'],
            config['kinematic_viscosity_m2_s'],config['turbulence_intensity'],
            config['turbulence_length_m'],device,dtype,model=model)
        self.config=config
        self.rotor=WeightedRotor(config['rotor_diameter_m']/2,config['sigma_m'],
            config['ct'],config['inner_diameter_m']/2,config['cutoff_sigma'],config['rho_kg_m3'])
        half=[config['rotor_thickness_m']/2]+[config['rotor_diameter_m']/2]*2
        indices=[]
        for p,r,h,n in zip(config['hub_xyz_m'],half,spacing,counts):
            start=max(1,math.floor((p-r)/h)-1);end=min(n-1,math.ceil((p+r)/h)+1)
            if p-r<=h or p+r>=(n-1)*h:
                raise ValueError('Rotor support must be clear of domain boundaries')
            indices.append(torch.arange(start,end,device=device))
        iz,iy,ix=torch.meshgrid(*indices[::-1],indexing='ij')
        self.indices=(iz,iy,ix)
        self.xyz=torch.stack(((ix.to(dtype)+.5)*spacing[0],(iy.to(dtype)+.5)*spacing[1],(iz.to(dtype)+.5)*spacing[2]),-1).to(dtype)
        self.volume=math.prod(spacing)

    def rotor_load(self):
        iz,iy,ix=self.indices
        velocity=torch.stack([u[iz,iy,ix] for u in self.centred()],-1)
        return self.rotor(self.xyz,velocity,self.volume,self.config['hub_xyz_m'],[1,0,0])

    def advance_rotor(self,dt):
        load_time=self.time
        load=self.rotor_load()
        acceleration=[torch.zeros_like(self.k) for _ in range(3)]
        for c in range(3):acceleration[c][self.indices]=load['acceleration'][...,c]
        force_error=abs(float(acceleration[0].sum())*self.volume*self.config['rho_kg_m3']+float(load['thrust']))
        result=self.advance(dt,acceleration)
        result.update(load_time_s=load_time,thrust_N=float(load['thrust']),disc_speed_m_s=float(load['disc_speed']),
                      force_balance_error_N=force_error)
        return result
