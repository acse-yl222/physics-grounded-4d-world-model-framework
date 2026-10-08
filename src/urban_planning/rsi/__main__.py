"""Urban RSI lifecycle: prepare, evolve, final, status, export."""
import argparse
import json
from pathlib import Path
from .provider import ResponsesProvider, FixtureProvider, ClaudeCodeProvider
from .runner import prepare, Engine, read


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--config',required=True)
    for name in ('evolve','final'):
        p=sub.add_parser(name);p.add_argument('--run',required=True)
        p.add_argument('--provider',choices=['claude','responses','fixture'],default='claude')
        p.add_argument('--model');p.add_argument('--base-url',default='https://api.openai.com/v1');p.add_argument('--key-env',default='OPENAI_API_KEY')
        if name=='evolve':p.add_argument('--arm',choices=['recursive','fixed_updater','fixed_agent'],default='recursive')
    p=sub.add_parser('status');p.add_argument('--run',required=True)
    p=sub.add_parser('export');p.add_argument('--run',required=True);p.add_argument('--retain',action='store_true')
    args=parser.parse_args()
    if args.command=='prepare':result={'run_directory':str(prepare(args.config))}
    elif args.command=='status':result=read(Path(args.run)/'state.json')
    elif args.command=='export':
        from .export import export
        target=export(args.run)
        if args.retain:
            from common.runs import promote
            from common.storage import Storage
            target=promote(Storage.load(),target)
        result={'run_directory':str(target)}
    else:
        provider=FixtureProvider() if args.provider=='fixture' else ClaudeCodeProvider(args.model) if args.provider=='claude' else ResponsesProvider(args.model,args.base_url,args.key_env)
        engine=Engine(args.run,provider)
        result=engine.evolve(args.arm) if args.command=='evolve' else engine.final()
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
