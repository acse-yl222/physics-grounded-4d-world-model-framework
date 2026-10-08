"""Compare explicitly selected converged OpenFOAM cases with paper Fig B.33.

Each case keeps its own actual D for both station placement and y/R. Geometry
hypotheses are labelled and are never treated as author-confirmed settings.
"""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common.export import digest
from .compare_paper_profiles import ordered_profile,errors

def render(paper,runs,out):
    out.mkdir(parents=True,exist_ok=False)
    ref=json.loads(paper.read_text());fig,axes=plt.subplots(3,1,figsize=(10,11),sharex=True)
    results=[];profiles=[]
    for ax,row in zip(axes,ref['profiles']):
        for key,color in [('kOmegaSST','blue'),('kEpsilon','red')]:
            a=np.asarray(row['curves'][key]);ax.plot(*a.T,color=color,lw=1.7,ls='--',label='Paper '+key)
        a=np.asarray(row['experimental_markers']);ax.scatter(*a.T,s=16,facecolors='none',edgecolors='black',label='Digitized experiment')
        ax.set_title(f"{row['x_over_D']}D downstream");ax.set_ylabel('Deficit 1 - U/U0');ax.grid(alpha=.2);ax.set_xlim(-1.5,1.5)
    palette=['#008d92','#d97706','#6d28d9','#348500','#994455']
    for index,run in enumerate(runs):
        cfg=json.loads((run/'configuration.json').read_text());status=json.loads((run/'reference_summary.json').read_text())
        if not status['numerical_convergence_verified']:raise ValueError(f'Unconverged case: {run}')
        model=cfg['turbulence_model'];diam=cfg['rotor_diameter_m']
        hypothesis='geometry_hypothesis' in cfg.get('diagnostic',{})
        label=f'{model}, D={diam:g} m'+(' [radius hypothesis]' if hypothesis else '')
        for ax,row in zip(axes,ref['profiles']):
            dist=row['x_over_D'];data=json.loads((run/f'data/wake_{dist}d.json').read_text());pos=np.asarray(data['positions'])
            if not np.allclose(pos[:,0],cfg['hub_xyz_m'][0]+dist*diam):raise ValueError('Incorrect downstream station')
            if not np.allclose(pos[:,2],cfg['hub_xyz_m'][2]):raise ValueError('Incorrect sample height')
            x,v=ordered_profile((pos[:,1]-cfg['hub_xyz_m'][1])/(diam/2),data['values'])
            key='kEpsilon' if model=='kEpsilon' else 'kOmegaSST';px,pv=ordered_profile(*np.asarray(row['curves'][key]).T)
            grid=np.linspace(max(x.min(),px.min(),-1.5),min(x.max(),px.max(),1.5),301)
            target=np.column_stack([grid,np.interp(grid,px,pv)])
            results.append({'run_id':run.name,'label':label,'x_over_D':dist,'paper_model':key,'uniform_grid_RMSE':errors(x,v,target),
                'experimental_marker_RMSE':errors(x,v,row['experimental_markers']),'configuration_sha256':digest(run/'configuration.json')})
            profiles.append({'run_id':run.name,'label':label,'x_over_D':dist,'y_over_R':x.tolist(),'deficit':v.tolist()})
            ax.plot(x,v,lw=1.8,color=palette[index % len(palette)],label=label)
    axes[0].legend(fontsize=8,ncol=2);axes[-1].set_xlabel('(y - hub_y) / R of each case')
    fig.suptitle('OpenFOAM reproduction audit | Paper Fig. B.33',fontsize=15)
    fig.tight_layout(rect=[0,.04,1,.97]);fig.text(.02,.015,'301 uniform y/R samples for curve RMSE. Hypotheses remain unconfirmed; digitized experiments are not raw data.',fontsize=9)
    fig.savefig(out/'openfoam_paper_comparison.png',dpi=150);plt.close(fig)
    payload={'paper_sha256':digest(paper),'raw_experiment':False,'reproduction_proven':False,'results':results,'profiles':profiles,'paper':ref}
    (out/'comparison.json').write_text(json.dumps(payload,indent=2)+'\n')
    return results
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--paper',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('runs',type=Path,nargs='+');a=p.parse_args();print(json.dumps(render(a.paper,a.runs,a.out),indent=2))
