"""Overlay current aligned profiles with vector-digitized paper Fig. B.33.

Curve RMSE uses a uniform transverse grid, not PDF vertex density. Experimental
errors use digitized marker positions. Neither is raw experimental validation.
"""
import argparse,csv,json,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .extract_paper_profiles import extract
from .compare_paper_profiles import ordered_profile,errors
from common.export import digest

def run(pdf,profiles,out):
    out.mkdir(parents=True,exist_ok=True)
    paper=extract(pdf); current=json.loads(profiles.read_text())
    (out/'paper_B33_digitized.json').write_text(json.dumps(paper,indent=2)+'\n')
    shutil.copyfile(profiles,out/'computed_profiles.json')
    with (out/'paper_B33_digitized.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['x_over_D','series','y_over_R','deficit_1_minus_U_over_U0'])
        for row in paper['profiles']:
            for name,pts in dict(row['curves'],experimental_markers=row['experimental_markers']).items():
                w.writerows([row['x_over_D'],name,*p] for p in pts)
    fig,axes=plt.subplots(3,2,figsize=(14,11),sharex=True,sharey=True)
    metrics=[];sanity=[]
    colors={'PyTorch SST':'#008d92','OpenFOAM SST':'#d97706','Jensen_1983':'#6d28d9','Bastankhah_PorteAgel_2014':'#348500'}
    for row, ref, axrow in zip(current,paper['profiles'],axes):
        assert row['x_over_D']==ref['x_over_D']
        d=row['x_over_D'];tx=np.asarray(row['y_over_R'])
        sx,sy=ordered_profile(*np.asarray(ref['curves']['kOmegaSST']).T)
        lo=max(-1.5,sx.min(),tx.min());hi=min(1.5,sx.max(),tx.max())
        grid=np.linspace(lo,hi,301);target=np.column_stack([grid,np.interp(grid,sx,sy)])
        for name,v in row['curves'].items():
            x,val=ordered_profile(tx,v)
            metrics.append({'x_over_D':d,'model':name,'vs_paper_SST_uniform_grid':errors(x,val,target),
                            'vs_digitized_experiment':errors(x,val,ref['experimental_markers'])})
        for name,pts in ref['curves'].items():
            px,py=ordered_profile(*np.asarray(pts).T)
            sanity.append({'x_over_D':d,'paper_model':name,'vs_digitized_experiment':errors(px,py,ref['experimental_markers'])})
        for col,ax in enumerate(axrow):
            for name,color,ls in [('kOmegaSST','#1d4ed8','-'),('kEpsilon','#dc2626','--')]:
                xy=np.asarray(ref['curves'][name]);ax.plot(*xy.T,color=color,ls=ls,lw=1.8,label='Paper '+('SST' if name=='kOmegaSST' else 'k-epsilon'))
            xy=np.asarray(ref['experimental_markers']);ax.scatter(*xy.T,s=18,facecolors='none',edgecolors='black',lw=.8,label='Paper experiment (digitized)',zorder=5)
            keys=['PyTorch SST','OpenFOAM SST'] if col==0 else ['Jensen_1983','Bastankhah_PorteAgel_2014']
            for name in keys:
                label={'Jensen_1983':'PyWake Jensen','Bastankhah_PorteAgel_2014':'PyWake Gaussian'}.get(name,name)
                ax.plot(tx,row['curves'][name],color=colors[name],lw=2,ls='-.' if name in ['OpenFOAM SST','Bastankhah_PorteAgel_2014'] else '-',label=label)
            ax.set_title(f'{d}D downstream | '+('Our CFD vs paper' if col==0 else 'PyWake vs paper'))
            ax.set_xlim(-1.5,1.5);ax.set_ylim(-.2,1.05);ax.grid(alpha=.2)
            ax.set_ylabel('Velocity deficit 1 - U/U0')
            if d==1:ax.legend(fontsize=8,loc='upper right')
            if d==5:ax.set_xlabel('Transverse coordinate (y - hub_y) / R')
    fig.suptitle('Comparison with Davidson et al. (2026), Fig. B.33 | U0 = 10 m/s',fontsize=16)
    fig.tight_layout(rect=[0,.055,1,.97])
    fig.text(.02,.032,'PDF vector paths / marker centres; not raw measurements. Current CFD: standard SST; paper Table 14 lists LF18 stabilization.',fontsize=9)
    fig.text(.02,.013,'PyWake: k = 0.04. Gaussian Ct = 0.95 exceeds width-formula range. No parameter fitting performed.',fontsize=9)
    fig.savefig(out/'paper_comparison.png',dpi=160);fig.savefig(out/'paper_comparison.pdf');plt.close(fig)
    result={'source_figure':'PDF page 24, Fig. B.33','pdf_sha256':digest(pdf),'current_profiles_sha256':digest(profiles),
            'digitization':paper['uncertainty'],'curve_metric':'RMSE of deficit on 301 equally spaced points in common y/R range [-1.5,1.5]; linear interpolation; no extrapolation.',
            'experimental_metric':'RMSE at PDF marker centres; not raw experimental uncertainty.',
            'limitations':['Standard SST in current CFD; Table 14 paper SST lists LF18 limiter.','Mesh, numerics, turbulence inlet assumptions remain relevant; not exact reproduction.','Digitization is not independent experimental validation.'],
            'comparisons':metrics,'paper_curve_digitization_crosscheck':sanity,
            'paper_reported_experimental_RMSE':{'kOmegaSST':[.117,.133,.0848],'kEpsilon':[.138,.132,.0675]}}
    (out/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'metrics.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['x_over_D','model','RMSE_vs_paper_SST','RMSE_vs_digitized_experiment'])
        for r in metrics:w.writerow([r['x_over_D'],r['model'],r['vs_paper_SST_uniform_grid']['rms'],r['vs_digitized_experiment']['rms']])
    for r in metrics:print(r['x_over_D'],r['model'],round(r['vs_paper_SST_uniform_grid']['rms'],4),round(r['vs_digitized_experiment']['rms'],4))
    print('Digitization crosscheck:',[(r['x_over_D'],r['paper_model'],round(r['vs_digitized_experiment']['rms'],4)) for r in sanity])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('profiles',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.pdf,a.profiles,a.out)
