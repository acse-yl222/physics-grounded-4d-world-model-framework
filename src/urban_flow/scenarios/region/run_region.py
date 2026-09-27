"""Resume the configured full workstation run and finalize the viewer export."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path('/home/yl222/workspace/UrbanWorldModel')
out = root / 'output/region'
out.mkdir(parents=True, exist_ok=True)
with (out / 'run.lock').open('w') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Region is already running.')
    record = {'started': time.strftime('%Y-%m-%d %H:%M:%S'), 'complete': False}
    status = out / 'launch_status.json'
    status.write_text(json.dumps(record, indent=2))
    try:
        subprocess.run([sys.executable, '-u', '-m', 'pipelines.run_scene', 'input/region'], cwd=root, check=True)
        pipeline = json.loads((out / 'pipeline_status.json').read_text())
        if not pipeline.get('complete'):
            raise RuntimeError('One or more configured stages did not complete; see pipeline_status.json.')
        subprocess.run([sys.executable, 'input/region/finalize_scene.py'], cwd=root, check=True)
        record['complete'] = True
    except Exception as exc:
        record['error'] = str(exc)
        raise
    finally:
        record['updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
        status.write_text(json.dumps(record, indent=2))
