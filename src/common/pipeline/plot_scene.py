"""Scene-local overview figures; all extents taken from the geometry manifest."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None,''):
    sys.path.insert(0,str(repo_root()))
from common.pipeline.paths import project_path


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--config',default='configs/white_city/scaled_latent.json')
    ap.add_argument('--step',type=int,help='Render an intermediate completed step to wind_latest.png')
    a=ap.parse_args();cfg=json.loads(project_path(a.config).read_text())
    run=project_path(cfg['output']);out=run/'figures';out.mkdir(exist_ok=True)
    meta=json.loads((project_path(cfg['geometry'])/'metadata.json').read_text())
    cell=cfg['cell_m']*cfg['coarse_factor'];z,ny,nx=meta['shape_zyx'];ox,oy,_=meta['source_region_origin_xyz_m']
    extent=[ox,ox+nx*cfg['cell_m'],oy,oy+ny*cfg['cell_m']]
    n=a.step if a.step is not None else cfg['wind_steps'];solid=np.load(run/f'temperature/solid_{cell}m_zyx.npy')
    with np.load(run/f'wind/wind{cell}m_{n:03d}.npz') as f:uvw=f['uvw']
    def map_panel(ax,array,title,mask=None,cmap='viridis',vmin=None,vmax=None):
        image=np.ma.masked_where(mask,array) if mask is not None else array
        im=ax.imshow(image,origin='lower',extent=extent,cmap=cmap,vmin=vmin,vmax=vmax)
        ax.set_title(title);ax.set_xlabel('Local x (m)');ax.set_ylabel('Local y (m)');plt.colorbar(im,ax=ax,shrink=.7)
    fig,axs=plt.subplots(1,2,figsize=(13,6),constrained_layout=True)
    for ax,h in zip(axs,[12,44]):
        layer=int(h//cell);speed=np.linalg.norm(uvw[:,layer],axis=0)
        map_panel(ax,speed,f'Wind step {n}: z=[{layer*cell},{(layer+1)*cell}) m; speed m/s',solid[layer])
    name='wind_latest.png' if a.step is not None else 'wind_final.png'
    pending=out/(name+'.partial')
    fig.savefig(pending,dpi=150,format='png');pending.replace(out/name);plt.close(fig)
    rows=json.loads((run/'wind/metrics.json').read_text())['steps']
    fig,ax=plt.subplots(figsize=(9,4));ax.plot([r['step'] for r in rows],[r['fluid_speed_mean'] for r in rows]);ax.set(xlabel='Model step',ylabel='Mean fluid speed (m/s)',title=f'{cfg["scene"]}: surrogate spin-up (no CFD reference)');ax.grid(alpha=.2)
    fig.tight_layout();pending=out/'wind_convergence.png.partial';fig.savefig(pending,dpi=150,format='png');pending.replace(out/'wind_convergence.png');plt.close(fig)
    if (run/'temperature/metrics.json').exists():
        rows=json.loads((run/'temperature/metrics.json').read_text());fig,ax=plt.subplots(figsize=(8,4))
        for mode in ['recursive','one_step','persistence']:
            data=[r for r in rows if r['mode']==mode];ax.plot([r['time_seconds'] for r in data],[r['mae_c'] for r in data],marker='o',label=mode)
        ax.set(xlabel='Controlled forecast time (s)',ylabel='MAE vs adapted solver (C)',title='Temperature transfer on 8 m grid');ax.legend();fig.tight_layout();fig.savefig(out/'temperature_mae.png',dpi=150);plt.close(fig)
    p=run/f'pollution/concentration_{n:03d}.npz'
    if p.exists():
        with np.load(p) as f:c=f['concentration']
        layer=1;fig,ax=plt.subplots(figsize=(8,7))
        map_panel(ax,np.log10(1+c[layer]),f'Assumed tracer source, step {n}: log10(1 + concentration)',solid[layer],cmap='magma')
        fig.tight_layout();fig.savefig(out/'pollution_final.png',dpi=150);plt.close(fig)


if __name__=='__main__':main()
