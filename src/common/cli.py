"""Unified command entrypoint for scene storage and protocol operations."""
import argparse
import json
from pathlib import Path
import sys
from jsonschema.exceptions import ValidationError
from .contract import validate
from .runs import promote, promote_bundle
from .storage import Storage


def main(argv=None):
    parser = argparse.ArgumentParser(prog='p4d')
    parser.add_argument('--root', type=Path, help='Scene workspace (or P4D_ROOT/UWM_ROOT)')
    commands = parser.add_subparsers(dest='command', required=True)
    paths = commands.add_parser('paths', help='Show resolved scene paths without creating data')
    paths.add_argument('scene')
    commands.add_parser('scenes', help='List registered scene metadata')
    check = commands.add_parser('validate', help='Validate a run and its data assets')
    check.add_argument('manifest', type=Path)
    keep = commands.add_parser('retain', help='Copy a complete trial into immutable scene runs')
    keep.add_argument('source', type=Path)
    server = commands.add_parser('serve', help='Serve the unified viewer and configured scene assets')
    server.add_argument('--host', default='127.0.0.1')
    server.add_argument('--port', type=int, default=8769)
    run = commands.add_parser('run', help='Run a scene pipeline in an isolated cache workspace')
    run.add_argument('--python', default=sys.executable, help='Python environment with the solver dependencies')
    run.add_argument('scene')
    run.add_argument('options', nargs=argparse.REMAINDER)
    experiment = commands.add_parser('experiment', help='Run a migrated flow experiment in cache')
    experiment.add_argument('--python', default=sys.executable)
    experiment.add_argument('--run-id')
    experiment.add_argument('simulation', choices=['actuator_lab','windfarm_2m','windfarm_crop','windfarm_neural'])
    experiment.add_argument('options', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate':
            print(f'VALID: {validate(args.manifest)} layers')
            return 0
        storage = Storage.load(args.root)
        if args.command == 'paths':
            print(json.dumps(storage.describe(args.scene), indent=2))
        elif args.command == 'scenes':
            scenes = []
            for path in sorted((storage.root / 'project').glob('*/project.json')):
                data = json.loads(path.read_text())
                scenes.append({'scene_id': data['scene_id'], 'title': data['title']})
            print(json.dumps(scenes, indent=2))
        elif args.command == 'run':
            import os, subprocess
            env = dict(os.environ, P4D_ROOT=str(storage.root), UWM_ROOT=str(storage.root))
            env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get('PYTHONPATH', '')
            return subprocess.call([args.python, '-m', 'common.pipeline.run_scene', args.scene, *args.options], cwd=storage.root, env=env)
        elif args.command == 'experiment':
            import os, subprocess
            env=dict(os.environ,P4D_ROOT=str(storage.root),UWM_ROOT=str(storage.root))
            env['PYTHONPATH']=str(Path(__file__).resolve().parents[1])+os.pathsep+env.get('PYTHONPATH','')
            if args.run_id:env['UWM_RUN_ID']=args.run_id
            return subprocess.call([args.python,'-m',f'urban_flow.scenarios.{args.simulation}.run',*args.options],cwd=storage.root,env=env)
        elif args.command == 'serve':
            from .server import serve
            serve(storage,args.host,args.port)
        else:
            print(promote_bundle(storage,args.source) if (args.source/'bundle.json').is_file() else promote(storage,args.source))
    except (ValueError, OSError, ValidationError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
