"""Explicit v0.2b recovery after verified truncated updater responses.

Preserves failed attempts; resumes curriculum from already frozen L1 agents.
No runner/evaluator source changes and no final feedback are used for recovery.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse
import copy
import json
from pathlib import Path
import shutil
import uuid
from common.storage import Storage
from common.runs import promote
from .problem import write_json,digest
from .rsi.runner import Engine,prepare,read,save,verify
from .rsi.curriculum import config,reference
from .rsi.provider import ClaudeCodeProvider
from .rsi.export import export


def recover_chain(suite,old,out):
    index=old['lineage'];job=out/f'lineage_{index}';job.mkdir()
    if old['status']!='failed' or len(old['runs'])!=2:raise ValueError('Recovery requires the observed L2 failure, not a running or different job')
    first=copy.deepcopy(old['runs'][0]);first_root=Path(first['directory']);verify(first_root)
    if read(first_root/'state.json')['status']!='frozen':raise ValueError('L1 must remain frozen and untested')
    failed_root=Path(old['runs'][1]['directory']);verify(failed_root)
    if read(failed_root/'state.json')['status']!='failed':raise ValueError('Original L2 process did not fail terminally')
    responses=[json.loads(x)['response'] for x in (failed_root/'events.jsonl').read_text().splitlines() if json.loads(x)['kind']=='model_response']
    if responses[-1].get('subtype')!='error_max_structured_output_retries' or responses[-1].get('usage',{}).get('output_tokens')!=4096:
        raise ValueError('Different failure: do not apply this repair')
    frozen=read(first_root/'frozen.json');seed=read(first_root/'revisions'/frozen['selected']/'revision.json')['revision']
    origin={'run_directory':str(first_root),'revision_id':frozen['selected']}
    status={'lineage':index,'status':'running','runs':[first],
            'superseded_attempts':[{'level':2,'directory':str(failed_root),'status':'failed_output_truncation','ledger':read(failed_root/'state.json')['ledger']}]}
    save(job/'status.json',status)
    try:
        for level in (2,3):
            cfg=config(suite,level,seed,origin);cfg['max_output_tokens']=16384
            cfg['scope']+=' v0.2b transport repair: output cap 4096->16384 after documented truncation; tasks, scoring, budgets and promotion gate unchanged.'
            cfg_path=job/f'level_{level}_config.json';write_json(cfg_path,cfg);root=prepare(cfg_path)
            if level==2:
                shutil.copytree(failed_root,root/'previous_failed_attempt')
                (root/'previous_failed_attempt/source_snapshot.tar.gz').rename(root/'previous_failed_attempt/failed_source_snapshot.tar.gz')
            status['runs'].append({'level':level,'directory':str(root),'phase':'evolving'});save(job/'status.json',status)
            frozen=Engine(root,ClaudeCodeProvider('claude-opus-5-5')).evolve()
            seed=read(root/'revisions'/frozen['selected']/'revision.json')['revision']
            origin={'run_directory':str(root),'revision_id':frozen['selected']}
            status['runs'][-1]['phase']='frozen';save(job/'status.json',status)
            print(json.dumps({'lineage':index,'level':level,'phase':'frozen','selected':frozen['selected']}),flush=True)
        for entry in status['runs']:
            root=Path(entry['directory']);entry['phase']='final';save(job/'status.json',status)
            report=Engine(root,ClaudeCodeProvider('claude-opus-5-5')).final()
            retained=promote(Storage.load(),export(root));entry.update(phase='complete',retained=str(retained),ledger=report['ledger'])
            if entry['level']==2:status['superseded_attempts'][0]['retained_evidence_directory']=str(retained/'previous_failed_attempt')
            save(job/'status.json',status)
            print(json.dumps({'lineage':index,'level':entry['level'],'phase':'complete'}),flush=True)
        status['status']='complete'
    except Exception as exc:status.update(status='failed',error_type=type(exc).__name__,error=str(exc))
    save(job/'status.json',status);return status


def recover(old_directory):
    old_directory=Path(old_directory);old=read(old_directory/'status.json')
    if old['status']!='completed_with_failures':raise ValueError('Wait for old batch process to finish')
    suite=read(old_directory/'suite.json');storage=Storage.load()
    name='rsi_recovery_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    out=storage.scratch('south_ken','urban_planning',name);out.mkdir(parents=True,exist_ok=False)
    write_json(out/'suite.json',suite)
    state={'status':'running','provider':'claude','recovery_of':str(old_directory),'suite_sha256':digest(out/'suite.json'),
           'repair':'Raise output cap to 16384 in new L2/L3 runs; preserve original two failed attempts and reuse frozen L1 results. No final score had been released.','lineages':[]}
    save(out/'status.json',state);print(json.dumps({'batch_directory':str(out)}),flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(recover_chain,suite,lineage,out) for lineage in sorted(old['lineages'],key=lambda x:x['lineage'])]
        for future in as_completed(futures):state['lineages'].append(future.result());save(out/'status.json',state)
    # References were computed only after all old model requests stopped and are never model inputs.
    shutil.copy2(old_directory/'references.json',out/'references.json')
    state['status']='complete' if all(x['status']=='complete' for x in state['lineages']) else 'completed_with_failures'
    save(out/'status.json',state);return out


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('batch');a=p.parse_args();print(recover(a.batch))
