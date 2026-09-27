"""Run confirmed solar and flood experiments sequentially and record status."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import json
from pathlib import Path
import subprocess
import sys

ROOT=repo_root()
sys.path.insert(0,str(ROOT))
from common.pipeline.scene_scaled_latent import save_json


def main():
    out=ROOT/'output/white_city/physics'
    completed=[]
    for stage in ('solar','flood'):
        status=out/f'{stage}_experimental/status.json'
        if not status.exists() or not json.loads(status.read_text()).get('complete'):
            save_json(out/'surface_workflow_status.json',{'complete':False,'stage':stage,'completed':completed})
            with (out/f'{stage}_experimental.log').open('a') as log:
                result=subprocess.run([sys.executable,'-u',str(ROOT/'src/common/pipeline/scene_surface_physics.py'),'--stage',stage],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:
                save_json(out/'surface_workflow_status.json',{'complete':False,'failed_stage':stage,'returncode':result.returncode,'completed':completed})
                raise SystemExit(result.returncode)
        completed.append(stage)
    save_json(out/'surface_workflow_status.json',{'complete':True,'completed':completed,'experimental_assumptions':True})


if __name__=='__main__':main()
