"""Pure PyTorch counterpart of mac.py; identical staggered-grid conventions.
Fixed Conv3d neighbour filters implement the masked pressure stencil.
No trained parameters, no Triton dependency. Intended for reference/small cases.
"""
import math
import torch
import torch.nn.functional as F

class MAC:
 def __init__(self,fluid,cell,inlet):
  self.f=fluid.contiguous(); self.shape=tuple(fluid.shape); self.h=cell
  self.nz,self.ny,self.nx=self.shape; self.count=int(fluid.sum()); self.inlet=inlet
  self.vel=[torch.zeros_like(inlet).new_zeros(self.shape) for _ in range(3)]
  self.p=torch.zeros_like(self.vel[0]); self.r=self.p.clone();self.q=self.p.clone();self.d=self.p.clone();self.z=self.p.clone()
  self.kernel=self.p.new_zeros((1,1,3,3,3))
  for axis in range(3):
   for end in (0,2):
    idx=[0,0,1,1,1];idx[axis+2]=end;self.kernel[tuple(idx)]=1
  self.levels=[];f=self.f
  while True:
   diag=self.neighbours(f.to(self.p.dtype));diag[:,:,-1]+=2
   self.levels.append(dict(f=f,diag=diag,tmp=torch.zeros_like(diag),res=torch.zeros_like(diag),rhs=torch.zeros_like(diag),x=torch.zeros_like(diag)))
   if min(f.shape)<=4:break
   if any(s%2 for s in f.shape):raise ValueError('Multigrid requires even dimensions before the coarsest level')
   f=F.max_pool3d(f[None,None].float(),2)[0,0].bool()
 def neighbours(self,x):
  # TF32 roundoff breaks the pressure/divergence consistency near convergence.
  with torch.backends.cudnn.flags(allow_tf32=False):
   return F.conv3d(x[None,None],self.kernel,padding=1)[0,0]
 def op(self,p,b,out,level=0,mode=0):
  l=self.levels[level]; f=l['f'];diag=l['diag'];s=self.neighbours(p*f)
  a=torch.where(f,diag*p-s,p)
  if mode==0:out.copy_(a)
  elif mode==2:out.copy_(b-a)
  else:out.copy_(torch.where(f,p/3+(2/3)*(b+s)/diag.clamp_min(1),0))
 def vcycle(self,b,x,lev=0):
  l=self.levels[lev];last=lev==len(self.levels)-1
  for _ in range(48 if last else 2):self.op(x,b,l['tmp'],lev,1);x.copy_(l['tmp'])
  if last:return
  self.op(x,b,l['res'],lev,2);c=self.levels[lev+1]
  c['rhs'].copy_(F.avg_pool3d(l['res'][None,None],2)[0,0]*4)
  c['x'].zero_();self.vcycle(c['rhs'],c['x'],lev+1)
  x.add_(F.interpolate(c['x'][None,None],scale_factor=2,mode='nearest')[0,0]);x.mul_(l['f'])
  for _ in range(2):self.op(x,b,l['tmp'],lev,1);x.copy_(l['tmp'])
 def opened(self,c):
  axis=2-c;f=self.f;mask=f&torch.roll(f,-1,axis)
  sl=[slice(None)]*3;sl[axis]=-1
  mask[tuple(sl)]=f[tuple(sl)] if c==0 else False
  return mask
 def rhs(self):
  u,v,w=self.vel
  west=F.pad(u[:,:,:-1],(1,0));west[:,:,0]=self.inlet
  south=F.pad(v[:,:-1,:],(0,0,1,0));bottom=F.pad(w[:-1],(0,0,0,0,1,0))
  return -self.h*(u-west+v-south+w-bottom)*self.f
 def project(self,rtol=1e-4,maxiter=100):
  self.r.copy_(self.rhs());bnorm=float(torch.linalg.vector_norm(self.r));tol=max(bnorm*rtol,1e-6*math.sqrt(self.count)*self.h**2)
  self.op(self.p,self.r,self.q);self.r.sub_(self.q);norm=float(torch.linalg.vector_norm(self.r));iterations=0
  if norm>tol:
   self.z.zero_();self.vcycle(self.r,self.z);self.d.copy_(self.z);rz=float((self.r*self.z).sum())
   for it in range(maxiter):
    self.op(self.d,self.r,self.q);dq=float((self.d*self.q).sum())
    if dq<=0 or not math.isfinite(dq):raise RuntimeError(('PCG breakdown',dq))
    alpha=rz/dq;self.p.add_(self.d,alpha=alpha);self.r.add_(self.q,alpha=-alpha);norm=float(torch.linalg.vector_norm(self.r));iterations=it+1
    if norm<=tol:break
    self.z.zero_();self.vcycle(self.r,self.z);newrz=float((self.r*self.z).sum());self.d.mul_(newrz/rz).add_(self.z);rz=newrz
  if norm>tol:raise RuntimeError(('Pressure convergence',iterations,norm,tol))
  for c in range(3):
   axis=2-c;dp=torch.roll(self.p,-1,axis)-self.p
   if c==0:dp[:,:,-1]=-2*self.p[:,:,-1]
   self.vel[c].sub_(dp/self.h).mul_(self.opened(c))
  rms=float(torch.linalg.vector_norm(self.rhs()))/(math.sqrt(self.count)*self.h**2)
  return dict(iterations=iterations,divergence_rms=rms,linear_relative_residual=norm/max(bnorm,1e-30))
 def advect(self,dt):
  padded=[]
  for c,q in enumerate(self.vel):
   p=F.pad(q[None,None],(1,1,1,1,1,1),mode='replicate')[0,0]
   if c==0:p[:,:,0]=F.pad(self.inlet[None,None],(1,1,1,1),mode='replicate')[0,0]
   else:
    p[:,:,0]=0
    if c==1:p[:,0,:]=0;p[:,-1,:]=0
    else:p[0,:,:]=0;p[-1,:,:]=0
   padded.append(p)
  def at(c,offset):return padded[c][tuple(slice(1+o,1+o+n) for o,n in zip(offset,self.shape))]
  new=[]
  for c,q in enumerate(self.vel):
   change=torch.zeros_like(q)
   for d in range(3):
    a=2-d;minus=[0]*3;plus=[0]*3;minus[a]=-1;plus[a]=1
    if c==d:speed=q
    else:
     shift=[0]*3;shift[2-c]=1;both=shift.copy();both[a]-=1
     speed=(at(d,[0]*3)+at(d,shift)+at(d,minus)+at(d,both))*.25
    upwind=torch.where(speed>=0,at(c,minus),at(c,plus))
    change.add_(speed.abs()*(q-upwind))
   new.append((q-dt/self.h*change)*self.opened(c))
  self.vel=new
 def maxsum(self):return float(sum(q.abs() for q in self.vel).max())
