import sys,json,math
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windfarm_2m'))
from mac_torch import MAC
from rotor import WeightedRotor

def main():
 torch.set_num_threads(4);torch.manual_seed(17)
 torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
 device='cuda' if torch.cuda.is_available() else 'cpu';shape=(8,16,32)
 f=torch.ones(shape,dtype=torch.bool,device=device);inlet=torch.full(shape[:2],8.,device=device)
 m=MAC(f,1.,inlet);m.vel[0].fill_(8);m.advect(.02);d=m.project()
 assert max(float((q-(8 if c==0 else 0)).abs().max()) for c,q in enumerate(m.vel))==0
 f[:2]=False;f[2:5,5:9,10:14]=False
 m=MAC(f,1.,inlet*0);m.vel=[torch.randn(shape,device=device)*.1*m.opened(c) for c in range(3)]
 initial=[q.clone() for q in m.vel];d=m.project(rtol=1e-7,maxiter=200);assert d['divergence_rms']<2e-6,d
 errors={}
 if device=='cuda':
  from mac import MAC as TritonMAC
  t=TritonMAC(f,1.,inlet*0);t.vel=[q.clone() for q in initial];t.project(rtol=1e-7,maxiter=200)
  errors['projection_max_abs']=max(float((a-b).abs().max()) for a,b in zip(t.vel,m.vel))
  # Test transport separately with exactly identical input fields.
  t.vel=[q.clone() for q in initial];m.vel=[q.clone() for q in initial];t.advect(.03);m.advect(.03)
  errors['advection_max_abs']=max(float((a-b).abs().max()) for a,b in zip(t.vel,m.vel))
  assert errors['projection_max_abs']<2e-5 and errors['advection_max_abs']<1e-6,errors
 h=.05;v=torch.arange(-1,1,h,device=device,dtype=torch.float64)+h/2
 z,y,x=torch.meshgrid(v,v,v,indexing='ij');xyz=torch.stack((x,y,z),-1);u=torch.zeros_like(xyz);u[...,0]=8
 r=WeightedRotor(.4,.1);o=r(xyz,u,h**3,[0,0,.2],[1,0,0],com=[0,0,0])
 conservation=float((o['acceleration'].sum((0,1,2))*r.rho*h**3+o['body_force']).abs().max());assert conservation<1e-10
 moved=r(xyz,u,h**3,[0,0,.2],[1,0,0],hub_velocity=[2,0,0])
 assert abs(float(moved['thrust']/o['thrust'])-.5625)<1e-10
 old=.5*r.rho*r.area*(4/3)*8**2
 assert abs(float(o['thrust'])-old)<1e-10
 result=dict(device=device,passed=True,projection=d,backend_errors=errors,force_conservation_error_N=conservation,stationary_thrust_N=float(o['thrust']),moving_thrust_N=float(moved['thrust']),moving_over_stationary=.5625,fixed_conv_no_training=True)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 with torch.inference_mode():main()
