"""Memory-bounded float32 MAC projection solver (PyTorch + fused Triton stencils).
Independent numerical variant, NOT the unchanged AI4Urban neural-convolution solver.
First-order upwind transport, voxel impermeable boundaries, MG-preconditioned CG.
All pressure levels are globally coupled; no independent subdomain pressure solves.
"""
import math
import torch
import triton as tr
import triton.language as tl

@tr.jit
def _coords(i,NX:tl.constexpr,NY:tl.constexpr):
 return i%NX,(i//NX)%NY,i//(NX*NY)

@tr.jit
def _op(P,F,B,O,NX:tl.constexpr,NY:tl.constexpr,NZ:tl.constexpr,MODE:tl.constexpr,BS:tl.constexpr):
 i=tl.program_id(0)*BS+tl.arange(0,BS);n=NX*NY*NZ;ok=i<n;x,y,z=_coords(i,NX,NY)
 f=tl.load(F+i,ok,other=0);v=tl.load(P+i,ok,other=0);diag=tl.where(x==NX-1,2.,0.);s=tl.full((BS,),0.,tl.float32)
 for direction in tl.static_range(6):
  if direction==0:off=-1;inside=x>0
  elif direction==1:off=1;inside=x<NX-1
  elif direction==2:off=-NX;inside=y>0
  elif direction==3:off=NX;inside=y<NY-1
  elif direction==4:off=-NX*NY;inside=z>0
  else:off=NX*NY;inside=z<NZ-1
  air=tl.load(F+i+off,ok&inside,other=0);w=air.to(tl.float32);diag+=w;s+=w*tl.load(P+i+off,ok&inside,other=0)
 diagonal=tl.where(f&(diag>0),diag,1.)
 if MODE==0:r=tl.where(f,diag*v-s,v)
 elif MODE==1:r=tl.where(f,(1.-2./3.)*v+(2./3.)*(tl.load(B+i,ok,other=0)+s)/diagonal,0.)
 else:r=tl.load(B+i,ok,other=0)-tl.where(f,diag*v-s,v)
 tl.store(O+i,r,ok)

@tr.jit
def _restrict(X,Y,NX:tl.constexpr,NY:tl.constexpr,NZ:tl.constexpr,FLUID:tl.constexpr,BS:tl.constexpr):
 i=tl.program_id(0)*BS+tl.arange(0,BS);nx=NX//2;ny=NY//2;nz=NZ//2;ok=i<nx*ny*nz;x,y,z=_coords(i,nx,ny);j=2*x+2*y*NX+2*z*NX*NY
 s=tl.full((BS,),0.,tl.float32)
 for dz in range(2):
  for dy in range(2):
   for dx in range(2):s+=tl.load(X+j+dx+dy*NX+dz*NX*NY,ok,other=0).to(tl.float32)
 if FLUID:tl.store(Y+i,s>0,ok)
 else:tl.store(Y+i,s*.5,ok) # average residual times h_coarse^2/h_fine^2

@tr.jit
def _prolong(C,X,F,NX:tl.constexpr,NY:tl.constexpr,NZ:tl.constexpr,BS:tl.constexpr):
 i=tl.program_id(0)*BS+tl.arange(0,BS);ok=i<NX*NY*NZ;x,y,z=_coords(i,NX,NY);j=x//2+(y//2)*(NX//2)+(z//2)*(NX//2)*(NY//2)
 r=tl.load(X+i,ok,other=0)+tl.load(C+j,ok,other=0);f=tl.load(F+i,ok,other=0);tl.store(X+i,tl.where(f,r,0.),ok)

@tr.jit
def _velocity(U,V,W,I,x,y,z,C:tl.constexpr,NX:tl.constexpr,NY:tl.constexpr,NZ:tl.constexpr):
 xx=tl.minimum(tl.maximum(x,0),NX-1);yy=tl.minimum(tl.maximum(y,0),NY-1);zz=tl.minimum(tl.maximum(z,0),NZ-1);idx=xx+yy*NX+zz*NX*NY
 if C==0:
  v=tl.load(U+idx);v=tl.where(x<0,tl.load(I+yy+zz*NY),v)
 elif C==1:
  v=tl.load(V+idx);v=tl.where((x<0)|(y<0)|(y>=NY),0.,v)
 else:
  v=tl.load(W+idx);v=tl.where((x<0)|(z<0)|(z>=NZ),0.,v)
 return v

@tr.jit
def _advect(U,V,W,I,F,O,NX:tl.constexpr,NY:tl.constexpr,NZ:tl.constexpr,H:tl.constexpr,DT,C:tl.constexpr,BS:tl.constexpr):
 i=tl.program_id(0)*BS+tl.arange(0,BS);ok=i<NX*NY*NZ;x,y,z=_coords(i,NX,NY)
 q=_velocity(U,V,W,I,x,y,z,C,NX,NY,NZ)
 if C==0:
  vx=q;vy=.25*(_velocity(U,V,W,I,x,y,z,1,NX,NY,NZ)+_velocity(U,V,W,I,x+1,y,z,1,NX,NY,NZ)+_velocity(U,V,W,I,x,y-1,z,1,NX,NY,NZ)+_velocity(U,V,W,I,x+1,y-1,z,1,NX,NY,NZ))
  vz=.25*(_velocity(U,V,W,I,x,y,z,2,NX,NY,NZ)+_velocity(U,V,W,I,x+1,y,z,2,NX,NY,NZ)+_velocity(U,V,W,I,x,y,z-1,2,NX,NY,NZ)+_velocity(U,V,W,I,x+1,y,z-1,2,NX,NY,NZ))
  other=tl.load(F+i+1,ok&(x<NX-1),other=1);opened=other
 elif C==1:
  vy=q;vx=.25*(_velocity(U,V,W,I,x,y,z,0,NX,NY,NZ)+_velocity(U,V,W,I,x-1,y,z,0,NX,NY,NZ)+_velocity(U,V,W,I,x,y+1,z,0,NX,NY,NZ)+_velocity(U,V,W,I,x-1,y+1,z,0,NX,NY,NZ))
  vz=.25*(_velocity(U,V,W,I,x,y,z,2,NX,NY,NZ)+_velocity(U,V,W,I,x,y+1,z,2,NX,NY,NZ)+_velocity(U,V,W,I,x,y,z-1,2,NX,NY,NZ)+_velocity(U,V,W,I,x,y+1,z-1,2,NX,NY,NZ))
  opened=tl.load(F+i+NX,ok&(y<NY-1),other=0)
 else:
  vz=q;vx=.25*(_velocity(U,V,W,I,x,y,z,0,NX,NY,NZ)+_velocity(U,V,W,I,x-1,y,z,0,NX,NY,NZ)+_velocity(U,V,W,I,x,y,z+1,0,NX,NY,NZ)+_velocity(U,V,W,I,x-1,y,z+1,0,NX,NY,NZ))
  vy=.25*(_velocity(U,V,W,I,x,y,z,1,NX,NY,NZ)+_velocity(U,V,W,I,x,y-1,z,1,NX,NY,NZ)+_velocity(U,V,W,I,x,y,z+1,1,NX,NY,NZ)+_velocity(U,V,W,I,x,y-1,z+1,1,NX,NY,NZ))
  opened=tl.load(F+i+NX*NY,ok&(z<NZ-1),other=0)
 qx=_velocity(U,V,W,I,x+tl.where(vx>=0,-1,1),y,z,C,NX,NY,NZ)
 qy=_velocity(U,V,W,I,x,y+tl.where(vy>=0,-1,1),z,C,NX,NY,NZ)
 qz=_velocity(U,V,W,I,x,y,z+tl.where(vz>=0,-1,1),C,NX,NY,NZ)
 new=q-DT/H*(tl.abs(vx)*(q-qx)+tl.abs(vy)*(q-qy)+tl.abs(vz)*(q-qz))
 f=tl.load(F+i,ok,other=0);tl.store(O+i,tl.where(f&opened,new,0.),ok)

@tr.jit
def _rhs(U,V,W,I,F,R,NX:tl.constexpr,NY:tl.constexpr,NZ:tl.constexpr,H:tl.constexpr,BS:tl.constexpr):
 i=tl.program_id(0)*BS+tl.arange(0,BS);ok=i<NX*NY*NZ;x,y,z=_coords(i,NX,NY)
 west=tl.load(U+i-1,ok&(x>0),other=0);west=tl.where(x==0,tl.load(I+y+z*NY,ok,other=0),west)
 div=tl.load(U+i,ok,other=0)-west+tl.load(V+i,ok,other=0)-tl.load(V+i-NX,ok&(y>0),other=0)+tl.load(W+i,ok,other=0)-tl.load(W+i-NX*NY,ok&(z>0),other=0)
 f=tl.load(F+i,ok,other=0);tl.store(R+i,tl.where(f,-H*div,0.),ok)

@tr.jit
def _project(U,V,W,P,F,NX:tl.constexpr,NY:tl.constexpr,NZ:tl.constexpr,H:tl.constexpr,BS:tl.constexpr):
 i=tl.program_id(0)*BS+tl.arange(0,BS);ok=i<NX*NY*NZ;x,y,z=_coords(i,NX,NY);f=tl.load(F+i,ok,other=0);p=tl.load(P+i,ok,other=0)
 fx=tl.load(F+i+1,ok&(x<NX-1),other=1);fy=tl.load(F+i+NX,ok&(y<NY-1),other=0);fz=tl.load(F+i+NX*NY,ok&(z<NZ-1),other=0)
 dx=tl.load(P+i+1,ok&(x<NX-1),other=0)-p;dx=tl.where(x==NX-1,-2*p,dx)
 dy=tl.load(P+i+NX,ok&(y<NY-1),other=0)-p;dz=tl.load(P+i+NX*NY,ok&(z<NZ-1),other=0)-p
 tl.store(U+i,tl.where(f&fx,tl.load(U+i,ok,other=0)-dx/H,0.),ok)
 tl.store(V+i,tl.where(f&fy,tl.load(V+i,ok,other=0)-dy/H,0.),ok)
 tl.store(W+i,tl.where(f&fz,tl.load(W+i,ok,other=0)-dz/H,0.),ok)

@tr.jit
def _maxsum(U,V,W,O,N:tl.constexpr,BS:tl.constexpr):
 i=tl.program_id(0)*BS+tl.arange(0,BS);v=tl.abs(tl.load(U+i,i<N,other=0))+tl.abs(tl.load(V+i,i<N,other=0))+tl.abs(tl.load(W+i,i<N,other=0));tl.store(O+tl.program_id(0),tl.max(v,axis=0))

class MAC:
 def __init__(self,fluid,cell,inlet):
  self.f=fluid.contiguous();self.shape=tuple(fluid.shape);self.h=cell;self.nz,self.ny,self.nx=self.shape;self.n=fluid.numel();self.count=int(fluid.sum());self.inlet=inlet.contiguous();self.vel=[torch.zeros(self.shape,device=fluid.device) for _ in range(3)]
  self.p=torch.zeros_like(self.vel[0]);self.r=torch.zeros_like(self.p);self.d=torch.zeros_like(self.p);self.q=torch.zeros_like(self.p);self.z=torch.zeros_like(self.p)
  self.levels=[];f=self.f;shape=self.shape
  while True:
   tmp=torch.zeros(shape,device=f.device);res=torch.zeros_like(tmp) if self.levels else self.q;rhs=torch.zeros_like(tmp) if self.levels else None;x=torch.zeros_like(tmp) if self.levels else None
   self.levels.append(dict(f=f,shape=shape,tmp=tmp,res=res,rhs=rhs,x=x))
   if min(shape)<=4:break
   coarse=tuple(s//2 for s in shape);cf=torch.empty(coarse,device=f.device,dtype=torch.bool)
   _restrict[(tr.cdiv(cf.numel(),256),)](f,cf,shape[2],shape[1],shape[0],True,256)
   f=cf;shape=coarse
  self.reduction=torch.empty(tr.cdiv(self.n,256),device=fluid.device)
 def op(self,p,b,out,level=0,mode=0):
  l=self.levels[level];nz,ny,nx=l['shape'];_op[(tr.cdiv(p.numel(),256),)](p,l['f'],b,out,nx,ny,nz,mode,256)
 def vcycle(self,b,x,lev=0):
  l=self.levels[lev];nz,ny,nx=l['shape'];last=lev==len(self.levels)-1
  for _ in range(48 if last else 2):self.op(x,b,l['tmp'],lev,1);x.copy_(l['tmp'])
  if last:return
  self.op(x,b,l['res'],lev,2);c=self.levels[lev+1]
  _restrict[(tr.cdiv(c['rhs'].numel(),256),)](l['res'],c['rhs'],nx,ny,nz,False,256)
  c['x'].zero_();self.vcycle(c['rhs'],c['x'],lev+1)
  _prolong[(tr.cdiv(x.numel(),256),)](c['x'],x,l['f'],nx,ny,nz,256)
  for _ in range(2):self.op(x,b,l['tmp'],lev,1);x.copy_(l['tmp'])
 def project(self,rtol=1e-4,maxiter=100):
  _rhs[(tr.cdiv(self.n,256),)](*self.vel,self.inlet,self.f,self.r,self.nx,self.ny,self.nz,self.h,256)
  bnorm=float(torch.linalg.vector_norm(self.r));tol=max(bnorm*rtol,1e-6*math.sqrt(self.count)*self.h**2)
  self.op(self.p,self.r,self.q);self.r.sub_(self.q)
  norm=float(torch.linalg.vector_norm(self.r));iterations=0
  if norm>tol:
   self.z.zero_();self.vcycle(self.r,self.z);self.d.copy_(self.z);rz=float(torch.dot(self.r.flatten(),self.z.flatten()))
   for it in range(maxiter):
    self.op(self.d,self.r,self.q);dq=float(torch.dot(self.d.flatten(),self.q.flatten()));assert dq>0 and math.isfinite(dq),('PCG breakdown',dq)
    alpha=rz/dq;self.p.add_(self.d,alpha=alpha);self.r.add_(self.q,alpha=-alpha);norm=float(torch.linalg.vector_norm(self.r));iterations=it+1
    if norm<=tol:break
    self.z.zero_();self.vcycle(self.r,self.z);newrz=float(torch.dot(self.r.flatten(),self.z.flatten()));self.d.mul_(newrz/rz).add_(self.z);rz=newrz
  assert norm<=tol,('Pressure convergence',iterations,norm,tol)
  _project[(tr.cdiv(self.n,256),)](*self.vel,self.p,self.f,self.nx,self.ny,self.nz,self.h,256)
  # Direct post-projection divergence is checked independently of the CG recurrence.
  _rhs[(tr.cdiv(self.n,256),)](*self.vel,self.inlet,self.f,self.q,self.nx,self.ny,self.nz,self.h,256)
  rms=float(torch.linalg.vector_norm(self.q))/(math.sqrt(self.count)*self.h**2)
  return dict(iterations=iterations,divergence_rms=rms,linear_relative_residual=norm/max(bnorm,1e-30))
 def advect(self,dt):
  old=self.vel;new=[torch.empty_like(old[0]) for _ in range(3)]
  for c in range(3):_advect[(tr.cdiv(self.n,256),)](*old,self.inlet,self.f,new[c],self.nx,self.ny,self.nz,self.h,dt,c,256)
  self.vel=new
 def maxsum(self):
  _maxsum[(tr.cdiv(self.n,256),)](*self.vel,self.reduction,self.n,256);return float(self.reduction.max())
