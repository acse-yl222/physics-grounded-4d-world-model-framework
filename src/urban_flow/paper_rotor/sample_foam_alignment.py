"""Sample reconstructed blockMesh cells with the same trilinear rule as Torch."""
import argparse,json,re
from pathlib import Path
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from common.export import write,digest

def vector_field(path):
    text=Path(path).read_text();m=re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\(',text)
    if not m:raise ValueError('Expected nonuniform ASCII vector field')
    stop=text.index('\n)',m.end())
    a=np.fromstring(text[m.end():stop].replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3)
    if len(a)!=int(m[1]) or not np.isfinite(a).all():raise ValueError('Invalid vector field')
    return a

def sample(case,iteration,out):
    case,out=Path(case),Path(out);cfg=json.loads((case/'configuration.json').read_text())
    c=vector_field(case/str(iteration)/'C');u=vector_field(case/str(iteration)/'U')
    n=np.array(cfg['grid_cells_xyz']);h=np.array(cfg['actual_spacing_xyz_m'])
    idx=np.rint(c/h-.5).astype(int)
    if not np.allclose(c,(idx+.5)*h,rtol=0,atol=1e-8) or (idx<0).any() or (idx>=n).any():raise ValueError('Nonuniform/mismatched mesh')
    linear=idx[:,0]+n[0]*(idx[:,1]+n[1]*idx[:,2])
    if len(np.unique(linear))!=np.prod(n) or len(u)!=len(c):raise ValueError('Incomplete reconstructed mesh')
    ux=np.empty(tuple(n[::-1]));ux[idx[:,2],idx[:,1],idx[:,0]]=u[:,0]
    axes=[(np.arange(ni)+.5)*hi for ni,hi in zip(n[::-1],h[::-1])]
    interp=RegularGridInterpolator(axes,ux,bounds_error=True)
    hx,hy,hz=cfg['hub_xyz_m'];D=cfg['rotor_diameter_m'];out.mkdir(parents=True,exist_ok=False)
    for d in [1,3,5]:
        y=np.linspace(hy-1.5*D,hy+1.5*D,121);pos=np.column_stack([np.full_like(y,hx+d*D),y,np.full_like(y,hz)])
        values=1-interp(pos[:,::-1])/cfg['inlet_m_s']
        write(out/f'wake_{d}d.json',{'positions':pos.tolist(),'values':values.tolist()})
    write(out/'provenance.json',{'iteration':iteration,'configuration_sha256':digest(case/'configuration.json'),'velocity_sha256':digest(case/str(iteration)/'U'),'centres_sha256':digest(case/str(iteration)/'C'),'interpolation':'trilinear cell-centred Ux','coordinate_order_verified':True})
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('case',type=Path);p.add_argument('iteration',type=int);p.add_argument('out',type=Path);a=p.parse_args();print(sample(a.case,a.iteration,a.out))
