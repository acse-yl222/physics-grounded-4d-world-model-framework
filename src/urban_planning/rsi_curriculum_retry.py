"""One explicit same-configuration retry of the recorded zero-output L2 failure."""
from pathlib import Path
import copy
import json
import shutil
from .rsi.runner import Engine,prepare,read,save,verify
from .rsi.curriculum import config
from .rsi.provider import ClaudeCodeProvider
from .rsi.export import export
from common.storage import Storage
from common.runs import promote


def retry(batch):
    batch=Path(batch);suite=read(batch/'suite.json');old=read(batch/'lineage_1/status.json')
    if old['status']!='failed':raise ValueError('Previous lineage must be terminally failed')
    first=copy.deepcopy(old['runs'][0]);first_root=Path(first['directory']);verify(first_root)
    if read(first_root/'state.json')['status']!='frozen':raise ValueError('Do not retry after test feedback')
    failed=Path(old['runs'][-1]['directory']);verify(failed)
    response=[json.loads(x)['response'] for x in (failed/'events.jsonl').read_text().splitlines() if json.loads(x)['kind']=='model_response'][-1]
    if response.get('subtype')!='error_max_structured_output_retries' or response['usage'].get('output_tokens')!=0:
        raise ValueError('Retry only the recorded zero-output error')
    out=batch/'lineage_1_retry';out.mkdir(exist_ok=False)
    status={'lineage':1,'status':'running','runs':[first], 'superseded_attempts':copy.deepcopy(old['superseded_attempts'])+[
        {'level':2,'directory':str(failed),'status':'failed_structured_response','ledger':read(failed/'state.json')['ledger']}]}
    frozen=read(first_root/'frozen.json');seed=read(first_root/'revisions'/frozen['selected']/'revision.json')['revision']
    origin={'run_directory':str(first_root),'revision_id':frozen['selected']}
    save(out/'status.json',status)
    try:
        for level in (2,3):
            cfg=config(suite,level,seed,origin);cfg['max_output_tokens']=16384
            cfg['scope']+=' v0.2b transport repair and one recorded same-configuration retry after zero-output structured response failure.'
            cfg_path=out/f'level_{level}_config.json';save(cfg_path,cfg);root=prepare(cfg_path)
            if level==2:
                for i,attempt in enumerate(status['superseded_attempts']):
                    dest=root/'failed_attempts'/str(i)
                    shutil.copytree(attempt['directory'],dest,ignore=shutil.ignore_patterns('previous_failed_attempt'))
                    (dest/'source_snapshot.tar.gz').rename(dest/'failed_source_snapshot.tar.gz')
            status['runs'].append({'level':level,'directory':str(root),'phase':'evolving'});save(out/'status.json',status)
            frozen=Engine(root,ClaudeCodeProvider('claude-opus-5-5')).evolve()
            seed=read(root/'revisions'/frozen['selected']/'revision.json')['revision'];origin={'run_directory':str(root),'revision_id':frozen['selected']}
            status['runs'][-1]['phase']='frozen';save(out/'status.json',status)
            print(json.dumps({'lineage':1,'level':level,'phase':'frozen','selected':frozen['selected']}),flush=True)
        for entry in status['runs']:
            root=Path(entry['directory']);entry['phase']='final';save(out/'status.json',status)
            report=Engine(root,ClaudeCodeProvider('claude-opus-5-5')).final()
            retained=promote(Storage.load(),export(root));entry.update(phase='complete',retained=str(retained),ledger=report['ledger'])
            if entry['level']==2:
                for i,attempt in enumerate(status['superseded_attempts']):attempt['retained_evidence_directory']=str(retained/'failed_attempts'/str(i))
            save(out/'status.json',status);print(json.dumps({'lineage':1,'level':entry['level'],'phase':'complete'}),flush=True)
        status['status']='complete'
    except Exception as exc:status.update(status='failed',error_type=type(exc).__name__,error=str(exc))
    save(out/'status.json',status);return status


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('batch');a=p.parse_args();print(json.dumps(retry(a.batch)),flush=True)
