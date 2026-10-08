"""python -m urban_planning: prepare, inspect, run JSON tools and pilot baselines."""
import argparse
import json

from .benchmark import benchmark
from .prepare import prepare
from .tools import CATALOG, call_tool, start_session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--config', required=True)
    sub.add_parser('catalog')
    p = sub.add_parser('start'); p.add_argument('--task', required=True); p.add_argument('--session', required=True)
    p.add_argument('--phase', choices=['initial', 'changed'], default='initial'); p.add_argument('--actor', required=True)
    p = sub.add_parser('call'); p.add_argument('--task', required=True); p.add_argument('--session', required=True)
    p.add_argument('--tool', choices=[x['name'] for x in CATALOG], required=True); p.add_argument('--arguments', default='{}')
    p = sub.add_parser('benchmark'); p.add_argument('--task', required=True)
    p = sub.add_parser('export'); p.add_argument('--task', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = {'task_directory': str(prepare(args.config))}
    elif args.command == 'catalog':
        result = CATALOG
    elif args.command == 'start':
        result = start_session(args.task, args.session, args.phase, args.actor)
    elif args.command == 'call':
        result = call_tool(args.task, args.session, args.tool, json.loads(args.arguments))
    elif args.command == 'benchmark':
        data = benchmark(args.task)
        result = {'runs': len(data['runs']), 'offline_reference': data['offline_exhaustive_reference']}
    else:
        from .export import export
        result = {'manifest': str(export(args.task))}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
