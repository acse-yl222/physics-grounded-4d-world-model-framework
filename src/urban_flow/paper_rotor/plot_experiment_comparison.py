"""Compare completed methods with the same digitized B.33 measurements."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from common.export import digest
from .compare_paper_profiles import errors, ordered_profile


def render(report, runs, out):
    out.mkdir(parents=True, exist_ok=False)
    paper_path = report/'paper_B33_digitized.json'
    common_path = report/'computed_profiles.json'
    paper = json.loads(paper_path.read_text())
    common = json.loads(common_path.read_text())
    specifications = [
        ('OpenFOAM SST', '20261005T185748Z_2e0e1c84', '#007f86'),
        ('OpenFOAM SST + LF18', '20261005T225803Z_bc9b3b47', '#e68a00'),
        ('OpenFOAM k-epsilon (matched numerics)', '20261006T093634Z_de892ab2', '#a4418b'),
        ('OpenFOAM standard k-omega', '20261006T093633Z_1d967ce5', '#946028'),
        ('PyTorch SST', '20261005T185458Z_e718707d', '#5059bd'),
    ]
    sources = {str(p): digest(p) for p in [paper_path, common_path]}
    metrics, exported = [], []
    fig, axes = plt.subplots(3, 3, figsize=(17, 11), sharex=True, sharey=True)
    for i, ref in enumerate(paper['profiles']):
        distance = ref['x_over_D']
        points = np.asarray(ref['experimental_markers'])
        groups = [[], [], []]
        for name, key, color in [('Paper SST', 'kOmegaSST', '#1764ba'), ('Paper k-epsilon', 'kEpsilon', '#c83e35')]:
            x, y = ordered_profile(*np.asarray(ref['curves'][key]).T)
            groups[0].append((name, x, y, color, '--'))
        for name, rid, color in specifications:
            run = runs/rid
            cfg_path = run/'configuration.json'
            cfg = json.loads(cfg_path.read_text())
            data_path = run/f'data/wake_{distance}d.json'
            data = json.loads(data_path.read_text())
            if name.startswith('OpenFOAM'):
                assert json.loads((run/'reference_summary.json').read_text())['numerical_convergence_verified']
            else:
                for audit_name in ['stationarity.json', 'full_state_stationarity.json']:
                    audit = run/audit_name
                    assert json.loads(audit.read_text())['finite_window_passed']
                    sources[str(audit)] = digest(audit)
            pos = np.asarray(data['positions'])
            assert np.allclose(pos[:, 0], cfg['hub_xyz_m'][0]+distance*cfg['rotor_diameter_m'])
            assert np.allclose(pos[:, 2], cfg['hub_xyz_m'][2])
            x, y = ordered_profile((pos[:, 1]-cfg['hub_xyz_m'][1])/(cfg['rotor_diameter_m']/2), data['values'])
            groups[1].append((name, x, y, color, '-'))
            sources[str(cfg_path)] = digest(cfg_path)
            sources[str(data_path)] = digest(data_path)
        row = next(r for r in common if r['x_over_D'] == distance)
        for name, key, color in [('PyWake Jensen', 'Jensen_1983', '#7750a1'), ('PyWake Gaussian', 'Bastankhah_PorteAgel_2014', '#448b32')]:
            x, y = ordered_profile(row['y_over_R'], row['curves'][key])
            groups[2].append((name, x, y, color, '-'))
        for col, group in enumerate(groups):
            ax = axes[i, col]
            ax.scatter(*points.T, facecolors='none', edgecolors='black', s=20, label='Digitized experiment', zorder=5)
            for name, x, y, color, style in group:
                ax.plot(x, y, color=color, ls=style, lw=1.8, label=name)
                metric = errors(x, y, points)
                metrics.append(dict(method=name, x_over_D=distance, **metric))
                exported.append(dict(method=name, x_over_D=distance, y_over_R=x.tolist(), deficit=y.tolist()))
            ax.set_title(f'{distance}D | '+['Published CFD', 'Our CFD', 'Engineering wake models'][col])
            ax.grid(alpha=.2)
            ax.set_xlim(-1.5, 1.5)
            if i == 0:
                ax.legend(fontsize=7, loc='upper right')
            if col == 0:
                ax.set_ylabel('Velocity deficit 1 - U/U0')
            if i == 2:
                ax.set_xlabel('(y - hub_y) / R')
    axes[0, 0].set_ylim(-.2, 1.05)
    fig.suptitle('Comparison against wind-tunnel measurements | Paper Fig. B.33', fontsize=17)
    fig.tight_layout(rect=[0, .065, 1, .96])
    fig.text(.02, .025, 'Same digitized experimental points in all panels; not raw measurements. OpenFOAM closures use matched geometry and upwind schemes.\n'
             'PyWake is an engineering approximation (no tunnel walls); high-Ct / near-wake applicability is limited. PyTorch passes finite-window stationarity checks, not SIMPLE residual checks.', fontsize=10)
    fig.savefig(out/'experiment_profiles.png', dpi=160)
    fig.savefig(out/'experiment_profiles.pdf')
    plt.close(fig)
    names = list(dict.fromkeys(r['method'] for r in metrics))
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, d in enumerate([1, 3, 5]):
        vals = [next(r['rms'] for r in metrics if r['method']==n and r['x_over_D']==d) for n in names]
        ax.bar(np.arange(len(names))+(i-1)*.25, vals, width=.25, label=f'{d}D')
    ax.set_xticks(np.arange(len(names)), [n.replace(' ', '\n', 1) for n in names], fontsize=8)
    ax.set_ylabel('RMSE of velocity deficit vs digitized experiment')
    ax.legend(); ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(out/'experiment_rmse.png', dpi=160); plt.close(fig)
    (out/'comparison.json').write_text(json.dumps(dict(sources_sha256=sources, metrics=metrics, profiles=exported,
        experimental_reference=paper, raw_measurements=False, accuracy_validated=False), indent=2)+'\n')
    with (out/'metrics.csv').open('w') as f:
        w=csv.DictWriter(f, fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--report', type=Path, required=True)
    p.add_argument('--runs', type=Path, required=True);p.add_argument('--out', type=Path, required=True)
    a=p.parse_args();render(a.report, a.runs, a.out)
