"""Controlled single-phase pilot, NOT a reproduction of paper B.2 or FOWT.
Compare fixed Conv3d PyTorch with Triton, and isolate rotor kernel changes.
"""
import sys,time,json,math,argparse
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windfarm_2m'))
from mac_torch import MAC
from rotor import WeightedRotor

def run(out,h=.1,refine_only=False):
 torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
 torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
 out.mkdir(parents=True,exist_ok=True)
 shape=tuple(round(v/h) for v in (3.2,3.2,9.6));U=2.;dt=.15*h;end=10.;rho=1.225;R=.4;sigma=.2
 z,y,x=torch.meshgrid(*[(torch.arange(n,device=device)+.5)*h for n in shape],indexing='ij')
 xyz=torch.stack((x,y,z),-1);hub=[2.4,1.6,1.6]
 rotor=WeightedRotor(R,sigma,ct=.75)
 fluid=torch.ones(shape,device=device,dtype=torch.bool);inlet=torch.full(shape[:2],U,device=device)
 cases=[('torch_paper',MAC,'paper'),('torch_legacy',MAC,'legacy')]
 if refine_only:cases=cases[:1]
 if device=='cuda' and not refine_only:
  from mac import MAC as TritonMAC
  cases.append(('triton_paper',TritonMAC,'paper'))
 metadata=dict(status='single_phase_pilot_not_paper_validation',device=device,shape_zyx=shape,cell_m=h,domain_xyz_m=[9.6,3.2,3.2],hub_xyz_m=hub,rotor_diameter_m=.8,sigma_m=sigma,ct=.75,ct_prime=4/3,inlet_m_s=U,end_s=end,pressure_rtol=1e-5,explicit_turbulence_model=None,boundaries='fixed inlet, pressure outlet; slip sides/top/bottom',cases={})
 for name,cls,kernel in cases:
  m=cls(fluid,h,inlet);m.vel[0].fill_(U)
  # Sampling at cell centres, force then linearly interpolated to stored east/north/top faces.
  t=0.;step=0;history=[];frames=[];next_save=0.;start=time.perf_counter()
  dummy=torch.zeros_like(xyz);base=rotor(xyz,dummy,h**3,hub,[1,0,0]);weight=base['weight']
  if kernel=='legacy':
   axial=x-hub[0];rad=((y-hub[1])**2+(z-hub[2])**2).sqrt()
   weight=torch.exp(-.5*(axial/sigma)**2)*torch.sigmoid((R-rad)/.05)
  denom=weight.sum()*h**3
  while t<end-1e-9:
   delta=min(dt,end-t)
   m.advect(delta)
   west=torch.cat((inlet[...,None],m.vel[0][...,:-1]),-1)
   ud=float((((m.vel[0]+west)*.5)*weight).sum()*h**3/denom)
   thrust=.5*rho*math.pi*R**2*(4/3)*ud**2*min(1.,t/1.)
   a=-thrust/rho*weight/denom
   face=.5*(a+torch.cat((a[...,1:],a[...,-1:]),-1))
   m.vel[0].add_(face,alpha=delta)
   diag=m.project(rtol=1e-5,maxiter=150)
   t+=delta;step+=1
   if t>=next_save-1e-9 or t>=end-1e-9:
    history.append([t,ud,thrust,diag['divergence_rms']]);frames.append(m.vel[0][shape[0]//2].cpu().numpy().copy());next_save+=.25
   if step%200==0:print(name,step,round(t,3),diag,flush=True)
  if device=='cuda':torch.cuda.synchronize()
  elapsed=time.perf_counter()-start
  np.savez_compressed(out/(name+'.npz'),history=np.array(history),frames=np.array(frames),u=m.vel[0].cpu().numpy())
  metadata['cases'][name]=dict(steps=step,wall_seconds=elapsed,final_disc_speed_m_s=ud,final_thrust_N=thrust,final_divergence_rms=diag['divergence_rms'])
  (out/'comparison.json').write_text(json.dumps(metadata,indent=2));print(name,metadata['cases'][name],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('output/paper_rotor'));p.add_argument('--cell',type=float,default=.1);p.add_argument('--refine-only',action='store_true');args=p.parse_args()
 with torch.inference_mode():run(args.out,args.cell,args.refine_only)
