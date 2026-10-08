"""Run two independent curricula with fixed schedules; keep every failed job."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import copy
import json
from pathlib import Path
import shutil
import uuid
from common.storage import Storage
from common.runs import promote
from ..problem import digest,write_json
from .curriculum import config,reference
from .contracts import INITIAL
from .runner import Engine,prepare,read,save
from .provider import ClaudeCodeProvider,FixtureProvider
from .export import export


def run_lineage(suite,directory,index,provider_kind):
    job=directory/f'lineage_{index}';job.mkdir(exist_ok=False)
    status={'lineage':index,'status':'running','runs':[]};save(job/'status.json',status)
    current=copy.deepcopy(INITIAL);origin=None
    def provider():return FixtureProvider() if provider_kind=='fixture' else ClaudeCodeProvider('claude-opus-5-5')
    try:
        for spec in suite['levels']:
            level=spec['level'];cfg=config(suite,level,current,origin)
            cfg_path=job/f'level_{level}_config.json';write_json(cfg_path,cfg)
            root=prepare(cfg_path);status['runs'].append({'level':level,'directory':str(root),'phase':'evolving'});save(job/'status.json',status)
            frozen=Engine(root,provider()).evolve()
            current=read(root/'revisions'/frozen['selected']/'revision.json')['revision']
            origin={'run_directory':str(root),'revision_id':frozen['selected']}
            status['runs'][-1]['phase']='frozen';save(job/'status.json',status)
            print(json.dumps({'lineage':index,'level':level,'phase':'frozen','selected':frozen['selected']}),flush=True)
        # No test scores exist until all evolution stages in this lineage have frozen.
        for entry in status['runs']:
            root=Path(entry['directory']);entry['phase']='final';save(job/'status.json',status)
            report=Engine(root,provider()).final()
            entry['phase']='complete';entry['retained']=str(promote(Storage.load(),export(root)))
            entry['ledger']=report['ledger'];save(job/'status.json',status)
            print(json.dumps({'lineage':index,'level':entry['level'],'phase':'complete'}),flush=True)
        status['status']='complete';save(job/'status.json',status)
    except Exception as exc:
        status.update(status='failed',error_type=type(exc).__name__,error=str(exc));save(job/'status.json',status)
        print(json.dumps({'lineage':index,'status':'failed','error_type':type(exc).__name__}),flush=True)
    return status


def run(suite_path,provider_kind='claude',workers=2):
    storage=Storage.load();suite=read(suite_path)
    name='rsi_batch_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    out=storage.scratch(suite.get('scene_id','south_ken'),'urban_planning',name);out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(suite_path,out/'suite.json')
    state={'status':'running','provider':provider_kind,'suite_sha256':digest(out/'suite.json'),'lineages':[]}
    write_json(out/'status.json',state);print(json.dumps({'batch_directory':str(out)}),flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(run_lineage,suite,out,i,provider_kind) for i in range(suite['lineages'])]
        for future in as_completed(futures):
            state['lineages'].append(future.result());save(out/'status.json',state)
    state['status']='analyzing'
    save(out/'status.json',state)
    # References are computed only after model decisions, in a separate controller artifact.
    references=[]
    for task in suite['tasks']:
        if task['role']=='test':
            result=reference(storage.assets(suite.get('scene_id','south_ken'),'input')/task['input_path'])
            result['level']=task['level'];references.append(result)
    write_json(out/'references.json',references)
    state['status']='complete' if all(x['status']=='complete' for x in state['lineages']) else 'completed_with_failures'
    save(out/'status.json',state)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--suite',required=True)
    parser.add_argument('--provider',choices=['claude','fixture'],default='claude');parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args();print(run(args.suite,args.provider,args.workers))
