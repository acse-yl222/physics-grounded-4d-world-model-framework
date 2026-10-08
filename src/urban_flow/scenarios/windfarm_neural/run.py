"""All 23 turbines on a 4 m grid with the pure-PyTorch "Neural Physics" solver.
Pressure Poisson operator = fixed Conv3d stencil; multigrid = pooling/upsampling
(U-Net-shaped V-cycle); no trained weights. Rotor loads use the Davidson et al.
2026 section 2.2 weighted actuator disc (paper_rotor/rotor.py) or, for a
controlled comparison, the legacy smooth kernel with the identical load law.
Not a reproduction of the paper's OpenFOAM model, and no turbulence closure.
"""

# Compatibility for direct source-script execution.
if __name__ == '__main__' and not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from common.runtime import source_path, trial_root
import argparse,json,math,sys,time,traceback
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
here=Path(__file__).resolve().parent
from urban_flow.solvers.mac_torch import MAC
from urban_flow.solvers.rotor import WeightedRotor

def write(path,data):
 t=path.with_suffix('.tmp');t.write_text(json.dumps(data,indent=2,allow_nan=False));t.replace(path)

@torch.inference_mode()
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--kernel',choices=['paper','legacy'],default='paper');ap.add_argument('--seconds',type=float,default=300);ap.add_argument('--save-every',type=float,default=2)
 ap.add_argument('--max-steps',type=int,default=0);ap.add_argument('--geometry',type=Path,default=source_path('legacy_output','windfarm_neural/geometry_4m'));ap.add_argument('--tag',default='')
 ap.add_argument('--sigma',type=float,default=8.);ap.add_argument('--cutoff',type=float,default=2.);ap.add_argument('--edge',type=float,default=4.);ap.add_argument('--open-top',action='store_true')
 a=ap.parse_args()
 torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False;torch.set_num_threads(8)
 name=a.tag or f'np4m_{a.kernel}'+('_opentop' if a.open_top else '');root=Path.cwd();out=trial_root('windfarm',name);web=out/'export'
 out.mkdir(parents=True,exist_ok=True);web.mkdir(parents=True,exist_ok=True);status=out/'status.json';started=time.time();last_time=0.;step=0;dev='cuda'
 try:
  g=json.loads((a.geometry/'metadata.json').read_text());h=float(g['cell_m']);solid=np.load(a.geometry/'solid.npy');ground=np.load(a.geometry/'ground.npy')
  nz,ny,nx=solid.shape;ox,oy,oz=g['origin_xyz_m'];U0=8.;rho=1.225;ct=.75;ramp_s=5.
  write(status,dict(state='initializing',target_seconds=a.seconds,shape_zyx=list(solid.shape),cell_m=h,simulated_seconds=0))
  f=torch.as_tensor(~solid,device=dev);z=(torch.arange(nz,device=dev)+.5)*h;gg=torch.as_tensor(ground,device=dev)
  profile=lambda gr:U0*(1-torch.exp(-(z[:,None,None]-gr[None]).clamp(min=0)/12))
  inlet=profile(gg[:,:1])[...,0]*f[:,:,0]
  m=MAC(f,h,inlet,open_top=a.open_top)
  m.vel[0].copy_(profile(gg)*m.f);m.vel[0][:,:,:-1]*=m.f[:,:,1:]
  rotor=WeightedRotor(1.,a.sigma,ct=ct,cutoff=a.cutoff,rho=rho)
  disks=[]
  for t in g['turbines']:
   hx,hy,hz=t['hub_xyz_m'];R=t['radius_m'];ext=a.cutoff*a.sigma if a.kernel=='paper' else 3*a.sigma
   lo=np.floor((np.array([hx-ext,hy-R-3*a.edge,hz-R-3*a.edge])-[ox,oy,oz])/h).astype(int)-1
   hi=np.ceil((np.array([hx+ext,hy+R+3*a.edge,hz+R+3*a.edge])-[ox,oy,oz])/h).astype(int)+2
   lo=np.maximum(lo,[1,0,0]);hi=np.minimum(hi,[nx-1,ny,nz]);(x0,y0,z0),(x1,y1,z1)=lo,hi
   zz,yy,xx=torch.meshgrid(*[(torch.arange(s,e,device=dev)+.5)*h+o for s,e,o in ((z0,z1,oz),(y0,y1,oy),(x0,x1,ox))],indexing='ij')
   xyz=torch.stack((xx,yy,zz),-1);fluid=m.f[z0:z1,y0:y1,x0:x1].float();vol=h**3*fluid
   if a.kernel=='paper':
    rotor.radius=R;rotor.area=math.pi*R*R;weight=rotor(xyz,torch.zeros_like(xyz),vol,[hx,hy,hz],[1,0,0])['weight']*fluid
   else:
    rad=((yy-hy)**2+(zz-hz)**2).sqrt();weight=torch.exp(-.5*((xx-hx)/a.sigma)**2)*torch.sigmoid((R-rad)/a.edge)*fluid
   # Last x slice carries no force so face interpolation conserves the total.
   weight[...,-1]=0
   if a.kernel=='paper':
    edge_mass=float(weight[:,:,[0,-2]].sum()+weight[:,[0,-1]].sum()+weight[[0,-1]].sum())/float(weight.sum())
    assert edge_mass==0,(t['id'],edge_mass)
   opened=m.opened(0)[z0:z1,y0:y1,x0:x1]
   disks.append(dict(fluid=fluid,id=t['id'],sl=(slice(z0,z1),slice(y0,y1),slice(x0,x1)),lo=(z0,y0,x0),xyz=xyz,vol=vol,weight=weight,opened=opened,hub=[hx,hy,hz],R=R,area=math.pi*R*R,cells=int((weight>0).sum())))
  def centred(sl,lo):
   z0,y0,x0=lo;zs,ys,xs=sl;u,v,w=m.vel
   uc=.5*(u[zs,ys,xs]+u[zs,ys,x0-1:xs.stop-1])
   vc=.5*(v[zs,ys,xs]+(v[zs,y0-1:ys.stop-1,xs] if y0>0 else F.pad(v[zs,:ys.stop-1,xs],(0,0,1,0))))
   wc=.5*(w[zs,ys,xs]+(w[z0-1:zs.stop-1,ys,xs] if z0>0 else F.pad(w[:zs.stop-1,ys,xs],(0,0,0,0,1,0))))
   return torch.stack((uc,vc,wc),-1)
  def rotor_force(t,dt):
   rows=[];ramp=min(t/ramp_s,1.)
   for d in disks:
    vel=centred(d['sl'],d['lo'])
    if a.kernel=='paper':
     rotor.radius=d['R'];rotor.area=d['area'];r=rotor(d['xyz'],vel,d['vol'],d['hub'],[1,0,0])
     # rotor() recomputes the weight; solid cells are already excluded through vol.
     ud=float(r['disc_speed']);T=float(r['thrust'])*ramp;acc=r['acceleration'][...,0]*ramp*d['fluid']
    else:
     W=d['weight']*d['vol'];ud=float((vel[...,0]*W).sum()/W.sum());T=.5*rho*d['area']*(4/3)*ud*ud*ramp;acc=-T*d['weight']/(rho*float(W.sum()))
    face=.5*(acc+F.pad(acc[...,1:],(0,1)))*d['opened']
    applied=float(face.sum())*rho*h**3
    if dt>0:m.vel[0][d['sl']].add_(face,alpha=dt)
    rows.append((ud,T,-applied))
   return rows
  def projection():
   total=0
   for refinement in range(3):
    info=m.project(rtol=1e-4,maxiter=120);total+=info['iterations']
    if info['divergence_rms']<=1e-5:break
    m.p.zero_()
   assert info['divergence_rms']<=1e-5,('True divergence check',info)
   info['total_iterations']=total;info['refinements']=refinement;return info
  config=dict(solver='Neural Physics style pure PyTorch MAC solver (tools/windfarm_2m/mac_torch.py): fixed Conv3d pressure stencil, pooling/upsampling multigrid V-cycle preconditioning CG, no trained weights, no Triton',
   rotor_kernel=a.kernel,rotor_model='Davidson, Barajas & Lara 2026 section 2.2 weighted actuator disc: truncated axial Gaussian, hard radial cut at R, weighted inflow, T=2 rho A a/(1-a) ud^2, Ct=0.75' if a.kernel=='paper' else 'Legacy smooth kernel: untruncated axial Gaussian, logistic radial edge; same load law T=0.5 rho A Ct_prime ud^2, Ct_prime=4/3',
   sigma_m=a.sigma,cutoff_sigma=a.cutoff if a.kernel=='paper' else None,radial_edge_m=None if a.kernel=='paper' else a.edge,cell_m=h,shape_zyx=[nz,ny,nx],target_seconds=a.seconds,inlet='U0=8 m/s, 1-exp(-AGL/12 m) profile, west face',rho=rho,startup_ramp_s=ramp_s,
   advection='First-order upwind; numerically dissipative, no LES or RANS closure',boundaries=('Prescribed west inlet; slip sides; p=0 open top;' if a.open_top else 'Prescribed west inlet; slip side/top;')+' impermeable voxel terrain, towers and nacelles; pressure outlet east',
   geometry='4 m voxels coarsened from the 2 m all-turbine geometry',
   limits=['Rotor module follows the paper; the flow solver is not OpenFOAM and has no turbulence model.','No rotating blades, shaft torque, power, controller or measured weather.','4 m cells; compare with the 2 m Triton run as a different grid and different kernel, not a pure kernel test.','Steady state and engineering accuracy not verified.'],
   references=['https://doi.org/10.1016/j.joes.2026.07.020','https://arxiv.org/abs/2402.17913'])
  write(out/'config.json',config);write(web/'config.json',config);write(web/'geometry.json',g);np.save(web/'ground.npy',ground);np.save(web/'terrain_valid.npy',np.load(a.geometry/'terrain_valid.npy'))
  yy,xx=np.indices((ny,nx),dtype=np.int64);zz=np.clip(np.floor((ground+80)/h).astype(np.int64),0,nz-1);mask=np.asarray(solid[zz,yy,xx],dtype='u1');np.save(web/'mask.npy',mask)
  ii=tuple(torch.as_tensor(v,device=dev) for v in (zz,yy,xx));del yy,xx,zz
  files=[];times=[];rows=[]
  def save(info,dt):
   loads=rotor_force(last_time,0);maxsum=m.maxsum();assert math.isfinite(maxsum) and maxsum<80,('Velocity guard',maxsum)
   iz,iy,ix=ii
   u=.5*(m.vel[0][iz,iy,ix]+torch.where(ix>0,m.vel[0][iz,iy,(ix-1).clamp(min=0)],m.inlet[iz,iy]))
   v=.5*(m.vel[1][iz,iy,ix]+torch.where(iy>0,m.vel[1][iz,(iy-1).clamp(min=0),ix],0))
   w=.5*(m.vel[2][iz,iy,ix]+torch.where(iz>0,m.vel[2][(iz-1).clamp(min=0),iy,ix],0))
   data=torch.stack([u,v,w]).cpu().numpy();data[:,mask!=0]=np.nan
   fn=f'uvw_s{step:07d}.npy';np.save(web/fn,data[None].astype('<f2'))
   row=dict(step=step,time_s=last_time,dt_s=dt,max_component_sum_m_s=maxsum,cfl_bound=3*maxsum*dt/h,pressure=info,gpu_peak_gib=torch.cuda.max_memory_allocated()/2**30,elapsed_s=time.time()-started,
    disk_velocity_m_s=[l[0] for l in loads],thrust_N=[l[1] for l in loads],applied_fluid_force_N=[l[2] for l in loads])
   files.append(fn);times.append(last_time);rows.append(row)
   man=dict(config,files=files,times=times,metrics=rows,complete=last_time>=a.seconds-1e-8,simulated_seconds=last_time,completed_steps=step,slice_agl_m=80)
   write(web/'manifest.json',man);write(web/'status.json',st:=dict(state='complete' if man['complete'] else 'running',simulated_seconds=last_time,completed_steps=step,target_seconds=a.seconds,last=row));write(status,st)
   print(json.dumps({k:row[k] for k in ('step','time_s','dt_s','max_component_sum_m_s','gpu_peak_gib','elapsed_s')}|dict(iters=info.get('total_iterations'),div=info['divergence_rms'])),flush=True)
  print('ALLOCATED',torch.cuda.memory_allocated()/2**30,'disk cells',[d['cells'] for d in disks],flush=True)
  info=projection();m.p.zero_();save(info,0.)
  next_save=a.save_every
  while last_time<a.seconds-1e-8:
   speed=m.maxsum();assert speed<80,('Velocity guard',speed)
   dt=min(.1,.2*h/max(speed,1.),a.seconds-last_time,next_save-last_time)
   if dt<1e-7:next_save+=a.save_every;continue
   m.advect(dt);rotor_force(last_time+dt/2,dt);info=projection();last_time+=dt;step+=1
   if last_time>=next_save-1e-8 or last_time>=a.seconds-1e-8:save(info,dt);next_save+=a.save_every
   if a.max_steps and step>=a.max_steps:save(info,dt);break
  # Final cell-centred u for analysis (float16, NaN in solids).
  u=.5*(m.vel[0]+torch.cat((m.inlet[...,None],m.vel[0][...,:-1]),-1));u=torch.where(m.f,u,torch.nan)
  np.save(out/'u_final.npy',u.half().cpu().numpy())
  if last_time<a.seconds-1e-8:write(status,dict(state='step_limit',simulated_seconds=last_time,completed_steps=step,target_seconds=a.seconds))
  print('FINISHED',step,last_time,time.time()-started,flush=True)
 except Exception as e:
  write(status,dict(state='failed',simulated_seconds=last_time,completed_steps=step,target_seconds=a.seconds,error=repr(e)));traceback.print_exc();raise
if __name__=='__main__':main()
