"""Immutable pilot task, constraints and numerical evaluator shared by all methods."""
from pathlib import Path
import hashlib
import itertools
import json
import time

import numpy as np

from .solar import panel_occlusion, reduced_energy


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


class Problem:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.task = json.loads((self.directory / 'task.json').read_text())
        self.candidates = {p['id']: p for p in self.task['candidates']}
        if len(self.candidates) != len(self.task['candidates']):
            raise ValueError('Duplicate candidate IDs')
        with np.load(self.directory / 'background.npz', allow_pickle=False) as data:
            self.arrays = {key: data[key] for key in data.files}
        self.identity = {
            'task_sha256': digest(self.directory / 'task.json'),
            'background_sha256': digest(self.directory / 'background.npz'),
            'evaluator_sha256': digest(Path(__file__)),
            'solar_sha256': digest(Path(__file__).with_name('solar.py')),
        }

    def constraints(self, phase):
        if phase not in self.task['phases']:
            raise ValueError('Unknown phase')
        return self.task['phases'][phase]

    def validate_plan(self, plan, phase):
        constraints = self.constraints(phase)
        if not isinstance(plan, list) or any(not isinstance(x, str) for x in plan):
            return ['Plan must be an array of candidate IDs']
        errors = []
        if len(set(plan)) != len(plan):
            errors.append('Duplicate candidate IDs')
        if set(plan) - self.candidates.keys():
            errors.append('Unknown candidate IDs')
        if len(plan) > constraints['max_panels']:
            errors.append('Panel count budget exceeded')
        if set(plan) & set(constraints['excluded_ids']):
            errors.append('Site unavailable in this phase')
        if errors:
            return errors
        panels = [self.candidates[x] for x in plan]
        if sum(p['cost_units'] for p in panels) > constraints['max_cost_units']:
            errors.append('Cost budget exceeded')
        for a, b in itertools.combinations(panels, 2):
            if (abs(a['x_m'] - b['x_m']) < (a['width_m'] + b['width_m']) / 2
                    and abs(a['y_m'] - b['y_m']) < (a['depth_m'] + b['depth_m']) / 2):
                errors.append('Overlapping panels')
        return errors

    def evaluate(self, plan, phase='initial', split='development'):
        if split not in ('development', 'holdout'):
            raise ValueError('Unknown split')
        start = time.perf_counter()
        errors = self.validate_plan(plan, phase)
        if errors:
            return {'plan': plan, 'feasible': False, 'errors': errors,
                    'phase': phase, 'split': split, 'wall_seconds': time.perf_counter() - start}
        panels = [self.candidates[x] for x in plan]
        result = {'plan': sorted(plan), 'phase': phase, 'split': split,
                  'cost_units': sum(p['cost_units'] for p in panels)}
        for season in ('summer', 'winter'):
            prefix = f'{season}_{split}_'
            direct = self.arrays[prefix + 'direct_w_m2']
            dt = self.arrays[prefix + 'duration_s']
            shade = panel_occlusion(self.arrays['receptors'], panels,
                                    self.arrays[prefix + 'altitude_deg'], self.arrays[prefix + 'azimuth_deg'])
            benefit = reduced_energy(direct, dt, shade)
            baseline = float((direct * dt[:, None]).sum() / 3.6e6)
            fraction = float(benefit.sum() / baseline) if baseline > 0 else 0.0
            result[f'{season}_reduction_fraction'] = fraction
            result[f'{season}_mean_reduction_kwh_m2'] = float(benefit.mean())
        cap = self.constraints(phase)['max_winter_loss_fraction']
        result['errors'] = [] if result['winter_reduction_fraction'] <= cap + 1e-12 else ['Winter direct-sunlight loss limit exceeded']
        result['feasible'] = not result['errors']
        result['wall_seconds'] = time.perf_counter() - start
        return result

    def plans(self, phase):
        c = self.constraints(phase)
        ids = sorted(self.candidates.keys() - set(c['excluded_ids']))
        return [list(p) for n in range(c['max_panels'] + 1) for p in itertools.combinations(ids, n)
                if not self.validate_plan(list(p), phase)]


def best_result(results):
    feasible = [r for r in results if r['feasible']]
    return max(feasible, key=lambda r: (r['summer_reduction_fraction'], -r['cost_units'], tuple(r['plan']))) if feasible else None
