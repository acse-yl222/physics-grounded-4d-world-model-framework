"""Finite pilot baselines. Exhaustive reference is offline and outside agent budget."""
import itertools
import math
import time

import numpy as np

from .problem import Problem, best_result, write_json


def constrained_ei_choice(problem, phase, observations, candidates):
    """Finite-space GP constrained expected improvement, fixed RBF/noise settings.

    Both objective and winter loss are learned from charged observations only.
    Hyperparameters are fixed before the pilot, not fitted on exhaustive scores.
    """
    ids = sorted(problem.candidates)
    encode = lambda plans: np.array([[float(c in p) for c in ids] for p in plans])
    x = encode([r['plan'] for r in observations])
    query = encode(candidates)
    kernel = lambda a, b: np.exp(-np.sum((a[:, None, :] - b[None, :, :])**2, axis=2) / 4.0)
    k = kernel(x, x) + np.eye(len(x)) * 1e-6
    cross = kernel(x, query)
    variance = np.maximum(1 - np.sum(cross * np.linalg.solve(k, cross), axis=0), 1e-12)
    cdf = lambda z: .5 * (1 + np.array([math.erf(float(v) / math.sqrt(2)) for v in z]))
    def posterior(metric):
        y = np.array([r[metric] for r in observations])
        scale = max(float(y.std()), 1e-6)
        mu = y.mean() + scale * (cross.T @ np.linalg.solve(k, (y-y.mean()) / scale))
        return mu, scale * np.sqrt(variance)
    mu, sigma = posterior('summer_reduction_fraction')
    incumbent = best_result(observations)['summer_reduction_fraction']
    z = (mu-incumbent) / sigma
    improvement = (mu-incumbent)*cdf(z) + sigma*np.exp(-.5*z*z)/np.sqrt(2*np.pi)
    winter, winter_sd = posterior('winter_reduction_fraction')
    feasible_probability = cdf((problem.constraints(phase)['max_winter_loss_fraction']-winter)/winter_sd)
    return candidates[int(np.argmax(improvement * feasible_probability))]


def run_policy(problem, phase, method, seed, previous=None):
    constraints = problem.constraints(phase)
    ids = sorted(problem.candidates.keys() - set(constraints['excluded_ids']))
    budget = constraints['evaluation_budget']
    rng = np.random.default_rng(seed)
    results = [problem.evaluate([], phase)]
    requested = set()
    trace = []
    def evaluate(plan):
        if len(trace) >= budget or tuple(sorted(plan)) in requested:
            return None
        requested.add(tuple(sorted(plan)))
        r = problem.evaluate(plan, phase)
        results.append(r)
        trace.append({'call': len(trace)+1, 'result': r,
                      'best_feasible_summer_reduction': best_result(results)['summer_reduction_fraction']})
        return r
    started = time.perf_counter()
    if previous and method != 'random_search':
        repaired = [x for x in previous['plan'] if x in ids][:constraints['max_panels']]
        if repaired:
            evaluate(repaired)
    if method == 'random_search':
        pool = [p for p in problem.plans(phase) if p]
        for i in rng.permutation(len(pool))[:budget]:
            evaluate(pool[int(i)])
    elif method == 'gp_constrained_ei':
        pool = [p for p in problem.plans(phase) if p]
        for i in rng.permutation(len(pool))[:4]:
            evaluate(pool[int(i)])
        while len(trace) < budget:
            remaining = [p for p in pool if tuple(p) not in requested]
            if not remaining:
                break
            evaluate(constrained_ei_choice(problem, phase, results, remaining))
    elif method in ('single_site_ranking', 'feasible_local_search'):
        for candidate in ids:
            if len(trace) >= budget:
                break
            evaluate([candidate])
        singles = sorted([r for r in results if len(r['plan']) == 1 and r['feasible']],
                         key=lambda r: r['summer_reduction_fraction'], reverse=True)
        if method == 'single_site_ranking':
            ranked = [r['plan'][0] for r in singles]
            for k in range(2, constraints['max_panels']+1):
                evaluate(ranked[:k])
        else:
            while len(trace) < budget:
                incumbent = best_result(results)['plan']
                pool = []
                for c in ids:
                    if c not in incumbent:
                        pool.append(sorted(incumbent + [c]))
                        for old in incumbent:
                            pool.append(sorted([x for x in incumbent if x != old]+[c]))
                pool = sorted({tuple(p) for p in pool if tuple(p) not in requested
                               and not problem.validate_plan(p, phase)})
                if not pool:
                    break
                # Deterministic neighbourhood order, explicitly a scripted baseline.
                evaluate(list(pool[0]))
    else:
        raise ValueError('Unknown policy')
    best = best_result(results)
    return {'method': method, 'seed': seed, 'phase': phase, 'calls_used': len(trace),
            'wall_seconds': time.perf_counter()-started, 'development': best,
            'holdout': problem.evaluate(best['plan'], phase, 'holdout'), 'trace': trace}


def benchmark(directory):
    problem = Problem(directory)
    destination = problem.directory / 'benchmark.json'
    if destination.exists():
        raise FileExistsError(destination)
    runs = []
    for method in ('random_search', 'single_site_ranking', 'feasible_local_search', 'gp_constrained_ei'):
        # Deterministic policies are run once, not reported as ten independent replicates.
        seeds = problem.task['seeds'] if method in ('random_search', 'gp_constrained_ei') else [0]
        for seed in seeds:
            first = run_policy(problem, 'initial', method, seed)
            changed = run_policy(problem, 'changed', method, seed, first['development'])
            runs.extend((first, changed))
    oracle = {}
    for phase in problem.task['phases']:
        start = time.perf_counter()
        results = [problem.evaluate(p, phase) for p in problem.plans(phase)]
        best = best_result(results)
        oracle[phase] = {'evaluations': len(results), 'feasible_plans': sum(r['feasible'] for r in results),
                         'development': best, 'holdout': problem.evaluate(best['plan'], phase, 'holdout'),
                         'wall_seconds': time.perf_counter()-start}
    for r in runs:
        r['development_regret_fraction'] = oracle[r['phase']]['development']['summer_reduction_fraction'] - r['development']['summer_reduction_fraction']
    output = {'identity': problem.identity, 'runs': runs, 'offline_exhaustive_reference': oracle,
              'claims': ['Engineering pilot, not evidence of LLM superiority.',
                         'All online methods share task/evaluator and per-phase call caps; actual calls and wall time reported.',
                         'Exhaustive reference is an offline finite-space diagnostic, not a budget-matched baseline.',
                         'Changed-phase scripted methods inherit their own initial incumbent; holdout never informs selection.',
                         'Temporal holdout uses correlated intervals; no weather, geographic or field validation.',
                         'GP constrained EI uses binary site features, fixed RBF length scale and 1e-6 jitter; hyperparameter sensitivity is pending.',
                         'Multiobjective evolutionary baseline and repeated LLM cohort are pending.']}
    write_json(destination, output)
    return output
