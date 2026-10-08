"""Predeclared task ladder on preserved South Kensington solar inputs."""
import argparse
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import uuid
import numpy as np
from common.storage import Storage
from ..problem import write_json,digest,Problem,best_result
from ..benchmark import run_policy
from .contracts import INITIAL,identity


LEVELS=[{'level':1,'name':'single_site','sites':8,'max_panels':1,'cost_cap':1,'winter_cap':.012,'evaluations':4},
        {'level':2,'name':'cost_constrained_pairs','sites':12,'max_panels':2,'cost_cap':4,'winter_cap':.008,'evaluations':5},
        {'level':3,'name':'size_choice_triples','sites':15,'max_panels':3,'cost_cap':6,'winter_cap':.005,'evaluations':6}]


def build(source_run='planning_pilot_20260930T020508Z_c8ba76',scene='south_ken'):
    if scene not in ('south_ken','white_city'):raise ValueError('Unsupported city scene')
    storage=Storage.load();source=storage.run(scene,source_run)
    original=json.loads((source/'task.json').read_text())
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    if original['scene_id'] != scene:raise ValueError('Source task scene mismatch')
    name='rsi_curriculum_'+stamp;directory=storage.assets(scene,'input')/name;directory.mkdir(parents=True,exist_ok=False)
    tasks=[]
    for level in LEVELS:
        for role_index,role in enumerate(('development','promotion','test')):
            case=f"l{level['level']}_{role}";rng=np.random.default_rng(73100+level['level']*100+role_index)
            task=copy.deepcopy(original)
            indices=rng.permutation(len(original['candidates']))[:level['sites']]
            candidates=[]
            for i in indices:
                parent=original['candidates'][int(i)]
                scales=(.5,1.) if level['level']==3 else (1.,)
                for scale in scales:
                    c=copy.deepcopy(parent);c['width_m']*=scale;c['depth_m']*=scale
                    c['cost_units']=1 if level['level']==1 or scale==.5 else 1+int((int(i)+role_index)%3) if level['level']==2 else 3
                    candidates.append(c)
            rng.shuffle(candidates)
            for n,c in enumerate(candidates):c['id']=f'c{n:02d}'
            excluded=[candidates[int(rng.integers(len(candidates)))]['id']] if level['level']>=2 else []
            task.update(task_id=case,run_id=name,candidates=candidates,candidate_count=len(candidates),
                        phases={'initial':{'max_panels':level['max_panels'],'max_cost_units':level['cost_cap'],
                                           'max_winter_loss_fraction':level['winter_cap'],'excluded_ids':excluded,
                                           'evaluation_budget':level['evaluations']}},
                        curriculum_level=level['level'],curriculum_role=role,
                        interpretation=original['interpretation']+' Curriculum uses synthetic costs/exclusions and nested panel sizes within original footprints. IDs are permuted independently across tasks; geometry remains fixed.',
                        split_note='New deterministic constraint/option tasks on previously inspected correlated solar intervals; not independent weather or city validation.')
            out=directory/case;out.mkdir();write_json(out/'task.json',task);shutil.copy2(source/'background.npz',out/'background.npz')
            p=Problem(out);plans=p.plans('initial')
            tasks.append({'id':case,'role':role,'level':level['level'],'input_path':f'{name}/{case}',
                          'task_sha256':digest(out/'task.json'),'background_sha256':digest(out/'background.npz'),
                          'structurally_feasible_plans':len(plans),'candidate_count':len(candidates)})
    plan={'version':'rsi-curriculum-0.2','scene_id':scene,'suite_id':name,'source_run':source_run,
          'levels':LEVELS,'tasks':tasks,'lineages':2,'proposals_per_level':1,'validation_repetitions':2,'final_repetitions':2,
          'escalation_rule':'Run levels 1,2,3 in each lineage; carry only approved frozen agent state. Escalation is scheduled, not conditioned on finding a positive result.',
          'selection_rule':'All child submissions valid; no per-task mean regression across two fresh repetitions; strict mean gain > 1e-6. Engineering gate, not a significance test.',
          'final_rule':'Freeze all three levels of a lineage before any final scoring. Compare selected versus original fixed seed, two episodes each; no final feedback enters later training.',
          'baselines':['random_search_10_seeds','single_site_ranking','gp_constrained_ei_10_seeds','offline_exhaustive_development_reference'],
          'scope':'Exploratory difficulty ladder; source solar physics is unchanged. Synthetic constraints/costs, no new weather or scene. Cross-task inheritance and prompt/updater/memory changes only.'}
    write_json(directory/'suite.json',plan)
    return directory/'suite.json'


def config(suite,level,seed=INITIAL,origin=None):
    spec=next(x for x in suite['levels'] if x['level']==level)
    tasks=[t for t in suite['tasks'] if t['level']==level]
    result={'schema_version':'urban-rsi-0.2','scene_id':suite.get('scene_id','south_ken'),'input_runs':{},
            'input_paths':{t['id']:t['input_path'] for t in tasks},
            'tasks':[{'id':t['id'],'input':t['id'],'phase':'initial','role':t['role']} for t in tasks],
            'generations':1,'episode_evaluations':spec['evaluations'],'episode_steps':spec['evaluations']+2,
            'max_model_calls':120,'max_output_tokens':16384,'max_total_tokens':1000000,'max_evaluations':200,
            'promotion_min_gain':.000001,'seed_revision':copy.deepcopy(seed),'control_revision':copy.deepcopy(INITIAL),
            'validation_repetitions':suite['validation_repetitions'],'final_repetitions':suite['final_repetitions'],'scope':suite['scope']}
    if origin is not None:result['seed_origin']=origin
    return result


def reference(input_directory):
    """Controller-only conventional baselines; never supplied to model prompts."""
    p=Problem(input_directory);plans=p.plans('initial')
    evaluated=[p.evaluate(plan,'initial') for plan in plans]
    optimum=best_result(evaluated)
    runs=[]
    for method in ('random_search','single_site_ranking','gp_constrained_ei'):
        for seed in (range(10) if method!='single_site_ranking' else [0]):
            runs.append(run_policy(p,'initial',method,seed))
    singles=[r for r in evaluated if len(r['plan'])==1 and r['feasible']]
    return {'task_id':p.task['task_id'],'identity':p.identity,'structurally_feasible_count':len(plans),
            'physically_feasible_count':sum(r['feasible'] for r in evaluated),
            'nonempty_feasible_count':sum(r['feasible'] and bool(r['plan']) for r in evaluated),
            'offline_reference':{'development':optimum,'holdout':p.evaluate(optimum['plan'],'initial','holdout'),
                                 'note':'Unbudgeted development-selected enumeration, not an online method.'},
            'best_feasible_single_score':max([r['summer_reduction_fraction'] for r in singles],default=0.),
            'runs':runs}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-run',default='planning_pilot_20260930T020508Z_c8ba76')
    parser.add_argument('--scene',choices=['south_ken','white_city'],default='south_ken')
    args=parser.parse_args();print(build(args.source_run,args.scene))
