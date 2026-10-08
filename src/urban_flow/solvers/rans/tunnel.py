"""Transient staggered-face PyTorch k-epsilon/SST tunnel, under validation.

Uniform rectangular cells; fixed inlet, pressure outlet, slip top/sides,
no-slip bottom with OF2312-style wall functions. First-order explicit transport
and locally implicit turbulence destruction differ from OpenFOAM SIMPLE.
"""
import torch
from .transport import face_pair, transport, divergence
from .pressure import RectangularPressure, project
from .stress import velocity_gradient, viscous_acceleration
from .kepsilon import eddy_viscosity, production_per_viscosity, step as turbulence_step
from .wall import kepsilon_wall
from . import sst


class Tunnel:
    def __init__(self,shape,spacing_xyz,inlet,nu,intensity,length,device='cpu',dtype=torch.float64,model='kEpsilon'):
        if model not in ('kEpsilon','kOmegaSST','kOmegaSSTLF18'):raise ValueError('Unsupported turbulence model')
        self.model=model
        self.shape=tuple(shape);self.h=tuple(spacing_xyz);self.inlet=inlet;self.nu=nu
        self.k_in=1.5*(inlet*intensity)**2
        self.e_in=.09**.75*self.k_in**1.5/length
        self.k=torch.full(shape,self.k_in,device=device,dtype=dtype)
        self.epsilon=torch.full_like(self.k,self.e_in)
        self.omega_in=self.e_in/(.09*self.k_in)
        self.omega=torch.full_like(self.k,self.omega_in)
        self.distance=(torch.arange(shape[0],device=device,dtype=dtype)+.5)[:,None,None]*self.h[2]
        self.faces=[]
        for c in range(3):
            dims=list(shape);dims[2-c]+=1
            self.faces.append(torch.full(dims,inlet if c==0 else 0.,device=device,dtype=dtype))
        self.pressure=RectangularPressure(shape,spacing_xyz,device,dtype)
        self.boundaries=[{0:(inlet,None),2:(0.,None)},
                         {0:(0.,None),1:(0.,0.),2:(0.,None)},
                         {0:(0.,None),2:(0.,0.)}]
        self.time=0.

    def centred(self):
        return [.5*(q.narrow(2-c,0,self.shape[2-c])+q.narrow(2-c,1,self.shape[2-c]))
                for c,q in enumerate(self.faces)]

    def viscosity(self,velocity=None,grad=None):
        if self.model=='kEpsilon':return eddy_viscosity(self.k,self.epsilon)
        if grad is None:grad=velocity_gradient(velocity or self.centred(),self.h,self.boundaries)
        return sst.eddy_viscosity(self.k,self.omega,self.distance,self.nu,grad,lf18=self.model=='kOmegaSSTLF18')

    def stable_dt(self,cfl=.3):
        velocity=self.centred();nut=self.viscosity(velocity)
        rate=sum(u.abs()/h for u,h in zip(velocity,self.h))
        rate+=4*(self.nu+nut)*sum(1/h**2 for h in self.h)
        return cfl/max(float(rate.max()),1e-20)

    def advance(self,dt,acceleration=None):
        if dt<=0 or dt>self.stable_dt(.45):
            raise ValueError('Timestep exceeds explicit transport stability bound')
        velocity=self.centred()
        grad=velocity_gradient(velocity,self.h,self.boundaries)
        nut=self.viscosity(velocity,grad)
        wall_function=kepsilon_wall if self.model=='kEpsilon' else sst.omega_wall
        wall=wall_function(self.k[0],torch.sqrt(velocity[0][0]**2+velocity[1][0]**2),self.h[2]/2,self.nu)
        flux={}
        for i in range(3):
            flux[i,2]=((self.nu+wall['nut'])*velocity[i][0]/(self.h[2]/2),0. if i!=2 else None)
            if i!=1:flux[i,1]=(0.,0.)
        viscous=viscous_acceleration(velocity,self.nu+nut,self.h,self.boundaries,flux)
        updated=[]
        for c,u in enumerate(velocity):
            rhs=transport(u,self.faces,0.,self.h,self.boundaries[c])+viscous[c]
            if acceleration is not None:rhs=rhs+acceleration[c]
            axis=2-c;left,right=face_pair(rhs,axis)
            increment=.5*(left+right)
            increment.narrow(axis,0,1).zero_()
            if c!=0:increment.narrow(axis,self.shape[axis],1).zero_()
            updated.append(self.faces[c]+dt*increment)
        updated,potential=project(updated,self.h,self.pressure)
        # Turbulence transport uses the old divergence-free velocity, consistently
        # with explicit advection and production. Wall epsilon constrains first cells.
        if self.model=='kEpsilon':
            k,e=turbulence_step(self.k,self.epsilon,self.faces,production_per_viscosity(grad),
                self.nu,self.h,dt,{0:(self.k_in,None)},{0:(self.e_in,None)},wall=wall)
        else:
            k,omega=sst.step(self.k,self.omega,self.faces,grad,self.nu,self.h,dt,self.distance,
                {0:(self.k_in,None)},{0:(self.omega_in,None)},wall=wall,lf18=self.model=='kOmegaSSTLF18')
            self.omega=omega
            e=.09*k*omega
        self.faces=updated;self.k=k;self.epsilon=e;self.time+=dt
        return {'time_s':self.time,'divergence_rms':float(divergence(updated,self.h).square().mean().sqrt()),
                'k_min':float(k.min()),'epsilon_min':float(e.min())}
