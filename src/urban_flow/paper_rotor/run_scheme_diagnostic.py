"""Run a paired SST turbulence-advection diagnostic on the formal B.2 mesh.

Only turbulence advection changes from the retained baseline. This is a
numerical sensitivity study, not an assertion about unpublished author schemes.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil

from common.export import digest, write
from common.provenance import snapshot_sources
from common.runtime import trial_root
from common.storage import Storage
from common.runs import promote
from .openfoam_reference import build_case, execute, IMAGE
from .analyze_reference import analyze
from .compare_paper_profiles import compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scheme', choices=['upwind', 'linearUpwind', 'limitedLinear'], default='linearUpwind')
    parser.add_argument('--momentum-scheme', choices=['upwind','linearUpwind'], default='linearUpwind')
    parser.add_argument('--model', choices=['kEpsilon', 'kOmega', 'kOmegaSST', 'paperSSTLF18'], default='kOmegaSST')
    parser.add_argument('--baseline-run', default='20260929T102827Z_052a5c78')
    parser.add_argument('--radii-hypothesis', action='store_true', help='Diagnostic only: interpret printed outer/inner diameters as radii, based on Fig B.31 mesh-image audit')
    parser.add_argument('--warm-start-fields', type=Path, help='Reconstructed field directory from a converged case with identical mesh and physical inputs')
    args = parser.parse_args()
    storage = Storage.load()
    metadata = storage.metadata('actuator_lab')
    baseline = storage.run('actuator_lab', args.baseline_run)
    config = json.loads((baseline/'configuration.json').read_text())
    config['turbulence_advection'] = args.scheme
    config['momentum_advection'] = args.momentum_scheme
    inherited_geometry = config.get('diagnostic', {}).get('geometry_hypothesis')
    config['diagnostic'] = {
        'baseline_run': baseline.name,
        'baseline_configuration_sha256': digest(baseline/'configuration.json'),
        'changed_numerics': f'k/omega: {args.scheme}; momentum: {args.momentum_scheme}',
        'requested_turbulence_model': args.model,
        'author_scheme_known': False,
        'purpose': 'Isolate turbulence-transport numerical diffusion without tuning physical inputs.'}
    if inherited_geometry:
        config['diagnostic']['geometry_hypothesis'] = inherited_geometry
    if args.model == 'kOmega':
        config['assumptions'].append('Standard kOmega is a supplementary closure sensitivity study; Fig B.33 has no corresponding standard kOmega curve.')
    if args.model == 'paperSSTLF18':
        config['assumptions'] = [v for v in config.get('assumptions', []) if 'limiter not implemented' not in v]
        config['assumptions'].append('Independent LF18 implementation; author source/case dictionaries unavailable. This is a reproduction diagnostic, not an exact author case.')
    if args.radii_hypothesis:
        config['rotor_diameter_m'] *= 2
        config['inner_diameter_m'] *= 2
        config['diagnostic']['geometry_hypothesis'] = 'Fig B.31 mesh count suggests ~2x printed diameter; interpret both printed dimensions as radii. Not author-confirmed.'
        config['diagnostic']['purpose'] = 'Test a documented text/mesh-image inconsistency, not fit wake curves.'
        config['assumptions'].append('Outer/inner diameter doubled relative to text; hypothesis only. Profiles normalized with the actual changed diameter.')
        config['matched_parameters'] = [v for v in config.get('matched_parameters', []) if v not in ('rotor_diameter_m', 'inner_diameter_m')]
    target = trial_root('actuator_lab', 'openfoam_scheme_diagnostic')
    if args.warm_start_fields:
        source_case = args.warm_start_fields.parent
        source_cfg = json.loads((source_case/'configuration.json').read_text())
        source_summary = json.loads((source_case/'reference_summary.json').read_text())
        if not source_summary['numerical_convergence_verified']:
            raise ValueError('Warm start must come from a converged case')
        for key in ['grid_cells_xyz','actual_spacing_xyz_m','domain_xyz_m','hub_xyz_m','rotor_diameter_m','inner_diameter_m','ct','inlet_m_s','sigma_m','rotor_thickness_m','turbulence_intensity','turbulence_length_m','kinematic_viscosity_m2_s']:
            if source_cfg[key] != config[key]:
                raise ValueError('Warm-start mismatch: '+key)
        names = ['U','p','k','omega','nut','phi']
        config['warm_start'] = {'source_run': source_case.name, 'iteration': args.warm_start_fields.name, 'fields_sha256': {name:digest(args.warm_start_fields/name) for name in names}, 'interpretation':'Initial guess only; all target residual/conservation/stationarity gates still required.'}
    build_case(target, config, args.model, 2500, 4)
    if args.warm_start_fields:
        for name in names:
            shutil.copyfile(args.warm_start_fields/name, target/'0'/name)
    revision = snapshot_sources(storage.root, target/'source_snapshot.tar.gz')
    write(target/'provenance.json', {
        'code_revision': revision, 'dirty': True,
        'source_snapshot_sha256': digest(target/'source_snapshot.tar.gz')})
    suffix = '' if args.model == 'kOmegaSST' else '_'+args.model
    if args.radii_hypothesis or inherited_geometry:
        suffix += '_radii_hypothesis'
    job = metadata/f'openfoam_{args.scheme}_{args.momentum_scheme}{suffix}_diagnostic_job.json'
    record = {'case': str(target), 'baseline_run': baseline.name,
              'state': 'running', 'experimental_accuracy_validated': False}
    write(job, record)
    print(target, flush=True)
    try:
        execute(target)
        # Re-sample reconstructed fields in serial to avoid incomplete MPI sets.
        command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '1',
                   '--user', f'{os.getuid()}:{os.getgid()}',
                   '-v', f'{target.resolve()}:/case', '-w', '/case',
                   '--entrypoint', '/bin/bash', IMAGE, '-lc',
                   'source /usr/lib/openfoam/openfoam2312/etc/bashrc; '
                   'postProcess -fields "(U k nut)" -latestTime > log.serialProfiles 2>&1']
        subprocess.run(command, check=True)
        sampling_log = (target/'log.serialProfiles').read_text()
        if 'Cannot find functionObject' in sampling_log or 'Cannot find registered field' in sampling_log:
            raise RuntimeError('Serial profile sampling did not execute')
        summary = analyze(target)
        if summary['numerical_convergence_verified'] and args.model != 'kOmega':
            compare(target, metadata/'formal_figure_b33.json', target/'paper_comparison.json')
        manifest = json.loads((target/'manifest.json').read_text())
        for name, mime in [('paper_comparison.json', 'application/json'),
                           ('log.serialProfiles', 'text/plain')]:
            if (target/name).exists():
                manifest['artifacts'].append({'id': Path(name).stem.replace('.', '_'),
                    'asset': name, 'sha256': digest(target/name), 'media_type': mime})
        write(target/'manifest.json', manifest)
        retained = promote(storage, target)
        write(job, record | {'state': 'completed_and_audited',
                            'retained_run': str(retained), 'summary': summary})
    except Exception as error:
        write(job, record | {'state': 'failed', 'error': repr(error)})
        raise


if __name__ == '__main__':
    main()
