"""TorchRotor-RANS v0.1: voxel-domain k-epsilon, staggered pressure projection.

Conservative upwind scalar/momentum transport, symmetric deviatoric viscous
stress; wall-face functions at h/2. Multi-face wall cells use equal-face mean
production/epsilon. This voxel wall extension is exploratory, not OF equivalence.
"""
import torch
from urban_flow.solvers.mac_torch import MAC
from .transport import face_pair, divergence
from .kepsilon import eddy_viscosity, production_per_viscosity
from .wall import kepsilon_wall


class TerrainRANS:
    def __init__(self, fluid, h, inlet=10., nu=1.5e-5, intensity=.01, length=10., dtype=torch.float32):
        self.f=fluid; self.h=h; self.nu=nu; self.shape=tuple(fluid.shape)
        self.k_in=1.5*(inlet*intensity)**2
        self.e_in=.09**.75*self.k_in**1.5/length
        self.k=torch.full(fluid.shape,self.k_in,device=fluid.device,dtype=dtype)
        self.epsilon=torch.full_like(self.k,self.e_in)
        self.mac=MAC(fluid,h,fluid[:,:,0].to(dtype)*inlet)
        self.mac.vel[0].copy_(self.mac.opened(0)*inlet)
        self.inlet=inlet;self.time=0.
        self.open=[];self.wall=[];self.wall_count=torch.zeros_like(self.k)
        for c in range(3):
            a=2-c;lo,hi=face_pair(fluid,a)
            op=lo&hi;wall=lo^hi
            # Exterior bottom is a wall; lateral/top boundaries are slip.
            wall.narrow(a,0,1).fill_(False);wall.narrow(a,self.shape[a],1).fill_(False)
            if c==2:wall[0]=fluid[0]
            if c!=0:
                op.narrow(a,0,1).fill_(False);op.narrow(a,self.shape[a],1).fill_(False)
            self.open.append(op);self.wall.append(wall)
            self.wall_count+=wall.narrow(a,0,self.shape[a])+wall.narrow(a,1,self.shape[a]).to(dtype)
        self.wall_count*=fluid
        self.last_pressure=self.project()

    def faces(self):
        out=[]
        for c,q in enumerate(self.mac.vel):
            dims=list(q.shape);dims[2-c]=1
            low=torch.zeros(dims,device=q.device,dtype=q.dtype)
            if c==0:low[...,0]=self.mac.inlet
            out.append(torch.cat((low,q),2-c))
        return out

    def centred(self):
        return [.5*(q.narrow(2-c,0,self.shape[2-c])+q.narrow(2-c,1,self.shape[2-c]))*self.f
                for c,q in enumerate(self.faces())]

    def project(self):
        info={}
        for _ in range(3):
            self.mac.p.zero_();info=self.mac.project(rtol=1e-5,maxiter=180)
            if info['divergence_rms']<1e-5:break
        if info['divergence_rms']>=1e-5:raise RuntimeError(('Divergence',info))
        return info

    def scalar_rhs(self,q,gamma,faces,inlet):
        flux=[]
        for c in range(3):
            a=2-c;l,r=face_pair(q,a,inlet if c==0 else None,None)
            gl,gr=face_pair(torch.ones_like(q)*gamma,a)
            grad=(r-l)/self.h
            if c==0:grad[...,0]*=2
            flux.append((faces[c]*torch.where(faces[c]>=0,l,r)-.5*(gl+gr)*grad)*self.open[c])
        return -divergence(flux,[self.h]*3)*self.f

    def gradients(self,u):
        rows=[]
        for c in range(3):
            cols=[]
            for d in range(3):
                a=2-d;l,r=face_pair(u[c],a,self.inlet if c==0 and d==0 else (0. if d==0 else None),None)
                value=.5*(l+r)
                value=torch.where(self.wall[d],0.,value)
                if d==0:value[...,0]=self.inlet if c==0 else 0.
                if c==d and d!=0:
                    value.narrow(a,0,1).zero_();value.narrow(a,self.shape[a],1).zero_()
                cols.append(torch.diff(value,dim=a)/self.h)
            rows.append(torch.stack(cols,-1))
        return torch.stack(rows,-2)

    def stable_dt(self):
        nut=eddy_viscosity(self.k,self.epsilon)
        rate=sum(q.abs()/self.h for q in self.centred())+12*(self.nu+nut)/self.h**2
        return .25/max(float(rate[self.f].max()),1e-12)

    def advance(self,dt,acceleration=None,face_acceleration=None):
        u=self.centred();faces=self.faces();grad=self.gradients(u)
        nut=eddy_viscosity(self.k,self.epsilon);gamma=self.nu+nut
        production=nut*production_per_viscosity(grad)
        wall_e=torch.zeros_like(self.k);wall_p=torch.zeros_like(self.k)
        wall_nut=[]
        for d in range(3):
            a=2-d;tangential=torch.sqrt(sum(u[c].square() for c in range(3) if c!=d))
            wall=kepsilon_wall(self.k,tangential,self.h/2,self.nu)
            l,r=face_pair(wall['nut'],a);fl,fr=face_pair(self.f,a)
            wn=torch.where(fl,l,r);wall_nut.append(wn)
            count=(self.wall[d].narrow(a,0,self.shape[a]).to(self.k.dtype)+self.wall[d].narrow(a,1,self.shape[a]))*self.f
            wall_e+=count*wall['epsilon'];wall_p+=count*wall['production']
        wallcells=self.wall_count>0
        production=torch.where(wallcells,wall_p/self.wall_count.clamp_min(1),production)
        en=(self.epsilon+dt*(self.scalar_rhs(self.epsilon,self.nu+nut/1.3,faces,self.e_in)+1.44*self.epsilon/self.k*production))/(1+dt*1.92*self.epsilon/self.k)
        en=torch.where(wallcells,wall_e/self.wall_count.clamp_min(1),en)
        kn=(self.k+dt*(self.scalar_rhs(self.k,self.nu+nut,faces,self.k_in)+production))/(1+dt*en/self.k)
        if not torch.isfinite(kn).all() or not torch.isfinite(en).all() or (kn[self.f]<=0).any() or (en[self.f]<=0).any():
            raise RuntimeError('Turbulence positivity/finite check failed')
        trace=grad.diagonal(dim1=-2,dim2=-1).sum(-1)
        rhs=[]
        for c in range(3):
            flux=[]
            for d in range(3):
                a=2-d;l,r=face_pair(u[c],a,self.inlet if c==0 and d==0 else (0. if d==0 else None),None)
                normal=(r-l)/self.h
                if d==0:normal[...,0]*=2
                gl,gr=face_pair(gamma,a);cl,cr=face_pair(grad[...,d,c]-(2/3)*trace if c==d else grad[...,d,c],a)
                stress=.5*(gl+gr)*(normal+.5*(cl+cr))*self.open[d]
                fl,fr=face_pair(self.f,a)
                # Wall traction: tangential log-law drag; normal velocity is impermeable.
                drag=(self.nu+wall_nut[d])*torch.where(fl,-l,r)/(self.h/2)
                stress=torch.where(self.wall[d],drag if c!=d else torch.zeros_like(drag),stress)
                if d!=0:
                    stress.narrow(a,self.shape[a],1).zero_()
                    if d==1:stress.narrow(a,0,1).zero_()
                flux.append(faces[d]*torch.where(faces[d]>=0,l,r)-stress)
            value=-divergence(flux,[self.h]*3)*self.f
            if acceleration is not None:value+=acceleration[c]
            rhs.append(value)
        for c in range(3):
            a=2-c;l,r=face_pair(rhs[c],a)
            self.mac.vel[c].add_(.5*(l+r).narrow(a,1,self.shape[a]),alpha=dt)
            if face_acceleration is not None:self.mac.vel[c].add_(face_acceleration[c],alpha=dt)
            self.mac.vel[c]*=self.mac.opened(c)
        self.k=torch.where(self.f,kn,self.k_in);self.epsilon=torch.where(self.f,en,self.e_in)
        self.last_pressure=self.project();self.time+=dt
        if not all(torch.isfinite(q).all() for q in self.mac.vel):raise RuntimeError('Nonfinite velocity')
        return dict(time_s=self.time,**self.last_pressure,k_min=float(self.k[self.f].min()),epsilon_min=float(self.epsilon[self.f].min()))
