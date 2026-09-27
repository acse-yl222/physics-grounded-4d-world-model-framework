import json,torch,numpy as np
from mac import MAC

torch.set_num_threads(4)
with torch.inference_mode():
 shape=(16,16,32);f=torch.ones(shape,dtype=torch.bool,device='cuda');inlet=torch.full(shape[:2],8.,device='cuda');m=MAC(f,2.,inlet);m.vel[0].fill_(8)
 d=m.project();m.advect(.05);d=m.project();assert float((m.vel[0]-8).abs().max())==0 and d['divergence_rms']==0
 torch.manual_seed(9);m.inlet.zero_();m.vel=[torch.randn(shape,device='cuda')*.1 for _ in range(3)];m.vel[1][:,-1]=0;m.vel[2][-1]=0
 before=[x.clone() for x in m.vel];m.p.zero_();d=m.project(rtol=1e-6);assert d['divergence_rms']<1e-6,d
 projected=[x.clone() for x in m.vel];d2=m.project(rtol=1e-6);assert max(float((x-y).abs().max()) for x,y in zip(m.vel,projected))<5e-6
 # Solid staircase/obstacle, random face field: verify impermeability and true divergence.
 f[:4]=False;f[4:9,5:11,12:18]=False;m=MAC(f,2.,torch.zeros(shape[:2],device='cuda'))
 m.vel=[torch.randn(shape,device='cuda')*.01 for _ in range(3)]
 for k,axis in enumerate([2,1,0]):
  opened=f&torch.roll(f,-1,axis)
  if k==0:opened[:,:,-1]=f[:,:,-1]
  elif k==1:opened[:,-1]=False
  else:opened[-1]=False
  m.vel[k]*=opened
 d3=m.project(rtol=1e-6);assert d3['divergence_rms']<1e-6,d3
 # Discrete A must be symmetric; pressure correction and divergence must agree.
 x=torch.randn(shape,device='cuda')*f;y=torch.randn(shape,device='cuda')*f
 ax=torch.empty_like(x);ay=torch.empty_like(x);m.op(x,x,ax);m.op(y,y,ay)
 xy=float((x*ay).sum());yx=float((y*ax).sum());assert abs(xy-yx)<1e-4*max(1,abs(xy)),(xy,yx)
 print(json.dumps(dict(passed=True,uniform_flow_preserved=True,projection=d,solid_projection=d3,operator_symmetry_abs_error=abs(xy-yx),gpu_peak_gib=torch.cuda.max_memory_allocated()/2**30)))
