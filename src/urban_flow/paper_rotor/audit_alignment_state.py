"""Compare saved full-state checkpoints without modifying the solver state."""
import argparse,json,math
from pathlib import Path
import torch
from common.export import write,digest

def audit(start,end,criteria,inlet):
    torch.set_num_threads(4)
    a=torch.load(start,map_location='cpu',weights_only=True);b=torch.load(end,map_location='cpu',weights_only=True)
    if a.get('model')!=b.get('model') or len(a['faces'])!=3 or len(b['faces'])!=3:
        raise ValueError('Checkpoint model or face count mismatch')
    c=json.loads(Path(criteria).read_text());delta=b['time_s']-a['time_s']
    if not math.isfinite(delta) or delta<=0:raise ValueError('Invalid checkpoint time interval')
    metrics={}
    for name,u,v in [(f'velocity_{i}',u,v) for i,(u,v) in enumerate(zip(a['faces'],b['faces']))]+[(k,a[k],b[k]) for k in ['k','omega']]:
        if u.shape!=v.shape or not torch.isfinite(u).all() or not torch.isfinite(v).all():raise ValueError('Invalid state')
        diff=(v-u).square().mean().sqrt().item()
        norm=inlet if name.startswith('velocity') else max(v.square().mean().sqrt().item(),1e-30)
        metrics[name]=diff/norm
    passed=delta>=c['min_interval_s'] and all(v<(c['velocity_rms_over_inlet_max'] if k.startswith('velocity') else c['turbulence_relative_l2_max']) for k,v in metrics.items())
    return {'interval_s':delta,'normalized_l2_changes':metrics,'criteria':c,'finite_window_passed':passed,
            'start_sha256':digest(start),'end_sha256':digest(end),'experimental_accuracy_validated':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();r=a.run
    cfg=json.loads((r/'configuration.json').read_text());result=audit(r/'stationarity_start.pt',r/'checkpoint.pt',r/'full_state_stationarity_criteria.json',cfg['inlet_m_s']);write(r/'full_state_stationarity.json',result);print(json.dumps(result,indent=2))
