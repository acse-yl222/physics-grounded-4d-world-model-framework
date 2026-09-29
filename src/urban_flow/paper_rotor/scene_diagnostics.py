"""Read physical-time farm loads; keep the final PIMPLE evaluation per rotor/time."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from common.export import write


def loads(log, rho, expected_rotors=23):
    rows=re.findall(r'^FARM_ROTOR\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$',log,re.M)
    if not rows:raise ValueError('No physical-time rotor diagnostics')
    data=np.asarray(rows,dtype=float)
    if not np.isfinite(data).all():raise ValueError('Nonfinite rotor load')
    if np.any(np.diff(data[:,1])<0):raise ValueError('Physical time moved backwards')
    by_time={}
    for identity,t,speed,force,error in data:
        if int(identity)!=identity or not 0<=identity<expected_rotors or error<0:
            raise ValueError('Invalid rotor identity or force error')
        by_time.setdefault(float(t),{})[int(identity)]=(float(speed),float(force),float(error*rho))
    if any(set(group)!=set(range(expected_rotors)) for group in by_time.values()):
        raise ValueError('Incomplete rotor group at a physical timestep')
    times=list(by_time)
    return {'times':times,'disk_velocity_m_s':[[by_time[t][i][0] for i in range(expected_rotors)] for t in times],
            'thrust_N':[[by_time[t][i][1] for i in range(expected_rotors)] for t in times],
            'max_integrated_force_error_N':float(data[:,4].max()*rho),
            'time_semantics':'physical seconds; final PIMPLE source evaluation at each time',
            'rotor_count':expected_rotors}


def analyze(case):
    case=Path(case)
    config=json.loads((case/'configuration.json').read_text())
    if config.get('time_semantics')!='physical seconds':raise ValueError('Not a transient case')
    if json.loads((case/'status.json').read_text())['state']!='transient_finished':
        raise ValueError('Transient solver has not finished successfully')
    log=(case/'log.pimpleFoam').read_text()
    if not re.search(r'\nEnd\s*(?:Finalising parallel run\s*)?$',log):raise ValueError('Missing clean solver termination')
    result=loads(log,config['rho_kg_m3'])
    if not np.isclose(result['times'][-1],config['target_seconds'],rtol=0,atol=1e-7):
        raise ValueError('Requested physical end time was not reached')
    courant=np.asarray(re.findall(r'Courant Number mean: (\S+) max: (\S+)',log),dtype=float)
    continuity=np.asarray(re.findall(r'continuity errors : sum local = (\S+), global = (\S+), cumulative = (\S+)',log),dtype=float)
    if courant.size==0 or continuity.size==0 or not np.isfinite(courant).all() or not np.isfinite(continuity).all():
        raise ValueError('Missing or nonfinite mass/stability diagnostics')
    result['max_courant_number']=float(courant[:,1].max())
    result['final_local_continuity_error']=float(continuity[-1,0])
    result['final_cumulative_continuity_error']=float(continuity[-1,2])
    force_scale=max(1.,float(np.max(np.abs(result['thrust_N']))))
    result['numerical_smoke_checks_passed']=bool(
        result['max_courant_number']<=.55 and abs(continuity[-1,0])<1e-5
        and result['max_integrated_force_error_N']<1e-8*force_scale)
    result['experimental_accuracy_validated']=False
    write(case/'physical_rotor_history.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('times','disk_velocity_m_s','thrust_N')},indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('case',type=Path)
    analyze(parser.parse_args().case)
