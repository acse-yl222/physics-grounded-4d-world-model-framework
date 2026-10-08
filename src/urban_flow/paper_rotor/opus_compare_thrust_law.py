"""Paired comparison of thrust-law runs against digitized Fig. B.33 (no fitting).

Metrics per station: RMS against the paper SST curve (uniform 301 points on
|y/R|<=1.5 and at curve vertices), RMS against digitized experimental markers,
annular peak deficit, centre (y/R=0) deficit and trough contrast = peak - centre,
plus the momentum-integral Ct (opus_momentum_audit). Digitized markers are not
raw measurements; agreement with them is not experimental validation.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from common.export import digest, write
from .compare_paper_profiles import errors, ordered_profile
from .opus_momentum_audit import implied_ct, run_profiles

STATIONS = (1, 3, 5)


def shape(x, values):
    centre = float(np.interp(0.0, x, values))
    annulus = (np.abs(x) >= 0.3) & (np.abs(x) <= 1.0)
    peak = float(values[annulus].max())
    return dict(centre=centre, annular_peak=peak, trough_contrast=peak-centre)


def evaluate(run, figure):
    profiles, applied = run_profiles(run)
    out = dict(run_id=run.name, **applied, stations={})
    for profile in figure['profiles']:
        s = profile['x_over_D']
        x, v = ordered_profile(*profiles[s])
        curve = np.asarray(profile['curves']['kOmegaSST'])
        grid = np.linspace(-1.5, 1.5, 301)
        uniform = np.interp(grid, x, v)-np.interp(grid, *ordered_profile(curve[:, 0], curve[:, 1]))
        out['stations'][s] = dict(
            vs_paper_sst_uniform_rms=float(np.sqrt(np.mean(uniform**2))),
            vs_paper_sst_vertices=errors(x, v, curve),
            vs_digitized_experiment=errors(x, v, profile['experimental_markers']),
            shape=shape(x, v), implied_ct=implied_ct(x, v)[0])
    return out


def paper_shapes(figure):
    result = {}
    for profile in figure['profiles']:
        for name in ('kOmegaSST', 'kEpsilon'):
            c = np.asarray(profile['curves'][name]); x, v = ordered_profile(c[:, 0], c[:, 1])
            result.setdefault(name, {})[profile['x_over_D']] = dict(shape(x, v), implied_ct=implied_ct(x, v)[0])
        # Digitized markers contain coincident abscissae; average them for shape metrics only.
        m = np.asarray(profile['experimental_markers']); x = np.unique(m[:, 0])
        v = np.array([m[m[:, 0] == p, 1].mean() for p in x])
        result.setdefault('experiment_markers', {})[profile['x_over_D']] = shape(x, v)
    return result


def plot(runs, labels, figure, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    for ax, profile in zip(axes, figure['profiles']):
        s = profile['x_over_D']
        m = np.asarray(profile['experimental_markers'])
        ax.plot(m[:, 0], m[:, 1], 'ko', mfc='none', ms=4, label='Digitized experiment (Fig. B.33)')
        for name, style in (('kOmegaSST', 'b--'), ('kEpsilon', 'r--')):
            c = np.asarray(profile['curves'][name]); ax.plot(c[:, 0], c[:, 1], style, lw=1.2, label=f'Paper {name}')
        for run, label in zip(runs, labels):
            profiles, _ = run_profiles(run); x, v = ordered_profile(*profiles[s]); ax.plot(x, v, lw=2, label=label)
        ax.set_xlim(-1.5, 1.5); ax.set_ylim(-0.2, 1.0); ax.grid(alpha=.3)
        ax.set_title(f'X/D = {s}'); ax.set_ylabel('1 - U/U0')
    axes[-1].set_xlabel('(y - hub_y)/R'); axes[0].legend(fontsize=7, loc='upper right')
    fig.text(0.01, 0.005, 'Digitized markers are not raw data; no experimental validation claim.', fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('figure', type=Path)
    parser.add_argument('--run', type=Path, action='append', required=True)
    parser.add_argument('--label', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True, help='Directory to create')
    args = parser.parse_args()
    if len(args.run) != len(args.label):
        raise ValueError('One label per run')
    args.output.mkdir(parents=True, exist_ok=False)
    figure = json.loads(args.figure.read_text())
    result = dict(figure_sha256=digest(args.figure), paper=paper_shapes(figure),
                  runs={label: evaluate(run, figure) for run, label in zip(args.run, args.label)},
                  experimental_accuracy_validated=False)
    write(args.output/'comparison.json', result)
    plot(args.run, args.label, figure, args.output/'profiles.png')
    for label, r in result['runs'].items():
        print(label, f"T={r['thrust_N']:.3f}N ut={r['disc_speed_m_s']:.3f} Ct_applied={r['ct_applied_full_area_U0']:.3f}")
        for s, v in r['stations'].items():
            print(f"  {s}D paperSST uniform={v['vs_paper_sst_uniform_rms']:.4f} vertices={v['vs_paper_sst_vertices']['rms']:.4f}"
                  f" exp={v['vs_digitized_experiment']['rms']:.4f} centre={v['shape']['centre']:.3f}"
                  f" peak={v['shape']['annular_peak']:.3f} contrast={v['shape']['trough_contrast']:.3f} Ct_impl={v['implied_ct']:.3f}")
    for name, vals in result['paper'].items():
        print(name, {s: {k: round(x, 3) for k, x in v.items()} for s, v in vals.items()})


if __name__ == '__main__':
    main()
