"""Measure finite-window load and wake stationarity; never equate steps with seconds."""
import argparse
import json
from pathlib import Path
import numpy as np
from common.export import write


def audit(run, window_s=1.2, profile_tolerance=1e-3, thrust_tolerance=1e-3):
    run=Path(run)
    history=json.loads((run/'history.json').read_text())
    if not history:raise ValueError('Empty history')
    end=history[-1]['time_s'];start=end-window_s
    rows=[r for r in history if r['time_s']>=start]
    thrust=np.array([r['thrust_N'] for r in rows])
    if not np.isfinite(thrust).all():raise ValueError('Nonfinite load history')
    snapshots=[]
    for d in sorted((run/'diagnostics').glob('step_*')):
        f=d/'data/wake_1d.json'
        if f.exists():
            t=json.loads(f.read_text())['time_s']
            if start<=t<=end:snapshots.append((t,d))
    snapshots.sort()
    changes={}
    for distance in (1,3,5):
        arrays=[];positions=None
        for _,d in snapshots:
            data=json.loads((d/f'data/wake_{distance}d.json').read_text())
            pos=np.array(data['positions'])
            if positions is not None and not np.allclose(pos,positions,atol=1e-12,rtol=0):
                raise ValueError('Sampling coordinates changed')
            positions=pos;arrays.append(data['values'])
        if len(arrays)>=2:
            a=np.array(arrays)
            if not np.isfinite(a).all():raise ValueError('Nonfinite profiles')
            changes[str(distance)]={'max_pointwise_range':float(np.ptp(a,axis=0).max()),
                                    'endpoint_rms':float(np.sqrt(np.mean((a[-1]-a[0])**2)))}
    coverage=snapshots[-1][0]-snapshots[0][0] if len(snapshots)>1 else 0
    load_range=float(np.ptp(thrust)/max(abs(thrust.mean()),1e-12))
    passed=(coverage>=.9*window_s and len(changes)==3 and load_range<thrust_tolerance
            and all(v['max_pointwise_range']<profile_tolerance for v in changes.values()))
    return {'end_time_s':end,'requested_window_s':window_s,'sampled_window_s':coverage,
            'thrust_range_over_mean':load_range,'profiles':changes,
            'thresholds':{'profile_pointwise_deficit_range':profile_tolerance,'relative_thrust_range':thrust_tolerance},
            'finite_window_passed':bool(passed),'physical_accuracy_validated':False,
            'scope':'Loads and 1D/3D/5D wake profiles only; not full-domain stationarity or grid independence.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--window',type=float,default=1.2);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=audit(a.run,a.window);write(a.output,result);print(json.dumps(result,indent=2))
