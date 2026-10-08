"""Plot the complete PyWake design without treating it as CFD validation."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot(run,out):
    run,out=Path(run),Path(out);out.mkdir(parents=True,exist_ok=True)
    profiles=json.loads((run/'profiles.json').read_text());pairs=json.loads((run/'two_turbines.json').read_text())
    models=['Jensen_1983','Bastankhah_PorteAgel_2014'];names=['Jensen','Bastankhah Gaussian']
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    for row,(model,name) in enumerate(zip(models,names)):
        for col,(key,values) in enumerate([('x_over_D',[1,3,5,7,10]),('expansion_k',[.02,.04,.075]),('ct',[.6,.75,.95])]):
            for value in values:
                filters={'x_over_D':5,'expansion_k':.04,'ct':.95};filters[key]=value
                r=next(r for r in profiles if r['model']==model and all(r[k]==v for k,v in filters.items()))
                axes[row,col].plot(r['y_over_R'],r['deficit'],label=f'{key}={value}')
            axes[row,col].set(title=name,xlabel='y/R',ylabel='1 - U/Uin');axes[row,col].legend(fontsize=8);axes[row,col].grid(alpha=.2)
    fig.suptitle('PyWake single-rotor experiments | Uin=10 m/s, D=0.4647 m\nFree-flow engineering models; near-wake curves diagnostic only; no physical validation')
    fig.savefig(out/'pywake_single_rotor.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for ax,model,name in zip(axes,models,names):
        for offset in (0,.5,1):
            rows=sorted([r for r in pairs if r['model']==model and r['offset_D']==offset and r['quadrature_resolution']==81],key=lambda r:r['separation_D'])
            ax.plot([r['separation_D'] for r in rows],[r['downstream_m_s'] for r in rows],'o-',label=f'Offset {offset}D')
        ax.set(title=name,xlabel='Downstream separation / D',ylabel='Downstream rotor-average wind (m/s)',ylim=(0,10.5));ax.legend();ax.grid(alpha=.2)
    fig.suptitle('Two-turbine experiments | Ct=0.95, expansion k=0.04\nArea sampling; no power curve or electrical generation estimate')
    fig.savefig(out/'pywake_two_turbines.png',dpi=160);plt.close(fig)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('out',type=Path);a=p.parse_args();plot(a.run,a.out)
