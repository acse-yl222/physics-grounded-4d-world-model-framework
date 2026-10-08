"""Compare a converged reference with digitized Fig. B.33, without fitting parameters."""
import argparse
import json
from pathlib import Path

import numpy as np

from common.contract import validate
from common.export import digest, write


def ordered_profile(x, values):
    x, values = np.asarray(x), np.asarray(values)
    if x.ndim != 1 or values.shape != x.shape or len(x) < 2:
        raise ValueError('Expected paired profile coordinates and values')
    if not np.isfinite(x).all() or not np.isfinite(values).all():
        raise ValueError('Nonfinite profile')
    order = np.argsort(x)
    x, values = x[order], values[order]
    unique, indices = np.unique(x, return_index=True)
    if any(np.ptp(values[x == position]) != 0 for position in unique):
        raise ValueError('Conflicting duplicate samples')
    if len(unique) < 2:
        raise ValueError('Insufficient distinct coordinates')
    return unique, values[indices]


def errors(x, values, target):
    target = np.asarray(target, dtype=float)
    if target.ndim != 2 or target.shape[1] != 2 or not np.isfinite(target).all():
        raise ValueError('Invalid digitized reference')
    if len(target) == 0 or target[:, 0].min() < x[0] or target[:, 0].max() > x[-1]:
        raise ValueError('Comparison would extrapolate outside computed profile')
    delta = np.interp(target[:, 0], x, values) - target[:, 1]
    return dict(points=len(target), rms=float(np.sqrt(np.mean(delta**2))),
                max_absolute=float(np.abs(delta).max()), mean_signed=float(delta.mean()))


def compare(run, paper, output):
    run, paper, output = map(Path, (run, paper, output))
    if output.exists():
        raise FileExistsError(output)
    validate(run/'manifest.json')
    summary = json.loads((run/'reference_summary.json').read_text())
    if not summary['numerical_convergence_verified']:
        raise ValueError('Only converged runs may be compared')
    config = json.loads((run/'configuration.json').read_text())
    reference = json.loads(paper.read_text())
    model = config['turbulence_model']
    # Fig. B.33 labels SST; Table 14 footnote specifies LF18 stabilization.
    paper_model = {'kEpsilon':'kEpsilon','kOmegaSST':'kOmegaSST',
                   'paperSSTLF18':'kOmegaSST'}[model]
    comparisons = []
    for profile in reference['profiles']:
        distance = profile['x_over_D']
        data = json.loads((run/f'data/wake_{distance}d.json').read_text())
        y = (np.asarray(data['positions'])[:, 1]-config['hub_xyz_m'][1])/(config['rotor_diameter_m']/2)
        x, values = ordered_profile(y, data['values'])
        comparisons.append(dict(x_over_D=distance,
            computed_vs_paper_model=errors(x, values, profile['curves'][paper_model]),
            computed_vs_digitized_experiment=errors(x, values, profile['experimental_markers']),
            identical_duplicates_removed=len(y)-len(x)))
    result = dict(run_id=run.name, model=model, paper_curve_model=paper_model, manifest_sha256=digest(run/'manifest.json'),
                  figure_data_sha256=digest(paper), source_pdf_sha256=reference['source_pdf_sha256'],
                  comparisons=comparisons, experimental_accuracy_validated=False,
                  interpretation='Deficit 1-U/Uref, transverse coordinate (y-hub_y)/R. Computed profiles linearly interpolated at digitized curve vertices or experimental marker centres; no extrapolation or parameter fitting. Curve-vertex RMS depends on PDF vertex spacing. Digitized measurements are not raw experimental data; these errors alone do not establish reproduction fidelity.')
    write(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('paper', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.run, args.paper, args.output), indent=2))
