if __name__ == '__main__' and not __package__:
 import sys
 from pathlib import Path
 sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

"""Checks for the open-top option of mac_torch.MAC (closed-lid behaviour must be unchanged)."""
import sys,json,math
from pathlib import Path
import torch
here=Path(__file__).resolve().parent
from urban_flow.solvers.mac_torch import MAC


def main():
 torch.backends.cudnn.allow_tf32=False
 dev='cuda' if torch.cuda.is_available() else 'cpu';torch.manual_seed(3);out={}
 with torch.inference_mode():
  shape=(16,16,64);f=torch.ones(shape,dtype=torch.bool,device=dev);inlet=torch.full(shape[:2],8.,device=dev)
  for top in (False,True):
   m=MAC(f,1.,inlet,open_top=top);m.vel[0].fill_(8);m.project();m.advect(.05);d=m.project()
   assert max(float((q-(8 if c==0 else 0)).abs().max()) for c,q in enumerate(m.vel))<1e-5,('uniform flow',top)
  # Random field with terrain step and open top: divergence, idempotence, symmetry.
  g=f.clone();g[:3]=False;g[3:7,:,20:40]=False
  m=MAC(g,1.,inlet*0,open_top=True);m.vel=[torch.randn(shape,device=dev)*.1*m.opened(c) for c in range(3)]
  d=m.project(rtol=1e-7,maxiter=200);assert d['divergence_rms']<2e-6,d;once=[q.clone() for q in m.vel];m.project(rtol=1e-7,maxiter=200)
  idem=max(float((a-b).abs().max()) for a,b in zip(once,m.vel));assert idem<5e-6,idem
  x=torch.randn(shape,device=dev)*g;y=torch.randn(shape,device=dev)*g;ax=torch.empty_like(x);ay=torch.empty_like(x);m.op(x,x,ax);m.op(y,y,ay)
  sym=abs(float((x*ay).sum()-(y*ax).sum()));assert sym<1e-3,sym
  out.update(uniform_flow_preserved=True,open_top_divergence_rms=d['divergence_rms'],idempotence_max_abs=idem,operator_symmetry_abs=sym)
  # Rising ground under a low lid: closed lid must accelerate by the depth ratio, open top much less.
  shape=(32,8,128);h=1.;k=torch.arange(shape[0],device=dev)[:,None,None];i=torch.arange(shape[2],device=dev)[None,None,:]
  ground=(4+12*(i/(shape[2]-1)).clamp(0,1)).expand(1,shape[1],shape[2]);g=(k*h>ground)
  for top in (False,True):
   m=MAC(g,h,torch.full(shape[:2],8.,device=dev)*g[:,:,0],open_top=top);m.vel[0].copy_(8*g*torch.roll(g,-1,2));m.vel[0][:,:,-1]=8*g[:,:,-1]
   for _ in range(400):m.advect(.02);m.project(rtol=1e-6,maxiter=200)
   col=shape[2]-8;u=m.vel[0][:,:,col][g[:,:,col]&g[:,:,col+1]]
   out['closed_lid_speedup' if not top else 'open_top_speedup']=float(u.mean()/8)
  out['depth_ratio']=float((shape[0]-4-1)/(shape[0]-ground[0,0,-8]-1))
  assert out['open_top_speedup']<out['closed_lid_speedup'];print(json.dumps(out,indent=1))
  # Slab-wise Conv3d must equal the single full Conv3d exactly.
  import torch.nn.functional as F
  x=torch.randn((150,512,1024),device=dev);m=MAC(torch.ones((8,8,8),dtype=torch.bool,device=dev),1.,torch.zeros((8,8),device=dev))
  full=F.conv3d(x[None,None],m.kernel,padding=1)[0,0];slab=m.neighbours(x);err=float((full-slab).abs().max());assert err<1e-5,err;print('slab conv max abs error',err)

if __name__ == '__main__':
 main()
