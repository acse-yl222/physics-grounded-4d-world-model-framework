"""Quasi-steady rotating actuator lines with adjoint MAC interpolation/spreading.

Prescribed angular speed; not blade-surface CFD or rotor/controller dynamics.
Moment-corrected Gaussian kernels preserve force, first moment and discrete work.
"""
from pathlib import Path
import math
import numpy as np
import torch

AIRFOILS=('Cylinder1','Cylinder2','DU40_A17','DU35_A17','DU30_A17','DU25_A17','DU21_A17','NACA64_A17')


def reference_blade(folder, elements=16):
    folder=Path(folder)
    rows=[]
    for line in (folder/'blade.dat').read_text().splitlines()[6:]:
        try:values=list(map(float,line.split()))
        except ValueError:continue
        if len(values)>=7:rows.append(values[:7])
        if len(rows)==19:break
    a=np.asarray(rows)
    if a.shape!=(19,7) or not np.all(np.diff(a[:,0])>0):raise ValueError('Unexpected reference blade')
    # NREL rotor radius 63 m and hub radius 1.5 m. Straighten sweep/prebend.
    edges=np.linspace(1.5,63.,elements+1);r=.5*(edges[:-1]+edges[1:]);span=r-1.5
    foil=np.abs(span[:,None]-a[None,:,0]).argmin(1)
    blade=dict(radius_fraction=r/63.,dr_fraction=np.diff(edges)/63.,chord_fraction=np.interp(span,a[:,0],a[:,5])/63.,twist_rad=np.deg2rad(np.interp(span,a[:,0],a[:,4])),airfoil_id=a[foil,6].astype(int)-1)
    polars=[]
    for name in AIRFOILS:
        lines=(folder/(name+'.dat')).read_text().splitlines();start=next(i for i,s in enumerate(lines) if 'NumAlf' in s);n=int(lines[start].split()[0]);data=[]
        for line in lines[start+1:]:
            try:v=list(map(float,line.split()))
            except ValueError:continue
            if len(v)>=4:data.append(v[:4])
            if len(data)==n:break
        tab=np.asarray(data)
        if tab.shape!=(n,4) or not np.all(np.diff(tab[:,0])>0) or tab[0,0]>-180 or tab[-1,0]<180:raise ValueError('Incomplete polar '+name)
        # Common angular grid, preserving piecewise-linear table interpolation.
        polars.append(tab)
    return blade,polars


def section_force(relative, axis, tangent, chord_dr, twist, cl, cd, rho):
    wn=(relative*axis).sum(-1);wt=(relative*tangent).sum(-1)
    speed=torch.sqrt(wn.square()+wt.square()).clamp_min(1e-12)
    lift=(-wt[:,None]*axis+wn[:,None]*tangent)/speed[:,None]
    drag=(wn[:,None]*axis+wt[:,None]*tangent)/speed[:,None]
    return (.5*rho*speed.square()*chord_dr)[:,None]*(cl[:,None]*lift+cd[:,None]*drag)


class FaceKernel:
    """One MAC component. Signed affine correction gives exact first moments."""
    def __init__(self,points,origin,h,shape,opened,component,sigma,cutoff=3.):
        device=points.device;dtype=points.dtype
        shift=torch.full((3,),.5,device=device,dtype=dtype);shift[component]=1.
        base=torch.floor((points-origin)/h-shift).long();extent=math.ceil(cutoff*sigma/h)+1
        q=torch.arange(-extent,extent+1,device=device)
        offsets=torch.stack(torch.meshgrid(q,q,q,indexing='ij'),-1).reshape(-1,3)
        ijk=base[:,None,:]+offsets[None,:,:];limits=torch.tensor(shape[::-1],device=device)
        inside=((ijk>=0)&(ijk<limits)).all(-1);safe=ijk.clamp_min(0);safe=torch.minimum(safe,limits-1)
        self.indices=(safe[...,2]*shape[1]+safe[...,1])*shape[2]+safe[...,0]
        delta=(origin+(ijk.to(dtype)+shift)*h-points[:,None,:])/h
        k=torch.exp(-.5*delta.square().sum(-1)/(sigma/h)**2)*inside*opened.reshape(-1)[self.indices]
        k*=delta.square().sum(-1)<=(cutoff*sigma/h)**2
        basis=torch.cat((torch.ones_like(delta[...,:1]),delta),-1)
        gram=torch.einsum('pk,pki,pkj->pij',k,basis,basis)
        target=torch.zeros((len(points),4,1),device=device,dtype=dtype);target[:,0]=1
        coeff=torch.linalg.solve(gram,target).squeeze(-1)
        self.weights=k*(basis*coeff[:,None,:]).sum(-1)
        self.moment=(self.weights[...,None]*basis).sum(1)
        if not torch.isfinite(self.weights).all() or (self.moment-target.squeeze(-1)).abs().max()>2e-5:raise RuntimeError('ALM kernel cannot reproduce force/first moment')
    def sample(self,field):return (field.reshape(-1)[self.indices]*self.weights).sum(-1)
    def spread(self,point_force,shape):
        result=torch.zeros(math.prod(shape),device=point_force.device,dtype=point_force.dtype)
        result.scatter_add_(0,self.indices.reshape(-1),(point_force[:,None]*self.weights).reshape(-1))
        return result.reshape(shape)


class RotatingFarm:
    def __init__(self,solver,geometry,config,blade_folder):
        self.m=solver;self.g=geometry;self.c=config;self.count=len(geometry['turbines']);self.elements=config['alm_elements'];self.per=3*self.elements
        device=solver.k.device;dtype=solver.k.dtype
        def tensor(x):return torch.as_tensor(x,device=device,dtype=dtype)
        self.tensor=tensor;blade,polars=reference_blade(blade_folder,self.elements)
        self.polars=[tensor(x) for x in polars];self.hubs=tensor([t['hub_xyz_m'] for t in geometry['turbines']]);self.radii=tensor([t['radius_m'] for t in geometry['turbines']]);self.axes=tensor([t['normal_xyz'] for t in geometry['turbines']]);self.axes/=torch.linalg.vector_norm(self.axes,dim=-1,keepdim=True)
        up=tensor([0,0,1]).expand_as(self.axes);self.e1=up-(up*self.axes).sum(-1,keepdim=True)*self.axes;self.e1/=torch.linalg.vector_norm(self.e1,dim=-1,keepdim=True);self.e2=torch.linalg.cross(self.axes,self.e1)
        self.omega=config['alm_tsr']*config['inlet_m_s']/self.radii
        self.radial=self.radii[:,None,None]*tensor(blade['radius_fraction'])[None,None,:]
        self.area=self.radii[:,None,None].square()*tensor(blade['chord_fraction']*blade['dr_fraction'])[None,None,:]
        self.twist=tensor(blade['twist_rad'])[None,None,:]+math.radians(config['alm_pitch_deg'])
        self.foil=torch.as_tensor(np.tile(blade['airfoil_id'],self.count*3),device=device)
        self.origin=tensor(geometry['origin_xyz_m']);self.sigma=config['alm_sigma_cells']*solver.h
        self.last_state=None
    def stable_dt(self):return min(.1/float(self.omega.max()),.25*self.m.h/float((self.omega*self.radii).max()))
    def loads(self,ramp=1.,time_s=None):
        m=self.m;t=m.time if time_s is None else time_s
        phase=self.omega[:,None,None]*t+self.tensor([0,2*math.pi/3,4*math.pi/3])[None,:,None]
        radial_unit=torch.cos(phase)[...,None]*self.e1[:,None,None,:]+torch.sin(phase)[...,None]*self.e2[:,None,None,:]
        tangent=torch.linalg.cross(self.axes[:,None,None,:],radial_unit,dim=-1)
        lever=(self.radial[...,None]*radial_unit).expand(-1,-1,self.elements,-1).reshape(-1,3)
        points=(self.hubs[:,None,None,:]+self.radial[...,None]*radial_unit).reshape(-1,3)
        tangent=tangent.expand(-1,-1,self.elements,-1).reshape(-1,3);axis=self.axes[:,None,None,:].expand(-1,3,self.elements,-1).reshape(-1,3)
        kernels=[FaceKernel(points,self.origin,m.h,m.shape,m.mac.opened(c),c,self.sigma) for c in range(3)]
        velocity=torch.stack([k.sample(q) for k,q in zip(kernels,m.mac.vel)],-1)
        moving=(self.omega[:,None,None]*self.radial).expand(-1,3,-1).reshape(-1,1)*tangent
        relative=velocity-moving;alpha=torch.atan2((relative*axis).sum(-1),-(relative*tangent).sum(-1))-self.twist.expand(self.count,3,-1).reshape(-1)
        degrees=torch.remainder(torch.rad2deg(alpha)+180,360)-180;cl=torch.empty_like(degrees);cd=torch.empty_like(degrees)
        for i,tab in enumerate(self.polars):
            mask=self.foil==i;x=degrees[mask];j=torch.searchsorted(tab[:,0].contiguous(),x).clamp(1,len(tab)-1);f=(x-tab[j-1,0])/(tab[j,0]-tab[j-1,0]);values=tab[j-1,1:3]+f[:,None]*(tab[j,1:3]-tab[j-1,1:3]);cl[mask]=values[:,0];cd[mask]=values[:,1]
        force=section_force(relative,axis,tangent,self.area.expand(-1,3,-1).reshape(-1),self.twist,cl,cd,self.c['rho_kg_m3'])*ramp
        if not torch.isfinite(force).all():raise RuntimeError('Nonfinite blade force')
        accelerations=[k.spread(-force[:,c]/(self.c['rho_kg_m3']*m.h**3),m.shape) for c,k in enumerate(kernels)]
        total=force.reshape(self.count,self.per,3).sum(1);torque=torch.linalg.cross(lever,force).reshape(self.count,self.per,3).sum(1);axial=(total*self.axes).sum(-1);q=(torque*self.axes).sum(-1)
        speed=(velocity*axis).sum(-1).reshape(self.count,self.per).mean(-1)
        moments=torch.stack([k.moment for k in kernels],1);force_error=((moments[:,:,0]-1)*force).reshape(self.count,self.per,3).sum(1).abs().amax(-1)
        self.last_points=points;self.last_force=force;self.last_velocity=velocity
        self.last_state=dict(phase_rad=(self.omega*t).tolist(),omega_rad_s=self.omega.tolist())
        rows=[dict(id=rotor['id'],disc_speed_m_s=float(speed[i]),thrust_N=float(axial[i]),shaft_torque_Nm=float(q[i]),aerodynamic_power_W=float(q[i]*self.omega[i]),omega_rad_s=float(self.omega[i]),phase_rad=float(self.omega[i]*t),force_error_N=float(force_error[i])) for i,rotor in enumerate(self.g['turbines'])]
        return accelerations,rows

    def grid_audit(self,acc):
        m=self.m;factor=self.c['rho_kg_m3']*m.h**3
        expected=-self.last_force.double().sum(0);expected_moment=-torch.linalg.cross(self.last_points.double(),self.last_force.double()).sum(0)
        actual=torch.stack([a.double().sum()*factor for a in acc]);moment=torch.zeros_like(actual);work=0.
        for c,a in enumerate(acc):
            f=a.double()*factor;work+=(f*m.mac.vel[c]).sum()
            for d in range(3):
                if c==d:continue
                dim=[1,1,1];dim[2-d]=m.shape[2-d]
                x=self.origin[d].double()+(torch.arange(m.shape[2-d],device=a.device,dtype=torch.float64)+.5)*m.h
                # d != c, so transverse face coordinate is the cell centre.
                e=torch.zeros(3,device=a.device,dtype=torch.float64);e[d]=1;ec=torch.zeros_like(e);ec[c]=1
                moment+=torch.linalg.cross(e,ec)*(f*x.reshape(dim)).sum()
        expected_work=-(self.last_force.double()*self.last_velocity.double()).sum()
        force_scale=self.last_force.double().norm(dim=-1).sum().clamp_min(1.)
        moment_scale=(self.last_points.double().norm(dim=-1)*self.last_force.double().norm(dim=-1)).sum().clamp_min(1.)
        result=dict(relative_force_error=float((actual-expected).norm()/force_scale),relative_global_moment_error=float((moment-expected_moment).norm()/moment_scale),relative_work_error=float(abs(work-expected_work)/max(abs(float(expected_work)),1.)),fluid_force_N=actual.tolist(),fluid_moment_about_origin_Nm=moment.tolist(),fluid_force_work_W=float(work),point_force_work_W=float(expected_work))
        if max(result[k] for k in ('relative_force_error','relative_global_moment_error','relative_work_error'))>1e-5:raise RuntimeError(('ALM conservation failure',result))
        return result
