"""Exploratory budgeted scenario selection and repair; no learned surrogate."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import numpy as np

from common.storage import Storage
from . import climate_experiment as previous
from .coupled_climate import ACTION, BASE, ClimateProblem, key
from .problem import write_json
from .rsi.provider import ClaudeCodeProvider


SEED = {'height_steps': [-1, 1, 0, 0], 'cool_sectors': [0, 3]}


def schema(ids):
    result = copy.deepcopy(ACTION)
    result['required'].append('scenarios')
    result['properties']['scenarios'] = {'type': 'array', 'uniqueItems': True,
        'maxItems': len(ids), 'items': {'type': 'string', 'enum': ids}}
    return result


def aggregate(plan, rows, required):
    complete = set(rows) == set(required)
    ordered = [rows[k] for k in required if k in rows]
    return {'plan': plan, 'complete': complete, 'feasible': complete and all(r['feasible'] for r in ordered),
            'score': min((r['score'] for r in ordered), default=-1.),
            'constraint': max((r['constraint'] for r in ordered), default=1.),
            'cost_units': sum(abs(x) for x in plan['height_steps'])+2*len(plan['cool_sectors']),
            'weather': [r['weather'][0] for r in ordered]}


class Trial:
    def __init__(self, problem):
        self.problem = problem
        self.weather = {w['id']: w for w in problem.cfg['development_weather']}
        self.ids = list(self.weather)
        self.used = 0
        self.observed = {}
        self.plans = {}
        for scenario in self.ids:
            self.observe(BASE, scenario)
        # Identical warm start for every method: prior nominal optimum, two known conditions.
        for scenario in self.ids[:2]:
            self.observe(SEED, scenario)

    def observe(self, plan, scenario):
        p = self.problem
        # Existing evaluator is reused on a singleton scenario, restoring its state even on error.
        saved_weather, saved_baselines = p.cfg['development_weather'], p.baselines
        try:
            p.cfg['development_weather'] = [self.weather[scenario]]
            p.baselines = {}
            result = p.evaluate(plan)
        finally:
            p.cfg['development_weather'], p.baselines = saved_weather, saved_baselines
        self.plans[key(plan)] = copy.deepcopy(plan)
        self.observed.setdefault(key(plan), {})[scenario] = result
        return result

    def query(self, plan, scenarios):
        if not scenarios or len(set(scenarios)) != len(scenarios) or any(s not in self.weather for s in scenarios):
            raise ValueError('Only nonempty unique public scenario IDs may be queried')
        if self.used+len(scenarios) > self.problem.cfg['evaluation_budget']:
            raise ValueError('Scenario evaluation budget exceeded')
        self.used += len(scenarios)  # Duplicates and structurally invalid plans are charged.
        errors = self.problem.validate(plan)
        if errors:
            return {'errors': errors}
        return {'results': [self.observe(plan, s) for s in scenarios], 'aggregate': self.result(plan)}

    def result(self, plan):
        return aggregate(plan, self.observed.get(key(plan), {}), self.ids)

    def complete_results(self):
        return [self.result(p) for p in self.plans.values() if self.result(p)['complete']]


def agent(root, problem, provider, mode, repeat):
    import jsonschema
    trial = Trial(problem); start = time.perf_counter(); selected = None; failure = None
    brief = problem.brief()
    brief['baseline'] = trial.result(BASE)
    history = [{'warm_start': trial.result(SEED)}]
    rules = ('Maximize worst-condition cooling subject to all constraints. One scenario evaluation costs one unit, '
             'including cached/repeated/invalid-plan queries. You may submit only a plan tested and feasible on ALL '
             'four public conditions. Submit uses an empty scenarios list. The unchanged baseline is allowed. '
             'Final scoring uses separate unavailable weather conditions; do not assume public feasibility proves generalization. '
             'This is a warm-start repair experiment, not discovery from scratch. Diagnose and repair the supplied plan. ')
    rules += ('Choose any nonempty subset of public scenarios per evaluate.' if mode == 'active' else
              'Every evaluate must request ALL four public scenarios; partial scenario selection is disabled.')
    for step in range(problem.cfg['max_steps']):
        prompt = {'operation': 'act', 'task': brief, 'history': history, 'rules': rules,
                  'remaining_scenario_evaluations': problem.cfg['evaluation_budget']-trial.used,
                  'remaining_steps': problem.cfg['max_steps']-step}
        previous.event(root, 'model_request', method=mode, repeat=repeat, step=step, prompt=prompt)
        try:
            response = provider.complete(prompt, schema(trial.ids), problem.cfg['max_output_tokens'])
            previous.event(root, 'model_response', method=mode, repeat=repeat, step=step, response=response)
            if sorted((response.get('model_usage') or {}).keys()) != [problem.cfg['model']]:
                raise ValueError('Resolved model mismatch')
            action = provider.parse(response); jsonschema.validate(action, schema(trial.ids))
        except Exception as exc:
            failure = str(exc); break
        if action['action'] == 'submit':
            result = trial.result(action['plan'])
            if result['feasible'] and not action['scenarios']:
                selected = result; break
            result = {'error': 'Submit requires an empty scenarios list and a fully tested feasible plan'}
        else:
            try:
                if mode == 'fixed' and set(action['scenarios']) != set(trial.ids):
                    raise ValueError('Fixed scenario control must query all four conditions')
                result = trial.query(action['plan'], action['scenarios'])
            except ValueError as exc:
                result = {'error': str(exc)}
            previous.event(root, 'evaluation', method=mode, repeat=repeat, used=trial.used, request=action, result=result)
        history.append({'request': action, 'result': result})
        print(mode, repeat, 'step', step, 'budget', trial.used, flush=True)
    record = {'method': 'claude_'+mode, 'repeat': repeat, 'submitted': selected is not None,
              'development': selected, 'calls_used': trial.used, 'wall_seconds': time.perf_counter()-start,
              'failure': failure if selected else (failure or 'No valid submission')}
    previous.event(root, 'episode', **record)
    return record


def control(root, problem, method, seed):
    trial = Trial(problem); start = time.perf_counter(); rng = np.random.default_rng(seed)
    pool = problem.plans()
    # All controls first verify the same warm-start plan on the two missing conditions.
    def query(plan, scenarios):
        result = trial.query(plan, scenarios)
        previous.event(root, 'evaluation', method=method, repeat=seed, used=trial.used,
                       request={'plan': plan, 'scenarios': scenarios}, result=result)
    query(SEED, trial.ids[2:])
    while trial.used+len(trial.ids) <= problem.cfg['evaluation_budget']:
        remaining = [p for p in pool if key(p) not in trial.observed]
        if method == 'materials_only':
            remaining = [p for p in remaining if not any(p['height_steps'])]
        if not remaining: break
        observations = trial.complete_results()
        if method == 'robust_gp' and len(observations) >= 4:
            plan = previous.gp_choice(observations, remaining)
        else:
            plan = remaining[int(rng.integers(len(remaining)))]
        query(plan, trial.ids)
    selected = previous.best(trial.complete_results())
    record = {'method': method, 'repeat': seed, 'submitted': True, 'development': selected,
              'calls_used': trial.used, 'wall_seconds': time.perf_counter()-start, 'failure': None}
    previous.event(root, 'episode', **record)
    return record


def prepare(config):
    root = previous.prepare(config)
    identity = previous.read(root/'identity.json')
    name = 'src/urban_planning/active_validation.py'
    identity['code'][name] = previous.sha(Storage.load().root/name)
    write_json(root/'identity.json', identity)
    return root


def run(root):
    root = Path(root); previous.verify(root)
    state = previous.read(root/'state.json')
    assert state['status'] == 'prepared'
    state['status'] = 'running'; write_json(root/'state.json', state)
    try:
        problem = ClimateProblem(root); cfg = problem.cfg
        provider = ClaudeCodeProvider(cfg['model'], timeout=240)
        write_json(root/'environment.json', {'python': sys.version, 'numpy': np.__version__, 'cli_version': provider.version})
        write_json(root/'legal_plans.json', problem.plans())
        records = []
        for repeat in range(cfg['agent_repetitions']):
            for mode in ('active', 'fixed'):
                records.append(agent(root, problem, provider, mode, repeat))
                write_json(root/'partial_results.json', records)
        for method in ('robust_gp', 'random', 'materials_only'):
            for seed in cfg['baseline_seeds']:
                records.append(control(root, problem, method, seed))
                write_json(root/'partial_results.json', records)
                print('CONTROL', method, seed, flush=True)
        write_json(root/'frozen_selections.json', records)
        previous.event(root, 'selections_frozen')
        # No holdout evaluation occurs before all online decisions are immutable.
        for record in records:
            record['holdout'] = problem.evaluate(record['development']['plan'], 'holdout') if record['submitted'] else None
            previous.event(root, 'holdout_score', method=record['method'], repeat=record['repeat'], result=record['holdout'])
        write_json(root/'warm_start_public.json', problem.evaluate(SEED))
        write_json(root/'warm_start_holdout.json', problem.evaluate(SEED, 'holdout'))
        previous.verify(root)
        write_json(root/'results.json', records)
        state['status'] = 'complete'; write_json(root/'state.json', state)
    except Exception as exc:
        state.update(status='failed', error=str(exc)); write_json(root/'state.json', state); raise
    print('COMPLETE', root, flush=True)


def export(root):
    from common.contract import validate
    from common.runs import promote
    root = Path(root); previous.verify(root)
    state = previous.read(root/'state.json'); assert state['status'] == 'complete'
    records = previous.read(root/'results.json'); cfg = previous.read(root/'config.json')
    events = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
    freeze = next(i for i, e in enumerate(events) if e['kind'] == 'selections_frozen')
    assert all(i < freeze for i, e in enumerate(events) if e['kind'] in ('model_request', 'evaluation', 'episode'))
    assert all(i > freeze for i, e in enumerate(events) if e['kind'] == 'holdout_score')
    assert all(r['calls_used'] <= cfg['evaluation_budget'] for r in records)
    responses = [e['response'] for e in events if e['kind'] == 'model_response']
    report = {'run_id': state['run_id'], 'trials': records, 'protocol': cfg['experiment_protocol'],
              'scope': cfg['scope'], 'all_selections_frozen_before_final_scores': True,
              'model_calls': len(responses), 'resolved_models': sorted({m for r in responses for m in r.get('model_usage', {})}),
              'input_tokens': sum(r.get('usage', {}).get('input_tokens', 0) for r in responses),
              'output_tokens': sum(r.get('usage', {}).get('output_tokens', 0) for r in responses),
              'reported_cost_usd': sum(r.get('reported_cost_usd') or 0 for r in responses),
              'warm_start_public': previous.read(root/'warm_start_public.json'),
              'warm_start_holdout': previous.read(root/'warm_start_holdout.json'),
              'limitations': ['Exploratory warm-start pilot, two repetitions, one layout; no significance or novelty claim.',
                             'Uncalibrated coarse numerical physics; no trained surrogate or model fidelity selection.',
                             'Equal scenario-query cap, not equal total compute: model tokens logged separately; shared caches prevent fair wall-time comparison.',
                             'Four public weather conditions include prior experiments; four new final conditions are hidden from model prompts, not from experiment authors.',
                             'GP uses a small fixed-kernel constrained-EI baseline, not a tuned state-of-the-art robust optimizer.',
                             'Materials-only control samples within the same cap; it is not exhaustive.']}
    write_json(root/'report.json', report)
    labels = [r['method']+'_'+str(r['repeat']) for r in records]
    layers = []
    for name, values in [('submitted', [int(r['submitted']) for r in records]),
                         ('final_feasible', [int(bool(r['holdout']) and r['holdout']['feasible']) for r in records]),
                         ('final_cooling_fraction', [r['holdout']['score'] if r['holdout'] else 0 for r in records])]:
        asset = 'data/'+name+'.json'; write_json(root/asset, {'labels': labels, 'values': values})
        layers.append({'id': name, 'kind': 'time_series', 'format': 'json', 'asset': asset, 'sampling': 'static',
                       'field': {'name': name, 'unit': '1'}, 'display': {'widget': 'time_series', 'capabilities': ['legend']}})
    identity = previous.read(root/'identity.json'); storage = Storage.load()
    artifacts = [{'id': 'source_snapshot' if p == root/'source_snapshot.tar.gz' else 'artifact_'+str(i),
                  'asset': str(p.relative_to(root)), 'sha256': previous.sha(p), 'media_type': 'application/octet-stream'}
                 for i, p in enumerate(sorted(root.rglob('*'))) if p.is_file() and p.name != 'manifest.json']
    manifest = {'schema_version': '1.1.0', 'scene_id': 'south_ken', 'simulation': 'active_validation',
                'run_id': state['run_id'], 'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
                'provenance': {'code_revision': identity['code_revision'], 'dirty': True, 'parameters': cfg,
                               'inputs': [{'id': 'frozen_inputs', 'sha256': previous.sha(root/'inputs.npz')}]},
                'spatial': previous.read(storage.metadata('south_ken')/'project.json')['spatial'],
                'time': {'unit': 's', 'samples': []}, 'layers': layers, 'artifacts': artifacts}
    write_json(root/'manifest.json', manifest); validate(root/'manifest.json')
    destination = promote(storage, root)
    write_json(storage.metadata('south_ken')/'reports'/('active-validation-'+state['run_id']+'.json'), report)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'run', 'export']); parser.add_argument('path')
    args = parser.parse_args(); print(globals()[args.action](args.path))
