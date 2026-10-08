"""Compare matched physical wake stations; retain solver/model distinctions."""
import argparse,json,re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common.export import write,digest
from .audit_alignment_stationarity import audit

KEYS=('inlet_m_s','rotor_diameter_m','inner_diameter_m','rotor_thickness_m','ct',
      'rho_kg_m3','sigma_m','cutoff_sigma','domain_xyz_m','hub_xyz_m','mesh_counts_xyz',
      'kinematic_viscosity_m2_s','turbulence_intensity','turbulence_length_m')

def compare(torch_run,foam_run,pywake_run,out,foam_samples=None):
    torch_run,foam_run,pywake_run,out=map(Path,(torch_run,foam_run,pywake_run,out))
    tc=json.loads((torch_run/'configuration.json').read_text());fc=json.loads((foam_run/'configuration.json').read_text())
    for key in KEYS:
        if tc[key]!=fc[key]:raise ValueError(f'CFD parameter mismatch: {key}')
    if tc['model']!='kOmegaSST' or fc['turbulence_model']!='kOmegaSST':raise ValueError('SST required')
    if json.loads((torch_run/'status.json').read_text())['state']!='diagnostic_finished':raise ValueError('PyTorch still running')
    stationarity=audit(torch_run,window_s=2.4)
    if not stationarity['finite_window_passed']:raise ValueError('PyTorch wake stationarity not demonstrated')
    full_state=json.loads((torch_run/'full_state_stationarity.json').read_text())
    if not full_state['finite_window_passed'] or full_state['end_sha256']!=digest(torch_run/'checkpoint.pt'):
        raise ValueError('Full-state stationarity missing or checkpoint changed')
    fs=json.loads((foam_run/'reference_summary.json').read_text())
    if not fs['numerical_convergence_verified']:raise ValueError('OpenFOAM convergence not demonstrated')
    if fc.get('momentum_advection')!='upwind' or fc.get('turbulence_advection','upwind')!='upwind':raise ValueError('Matched upwind reference required')
    if foam_samples is None:raise ValueError('Common trilinear OpenFOAM samples required')
    foam_samples=Path(foam_samples)
    sampling=json.loads((foam_samples/'provenance.json').read_text())
    if sampling['configuration_sha256']!=digest(foam_run/'configuration.json') or sampling['iteration']!=fs['iterations']:
        raise ValueError('OpenFOAM sampling provenance mismatch')
    pc=json.loads((pywake_run/'configuration.json').read_text())
    for k in ['inlet_m_s','rotor_diameter_m','ct','turbulence_intensity']:
        if pc[k]!=tc[k]:raise ValueError(f'PyWake shared-input mismatch: {k}')
    profiles=json.loads((pywake_run/'profiles.json').read_text());out.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(1,3,figsize=(15,4),sharey=True);metrics=[];data=[]
    R=tc['rotor_diameter_m']/2;hy=tc['hub_xyz_m'][1]
    for ax,d in zip(axes,(1,3,5)):
        tr=json.loads((torch_run/f'data/wake_{d}d.json').read_text());fr=json.loads((foam_samples/f'wake_{d}d.json').read_text())
        for profile in (tr,fr):
            coordinates=np.asarray(profile['positions'])
            expected_x=tc['hub_xyz_m'][0]+d*tc['rotor_diameter_m']
            if not np.allclose(coordinates[:,0],expected_x,atol=1e-8,rtol=0):raise ValueError('Wrong downstream station')
            if not np.allclose(coordinates[:,2],tc['hub_xyz_m'][2],atol=1e-8,rtol=0):raise ValueError('Wrong sampling height')
        tx=(np.array(tr['positions'])[:,1]-hy)/R;fx=(np.array(fr['positions'])[:,1]-hy)/R
        x=np.linspace(-3,3,121)
        def sample(xx,yy):
            order=np.argsort(xx);xx=np.asarray(xx)[order];yy=np.asarray(yy)[order]
            if xx[0]>x[0]+1e-9 or xx[-1]<x[-1]-1e-9:raise ValueError('Extrapolation required')
            if not np.isfinite(yy).all():raise ValueError('Nonfinite profile')
            return np.interp(x,xx,yy)
        curves={'OpenFOAM SST':sample(fx,fr['values']),'PyTorch SST':sample(tx,tr['values'])}
        for model in ('Jensen_1983','Bastankhah_PorteAgel_2014'):
            row=next(r for r in profiles if r['model']==model and r['ct']==.95 and r['expansion_k']==.04 and r['x_over_D']==d)
            curves[model]=sample(row['y_over_R'],row['deficit'])
        for label,y in curves.items():
            ax.plot(x,y,label=label)
            delta=y-curves['OpenFOAM SST']
            metrics.append({'x_over_D':d,'model':label,'rms_vs_openfoam':float(np.sqrt(np.mean(delta**2))),'max_absolute_vs_openfoam':float(abs(delta).max())})
        data.append({'x_over_D':d,'y_over_R':x.tolist(),'curves':{k:v.tolist() for k,v in curves.items()}})
        ax.set(title=f'{d}D',xlabel='(y - hub_y) / R');ax.grid(alpha=.25)
    axes[0].set_ylabel('Velocity deficit 1 - Ux / Uin');axes[-1].legend(fontsize=7)
    fig.suptitle('Matched single-rotor inputs; PyWake has no tunnel walls or annular forcing\nGaussian Ct=0.95 is outside its width-formula range; k=0.04 is untuned; not physical validation')
    fig.tight_layout();fig.savefig(out/'three_way_profiles.png',dpi=180);plt.close(fig)
    write(out/'common_profiles.json',data)
    history=json.loads((torch_run/'history.json').read_text())
    torch_thrust=history[-1]['thrust_N'];foam_thrust=fs['last_thrust_N']
    foam_clocks=re.findall(r'ClockTime = ([0-9.]+) s',(foam_run/'log.simpleFoam').read_text())
    timing={'torch_wall_seconds':json.loads((torch_run/'status.json').read_text())['wall_seconds'],
            'foam_solver_clock_seconds':float(foam_clocks[-1]) if foam_clocks else None,
            'interpretation':'GPU transient versus CPU steady solver; different stopping criteria and workloads, not a backend speed benchmark.'}
    write(out/'comparison.json',{'metrics':metrics,'torch_stationarity':stationarity,'torch_full_state_stationarity':full_state,'openfoam_convergence':fs,
      'loads':{'torch_thrust_N':torch_thrust,'openfoam_thrust_N':foam_thrust,'relative_thrust_difference':(torch_thrust-foam_thrust)/foam_thrust},'timing':timing,
      'physical_accuracy_validated':False,'parameter_keys_verified':KEYS,'common_sampling':sampling,
      'input_hashes':{str(p):digest(p) for p in [torch_run/'configuration.json',foam_run/'configuration.json',pywake_run/'profiles.json']},
      'remaining_method_differences':['MAC versus collocated finite volumes','Transient projection versus steady SIMPLE','Pressure and velocity interpolation','Wall function implementation details','PyWake open flow versus CFD wind tunnel; no annular hole or RANS closure in PyWake','PyWake 2.6.20 Gaussian width uses min(Ct,0.899); Ct=.95 is extrapolative; 1D k=.04 amplitude is clipped']})
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['torch_run','foam_run','pywake_run','out']:p.add_argument(name,type=Path)
    p.add_argument('--foam-samples',type=Path,required=True)
    a=p.parse_args();print(compare(a.torch_run,a.foam_run,a.pywake_run,a.out,a.foam_samples))
