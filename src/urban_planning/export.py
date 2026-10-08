"""Export pilot maps and complete evaluation inputs using the existing v1 contract."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import numpy as np

from common.contract import validate
from common.provenance import snapshot_sources
from common.storage import Storage
from .problem import Problem, digest, write_json
from .solar import panel_occlusion, reduced_energy


def export(directory):
    problem = Problem(directory)
    benchmark = json.loads((problem.directory/'benchmark.json').read_text())
    if benchmark['identity'] != problem.identity:
        raise ValueError('Benchmark evaluated different task/input/source identities')
    out = problem.directory/'export'
    out.mkdir(exist_ok=False)
    layers = []
    artifacts = []
    def artifact(path, role, media='application/json'):
        artifacts.append({'id': role, 'asset': str(path.relative_to(out)),
                          'sha256': digest(path), 'media_type': media})
    for name in ('task.json', 'config.json', 'input_provenance.json', 'spatial.json', 'benchmark.json', 'background.npz'):
        shutil.copy2(problem.directory/name, out/name)
        artifact(out/name, name.replace('.', '_'), 'application/octet-stream' if name.endswith('.npz') else 'application/json')
    for path in sorted((problem.directory/'sessions').glob('*.json')):
        state = json.loads(path.read_text())
        if state['identity'] != problem.identity:
            raise ValueError('Session identity mismatch')
        destination = out/'sessions'/path.name
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(path, destination)
        artifact(destination, f'session_{path.stem}')
    positions = problem.arrays['receptors'].copy()
    positions[:, 2] = 0  # Explicit 2-D planning plane, not an invented ground height.
    for phase, reference in benchmark['offline_exhaustive_reference'].items():
        plan = reference['development']['plan']
        panels = [problem.candidates[x] for x in plan]
        for season in ('summer', 'winter'):
            benefit = np.zeros(len(positions))
            for split in ('development', 'holdout'):
                prefix = f'{season}_{split}_'
                shade = panel_occlusion(problem.arrays['receptors'], panels,
                                        problem.arrays[prefix+'altitude_deg'], problem.arrays[prefix+'azimuth_deg'])
                benefit += reduced_energy(problem.arrays[prefix+'direct_w_m2'], problem.arrays[prefix+'duration_s'], shade)
            layer_id = f'{phase}_{season}_direct_reduction'
            asset = f'data/{layer_id}.json'
            write_json(out/asset, {'positions': positions.tolist(), 'values': benefit.tolist()})
            artifact(out/asset, f'checksum_{layer_id}')
            layers.append({'id': layer_id, 'kind': 'scalar_field', 'format': 'json', 'asset': asset,
                           'sampling': 'static', 'field': {'name': 'direct_ground_irradiation_reduction_10_16utc', 'unit': 'kWh/m2'},
                           'display': {'widget': 'scalar_field', 'capabilities': ['pick', 'legend']}})
    root = Storage.load().root
    revision = snapshot_sources(root, out/'source_snapshot.tar.gz')
    artifact(out/'source_snapshot.tar.gz', 'source_snapshot', 'application/gzip')
    manifest = {'schema_version': '1.1.0', 'scene_id': problem.task['scene_id'], 'simulation': 'urban_planning',
                'run_id': problem.task['run_id'], 'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
                'provenance': {'code_revision': revision, 'dirty': True,
                               'parameters': {'pilot': True, 'source_solver_provenance': problem.task['source_solver_provenance'],
                                              'physical_scope': problem.task['physical_scope'],
                                              'display': 'Offline reference solutions, static accumulated direct-radiation reduction, z=0 planning plane.',
                                              'claim': 'No LLM superiority, thermal comfort or real intervention benefit established.'},
                               'inputs': [{'id': 'task', 'sha256': problem.identity['task_sha256']},
                                          {'id': 'background', 'sha256': problem.identity['background_sha256']}]},
                'spatial': json.loads((out/'spatial.json').read_text()), 'time': {'unit': 's', 'samples': []},
                'layers': layers, 'artifacts': artifacts}
    write_json(out/'manifest.json', manifest)
    validate(out/'manifest.json')
    return out/'manifest.json'
