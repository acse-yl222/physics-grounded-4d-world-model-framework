"""Compare converged reference grids without treating refinement as experimental validation."""
import argparse
import json
from pathlib import Path

import numpy as np

from common.contract import validate
from common.export import digest, write


def compare(runs, output):
    records = []
    configs = []
    for root in map(Path, runs):
        validate(root/'manifest.json')
        config = json.loads((root/'configuration.json').read_text())
        summary = json.loads((root/'reference_summary.json').read_text())
        if not summary['numerical_convergence_verified']:
            raise ValueError(f'Unconverged grid: {root}')
        configs.append(config)
        records.append(dict(run_id=root.name, root=root, cell_m=config['cell_m'],
                            thrust_N=summary['last_thrust_N'],
                            manifest_sha256=digest(root/'manifest.json')))
    if len(records) < 3 or len({r['cell_m'] for r in records}) != len(records):
        raise ValueError('At least three distinct grids are required')
    # Only grid discretization may change; compare the complete physical configuration.
    ignored = {'cell_m', 'grid_cells_xyz', 'mesh_counts_xyz', 'actual_spacing_xyz_m', 'processes'}
    physical = [{k: v for k, v in c.items() if k not in ignored} for c in configs]
    if any(c != physical[0] for c in physical[1:]):
        raise ValueError('Configurations differ beyond grid or processor count')
    records.sort(key=lambda r: r['cell_m'], reverse=True)
    for coarse, fine in zip(records, records[1:]):
        fine['relative_thrust_change'] = (fine['thrust_N']-coarse['thrust_N'])/coarse['thrust_N']
        differences = {}
        for distance in (1, 3, 5):
            def profile(record):
                data = json.loads((record['root']/f'data/wake_{distance}d.json').read_text())
                y = np.asarray(data['positions'])[:, 1]
                values = np.asarray(data['values'])
                if not np.isfinite(y).all() or not np.isfinite(values).all() or np.any(np.diff(y) < 0):
                    raise ValueError('Invalid profile coordinates or values')
                unique, indices = np.unique(y, return_index=True)
                if any(np.ptp(values[y == position]) != 0 for position in unique):
                    raise ValueError('Conflicting duplicate profile samples')
                record.setdefault('sampling', {})[f'{distance}D'] = dict(
                    raw_points=len(y), unique_points=len(unique),
                    identical_duplicates_removed=len(y)-len(unique))
                return unique, values[indices]
            cy, cv = profile(coarse)
            fy, fv = profile(fine)
            if cy[0] != fy[0] or cy[-1] != fy[-1]:
                raise ValueError('Profile support differs')
            delta = fv-np.interp(fy, cy, cv)
            differences[f'{distance}D'] = dict(deficit_rms_change=float(np.sqrt(np.mean(delta**2))),
                                              deficit_max_change=float(np.max(np.abs(delta))))
        fine['profile_changes'] = differences
    for record in records:
        del record['root']
    result = dict(grids=records, experimental_accuracy_validated=False,
                  interpretation='Measured grid sensitivity only; identical coordinate/value duplicates removed and coarse profiles linearly interpolated at fine sample coordinates. No assumed asymptotic order or GCI; annular cell-centre masks may converge non-monotonically.')
    if Path(output).exists():
        raise FileExistsError(output)
    write(Path(output), result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.runs, args.output), indent=2))
