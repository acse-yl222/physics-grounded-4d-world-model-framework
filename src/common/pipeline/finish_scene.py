"""Wait for an existing wind-temperature process, then run downstream stages."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

if __package__ in (None,''):
    sys.path.insert(0,str(repo_root()))
from common.pipeline.paths import ROOT,project_path
from common.pipeline.scene_scaled_latent import save_json


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--pid',type=int,required=True)
    ap.add_argument('--config',default='configs/white_city/scaled_latent.json');a=ap.parse_args()
    cfg=json.loads(project_path(a.config).read_text());out=project_path(cfg['output'])
    start=time.monotonic()
    while time.monotonic()-start<24*3600:
        state=out/'status.json'
        if state.exists() and json.loads(state.read_text()).get('stage')=='wind_temperature_complete':break
        try:
            os.kill(a.pid,0)
            proc=Path(f'/proc/{a.pid}/status')
            if proc.exists() and any(line.startswith('State:') and 'Z' in line for line in proc.read_text().splitlines()):
                raise ProcessLookupError()
        except ProcessLookupError:
            save_json(out/'workflow_status.json',{'complete':False,'stage':'upstream_failed','detail':'Check run.log; completed wind checkpoints may be resumed.'})
            raise RuntimeError('Upstream process stopped before wind/temperature completion. Check run.log.')
        time.sleep(10)
    else:raise TimeoutError('Wind/temperature did not complete within 24 hours')
    for script in ['scene_pollution.py','plot_scene.py']:
        save_json(out/'workflow_status.json',{'stage':script,'complete':False})
        try:
            subprocess.run([sys.executable,str(ROOT/'pipelines'/script),'--config',a.config],cwd=ROOT,check=True)
        except subprocess.CalledProcessError as error:
            save_json(out/'workflow_status.json',{'complete':False,'stage':script,'failed':True,'returncode':error.returncode})
            raise
    save_json(out/'workflow_status.json',{'complete':True,'completed':['wind','controlled_temperature','pollution','figures'],
        'pending':{'solar':'GLB compass orientation and geographic location need confirmation',
                   'flood':'No verified White City terrain/vertical datum supplied',
                   'temperature3d_solar':'Depends on scene solar/land-surface inputs'}})
    print('Wind, controlled temperature, tracer and figures complete.',flush=True)


if __name__=='__main__':main()
