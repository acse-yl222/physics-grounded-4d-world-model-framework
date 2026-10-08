"""Bounded agent episodes, independent promotion and immutable revision lineage."""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import difflib
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import time
import uuid

from common.storage import Storage, identifier, within
from common.provenance import snapshot_sources
from ..problem import digest, write_json
from ..tools import locked
from .contracts import ACTION, PROPOSAL, REVISION, INITIAL, identity, validate


def read(path):return json.loads(Path(path).read_text())


def save(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp');write_json(tmp,value);tmp.replace(path)


def code_identity():
    root=Path(__file__).parent
    files=list(root.glob('*.py'))+[root.parent/'problem.py',root.parent/'solar.py']
    return {str(p.relative_to(root.parent)):digest(p) for p in sorted(files)}


def verify(root):
    if read(root/'code_identity.json')!=code_identity():raise ValueError('Runner/evaluator source changed since preparation; prepare a new run')
    expected=read(root/'input_identity.json')
    if {p:digest(root/p) for p in expected}!=expected:raise ValueError('Frozen configuration or inputs changed')


def prepare(config_path):
    storage=Storage.load();cfg=read(config_path)
    allowed={'schema_version','scene_id','input_runs','tasks','generations','episode_evaluations','episode_steps',
             'max_model_calls','max_output_tokens','max_total_tokens','max_evaluations','promotion_min_gain','seed_revision','scope'}
    optional={'input_paths','validation_repetitions','final_repetitions','control_revision','seed_origin'}
    if not allowed.issubset(cfg) or set(cfg)-allowed-optional or cfg['schema_version'] not in ('urban-rsi-0.1','urban-rsi-0.2'):raise ValueError('Invalid RSI configuration keys/version')
    if cfg['scene_id'] not in ('south_ken','white_city'):raise ValueError('Unsupported city scene')
    for k in ['generations','episode_evaluations','episode_steps','max_model_calls','max_output_tokens','max_total_tokens','max_evaluations']:
        if type(cfg[k]) is not int or cfg[k]<1:raise ValueError(f'{k} must be a positive integer')
    if not isinstance(cfg['promotion_min_gain'],(float,int)) or not 0<=cfg['promotion_min_gain']<=1:raise ValueError('Invalid promotion gain')
    validate(cfg['seed_revision'],REVISION)
    for key in ('validation_repetitions','final_repetitions'):
        if type(cfg.get(key,1)) is not int or not 1<=cfg.get(key,1)<=20:raise ValueError('Invalid repetition count')
    if 'control_revision' in cfg:validate(cfg['control_revision'],REVISION)
    ids=set();slots=set()
    for t in cfg['tasks']:
        if set(t)!={'id','input','phase','role'}:raise ValueError('Invalid task entry')
        identifier(t['id']);identifier(t['input'])
        if t['id'] in ids:raise ValueError('Duplicate task ID')
        ids.add(t['id'])
        if t['role'] not in ('development','promotion','test'):raise ValueError('Invalid role')
        slot=(t['input'],t['phase'],'holdout' if t['role']=='test' else 'development')
        if slot in slots:raise ValueError('Development/promotion/test scoring slots overlap')
        slots.add(slot)
    if {t['role'] for t in cfg['tasks']}!={'development','promotion','test'}:raise ValueError('All three task roles are required')
    run_id='rsi_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    root=storage.scratch(cfg['scene_id'],'urban_planning',run_id);root.mkdir(parents=True,exist_ok=False)
    write_json(root/'state.json',{'status':'preparing','run_id':run_id})
    try:
        provenance=[]
        if set(cfg['input_runs']) & set(cfg.get('input_paths',{})):raise ValueError('Duplicate input alias')
        sources={name:storage.run(cfg['scene_id'],run) for name,run in cfg['input_runs'].items()}
        sources.update({name:within(storage.assets(cfg['scene_id'],'input'),path) for name,path in cfg.get('input_paths',{}).items()})
        if len(set(sources.values()))!=len(sources):raise ValueError('Do not alias the same input directory twice')
        for name,source in sources.items():
            identifier(name)
            destination=root/'inputs'/name;destination.mkdir(parents=True)
            for filename in ('task.json','background.npz'):
                shutil.copy2(source/filename,destination/filename)
                provenance.append({'input':name,'asset':filename,'source_directory':str(source),'sha256':digest(destination/filename)})
        if 'seed_origin' in cfg:
            origin=cfg['seed_origin'];previous=Path(origin['run_directory']);verify(previous)
            if read(previous/'state.json')['status']!='frozen':raise ValueError('Carry a seed before any final evaluation of its lineage')
            frozen=read(previous/'frozen.json');p=previous/'revisions'/frozen['selected']/'revision.json'
            if origin['revision_id']!=frozen['selected'] or digest(p)!=frozen['archive_file_sha256'] or read(p)['revision']!=cfg['seed_revision']:
                raise ValueError('Inherited seed differs from approved frozen revision')
            write_json(root/'seed_origin.json',{'origin':origin,'frozen':frozen,'revision':read(p)})
        for t in cfg['tasks']:
            task=read(root/'inputs'/t['input']/'task.json')
            if task['scene_id'] != cfg['scene_id']:raise ValueError('Task scene differs from RSI configuration')
            if t['phase'] not in task['phases']:raise ValueError('Unknown task phase')
        write_json(root/'config.json',cfg);write_json(root/'input_provenance.json',provenance)
        write_json(root/'input_identity.json',{str(p.relative_to(root)):digest(p) for p in [root/'config.json',*root.glob('seed_origin.json'),*sorted((root/'inputs').rglob('*'))] if p.is_file()})
        write_json(root/'code_identity.json',code_identity())
        revision=snapshot_sources(storage.root,root/'source_snapshot.tar.gz')
        write_json(root/'environment.json',{'python':sys.version,'code_revision':revision,'isolation':'Remote structured-text model; trusted separate evaluator process. No generated code execution or OS sandbox claim.'})
        save(root/'state.json',{'status':'prepared','run_id':run_id,'selected':None,'generation':0,
                               'ledger':{'model_calls':0,'input_tokens':0,'output_tokens':0,'unknown_usage_calls':0,'evaluations':0,'evaluator_seconds':0.,'model_seconds':0.,'reported_cost_usd':0.,'unknown_cost_calls':0}})
    except Exception as exc:
        save(root/'state.json',{'status':'failed_preparation','run_id':run_id,'error':type(exc).__name__});raise
    return root


class Worker:
    def __init__(self,root,mode):
        self.process=subprocess.Popen([sys.executable,'-m','urban_planning.rsi.evaluator',str(root),mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    def call(self,payload):
        self.process.stdin.write(json.dumps(payload)+'\n');self.process.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout,selectors.EVENT_READ)
            if not selector.select(60):raise TimeoutError('Evaluator response timed out')
        line=self.process.stdout.readline()
        if not line:raise RuntimeError('Evaluator process exited unexpectedly')
        return json.loads(line)
    def close(self):
        self.process.stdin.close()
        try:self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill();self.process.wait()
        self.process.stdout.close();self.process.stderr.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


class Engine:
    def __init__(self,root,provider):
        self.root=Path(root);verify(self.root)
        self.cfg=read(self.root/'config.json');self.state=read(self.root/'state.json');self.provider=provider
        self.events=self.root/'events.jsonl'

    def event(self,kind,data):
        with self.events.open('a') as f:f.write(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'kind':kind,**data},allow_nan=False)+'\n')
        save(self.root/'state.json',self.state)

    def ask(self,prompt,schema):
        ledger=self.state['ledger'];cfg=self.cfg
        if ledger['model_calls']>=cfg['max_model_calls']:raise RuntimeError('Total model-call budget exhausted')
        if ledger['input_tokens']+ledger['output_tokens']>=cfg['max_total_tokens']:raise RuntimeError('Total reported token budget exhausted')
        ledger['model_calls']+=1;call_id=ledger['model_calls'];started=time.perf_counter()
        self.event('model_request',{'call_id':call_id,'prompt':prompt,'schema':schema,'provider':self.provider.kind,'requested_model':self.provider.model})
        raw=None
        try:
            raw=self.provider.complete(prompt,schema,cfg['max_output_tokens'])
            cost=raw.get('reported_cost_usd')
            if isinstance(cost,(int,float)) and cost>=0:ledger['reported_cost_usd']+=cost
            else:ledger['unknown_cost_calls']+=1
            usage=raw.get('usage') or {}
            if all(type(usage.get(k)) is int and usage[k]>=0 for k in ('input_tokens','output_tokens')):
                ledger['input_tokens']+=usage['input_tokens'];ledger['output_tokens']+=usage['output_tokens']
            else:ledger['unknown_usage_calls']+=1
            ledger['model_seconds']+=time.perf_counter()-started
            self.event('model_response',{'call_id':call_id,'response':raw})
            models=sorted((raw.get('model_usage') or {}).keys()) or [raw.get('model',self.provider.model)]
            if self.state.get('resolved_models') and models!=self.state['resolved_models']:
                raise ValueError('Resolved model changed within lineage')
            self.state['resolved_models']=models
            return validate(self.provider.parse(raw),schema)
        except Exception as exc:
            if raw is None:
                ledger['unknown_usage_calls']+=1;ledger['unknown_cost_calls']+=1
                ledger['model_seconds']+=time.perf_counter()-started
            self.event('model_error',{'call_id':call_id,'error_type':type(exc).__name__})
            raise

    def evaluate(self,worker,payload):
        ledger=self.state['ledger']
        if payload['op'] in ('open','evaluate','diagnose','score_submitted'):
            if ledger['evaluations']>=self.cfg['max_evaluations']:raise RuntimeError('Total evaluation budget exhausted')
            ledger['evaluations']+=1
        answer=worker.call(payload);ledger['evaluator_seconds']+=answer['wall_seconds']
        self.event('evaluator',{'request':payload,'response':answer})
        if not answer['ok']:raise ValueError(answer['error'])
        return answer['result']

    def episode(self,worker,revision,task,label):
        opened=self.evaluate(worker,{'op':'open','task_id':task['id'],'session':label})
        history=[{'request':None,'result':opened['baseline']}];left=opened['task']['evaluation_budget'];submitted=False
        result=None;failure=None
        for step in range(self.cfg['episode_steps']):
            prompt={'operation':'act','rules':'Return one JSON action. evaluate and diagnose each cost one evaluation, including invalid/repeated requests. diagnose returns spatial summaries but does not register a plan for submission. submit closes this episode without revealing final-test scores. No file access or code execution. Maximize feasible summer reduction under all constraints.',
                    'agent':revision,'task':opened['task'],'history':history,
                    'remaining':{'evaluations':left,'steps':self.cfg['episode_steps']-step}}
            try:
                action=self.ask(prompt,ACTION)
            except Exception as exc:
                failure=type(exc).__name__;break  # Do not silently replace a failed model by a script.
            if action['action'] in ('evaluate','diagnose'):
                if left<=0:
                    history.append({'request':action,'result':{'error':'Episode evaluation budget exhausted'}});continue
                left-=1
            try:
                answer=self.evaluate(worker,{'op':action['action'],'session':label,'plan':action['plan']})
                history.append({'request':action,'result':answer})
                if action['action']=='submit':result=answer;submitted=True;break
            except ValueError as exc:history.append({'request':action,'result':{'error':str(exc)}})
        if not submitted:
            failure=failure or 'No valid submission within step budget'
        output={'task_id':task['id'],'session':label,'submitted':submitted,'result':result,
                'score':result['summer_reduction_fraction'] if submitted else 0.,'failure':failure,'history':history}
        self.event('episode',output)
        return output

    def suite(self,worker,revision,role,label):
        return [self.episode(worker,revision,t,label+'_'+t['id']) for t in self.cfg['tasks'] if t['role']==role]

    def compare(self,worker,parent,child,generation):
        scores={'parent':[],'child':[]};revisions={'parent':parent,'child':child}
        for repeat in range(self.cfg.get('validation_repetitions',1)):
            # Counterbalance order; repetitions are fresh stochastic episodes, not seeded pairs.
            order=('parent','child') if repeat%2==0 else ('child','parent')
            for name in order:
                episodes=self.suite(worker,revisions[name],'promotion',f'g{generation}_{name}_r{repeat}')
                for ep in episodes:ep['repeat']=repeat
                scores[name].extend(episodes)
        return scores['parent'],scores['child']

    def archive(self,revision,parent,author,rationale,number):
        validate(revision,REVISION)
        entry={'id':f'g{number:03d}_{identity(revision)[:12]}','parent':parent,'revision':revision,
               'revision_sha256':identity(revision),'author':author,'rationale':rationale,'generation':number}
        path=self.root/'revisions'/entry['id'];path.mkdir(parents=True,exist_ok=False)
        write_json(path/'revision.json',entry)
        old=read(self.root/'revisions'/parent/'revision.json')['revision'] if parent else {}
        (path/'changes.diff').write_text(''.join(difflib.unified_diff(json.dumps(old,indent=2).splitlines(True),json.dumps(revision,indent=2).splitlines(True),fromfile=parent or 'none',tofile=entry['id'])))
        return entry

    def evolve(self,arm='recursive'):
        with locked(self.root/'lifecycle.json'):
            self.state=read(self.root/'state.json');verify(self.root)
            if self.state['status']!='prepared':raise ValueError('Evolution starts only from prepared; use a new run after failure or freezing')
            if arm not in ('recursive','fixed_updater','fixed_agent'):raise ValueError('Unknown experimental arm')
            self.state.update(status='evolving',arm=arm,provider=self.provider.kind,model=self.provider.model)
            self.event('evolution_started',{'arm':arm})
            try:
                inherited='seed_origin' in self.cfg
                current=self.archive(self.cfg['seed_revision'],None,'inherited_approved_agent' if inherited else 'human_seed',
                                     'Approved predecessor recorded in seed_origin.json' if inherited else 'Configured initial agent',0)
                self.state['selected']=current['id']
                with Worker(self.root,'evolution') as worker:
                    for generation in range(1,self.cfg['generations']+1):
                        verify(self.root)
                        parent_revision=current['revision'];dev=self.suite(worker,parent_revision,'development',f'g{generation}_dev')
                        self.state['generation']=generation
                        if arm=='fixed_agent':
                            self.event('fixed_agent_round',{'generation':generation});continue
                        updater=parent_revision['updater'] if arm=='recursive' else self.cfg['seed_revision']['updater']
                        proposal=self.ask({'operation':'revise','instructions':updater,'parent':parent_revision,'development_episodes':dev,
                                           'rules':'Return only the editable revision and a rationale. The next generation inherits the revision. Evaluator, budgets, task splits and scoring are immutable. Use reusable mechanisms rather than memorized task answers.'},PROPOSAL)
                        if arm=='fixed_updater':proposal['revision']['updater']=self.cfg['seed_revision']['updater']
                        candidate=self.archive(proposal['revision'],current['id'],self.provider.kind,proposal['rationale'],generation)
                        if identity(parent_revision)==identity(candidate['revision']):
                            decision={'promoted':False,'reason':'Unchanged revision','parent':current['id'],'candidate':candidate['id']}
                        else:
                            parent_scores,child_scores=self.compare(worker,parent_revision,candidate['revision'],generation)
                            decision=promotion(parent_scores,child_scores,self.cfg['promotion_min_gain'])
                            decision.update(parent=current['id'],candidate=candidate['id'],parent_episodes=parent_scores,child_episodes=child_scores)
                        write_json(self.root/'revisions'/candidate['id']/'decision.json',decision)
                        self.event('promotion',decision)
                        if decision['promoted']:current=candidate;self.state['selected']=current['id']
                frozen={'selected':current['id'],'revision_sha256':current['revision_sha256'],
                        'archive_file_sha256':digest(self.root/'revisions'/current['id']/'revision.json'),
                        'input_identity_sha256':digest(self.root/'input_identity.json'),'arm':arm,'provider':self.provider.kind,'model':self.provider.model,
                        'resolved_models':self.state.get('resolved_models'),
                        'evolution_ledger':copy.deepcopy(self.state['ledger'])}
                write_json(self.root/'frozen.json',frozen)
                self.state['status']='frozen';self.event('frozen',frozen)
                return frozen
            except Exception as exc:
                self.state['status']='failed';self.event('run_failed',{'error_type':type(exc).__name__});raise

    def final(self):
        with locked(self.root/'lifecycle.json'):
            self.state=read(self.root/'state.json');verify(self.root)
            if self.state['status']!='frozen':raise ValueError('Final evaluation requires a frozen, unevaluated lineage')
            frozen=read(self.root/'frozen.json');path=self.root/'revisions'/frozen['selected']/'revision.json'
            if digest(path)!=frozen['archive_file_sha256'] or digest(self.root/'input_identity.json')!=frozen['input_identity_sha256']:raise ValueError('Frozen revision or identity was changed')
            if (self.provider.kind,self.provider.model)!=(frozen['provider'],frozen['model']):raise ValueError('Final model/provider must match evolution')
            revision=read(path)['revision'];self.state['status']='final_running';self.event('final_started',{'selected':frozen['selected']})
            try:
                with Worker(self.root,'final') as worker:
                    episodes=[];arms={'selected':revision}
                    if 'control_revision' in self.cfg:arms['fixed_seed']=self.cfg['control_revision']
                    repeats=self.cfg.get('final_repetitions',1)
                    for repeat in range(repeats):
                        order=list(arms) if repeat%2==0 else list(reversed(arms))
                        for arm in order:
                            group=self.suite(worker,arms[arm],'test',f'final_{arm}_r{repeat}')
                            for ep in group:ep.update(arm=arm,repeat=repeat)
                            episodes.extend(group)
                    # Collect all decisions before any withheld scoring. These scores never enter model prompts.
                    scores=[]
                    for ep in episodes:
                        score=self.evaluate(worker,{'op':'score_submitted','session':ep['session'],'plan':ep['result']['plan']}) if ep['submitted'] else None
                        label=ep['task_id'] if repeats==1 and len(arms)==1 else f"{ep['task_id']}:{ep['arm']}:r{ep['repeat']}"
                        scores.append({'task_id':label,'base_task_id':ep['task_id'],'arm':ep['arm'],'repeat':ep['repeat'],
                                       'submitted':ep['submitted'],'holdout':score})
                report={'selected':frozen['selected'],'provider':self.provider.kind,'model':self.provider.model,
                        'scope':self.cfg['scope'],'scores':scores,'ledger':copy.deepcopy(self.state['ledger']),
                        'claim':'Engineering acceptance only; scripted fixtures are not LLM or RSI performance evidence.' if self.provider.kind=='scripted_test_fixture' else 'Single lineage; no demonstrated RSI advantage without independent tasks and controls.'}
                write_json(self.root/'final.json',report);self.state['status']='complete';self.event('complete',{'selected':frozen['selected']})
                return report
            except Exception as exc:
                self.state['status']='failed_final';self.event('final_failed',{'error_type':type(exc).__name__});raise


def promotion(parent,child,min_gain):
    if [x['task_id'] for x in parent]!=[x['task_id'] for x in child] or not child:raise ValueError('Promotion tasks must be paired')
    feasible=all(x['submitted'] for x in child)
    names=list(dict.fromkeys(x['task_id'] for x in parent))
    gains=[sum(x['score'] for x in child if x['task_id']==name)/sum(x['task_id']==name for x in child)
           -sum(x['score'] for x in parent if x['task_id']==name)/sum(x['task_id']==name for x in parent) for name in names]
    mean=sum(gains)/len(gains)
    accepted=feasible and min(gains)>=-1e-12 and mean>min_gain
    return {'promoted':accepted,'mean_gain':mean,'per_task_gain':gains,'task_ids':names,'repetitions':len(parent)//len(names),
            'reason':'Strict mean improvement without task-mean regression; not a significance test' if accepted else 'Failed submission, regression, tie or insufficient improvement'}
