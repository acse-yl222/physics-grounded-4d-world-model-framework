"""Persist terrain-relative dense slices without keeping their history in GPU RAM."""
import json
from pathlib import Path
import numpy as np
import torch

class DenseSeries:
    def __init__(self,root,solid,ground,study,dt,target,reset=False,prefix='ai4urban'):
        self.out=Path(root)/'visualizer/scenes/region/physics/ai4urban'
        self.path=self.out/'manifest.json'
        self.manifest=json.loads(self.path.read_text())
        self.prefix=prefix
        if reset:
            (self.out/f'manifest_before_{prefix}.json').write_text(self.path.read_text())
            for f in self.manifest['fields']:
                f['files']=[];f['steps']=[];f['times']=[]
            for k in ['failed','stop_reason']:self.manifest.pop(k,None)
        self.dt=dt;self.target=target;self.indices={}
        nz,ny,nx=solid.shape
        yy,xx=np.indices((ny,nx))
        for f in self.manifest['fields']:
            agl=f['agl_m'];z=np.floor((ground+agl)/8).astype(int)
            valid=study&(z>=0)&(z<nz);z=np.clip(z,0,nz-1)
            valid &= ~solid[z,yy,xx]
            self.indices[agl]=(tuple(torch.as_tensor(a,device='cuda') for a in (z,yy,xx)),valid)
            if 'files' not in f:
                f['files']=[f['file']];f['steps']=[f['source_step']];f['times']=[f['t0']]
        self.manifest.update(target_steps=target,complete=False,source='AI4Urban time integration; terrain-relative dense 8 m slices; float16 display export, float32 solver/checkpoint.')
    def save(self,step,state):
        for f in self.manifest['fields']:
            if not f['steps'] or step>f['steps'][-1]:
                (z,y,x),valid=self.indices[f['agl_m']]
                data=np.stack([s[0,0,z,y,x].cpu().numpy() for s in state[:3]])
                data[0]*=-1;data[:,~valid]=np.nan
                name=f"{self.prefix}_uvw_agl{f['agl_m']}_s{step:06d}_tcyx.npy"
                with (self.out/(name+'.tmp')).open('wb') as stream:np.save(stream,data[None].astype('<f2'))
                (self.out/(name+'.tmp')).replace(self.out/name)
                f['files'].append('ai4urban/'+name);f['steps'].append(step);f['times'].append(step*self.dt)
                f['file']=f['files'][0]
                f['range'][1]=max(f['range'][1],float(np.ceil(np.nanmax(np.linalg.norm(data,axis=0))*10)/10))
            f['label']=f"AI4Urban · 目标离地 {f['agl_m']} m（地形随动，误差 ±4 m）· 时间推进过程；尚未验证稳态。"
        self.manifest.update(completed_steps=step,simulated_seconds=step*self.dt,complete=step>=self.target,running=step<self.target)
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(self.manifest,indent=2,allow_nan=False));tmp.replace(self.path)
