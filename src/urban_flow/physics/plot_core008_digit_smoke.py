"""Produce consistent visual and numerical comparison of DIGIT smoke outputs."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

root=repo_root()/'output/core008/physics/digit_smoke'
palette=np.array([[16,35,74],[29,105,158],[68,189,168],[231,217,108],[229,98,58]],float)
canvas=Image.new('RGB',(1480,1540),'#101b29');d=ImageDraw.Draw(canvas)
d.text((24,15),'DIGIT | matched 256 x 256 m crop | final frame (3) | north up',fill='white')
d.text((24,37),'Speed: source conversion [-4,4]; shared scale 0-2 | Grey = solid | Arrows = horizontal flow',fill='#becbd9')
for column,spacing in enumerate((2,1)):
    v=np.load(root/f'{spacing}m/velocity_tczyx.npy',mmap_mode='r')[-1]
    fluid=np.load(root/f'{spacing}m/solver_fluid_zyx.npy')
    for row,altitude in enumerate((10,40)):
        k=altitude//spacing
        speed=np.linalg.norm(v[:,k],axis=0)
        val=np.clip(speed/2,0,1)*4
        idx=np.minimum(val.astype(int),3);t=(val-idx)[...,None]
        rgb=(palette[idx]*(1-t)+palette[idx+1]*t).astype(np.uint8)
        rgb[~fluid[k]]=[108,113,121]
        x=24+column*735;y=80+row*725;side=700;n=speed.shape[0]
        d.text((x,y),f'{spacing} m resolution | layer {altitude}-{altitude+spacing} m',fill='white')
        canvas.paste(Image.fromarray(rgb[::-1]).resize((side,side),Image.Resampling.NEAREST),(x,y+22))
        stride=max(1,n//20)
        for iy in range(stride//2,n,stride):
            for ix in range(stride//2,n,stride):
                if not fluid[k,iy,ix]:continue
                u,w=float(v[0,k,iy,ix]),float(v[1,k,iy,ix])
                a=x+(ix+.5)/n*side;b=y+22+(1-(iy+.5)/n)*side
                dx=u*12;dy=-w*12
                d.line((a,b,a+dx,b+dy),fill='#e0ecf4',width=1)
                length=np.hypot(dx,dy)
                if length>1:
                    ux,uy=dx/length,dy/length
                    d.line((a+dx-3*ux+2*uy,b+dy-3*uy-2*ux,a+dx,b+dy,a+dx-3*ux-2*uy,b+dy-3*uy+2*ux),fill='#e0ecf4')
d.text((24,1523),'Local inference only. No CFD reference; physical timestep and grid-scale transfer are unverified.',fill='#becbd9')
canvas.save(root/'wind_comparison.png')
a=np.load(root/'1m/velocity_tczyx.npy',mmap_mode='r')[-1]
b=np.load(root/'2m/velocity_tczyx.npy',mmap_mode='r')[-1]
coarse=a.reshape(3,64,2,128,2,128,2).mean(axis=(2,4,6))
f1=np.load(root/'1m/solver_fluid_zyx.npy').reshape(64,2,128,2,128,2).all(axis=(1,3,5))
f2=np.load(root/'2m/solver_fluid_zyx.npy')
mask=f1&f2
delta=coarse[:,mask]-b[:,mask]
report={'comparison':'Final frame: average 1m velocity in each 2m cell versus direct 2m inference',
        'mask':'Only cells fluid in both models and all eight fine cells',
        'velocity_component_rmse':float(np.sqrt(np.mean(delta**2))),
        'velocity_component_mae':float(np.abs(delta).mean()),
        'note':'Resolution consistency diagnostic; neither output is ground truth.'}
(root/'resolution_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
