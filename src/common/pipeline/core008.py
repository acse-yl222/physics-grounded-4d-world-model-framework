"""Configured core008 solar simulation and plotting entry point."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(repo_root()))
from common.pipeline.paths import ROOT, project_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/core008/solar.json')
    parser.add_argument('--stage', choices=('run', 'plot', 'all'), default='run')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    config = json.loads(project_path(args.config).read_text())
    output = project_path(config['output'])
    commands = {
        'run': [sys.executable, str(ROOT / 'src/urban_flow/physics/run_core008_solar.py'),
                '--out', str(output), '--dates', ','.join(config['dates']),
                '--minutes', str(config['minutes']), '--hourly_1m', str(config['hourly_1m'])],
        'plot': [sys.executable, str(ROOT / 'src/urban_flow/physics/plot_core008_solar.py'), '--out', str(output)],
    }
    stages = ('run', 'plot') if args.stage == 'all' else (args.stage,)
    if not args.dry_run:
        missing = [str(project_path(p)) for p in config['required_inputs'] if not project_path(p).is_file()]
        if missing:
            parser.error('Missing prepared inputs: ' + ', '.join(missing))
    for stage in stages:
        print(shlex.join(commands[stage]), flush=True)
        if not args.dry_run:
            subprocess.run(commands[stage], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
