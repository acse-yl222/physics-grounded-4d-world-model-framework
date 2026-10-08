"""Temporal diagnostics for completed or ongoing farm runs; no accuracy claim."""
import argparse,json
from pathlib import Path
import numpy as np
from common.export import write


def analyze(root,window_s=100.):
    root=Path(root)
    history=json.loads((root/'history.json').read_text())
    end=history[-1]['time_s'];start=end-window_s
    window=[r for r in history if r['time_s']>=start-1e-8]
    sufficient=end>=window_s and len(window)>1 and abs(window[0]['time_s']-start)<1e-7
    bounds={}
    for name in ('u','v','w','k','epsilon'):
        changes=[r.get('full_domain_change_since_previous_sample',{}).get(name) for r in window[1:]]
        changes=[x for x in changes if x is not None]
        bounds[name]=dict(cumulative_rms_change_bound=sum(x['rms_change'] for x in changes),
                          cumulative_relative_change_indicator=sum(x['relative_l2_change'] for x in changes))
    forces=np.array([[t['thrust_N'] for t in r['rotors']] for r in window])
    force_range=np.ptp(forces,axis=0)/np.maximum(forces.mean(axis=0),1.)
    thresholds=dict(window_s=window_s,velocity_cumulative_rms_bound_m_s=.05,turbulence_cumulative_relative_indicator=.02,rotor_thrust_relative_range=.01)
    has_changes=all(all(name in r.get('full_domain_change_since_previous_sample',{}) for name in ('u','v','w','k','epsilon')) for r in window[1:])
    passed=bool(sufficient and has_changes and all(bounds[k]['cumulative_rms_change_bound']<=.05 for k in ('u','v','w')) and all(bounds[k]['cumulative_relative_change_indicator']<=.02 for k in ('k','epsilon')) and float(force_range.max())<=.01)
    result=dict(run_id=root.name,window_start_s=window[0]['time_s'],window_end_s=end,complete_window=sufficient,full_domain_change_data_present=has_changes,thresholds=thresholds,full_domain_change=bounds,maximum_rotor_thrust_relative_range=float(force_range.max()),per_rotor_thrust_relative_range=force_range.tolist(),finite_window_stationarity_screen_passed=passed,experimental_accuracy_validated=False,grid_independence_verified=False,interpretation='Sum of consecutive full-domain RMS changes bounds endpoint RMS change; relative k/epsilon sums are indicators with changing denominators. These explicit engineering thresholds are not paper convergence criteria. Passing is finite-window stationarity only, not asymptotic steady state or accuracy.')
    # These are ideal actuator-disc T*Ud proxies, NOT electrical power or
    # exact discretized forcing work after face normalization.
    last=history[-1]['rotors'];result['final_ideal_T_times_Ud_proxy_W']=sum(t['thrust_N']*t['disc_speed_m_s'] for t in last)
    result['power_interpretation']='Ideal thrust times disc-speed proxy only; no generator, controller or electrical-power model.'
    if len(window)>1:
        indices=[history.index(window[0]),len(history)-1]
        arrays=[np.load(root/f'data/frame-{i:04d}.npy')[0,0] for i in indices]
        valid=np.isfinite(arrays[0])&np.isfinite(arrays[1]);delta=arrays[1][valid]-arrays[0][valid]
        result['slice_endpoint_rms_change_m_s']=float(np.sqrt(np.mean(delta.astype(float)**2)))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--window',type=float,default=100.);a=p.parse_args();result=analyze(a.root,a.window);write(a.root/'stationarity_audit.json',result);print(json.dumps(result,indent=2))
