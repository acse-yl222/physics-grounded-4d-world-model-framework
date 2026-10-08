"""Frozen, budgeted Claude / random / constrained-GP climate planning experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
import time
import uuid

import numpy as np

from common.provenance import snapshot_sources
from common.storage import Storage
from .coupled_climate import ACTION, BASE, ClimateProblem, key
from .problem import write_json
from .rsi.provider import ClaudeCodeProvider


def read(path): return json.loads(Path(path).read_text())


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_files():
    return ['src/urban_planning/'+name for name in
            ('coupled_climate.py', 'climate_experiment.py', 'traffic_morphology.py', 'rsi/provider.py')] + [
        'src/urban_flow/solvers/mac_torch.py', 'src/urban_flow/physics/solar/model.py',
        'src/urban_flow/physics/diurnal_solver.py', 'src/common/pipeline/scene_temperature_physical.py',
        'src/urban_flow/physics/environment-integration/members/yiqi_temperature/models/physical_model/south_kensington_temperature_3d.py']


def prepare(config):
    storage = Storage.load(); cfg = read(config)
    rid = 'climate_agent_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    root = storage.scratch('south_ken', 'coupled_climate', rid)
    root.mkdir(parents=True, exist_ok=False)
    source = storage.run('south_ken', cfg['source_run'])
    shutil.copy2(config, root/'config.json')
    shutil.copy2(source/'inputs.npz', root/'inputs.npz')
    shutil.copy2(source/'input_provenance.json', root/'input_provenance.json')
    revision = snapshot_sources(storage.root, root/'source_snapshot.tar.gz')
    write_json(root/'identity.json', {'code': {p: sha(storage.root/p) for p in code_files()},
                                    'inputs': {p: sha(root/p) for p in ('config.json', 'inputs.npz')},
                                    'code_revision': revision, 'source_run': cfg['source_run']})
    write_json(root/'state.json', {'status': 'prepared', 'run_id': rid})
    return root


def verify(root):
    identity = read(root/'identity.json'); storage = Storage.load()
    assert all(sha(storage.root/path) == value for path, value in identity['code'].items()), 'Code changed after freezing'
    assert all(sha(root/path) == value for path, value in identity['inputs'].items()), 'Inputs changed after freezing'


def event(root, kind, **payload):
    with (root/'events.jsonl').open('a') as handle:
        handle.write(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'kind': kind, **payload}, allow_nan=False)+'\n')


def best(results):
    return max((r for r in results if r['feasible']), key=lambda r: (r['score'], -r['cost_units']))


def agent_episode(root, problem, provider, repeat):
    import jsonschema
    cfg = problem.cfg; started = time.perf_counter(); calls = 0
    history = [{'request': None, 'result': problem.evaluate(BASE)}]
    evaluated = {key(BASE): history[0]['result']}
    selected = None; failure = None
    for step in range(cfg['max_steps']):
        prompt = {'operation': 'act', 'task': problem.brief(), 'history': history,
                  'remaining_evaluations': cfg['evaluation_budget']-calls,
                  'remaining_steps': cfg['max_steps']-step,
                  'rules': 'Return one JSON action. Every evaluate attempt costs one query, including invalid or duplicate plans. Submit a previously evaluated feasible plan before limits expire. No file access or code execution. No final-weather scores are available. Use geometry/material tradeoffs and feedback; keep reason concise.'}
        event(root, 'model_request', repeat=repeat, step=step, prompt=prompt)
        try:
            response = provider.complete(prompt, ACTION, cfg['max_output_tokens'])
            event(root, 'model_response', repeat=repeat, step=step, response=response)
            if sorted((response.get('model_usage') or {}).keys()) != [cfg['model']]:
                raise ValueError('Resolved model mismatch')
            action = provider.parse(response); jsonschema.validate(action, ACTION)
        except Exception as exc:
            failure = str(exc); event(root, 'model_error', repeat=repeat, step=step, error=failure); break
        if action['action'] == 'submit':
            result = evaluated.get(key(action['plan']))
            if result is not None and result['feasible']:
                selected = result; break
            history.append({'request': action, 'result': {'error': 'Submit an evaluated feasible plan'}})
        elif calls >= cfg['evaluation_budget']:
            history.append({'request': action, 'result': {'error': 'Evaluation budget exhausted'}})
        else:
            calls += 1
            result = problem.evaluate(action['plan'])
            evaluated[key(action['plan'])] = result
            history.append({'request': action, 'result': result})
            event(root, 'evaluation', method='claude', repeat=repeat, call=calls, result=result)
    record = {'method': 'claude', 'repeat': repeat, 'submitted': selected is not None,
              'development': selected, 'failure': failure if selected else (failure or 'No valid submission'),
              'calls_used': calls, 'wall_seconds': time.perf_counter()-started}
    event(root, 'episode', **record)
    return record


def features(plans):
    return np.asarray([p['height_steps']+[int(i in p['cool_sectors']) for i in range(4)] for p in plans], dtype=float)


def gp_choice(observations, candidates):
    """Same finite RBF constrained-EI approach as the existing solar benchmark."""
    x = features([r['plan'] for r in observations]); query = features(candidates)
    kernel = lambda a, b: np.exp(-np.sum((a[:, None]-b[None])**2, axis=2)/4.)
    k = kernel(x, x)+np.eye(len(x))*1e-6; cross = kernel(x, query)
    variance = np.maximum(1-np.sum(cross*np.linalg.solve(k, cross), axis=0), 1e-12)
    def posterior(name):
        y = np.asarray([r[name] for r in observations]); scale = max(float(y.std()), 1e-6)
        return y.mean()+scale*(cross.T@np.linalg.solve(k, (y-y.mean())/scale)), scale*np.sqrt(variance)
    cdf = lambda z: .5*(1+np.asarray([math.erf(float(v)/math.sqrt(2)) for v in z]))
    mu, sd = posterior('score'); z = (mu-best(observations)['score'])/sd
    ei = (mu-best(observations)['score'])*cdf(z)+sd*np.exp(-z*z/2)/np.sqrt(2*np.pi)
    violation, uncertainty = posterior('constraint')
    return candidates[int(np.argmax(ei*cdf(-violation/uncertainty)))]


def baseline_episode(root, problem, pool, method, seed):
    started = time.perf_counter(); rng = np.random.default_rng(seed)
    observations = [problem.evaluate(BASE)]; tried = {key(BASE)}
    for call in range(problem.cfg['evaluation_budget']):
        remaining = [p for p in pool if key(p) not in tried]
        if method == 'materials_only':
            remaining = [p for p in remaining if not any(p['height_steps'])]
        if not remaining: break
        if method == 'materials_only': plan = remaining[0]
        else: plan = remaining[int(rng.integers(len(remaining)))] if method == 'random' or call < 3 else gp_choice(observations, remaining)
        result = problem.evaluate(plan); observations.append(result); tried.add(key(plan))
        event(root, 'evaluation', method=method, repeat=seed, call=call+1, result=result)
    record = {'method': method, 'repeat': seed, 'submitted': True, 'development': best(observations),
              'failure': None, 'calls_used': len(observations)-1, 'wall_seconds': time.perf_counter()-started}
    event(root, 'episode', **record)
    return record


def run(root):
    root = Path(root); verify(root)
    state = read(root/'state.json'); assert state['status'] == 'prepared', 'Prepare a fresh run; never overwrite a failed trial'
    state['status'] = 'running'; write_json(root/'state.json', state)
    try:
        problem = ClimateProblem(root); cfg = problem.cfg
        provider = ClaudeCodeProvider(cfg['model'], timeout=240)
        pool = problem.plans()
        write_json(root/'task_brief.json', problem.brief())
        write_json(root/'legal_plans.json', pool)
        write_json(root/'environment.json', {'python': sys.version, 'numpy': np.__version__, 'cli_version': provider.version})
        records = []
        for repeat in range(cfg['agent_repetitions']):
            records.append(agent_episode(root, problem, provider, repeat))
            print('AGENT', repeat, records[-1]['submitted'], records[-1]['failure'], flush=True)
        for method in ('random', 'gp'):
            for seed in cfg['baseline_seeds']:
                records.append(baseline_episode(root, problem, pool, method, seed))
                print('BASELINE', method, seed, records[-1]['development']['score'], flush=True)
        if cfg.get('include_materials_control'):
            records.append(baseline_episode(root, problem, pool, 'materials_only', 0))
        # Freeze every online selection before evaluating ANY held-out weather.
        write_json(root/'frozen_selections.json', records)
        event(root, 'selections_frozen')
        for record in records:
            record['holdout'] = problem.evaluate(record['development']['plan'], 'holdout') if record['submitted'] else None
            event(root, 'holdout_score', method=record['method'], repeat=record['repeat'], result=record['holdout'])
        verify(root)
        write_json(root/'results.json', records)
        state['status'] = 'complete'; write_json(root/'state.json', state)
        print('COMPLETE', root, flush=True)
    except Exception as exc:
        state.update(status='failed', error=str(exc)); write_json(root/'state.json', state); raise


def export(root):
    """Run under the existing Python >=3.11 contract environment after simulation."""
    from common.contract import validate
    from common.runs import promote
    root = Path(root); verify(root); cfg = read(root/'config.json'); state = read(root/'state.json')
    assert state['status'] == 'complete'
    records = read(root/'results.json'); events = [json.loads(x) for x in (root/'events.jsonl').read_text().splitlines()]
    frozen = next(i for i, e in enumerate(events) if e['kind'] == 'selections_frozen')
    assert all(i < frozen for i, e in enumerate(events) if e['kind'] in ('model_request', 'evaluation', 'episode'))
    assert all(i > frozen for i, e in enumerate(events) if e['kind'] == 'holdout_score')
    assert all(r['calls_used'] <= cfg['evaluation_budget'] for r in records)
    responses = [e['response'] for e in events if e['kind'] == 'model_response']
    summary = []
    for method in dict.fromkeys(record['method'] for record in records):
        group = [r for r in records if r['method'] == method]
        values = [r['holdout']['score']*100 for r in group if r['holdout'] and r['holdout']['feasible']]
        summary.append({'method': method, 'episodes': len(group), 'submissions': sum(r['submitted'] for r in group),
                        'holdout_feasible': len(values), 'conditional_holdout_cooling_percent': statistics.mean(values) if values else None,
                        'mean_calls': statistics.mean(r['calls_used'] for r in group),
                        'mean_wall_seconds': statistics.mean(r['wall_seconds'] for r in group)})
    report = {'run_id': state['run_id'], 'scope': cfg['scope'], 'legal_plans': len(read(root/'legal_plans.json')),
              'summary': summary, 'trials': records, 'model_calls': len(responses),
              'input_tokens': sum(r.get('usage', {}).get('input_tokens', 0) for r in responses),
              'output_tokens': sum(r.get('usage', {}).get('output_tokens', 0) for r in responses),
              'reported_cost_usd': sum(r.get('reported_cost_usd') or 0 for r in responses),
              'resolved_models': sorted({m for r in responses for m in r.get('model_usage', {})}),
              'audit': {'all_selections_frozen_before_holdout': True, 'code_inputs_verified': True,
                        'cache_hits_still_charged': True, 'no_scripted_model_fallback': True},
              'limitations': ['Two stochastic repeats per method; deterministic material control once when enabled. One crop, controlled weather; no significance/generalization claim.',
                             'No direct comparison to solar-only scores; objectives and physics differ.',
                             'No learned surrogate or self-improvement. Absolute temperatures are uncalibrated screening outputs.',
                             'All methods receive the unchanged-plan baseline without charge; development and holdout each aggregate two scenarios.',
                             'Shared deterministic simulation cache means wall times are not fair cold-start speed comparisons.',
                             'Holdout feasibility may fail; do not average only feasible trials as evidence of overall superiority.']}
    write_json(root/'report.json', report)
    layers = []
    labels = [r['method']+str(r['repeat']) for r in records]
    for name, values in (
        ('submitted', [int(r['submitted']) for r in records]),
        ('holdout_feasible', [int(bool(r['holdout']) and r['holdout']['feasible']) for r in records]),
        ('holdout_cooling_fraction', [r['holdout']['score'] if r['holdout'] else 0 for r in records])):
        asset = 'data/'+name+'.json'; write_json(root/asset, {'labels': labels, 'values': values})
        layers.append({'id': name, 'kind': 'time_series', 'format': 'json', 'asset': asset, 'sampling': 'static',
                       'field': {'name': name, 'unit': '1'}, 'display': {'widget': 'time_series', 'capabilities': ['legend']}})
    # Physical maps for a development-selected agent plan, never chosen by holdout.
    candidates = [r for r in records if r['method'] == 'claude' and r['submitted']]
    if candidates:
        chosen = max(candidates, key=lambda r: r['development']['score'])
        simulation = chosen['development']['weather'][0]['simulation_id']
        with np.load(root/'simulations'/simulation/'fields.npz') as fields:
            np.save(root/'data/air.npy', fields['air_c'].astype('<f4'))
            np.save(root/'data/air_invalid.npy', (~fields['receptor_mask']).astype('u1'))
        layers.append({'id': 'selected_development_air', 'kind': 'scalar_field', 'format': 'npy', 'asset': 'data/air.npy',
                       'sampling': 'static', 'field': {'name': 'temperature', 'unit': 'degC'},
                       'encoding': {'coordinate_frame': 'ENU', 'dtype': '<f4', 'shape': [32, 32], 'axes': 'YX',
                                    'origin_m': [64, -128, 12], 'spacing_m': [8, 8], 'sample_location': 'cell_center',
                                    'byte_order': 'little', 'compression': 'none', 'mask_asset': 'data/air_invalid.npy',
                                    'mask_dtype': '|u1', 'mask_semantics': 'invalid_nonzero'},
                       'display': {'widget': 'scalar_field', 'capabilities': ['pick', 'legend', 'opacity']}})
    storage = Storage.load(); identity = read(root/'identity.json')
    artifacts = [{'id': 'source_snapshot' if path == root/'source_snapshot.tar.gz' else 'artifact_'+str(i),
                  'asset': str(path.relative_to(root)), 'sha256': sha(path), 'media_type': 'application/octet-stream'}
                 for i, path in enumerate(sorted(root.rglob('*'))) if path.is_file() and path.name != 'manifest.json']
    manifest = {'schema_version': '1.1.0', 'scene_id': 'south_ken', 'simulation': 'coupled_climate',
                'run_id': state['run_id'], 'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
                'provenance': {'code_revision': identity['code_revision'], 'dirty': True, 'parameters': cfg,
                               'inputs': [{'id': 'frozen_inputs', 'sha256': sha(root/'inputs.npz')}]},
                'spatial': read(storage.metadata('south_ken')/'project.json')['spatial'],
                'time': {'unit': 's', 'samples': []}, 'layers': layers, 'artifacts': artifacts}
    write_json(root/'manifest.json', manifest); validate(root/'manifest.json')
    destination = promote(storage, root)
    write_json(storage.metadata('south_ken')/'reports'/('agentic-coupled-climate-'+state['run_id']+'.json'), report)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'run', 'export'))
    parser.add_argument('path')
    args = parser.parse_args()
    print({'prepare': prepare, 'run': run, 'export': export}[args.action](args.path))
