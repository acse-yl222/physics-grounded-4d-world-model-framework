"""Infer the rotor thrust carried by wake profiles from the momentum-flux deficit.

For a steady wake with recovered pressure, T ~= rho U0^2 * int d(1-d) dA with
d = 1-U/U0. Assuming axisymmetry about the hub, a horizontal traverse gives
Ct_impl = 4 int_0^eta_max d(1-d) eta d eta (eta = r/R, mean of both halves).

The estimator is calibrated on retained OpenFOAM runs whose applied thrust is
logged, then applied unchanged to the digitized Fig. B.33 curves. Turbulence
closures redistribute but cannot remove momentum deficit, so this discriminates
force-law hypotheses independently of the turbulence model.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from common.export import digest, write

STATIONS = (1, 3, 5)


def implied_ct(eta, deficit, eta_max=1.5):
    eta = np.asarray(eta, float); deficit = np.asarray(deficit, float)
    halves = []
    for sign in (1, -1):
        mask = (sign*eta >= 0) & (sign*eta <= eta_max)
        r = np.abs(eta[mask]); d = deficit[mask]; order = np.argsort(r)
        halves.append(float(4*np.trapezoid(d[order]*(1-d[order])*r[order], r[order])))
    return float(np.mean(halves)), halves


def run_profiles(run):
    config = json.loads((run/'configuration.json').read_text())
    radius = config['rotor_diameter_m']/2; hub = config['hub_xyz_m'][1]
    profiles = {}
    for station in STATIONS:
        data = json.loads((run/f'data/wake_{station}d.json').read_text())
        y = np.asarray(data['positions'])[:, 1]
        profiles[station] = ((y-hub)/radius, np.asarray(data['values']))
    history = np.loadtxt(run/'rotor_iterations.csv', delimiter=',', skiprows=1)
    thrust = float(history[-1, 2])
    applied = thrust/(0.5*config['rho_kg_m3']*config['inlet_m_s']**2*np.pi*radius**2)
    return profiles, dict(thrust_N=thrust, disc_speed_m_s=float(history[-1, 1]), ct_applied_full_area_U0=applied)


def audit(runs, figure, eta_max=1.5):
    paper = json.loads(Path(figure).read_text())
    result = dict(method=__doc__.strip(), eta_max=eta_max, figure=str(figure), figure_sha256=digest(Path(figure)),
                  paper={}, runs={})
    for profile in paper['profiles']:
        for name, curve in profile['curves'].items():
            curve = np.asarray(curve)
            result['paper'].setdefault(name, {})[profile['x_over_D']] = implied_ct(curve[:, 0], curve[:, 1], eta_max)[0]
    for run in map(Path, runs):
        profiles, applied = run_profiles(run)
        implied = {s: implied_ct(*profiles[s], eta_max)[0] for s in STATIONS}
        result['runs'][run.name] = dict(applied, implied=implied,
            recovery_ratio={s: implied[s]/applied['ct_applied_full_area_U0'] for s in STATIONS})
    # Calibrate with the far-wake stations only: 1D retains unrecovered pressure.
    ratios = [r['recovery_ratio'][s] for r in result['runs'].values() for s in (3, 5)]
    if ratios:
        lo, hi = min(ratios), max(ratios)
        result['calibration_ratio_range_3D_5D'] = [lo, hi]
        result['paper_applied_ct_estimate'] = {name: {s: [v/hi, v/lo] for s, v in vals.items() if s in (3, 5)}
                                               for name, vals in result['paper'].items()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('figure', type=Path, help='paper_B33_digitized.json')
    parser.add_argument('runs', type=Path, nargs='+', help='Retained OpenFOAM run directories')
    parser.add_argument('--eta-max', type=float, default=1.5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = audit(args.runs, args.figure, args.eta_max)
    write(args.output, result)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
