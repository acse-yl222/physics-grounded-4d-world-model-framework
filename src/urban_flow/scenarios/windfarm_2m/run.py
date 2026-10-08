"""All 23 turbines, actual isotropic 2 m grid; independent MAC numerical solver.
A separate experiment, NOT an equivalent AI4Urban implementation or trained inference.
"""

# Compatibility for direct source-script execution.
if __name__ == '__main__' and not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from common.runtime import source_path, trial_root
import argparse,json,math,time,traceback
from pathlib import Path
import numpy as np
import torch
import h5py

def write(path,data):
 t=path.with_suffix('.tmp');t.write_text(json.dumps(data,indent=2,allow_nan=False));t.replace(path)

@torch.inference_mode()
def main():
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=300);p.add_argument('--max-steps',type=int,default=0);p.add_argument('--resume',action='store_true');p.add_argument('--save-every',type=float,default=2);a=p.parse_args()
 from urban_flow.solvers.mac_triton import MAC
 root=Path.cwd();geom=source_path('legacy_output','region_crop_2m/geometry');out=trial_root('windfarm','mac_2m');web=out/'export';out.mkdir(parents=True,exist_ok=True);web.mkdir(parents=True,exist_ok=True)
 status=out/'status.json';started=time.time();last_time=0.;step=0
 try:
  torch.set_num_threads(8);g=json.loads((geom/'metadata.json').read_text());h=2.;solid=np.load(geom/'solid.npy',mmap_mode='r');ground=np.load(geom/'ground.npy');nz,ny,nx=solid.shape;ox,oy,oz=g['origin_xyz_m'];U0=8.;rho=1.225;ct=4/3
  write(status,dict(state='initializing',target_seconds=a.seconds,shape_zyx=list(solid.shape),cell_m=2,simulated_seconds=0))
  f=torch.as_tensor(~solid,device='cuda');z=(torch.arange(nz,device='cuda')+.5)*h
  ground_gpu=torch.as_tensor(ground,device='cuda');inlet=U0*(1-torch.exp(-(z[:,None]-ground_gpu[None,:,0]).clamp(min=0)/12));inlet*=f[:,:,0]
  m=MAC(f,h,inlet);del f
  # u is stored on the right x face of each cell. Keep all closed faces zero.
  for k in range(nz):
   m.vel[0][k]=U0*(1-torch.exp(-(z[k]-ground_gpu).clamp(min=0)/12))*m.f[k]
   m.vel[0][k,:,:-1]*=m.f[k,:,1:]
  del ground_gpu
  disks=[]
  for t in g['turbines']:
   hx,hy,hz=t['hub_xyz_m'];r=t['radius_m'];sigma=8.;edge=4.
   lo=np.maximum(np.floor((np.array([hx-24,hy-r-12,hz-r-12])-[ox,oy,oz])/h).astype(int),0)
   hi=np.minimum(np.ceil((np.array([hx+24,hy+r+12,hz+r+12])-[ox,oy,oz])/h).astype(int),[nx-1,ny,nz]);x0,y0,z0=lo;x1,y1,z1=hi;sl=(slice(z0,z1),slice(y0,y1),slice(x0,x1))
   zz,yy,xx=torch.meshgrid((torch.arange(z0,z1,device='cuda')+.5)*h+oz,(torch.arange(y0,y1,device='cuda')+.5)*h+oy,(torch.arange(x0,x1,device='cuda')+1)*h+ox,indexing='ij')
   kernel=torch.exp(-.5*((xx-hx)/sigma)**2)*torch.sigmoid((r-torch.sqrt((yy-hy)**2+(zz-hz)**2))/edge)
   opened=m.f[sl]&m.f[z0:z1,y0:y1,x0+1:x1+1];kernel*=opened;kernel/=kernel.sum()*h**3
   assert abs(float(kernel.sum()*h**3)-1)<1e-5
   disks.append((sl,kernel,math.pi*r*r))
  del zz,yy,xx,opened,kernel
  config=dict(solver='Independent float32 MAC upwind/projection, fused Triton kernels; NOT original AI4Urban',cell_m=2,shape_zyx=list(solid.shape),target_seconds=a.seconds,
    advection='First-order upwind; numerically dissipative, no LES closure',pressure='Globally coupled MG-preconditioned CG on staggered faces; solid no-penetration, outlet p=0; independent true-divergence check',
    boundaries='Prescribed west inlet profile; impermeable slip side/top/bottom and voxel surfaces; pressure outlet on east face',force='All 23 stationary axial-force disks yawed +x, Ct_prime=4/3, rho=1.225, 5 s ramp; same 8 m axial / 4 m radial force smoothing as 4 m experiment',
    limits=['New numerical scheme; do not treat differences from 4 m AI4Urban as a pure grid-convergence comparison.','No rotating blades, torque, electrical power, measured weather, or turbulence closure.','First-order upwind and stair-step boundaries are approximate; finer grid alone does not establish engineering accuracy.','Steady-state and engineering accuracy not verified.'],references=['https://www.cs.ubc.ca/~rbridson/fluidsimulation/','https://lesgo.me.jhu.edu/actuator-disk.html'])
  write(out/'config.json',config);write(web/'config.json',config);write(web/'geometry.json',g);np.save(web/'ground.npy',ground);np.save(web/'terrain_valid.npy',np.load(geom/'terrain_valid.npy'))
  yy,xx=np.indices((ny,nx),dtype=np.int32);zz=np.clip(np.floor((ground+80)/h).astype(np.int32),0,nz-1);mask=np.asarray(solid[zz,yy,xx],dtype='u1');np.save(web/'mask.npy',mask)
  ii=tuple(torch.as_tensor(v.astype(np.int64),device='cuda') for v in (zz,yy,xx));del yy,xx,zz,solid
  files=[];times=[];rows=[];checkpoint=out/'checkpoint.h5'
  if a.resume:
   with h5py.File(checkpoint,'r') as cp:
    step=int(cp.attrs['step']);last_time=float(cp.attrs['time_s'])
    for key,v in zip(['u','v','w','phi'],[*m.vel,m.p]):
     for k in range(0,nz,8):v[k:k+8].copy_(torch.as_tensor(cp[key][k:k+8],device='cuda'))
   old=json.loads((web/'manifest.json').read_text());keep=[i for i,t in enumerate(old['times']) if t<=last_time+1e-8];files=[old['files'][i] for i in keep];times=[old['times'][i] for i in keep];rows=old['metrics'][:len(keep)]
  def projection():
   all_iters=0
   for refinement in range(3):
    info=m.project(rtol=1e-4,maxiter=120);all_iters+=info['iterations']
    if info['divergence_rms']<=1e-5:break
    m.p.zero_()
   assert info['divergence_rms']<=1e-5,('True divergence check',info)
   info['total_iterations']=all_iters;info['refinements']=refinement;return info
  def disk_force(t,dt):
   vel=[];thrust=[]
   for sl,k,area in disks:
    u=m.vel[0][sl];ud=float((u*k).sum()*h**3);T=.5*rho*area*ct*ud*abs(ud)*min(t/5,1);u.add_(k,alpha=-dt*T/rho);vel.append(ud);thrust.append(T)
   return vel,thrust
  def save(info,dt):
   ud,T=disk_force(last_time,0);maxsum=m.maxsum();assert math.isfinite(maxsum) and maxsum<80,('Velocity guard',maxsum)
   iz,iy,ix=ii
   # Interpolate face velocities to cell centers before terrain-following sampling.
   u=.5*(m.vel[0][iz,iy,ix]+torch.where(ix>0,m.vel[0][iz,iy,torch.clamp(ix-1,min=0)],m.inlet[iz,iy]))
   v=.5*(m.vel[1][iz,iy,ix]+torch.where(iy>0,m.vel[1][iz,torch.clamp(iy-1,min=0),ix],0))
   w=.5*(m.vel[2][iz,iy,ix]+torch.where(iz>0,m.vel[2][torch.clamp(iz-1,min=0),iy,ix],0))
   data=torch.stack([u,v,w]).cpu().numpy();data[:,mask!=0]=np.nan;assert np.isfinite(data[:,mask==0]).all()
   name=f'uvw_s{step:07d}.npy';np.save(web/name,data[None].astype('<f2'))
   row=dict(step=step,time_s=last_time,dt_s=dt,max_component_sum_m_s=maxsum,cfl_bound=3*maxsum*dt/h,pressure=info,gpu_peak_gib=torch.cuda.max_memory_allocated()/2**30,elapsed_s=time.time()-started,disk_velocity_m_s=ud,thrust_N=T)
   if times and abs(times[-1]-last_time)<1e-8:files[-1]=name;rows[-1]=row
   else:files.append(name);times.append(last_time);rows.append(row)
   manifest=dict(config,files=files,times=times,metrics=rows,complete=last_time>=a.seconds-1e-8,simulated_seconds=last_time,completed_steps=step,slice_agl_m=80)
   write(web/'manifest.json',manifest);write(status,dict(state='complete' if manifest['complete'] else 'running',**{k:manifest[k] for k in ['simulated_seconds','completed_steps','target_seconds']},last=row))
   print(json.dumps(row),flush=True)
  def save_checkpoint():
   tmp=out/'checkpoint.tmp.h5'
   with h5py.File(tmp,'w') as cp:
    cp.attrs['step']=step;cp.attrs['time_s']=last_time
    for key,v in zip(['u','v','w','phi'],[*m.vel,m.p]):
     ds=cp.create_dataset(key,shape=m.shape,dtype='f4',chunks=(8,128,256))
     for k in range(0,nz,8):ds[k:k+8]=v[k:k+8].cpu().numpy()
   tmp.replace(checkpoint)
  print('ALLOCATED',torch.cuda.memory_allocated()/2**30,flush=True)
  info=projection();m.p.zero_();save(info,0.)
  next_save=last_time+a.save_every;next_checkpoint=last_time+30
  while last_time<a.seconds-1e-8:
   speed=m.maxsum();assert speed<80,('Velocity guard',speed)
   dt=min(.1,.2*h/max(speed,1.),a.seconds-last_time,next_save-last_time)
   if dt<1e-7:next_save+=a.save_every;continue
   m.advect(dt);disk_force(last_time+dt/2,dt);info=projection();last_time+=dt;step+=1
   if last_time>=next_save-1e-8 or last_time>=a.seconds-1e-8:save(info,dt);next_save+=a.save_every
   if last_time>=next_checkpoint:save_checkpoint();next_checkpoint+=30
   if a.max_steps and step>=a.max_steps:save(info,dt);break
  save_checkpoint()
  if last_time<a.seconds-1e-8:write(status,dict(state='step_limit',simulated_seconds=last_time,completed_steps=step,target_seconds=a.seconds))
  print('FINISHED',step,last_time,flush=True)
 except Exception as e:
  write(status,dict(state='failed',simulated_seconds=last_time,completed_steps=step,target_seconds=a.seconds,error=repr(e)));traceback.print_exc();raise
if __name__=='__main__':main()
