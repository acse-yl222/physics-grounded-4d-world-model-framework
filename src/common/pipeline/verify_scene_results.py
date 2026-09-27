"""Check completed scene output shapes, finite values, masks and frame counts."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import argparse
import json
from pathlib import Path
import sys

import numpy as np

if __package__ in (None,''):
    sys.path.insert(0,str(repo_root()))
from common.pipeline.paths import project_path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',default='configs/white_city/scaled_latent.json')
    args=ap.parse_args();cfg=json.loads(project_path(args.config).read_text())
    run=project_path(cfg['output']);cell=cfg['cell_m']*cfg['coarse_factor'];n=cfg['wind_steps']
    status=json.loads((run/'workflow_status.json').read_text())
    assert status['complete'], 'Downstream stages not complete'
    mask=np.load(run/f'temperature/solid_{cell}m_zyx.npy')
    for k in range(n+1):
        with np.load(run/f'wind/wind{cell}m_{k:03d}.npz') as f:
            a=f['uvw'];assert a.shape==(3,*mask.shape) and np.isfinite(a).all()
            assert not np.any(a[:,mask])
        if k:
            with np.load(run/f'wind/latent/{k:04d}.npz') as f:
                a=f['state'];assert a.shape==(1,4,*mask.shape) and np.isfinite(a).all()
            with np.load(run/f'pollution/concentration_{k:03d}.npz') as f:
                a=f['concentration'];assert a.shape==mask.shape and np.isfinite(a).all()
                assert a.min()>=0 and not np.any(a[mask])
        if k%20==0:print(f'Checked frames through {k}/{n}',flush=True)
    fields=list((run/'temperature').glob('reference_*.npy'))+list((run/'temperature').glob('recursive_*.npy'))+list((run/'temperature').glob('one_step_*.npy'))
    assert len(fields)==18
    for path in fields:
        a=np.load(path);assert a.shape==mask.shape and np.isfinite(a).all()
    a=np.load(run/f'wind/velocity_final_{cfg["cell_m"]}m_raw_czyx_float16.npy',mmap_mode='r')
    fine=np.load(run/f'wind/solid_{cfg["cell_m"]}m_zyx.npy',mmap_mode='r')
    assert a.shape==(3,*fine.shape)
    for c in range(3):
        for z in range(fine.shape[0]):
            assert np.isfinite(a[c,z]).all() and not np.any(a[c,z][fine[z]])
    figures=['wind_final.png','wind_convergence.png','temperature_mae.png','pollution_final.png']
    for name in figures:assert (run/'figures'/name).stat().st_size>0
    report={'all_pass':True,'wind_frames':n+1,'latent_checkpoints':n,'pollution_frames':n,
            'temperature_arrays':len(fields),'final_wind_shape_czyx':list(a.shape),
            'fine_cell_m':cfg['cell_m'],'coarse_cell_m':cell,'figures':figures,
            'limits':'File integrity and numerical sanity checks only; not physical accuracy validation.',
            'pending':status.get('pending',{})}
    (run/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
