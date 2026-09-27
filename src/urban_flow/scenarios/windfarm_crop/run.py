"""All-turbine 4 m terrain crop: paired actuator-on/off AI4Urban trial."""
from common.runtime import source_path, trial_root
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import argparse,json,math,sys,time
from pathlib import Path
import numpy as np
import torch
import h5py
sys.path.insert(0,str((repo_root() / 'src/urban_flow/scenarios/region')))
from run_ai4urban import build_model,allocate,advance,write_json

@torch.inference_mode()
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',choices=['control','actuator'],required=True);p.add_argument('--steps',type=int,default=400);a=p.parse_args()
 torch.set_num_threads(8);torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
 root=Path.cwd();geom=source_path('legacy_output','region_crop/geometry');web=trial_root('windfarm','crop');out=web/a.case;out.mkdir(parents=True,exist_ok=True)
 meta=json.loads((geom/'metadata.json').read_text());solid=np.load(geom/'solid.npy');ground=np.load(geom/'ground.npy');valid_terrain=np.load(geom/'terrain_valid.npy')
 nz,ny,nx=solid.shape;cell=4.;dt=.025;U=8.;ct=4/3 if a.case=='actuator' else 0.;rho=1.225;ox,oy,oz=meta['origin_xyz_m'];steps=a.steps
 config=dict(case=a.case,shape_zyx=list(solid.shape),cell_m=cell,dt_s=dt,steps=steps,U0_m_s=U,Ct_prime=ct,rho=rho,mg_iterations=10,gradient_gain=[-1,1,1],
  initial_condition='Air: u=8*(1-exp(-height_above_terrain/12)); v=w=p=0. Solids zero.',
  boundary='Prescribed west profile; east zero-gradient velocities and p=0; reference side/top/bottom conditions. Terrain mask applied at x faces.',
  force='Normalized smoothed axial disk drag, physical force split before/after PDE update; 5 s ramp; assumed yaw +x; sigma_x=8 m, radial edge=4 m.',
  limits=meta['assumptions']+['Short transient, no measured-weather or engineering validation.','Original AI4Urban gradients rescaled to unit gain in this isolated crop only.','No rotor spin, torque, turbulence closure or electrical power.','No steady-state claim; outlet and pressure-projection error require further study.'])
 write_json(out/'config.json',config)
 model,ns=build_model(solid,cell,torch.device('cuda'),dt=dt,ub=-U)
 for op in [model.xadv,model.yadv,model.zadv]:op.weight.mul_(2)
 state,pads,k1=allocate(solid.shape,'cuda')
 solid_gpu=torch.as_tensor(solid,device='cuda');ground_gpu=torch.as_tensor(ground,device='cuda')
 z=(torch.arange(nz,device='cuda')+.5)*cell
 for iz in range(nz):state[0][0,0,iz]=-U*(1-torch.exp(-(z[iz]-ground_gpu).clamp(min=0)/12))*(~solid_gpu[iz])
 inlet=state[0][0,0,:,:,0].clone();old_u=model.boundary_condition_u;old_v=model.boundary_condition_v;old_w=model.boundary_condition_w
 def bu(u,pad):
  old_u(u,pad);pad[0,0,1:-1,1:-1,0]=inlet;pad[0,0,1:-1,1:-1,-1]=u[0,0,:,:,-1]*(~solid_gpu[:,:,-1]);return pad
 def bv(v,pad):
  old_v(v,pad);pad[0,0,1:-1,1:-1,-1]=v[0,0,:,:,-1]*(~solid_gpu[:,:,-1]);return pad
 def bw(w,pad):
  old_w(w,pad);pad[0,0,1:-1,1:-1,-1]=w[0,0,:,:,-1]*(~solid_gpu[:,:,-1]);return pad
 model.boundary_condition_u=bu;model.boundary_condition_v=bv;model.boundary_condition_w=bw
 disks=[];hub_agl=[]
 for t in meta['turbines']:
  hx,hy,hz=t['hub_xyz_m'];r=t['radius_m'];sigma=8.;edge=4.
  low=np.floor((np.array([hx-3*sigma,hy-r-3*edge,hz-r-3*edge])-[ox,oy,oz])/cell).astype(int)
  high=np.ceil((np.array([hx+3*sigma,hy+r+3*edge,hz+r+3*edge])-[ox,oy,oz])/cell).astype(int)
  x0,y0,z0=np.maximum(low,0);x1,y1,z1=np.minimum(high,[nx,ny,nz]);sl=(slice(z0,z1),slice(y0,y1),slice(x0,x1))
  zz,yy,xx=torch.meshgrid(*[torch.arange(lo,hi,device='cuda')*cell+cell/2+origin for lo,hi,origin in [(z0,z1,oz),(y0,y1,oy),(x0,x1,ox)]],indexing='ij')
  kernel=torch.exp(-.5*((xx-hx)/sigma)**2)*torch.sigmoid((r-torch.sqrt((yy-hy)**2+(zz-hz)**2))/edge)
  total=float(kernel.sum());kernel*=~solid_gpu[sl];airfrac=float(kernel.sum())/total;assert airfrac>.75,(t['id'],airfrac)
  kernel/=kernel.sum()*cell**3;assert abs(float(kernel.sum()*cell**3)-1)<1e-5
  disks.append((t['id'],sl,kernel,math.pi*r*r));t['force_kernel_air_fraction']=airfrac
  ix=int((hx-ox)/cell);iy=int((hy-oy)/cell);t['hub_agl_m']=hz-float(ground[iy,ix]);hub_agl.append(t['hub_agl_m'])
 del xx,yy,zz,ground_gpu
 meta['hub_agl_range_m']=[min(hub_agl),max(hub_agl)]
 agl=float(round(np.median(hub_agl)/cell)*cell);meta['slice_agl_m']=agl
 yy,xx=np.indices((ny,nx));iz=np.floor((ground+agl-oz)/cell).astype(int);inside=(iz>=0)&(iz<nz);iz=np.clip(iz,0,nz-1)
 mask=np.where(~inside,2,np.where(solid[iz,yy,xx],1,0)).astype('u1')
 indices=tuple(torch.as_tensor(v,device='cuda') for v in (iz,yy,xx));np.save(web/'slice_mask.npy',mask);np.save(web/'ground.npy',ground);np.save(web/'terrain_valid.npy',valid_terrain);write_json(web/'geometry.json',meta)
 times=[];files=[];metrics=[];started=time.time()
 def force(t,h):
  udlist=[];thrusts=[]
  for bid,sl,kernel,area in disks:
   patch=state[0][0,0][sl];ud=float((-patch*kernel).sum()*cell**3)
   thrust=.5*rho*area*ct*ud*abs(ud)*min(t/5,1);patch.add_(h*thrust/rho*kernel)
   udlist.append(ud);thrusts.append(thrust)
  return udlist,thrusts
 def save(step,ud,thrust,pe):
  assert all(torch.isfinite(s).all() for s in state),'Nonfinite state'
  u,v,w,p=state;cfl=float((u.abs()+v.abs()+w.abs()).max())*dt/cell;assert cfl<.8,('CFL',cfl)
  div=model.xadv(bu(u,pads[0]))+model.yadv(bv(v,pads[1]))+model.zadv(bw(w,pads[2]))
  air=~solid_gpu
  row=dict(step=step,time_s=step*dt,cfl=cfl,pressure_correction=pe,air_divergence_rms_s_inv=float(div[0,0][air].square().mean().sqrt()),max_speed_m_s=float(torch.sqrt(u.square()+v.square()+w.square()).max()),gpu_peak_gib=torch.cuda.max_memory_allocated()/2**30,elapsed_s=time.time()-started,disk_velocity_m_s=ud,thrust_N=thrust)
  metrics.append(row);write_json(out/'metrics.json',metrics);print(json.dumps({k:v for k,v in row.items() if not isinstance(v,list)}),flush=True)
  data=np.stack([s[0,0][indices].cpu().numpy()*(-1 if i==0 else 1) for i,s in enumerate(state[:3])]);data[:,mask!=0]=np.nan
  name=f'uvw_s{step:06d}.npy';np.save(out/name,data[None].astype('<f4'));files.append(a.case+'/'+name);times.append(step*dt)
  result=dict(config,files=files,times=times,metrics=metrics,complete=step==steps,completed_steps=step,slice_agl_m=agl)
  write_json(out/'result.json',result)
 ud,thrust=force(0,0);save(0,ud,thrust,0.)
 for step in range(1,steps+1):
  force((step-.5)*dt,dt/2);state,corr,residual=advance(model,state,pads,k1,dt,10)
  pe=float(corr.abs().max());assert math.isfinite(pe) and pe<80000,'Pressure divergence'
  del corr,residual
  ud,thrust=force((step-.5)*dt,dt/2)
  if step%20==0 or step==steps:save(step,ud,thrust,pe)
 print('COMPLETE',a.case,flush=True)
if __name__=='__main__':main()
