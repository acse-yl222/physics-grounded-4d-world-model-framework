"""Pre-registered B.2 sensitivity: force-region resolution per paper Section 2.2.1.

The paper states stable weighted-body-force behaviour needs sigma*sqrt(N) >= 2.5 dx
(N=2 default), but B.2 prints a 0.08 m rotor width (sigma=0.02 m), violating that
guidance about threefold on MM2. This run keeps N=2, Eq. 11, Ct=0.95, geometry,
mesh, inlet turbulence, closure and numerics from the baseline, and sets
sigma = 2.5 dx/sqrt(N). Width therefore departs from the printed value; both
values come from the paper. Not author-confirmed; no fitting.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess

from common.export import digest, write
from common.provenance import snapshot_sources
from common.runs import promote
from common.runtime import trial_root
from common.storage import Storage
from .openfoam_reference import build_case, execute, IMAGE
from .analyze_reference import analyze
from .compare_paper_profiles import compare

REGENERATED = ('turbulence_model', 'iterations', 'processes', 'openfoam_image', 'grid_cells_xyz',
               'actual_spacing_xyz_m', 'inlet_turbulence', 'boundary_conditions', 'time_semantics',
               'reproduction_status')


def resolved_config(baseline_config, factor=2.5):
    config = {k: v for k, v in baseline_config.items() if k not in REGENERATED}
    dx = baseline_config['actual_spacing_xyz_m'][0]
    n = config['cutoff_sigma']
    config['sigma_m'] = factor*dx/math.sqrt(n)
    config['rotor_thickness_m'] = 2*n*config['sigma_m']
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-run', default='20261005T225803Z_bc9b3b47')
    parser.add_argument('--preregistration', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    storage = Storage.load()
    metadata = storage.metadata('actuator_lab')
    baseline = storage.run('actuator_lab', args.baseline_run)
    base = json.loads((baseline/'configuration.json').read_text())
    model = base['turbulence_model']
    config = resolved_config(base)
    config['diagnostic'] = {
        'baseline_run': baseline.name,
        'baseline_configuration_sha256': digest(baseline/'configuration.json'),
        'baseline_diagnostic': base.get('diagnostic'),
        'changed': f"sigma_m {base['sigma_m']} -> {config['sigma_m']:.6g}; rotor_thickness_m {base['rotor_thickness_m']} -> {config['rotor_thickness_m']:.6g}",
        'paper_basis': 'Section 2.2.1 sigma*sqrt(N) >= 2.5 dx; conflicts with printed B.2 width 0.08 m',
        'preregistration_sha256': digest(args.preregistration),
        'author_confirmed': False,
        'purpose': 'Discriminate force-region resolution from shear-layer turbulence onset as cause of centre-jet persistence.'}
    config['assumptions'] = list(base.get('assumptions', [])) + [
        'Force-region sigma follows the paper stability guidance; rotor width therefore differs from printed 0.08 m.']
    config['matched_parameters'] = [v for v in base.get('matched_parameters', []) if v != 'rotor_thickness_m']
    target = trial_root('actuator_lab', 'opus_independent')
    build_case(target, config, model, 2500, 4)
    (target/'preregistration.json').write_bytes(args.preregistration.read_bytes())
    revision = snapshot_sources(storage.root, target/'source_snapshot.tar.gz')
    write(target/'provenance.json', {'code_revision': revision, 'dirty': True,
                                    'source_snapshot_sha256': digest(target/'source_snapshot.tar.gz')})
    print(target, flush=True)
    if args.prepare_only:
        return
    execute(target)
    command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '1',
               '--user', f'{os.getuid()}:{os.getgid()}', '-v', f'{target.resolve()}:/case', '-w', '/case',
               '--entrypoint', '/bin/bash', IMAGE, '-lc',
               'source /usr/lib/openfoam/openfoam2312/etc/bashrc; '
               'postProcess -fields "(U k nut)" -latestTime > log.serialProfiles 2>&1']
    subprocess.run(command, check=True)
    log = (target/'log.serialProfiles').read_text()
    if 'Cannot find functionObject' in log or 'Cannot find registered field' in log:
        raise RuntimeError('Serial profile sampling did not execute')
    summary = analyze(target)
    manifest = json.loads((target/'manifest.json').read_text())
    extras = [('preregistration', 'preregistration.json', 'application/json'),
              ('serial_profiles_log', 'log.serialProfiles', 'text/plain')]
    if summary['numerical_convergence_verified']:
        compare(target, metadata/'formal_figure_b33.json', target/'paper_comparison.json')
        extras.append(('paper_comparison', 'paper_comparison.json', 'application/json'))
    for key, name, mime in extras:
        manifest['artifacts'].append({'id': key, 'asset': name, 'sha256': digest(target/name), 'media_type': mime})
    write(target/'manifest.json', manifest)
    if summary['numerical_convergence_verified']:
        print('retained', promote(storage, target), flush=True)


if __name__ == '__main__':
    main()
