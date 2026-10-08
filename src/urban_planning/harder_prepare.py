"""Derive a constrained size-choice experiment from existing city solar inputs."""
import argparse
import copy
from pathlib import Path
import shutil

import numpy as np

from common.storage import Storage, within
from .problem import Problem, digest, write_json
from .rsi.runner import read


def build(spec_path):
    spec = read(spec_path)
    storage = Storage.load()
    inputs = storage.assets(spec['scene_id'], 'input')
    source = within(inputs, spec['source_input'])
    target = within(inputs, spec['task_id'])
    task = read(source / 'task.json')
    assert task['scene_id'] == spec['scene_id']
    candidates, origins = [], {}
    for index, parent in enumerate(task['candidates']):
        for variant in spec['variants']:
            candidate = copy.deepcopy(parent)
            candidate['width_m'] *= variant['scale']
            candidate['depth_m'] *= variant['scale']
            candidate['cost_units'] = variant['cost_units'] + index % 2
            candidate['_parent'] = parent['id']
            candidates.append(candidate)
    np.random.default_rng(spec['permutation_seed']).shuffle(candidates)
    for index, candidate in enumerate(candidates):
        candidate['id'] = f'c{index:02d}'
        origins[candidate['id']] = candidate.pop('_parent')
    phases = copy.deepcopy(spec['phases'])
    for phase in phases.values():
        excluded = phase.pop('excluded_sites')
        phase['excluded_ids'] = [c for c, parent in origins.items() if parent in excluded]
    task.update(task_id=spec['task_id'], run_id=spec['task_id'], candidates=candidates,
                candidate_count=len(candidates), phases=phases,
                interpretation=spec['scope'], seeds=spec['baseline_seeds'])
    # Dimensions are now per option; remove misleading uniform-size metadata.
    task.pop('panel_width_m', None)
    task.pop('panel_depth_m', None)
    target.mkdir(parents=True, exist_ok=False)
    write_json(target / 'task.json', task)
    shutil.copy2(source / 'background.npz', target / 'background.npz')
    problem = Problem(target)
    counts = {phase: len(problem.plans(phase)) for phase in phases}
    write_json(target / 'preparation.json', {
        'spec': spec, 'source_input': spec['source_input'],
        'source_task_sha256': digest(source / 'task.json'),
        'background_sha256': digest(source / 'background.npz'),
        'generator_sha256': digest(Path(__file__)), 'parent_sites': origins,
        'structurally_feasible_plans': counts,
        'note': 'No physical scores or holdout values used in task construction.'})
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('spec')
    print(build(parser.parse_args().spec))
