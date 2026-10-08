"""Diagnose hub-hole centre-jet persistence in retained B.2 OpenFOAM runs (read-only).

Stage mask_source: rebuild the exact discrete rotor mask/weights of the generated
fvOptions, recompute disc speed and Eq. 11 (or local-law) thrust from saved U and
compare with solver logs; check source units/sign through the kinematic pressure
jump; quantify hole and annulus representation on the generated mesh.
Stage centre_jet: centreline/hole/shear-layer U, k, nut along x for each closure.
Stage turbulence: SST production limiter, stress limiter (F2 with bottom-wall
distance) and nut ratios from the installed OpenFOAM 2312 kOmegaSST formulation.
No parameter is fitted; existing cases are never written.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from .opus_foam_fields import Grid, load_case, read_internal, write_progress

ROOT = Path(__file__).resolve().parents[3]
CASES = {
    'SST_eq11': ('cache/actuator_lab/openfoam_scheme_diagnostic/20261005T185748Z_2e0e1c84', 840, 'eq11'),
    'SST_LF18_eq11': ('cache/actuator_lab/openfoam_scheme_diagnostic/20261005T225803Z_bc9b3b47', 848, 'eq11'),
    'kOmega_eq11': ('cache/actuator_lab/openfoam_scheme_diagnostic/20261006T093633Z_1d967ce5', 1598, 'eq11'),
    'kEpsilon_eq11': ('cache/actuator_lab/openfoam_scheme_diagnostic/20261006T093634Z_de892ab2', 842, 'eq11'),
    'SST_localCt': ('cache/actuator_lab/opus_independent/20261006T110547Z_190d6d1f', 662, 'local'),
}
NU = 1.5e-5


def rotor_mask(grid, config):
    """Exact replica of the generated C++ mask (cell centres, inclusive bounds)."""
    X, Y, Z = np.meshgrid(*grid.axes, indexing='ij')
    hub = np.asarray(config['hub_xyz_m'])
    axial = X-hub[0]
    radial2 = np.maximum(0.0, (X-hub[0])**2+(Y-hub[1])**2+(Z-hub[2])**2-axial**2)
    R, r, half, sigma = config['rotor_diameter_m']/2, config['inner_diameter_m']/2, config['rotor_thickness_m']/2, config['sigma_m']
    inside = (np.abs(axial) <= half) & (radial2 <= R*R) & (radial2 >= r*r)
    hole = (np.abs(axial) <= half) & (radial2 < r*r)
    weight = np.where(inside, np.exp(-axial**2/(2*sigma**2)), 0.0)
    return inside, hole, weight, axial, np.sqrt(radial2)


def thrust_over_rho(config, speed, law):
    R = config['rotor_diameter_m']/2; ct = config['ct']; A = math.pi*R*R
    a = (1-math.sqrt(1-ct))/2
    return 2*A*a/(1-a)*speed**2 if law == 'eq11' else 0.5*ct*A*speed**2


def stage_mask_source(grid, config, cases, scratch):
    """Geometry from the shared config; each case's own configuration drives its recomputation."""
    result = mask_geometry_and_runs(grid, config, {}, scratch)
    for name, spec in cases.items():
        own = json.loads((ROOT/spec[0]/'configuration.json').read_text())
        part = mask_geometry_and_runs(grid, own, {name: spec}, scratch)
        result['runs'].update(part['runs'])
        if (own['sigma_m'], own['rotor_thickness_m']) != (config['sigma_m'], config['rotor_thickness_m']):
            result.setdefault('geometry_variants', {})[name] = part['geometry']
    return result


def mask_geometry_and_runs(grid, config, cases, scratch):
    inside, hole, weight, axial, radius = rotor_mask(grid, config)
    layers = sorted(set(np.round(axial[inside], 6)))
    hub = config['hub_xyz_m']
    ix = [int(i) for i in np.unique(np.nonzero(inside)[0])]
    plane = inside[ix[0]]; hole_plane = hole[ix[0]]
    R, r = config['rotor_diameter_m']/2, config['inner_diameter_m']/2
    hy, hz = grid.h[1], grid.h[2]
    hole_cells = [[round(grid.axes[1][j]-hub[1], 5), round(grid.axes[2][k]-hub[2], 5)] for j, k in zip(*np.nonzero(hole_plane))]
    geometry = dict(
        cells_total=int(inside.sum()), axial_layers=len(layers),
        layer_axial_offsets_m=[float(v) for v in layers],
        layer_weights=[float(math.exp(-v*v/(2*config['sigma_m']**2))) for v in layers],
        annulus_cells_per_layer=int(plane.sum()),
        annulus_area_represented_m2=float(plane.sum()*hy*hz), annulus_area_exact_m2=math.pi*(R*R-r*r),
        hole_cells_per_layer=int(hole_plane.sum()), hole_cell_offsets_yz_m=hole_cells,
        hole_area_represented_m2=float(hole_plane.sum()*hy*hz), hole_area_exact_m2=math.pi*r*r,
        hole_diameter_in_cells_y=2*r/hy, hole_diameter_in_cells_z=2*r/hz,
        hub_offset_from_nearest_cell_centre_m=[float(min(np.abs(a-c))) for a, c in zip(grid.axes, hub)],
        spacing_m=list(grid.h))
    results = {}
    for name, (case, iteration, law) in cases.items():
        fields, digests = load_case(ROOT/case, iteration, ['U', 'p'], scratch)
        U = grid.cube(fields['U']); p = grid.cube(fields['p'])
        wv = weight*grid.volume
        speed = float(abs((wv[..., None]*U).sum((0, 1, 2))[0]/wv.sum()))
        T = thrust_over_rho(config, speed, law)
        log = np.loadtxt(ROOT/case/'rotor_iterations.csv', delimiter=',', skiprows=1) if (ROOT/case/'rotor_iterations.csv').exists() else None
        logged = log[-1] if log is not None else None
        # Kinematic pressure jump across the force region, averaged over annulus cells.
        up, down = ix[0]-1, ix[-1]+1
        dp = float((p[up][plane]-p[down][plane]).mean())
        results[name] = dict(iteration=iteration, law=law, fields_sha256=digests,
            disc_speed_recomputed=speed, disc_speed_logged=None if logged is None else float(logged[1]),
            thrust_N_recomputed=T*config['rho_kg_m3'], thrust_N_logged=None if logged is None else float(logged[2]),
            pressure_jump_times_annulus_area_over_T_over_rho=dp*geometry['annulus_area_represented_m2']/T,
            upstream_minus_downstream_kinematic_pressure=dp)
    return dict(geometry=geometry, runs=results)


def interp_line(field, grid, x, y, z):
    from scipy.interpolate import RegularGridInterpolator
    f = RegularGridInterpolator(grid.axes, field, bounds_error=False, fill_value=np.nan)
    return f(np.column_stack(np.broadcast_arrays(x, y, z)))


def stage_centre_jet(grid, config, cases, scratch):
    hub = np.asarray(config['hub_xyz_m']); D = config['rotor_diameter_m']; R = D/2; U0 = config['inlet_m_s']
    xs = hub[0]+np.linspace(-0.5, 6, 131)*D
    ys = np.linspace(-1.5, 1.5, 241)*R
    out = {}
    for name, (case, iteration, law) in cases.items():
        names = ['U', 'k', 'nut'] + (['epsilon'] if 'Epsilon' in name else ['omega'])
        fields, _ = load_case(ROOT/case, iteration, names, scratch)
        Ux = grid.cube(fields['U'][:, 0]); k = grid.cube(fields['k']); nut = grid.cube(fields['nut'])
        rows = []
        for x in xs:
            u = interp_line(Ux, grid, x, hub[1]+ys, hub[2])
            d = 1-u/U0
            centre = float(np.interp(0, ys, d))
            ring = (np.abs(ys) >= 0.3*R) & (np.abs(ys) <= 1.0*R)
            kk = interp_line(k, grid, x, hub[1]+ys, hub[2]); nn = interp_line(nut, grid, x, hub[1]+ys, hub[2])
            inner = (np.abs(ys) >= 0.0*R) & (np.abs(ys) <= 0.4*R)
            outer = (np.abs(ys) >= 0.8*R) & (np.abs(ys) <= 1.2*R)
            rows.append(dict(x_over_D=float((x-hub[0])/D), centre_deficit=centre, ring_peak_deficit=float(d[ring].max()),
                             fill_ratio=centre/float(d[ring].max()) if d[ring].max() > 1e-6 else None,
                             centre_nut_over_nu=float(np.interp(0, ys, nn))/NU, inner_max_nut_over_nu=float(nn[inner].max())/NU,
                             outer_max_nut_over_nu=float(nn[outer].max())/NU,
                             centre_k=float(np.interp(0, ys, kk)), inner_max_k=float(kk[inner].max()), outer_max_k=float(kk[outer].max())))
        fills = [r for r in rows if r['x_over_D'] > 0.3 and r['fill_ratio'] is not None and r['fill_ratio'] >= 0.5]
        upstream = interp_line(nut, grid, hub[0]-0.5*D, hub[1], hub[2])[0]
        inlet_region = interp_line(nut, grid, 0.2, hub[1], hub[2])[0]
        out[name] = dict(stations={s: min(rows, key=lambda r: abs(r['x_over_D']-s)) for s in (0.5, 1, 2, 3, 5)},
                         half_fill_x_over_D=fills[0]['x_over_D'] if fills else None,
                         freestream_nut_over_nu={'x=0.2m': float(inlet_region)/NU, 'x=hub-0.5D': float(upstream)/NU},
                         profile=rows)
    return out


def sst_coefficients():
    return dict(a1=0.31, b1=1.0, c1=10.0, betaStar=0.09, alphaOmega2=0.856, F3=False)


def stage_turbulence(grid, config, cases, scratch):
    """Limiter activity on the wake slab |y-hub|,|z-hub| <= 1.5R, 0 <= x-hub <= 6D."""
    c = sst_coefficients(); hub = config['hub_xyz_m']; D = config['rotor_diameter_m']; R = D/2
    X, Y, Z = np.meshgrid(*grid.axes, indexing='ij')
    region = (X >= hub[0]) & (X <= hub[0]+6*D) & (np.abs(Y-hub[1]) <= 1.5*R) & (np.abs(Z-hub[2]) <= 1.5*R)
    inner = region & (np.hypot(Y-hub[1], Z-hub[2]) <= 0.4*R)
    out = {}
    for name, (case, iteration, law) in cases.items():
        if 'Epsilon' in name:
            fields, _ = load_case(ROOT/case, iteration, ['U', 'k', 'nut', 'epsilon'], scratch)
        else:
            fields, _ = load_case(ROOT/case, iteration, ['U', 'k', 'nut', 'omega'], scratch)
        U = grid.cube(fields['U']); k = grid.cube(fields['k']); nut = grid.cube(fields['nut'])
        g = np.empty(U.shape[:3]+(3, 3))
        for i in range(3):
            for j in range(3):
                g[..., i, j] = np.gradient(U[..., i], grid.h[j], axis=j)
        S = 0.5*(g+np.swapaxes(g, -1, -2)); W = 0.5*(g-np.swapaxes(g, -1, -2))
        S2 = 2*(S*S).sum((-1, -2)); O2 = 2*(W*W).sum((-1, -2))
        G = nut*S2
        entry = dict(nut_over_nu_median_region=float(np.median(nut[region]))/NU,
                     nut_over_nu_median_inner=float(np.median(nut[inner]))/NU,
                     strain_over_rotation_median_inner=float(np.median(S2[inner]/np.maximum(O2[inner], 1e-30))))
        if 'omega' in fields:
            om = grid.cube(fields['omega'])
            Pk_lim = c['c1']*c['betaStar']*k*om
            y = Z  # meshWave distance to the only wall patch (bottom)
            arg2 = np.maximum(2*np.sqrt(k)/(c['betaStar']*om*y), 500*NU/(y*y*om))
            F2 = np.tanh(arg2**2)
            stress = c['b1']*F2*np.sqrt(S2) > c['a1']*om
            entry.update(production_limiter_active_fraction_region=float((G > Pk_lim)[region].mean()),
                         production_limiter_active_fraction_inner=float((G > Pk_lim)[inner].mean()),
                         F2_median_region=float(np.median(F2[region])),
                         stress_limiter_active_fraction_region=float(stress[region].mean()),
                         stress_limiter_active_fraction_inner=float(stress[inner].mean()),
                         nut_over_k_over_omega_median_inner=float(np.median((nut/(k/om))[inner])),
                         nut_over_k_over_omega_median_region=float(np.median((nut/(k/om))[region])))
        out[name] = entry
    return out


RETAINED = {'SST_eq11': '20261005T185748Z_2e0e1c84', 'SST_LF18_eq11': '20261005T225803Z_bc9b3b47',
            'kOmega_eq11': '20261006T093633Z_1d967ce5', 'kEpsilon_eq11': '20261006T093634Z_de892ab2',
            'SST_localCt': '20261006T110547Z_190d6d1f'}
PAPER_CURVE = {'SST_eq11': 'kOmegaSST', 'SST_LF18_eq11': 'kOmegaSST', 'SST_localCt': 'kOmegaSST',
               'kEpsilon_eq11': 'kEpsilon', 'kOmega_eq11': None}


def profile_errors(run, figure, curve_name):
    """Errors vs the corresponding paper curve and, separately, digitized markers."""
    from .compare_paper_profiles import errors, ordered_profile
    from .opus_compare_thrust_law import shape
    config = json.loads((run/'configuration.json').read_text())
    R = config['rotor_diameter_m']/2; hub = config['hub_xyz_m'][1]
    out = {}
    for profile in figure['profiles']:
        s = profile['x_over_D']
        data = json.loads((run/f'data/wake_{s}d.json').read_text())
        x, v = ordered_profile((np.asarray(data['positions'])[:, 1]-hub)/R, data['values'])
        entry = dict(vs_digitized_experiment=errors(x, v, profile['experimental_markers']), shape=shape(x, v))
        if curve_name:
            c = np.asarray(profile['curves'][curve_name]); grid = np.linspace(-1.5, 1.5, 301)
            cx, cv = ordered_profile(c[:, 0], c[:, 1])
            entry['paper_curve'] = curve_name
            entry['vs_paper_curve_vertices'] = errors(x, v, c)
            entry['vs_paper_curve_uniform_rms'] = float(np.sqrt(np.mean((np.interp(grid, x, v)-np.interp(grid, cx, cv))**2)))
        out[str(s)] = entry
    return out


def stage_paper_errors(grid, config, cases, scratch, retained=None):
    figure = json.loads((ROOT/'project/actuator_lab/formal_figure_b33.json').read_text())
    retained = retained or RETAINED
    return {name: dict(run_id=rid, **profile_errors(ROOT/'project/actuator_lab/runs'/rid, figure, PAPER_CURVE.get(name, 'kOmegaSST')))
            for name, rid in retained.items()}


def stage_shear_layer(grid, config, cases, scratch):
    """k, omega and production-limiter ratio along the hole-edge shear layer and upstream axis."""
    c = sst_coefficients(); hub = np.asarray(config['hub_xyz_m']); D = config['rotor_diameter_m']
    out = {}
    for name, (case, iteration, law) in cases.items():
        if 'Epsilon' in name:
            continue
        fields, _ = load_case(ROOT/case, iteration, ['U', 'k', 'omega', 'nut'], scratch)
        U = grid.cube(fields['U']); k = grid.cube(fields['k']); om = grid.cube(fields['omega']); nut = grid.cube(fields['nut'])
        dudy = np.gradient(U[..., 0], grid.h[1], axis=1)
        rows = []
        for xd in (-3, -1, -0.25, 0.25, 0.5, 1, 2, 3, 4, 5):
            x = hub[0]+xd*D
            y = hub[1]+np.linspace(0.02, 0.12, 21)  # hole edge r=0.045 lies inside this band
            kk = interp_line(k, grid, x, y, hub[2]); ww = interp_line(om, grid, x, y, hub[2])
            ss = np.abs(interp_line(dudy, grid, x, y, hub[2])); nn = interp_line(nut, grid, x, y, hub[2])
            i = int(np.nanargmax(ss))
            y_wall = hub[2]
            F2 = math.tanh(max(2*math.sqrt(kk[i])/(c['betaStar']*ww[i]*y_wall), 500*NU/(y_wall**2*ww[i]))**2)
            rows.append(dict(x_over_D=xd, r_at_max_shear_m=float(y[i]-hub[1]), max_dUdy=float(ss[i]), k=float(kk[i]),
                             omega=float(ww[i]), nut_over_nu=float(nn[i])/NU,
                             unlimited_G_over_cap=float(nn[i]*ss[i]**2/(c['c1']*c['betaStar']*kk[i]*ww[i])),
                             F2_bottom_wall=F2, k_growth_rate_cap_per_s=(c['c1']-1)*c['betaStar']*float(ww[i])))
        out[name] = rows
    return out


def stage_figures(grid, config, cases, scratch, output=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    jet = json.loads((output/'centre_jet.json').read_text())
    shear = json.loads((output/'shear_layer.json').read_text())
    errors = json.loads((output/'paper_errors.json').read_text())
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for name, data in jet.items():
        x = [r['x_over_D'] for r in data['profile']]
        axes[0, 0].plot(x, [r['centre_deficit'] for r in data['profile']], label=name)
        axes[0, 1].plot(x, [r['ring_peak_deficit'] for r in data['profile']], label=name)
    for curve, style in (('kOmegaSST', 'ks'), ('kEpsilon', 'k^')):
        paper = {1: (0.182, 0.442), 3: (0.398, 0.394), 5: (0.350, 0.325)} if curve == 'kOmegaSST' else {1: (0.067, 0.474), 3: (0.299, 0.459), 5: (0.372, 0.402)}
        axes[0, 0].plot(list(paper), [v[0] for v in paper.values()], style, mfc='none', label=f'paper {curve}')
        axes[0, 1].plot(list(paper), [v[1] for v in paper.values()], style, mfc='none', label=f'paper {curve}')
    for name, rows in shear.items():
        axes[1, 0].semilogy([r['x_over_D'] for r in rows], [r['k'] for r in rows], 'o-', label=name)
        axes[1, 1].semilogy([r['x_over_D'] for r in rows], [max(r['unlimited_G_over_cap'], 1e-3) for r in rows], 'o-', label=name)
    axes[1, 1].axhline(1, color='k', lw=.8)
    titles = ['Centre deficit (y/R=0, hub height)', 'Annular peak deficit (0.3<=|y/R|<=1)',
              'k at max |dU/dy| in hole-edge band', 'Unlimited SST production / Menter cap (>1: capped)']
    for ax, t in zip(axes.flat, titles):
        ax.set_title(t, fontsize=10); ax.set_xlabel('x/D'); ax.grid(alpha=.3)
    axes[0, 0].legend(fontsize=7); axes[1, 0].legend(fontsize=7)
    fig.text(0.01, 0.005, 'Paper points: Fig. B.33 digitized curves. No experimental-validation claim.', fontsize=7)
    fig.tight_layout(); fig.savefig(output/'centre_diagnostic.png', dpi=140); plt.close(fig)
    return {'figure': 'centre_diagnostic.png', 'runs': list(errors)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stages', default='mask_source,centre_jet,turbulence')
    parser.add_argument('--extra', action='append', default=[],
                        help='name=case_dir:iteration:law[:run_id[:paper_curve]] (additional read-only case)')
    args = parser.parse_args()
    for spec in args.extra:
        name, rest = spec.split('=', 1)
        parts = rest.split(':')
        CASES[name] = (parts[0], int(parts[1]), parts[2])
        if len(parts) > 3:
            RETAINED[name] = parts[3]
            PAPER_CURVE[name] = parts[4] if len(parts) > 4 else 'kOmegaSST'
    args.output.mkdir(parents=True, exist_ok=True)
    scratch = args.output/'field_cache'
    base = ROOT/CASES['SST_eq11'][0]
    config = json.loads((base/'configuration.json').read_text())
    grid = Grid(config)
    err = grid.verify(read_internal(base/'840/C'))
    if err > 1e-9:
        raise ValueError(f'Structured cell ordering mismatch: {err}')
    progress = args.output/'progress.json'
    write_progress(progress, 'grid_verification', dict(max_centre_error_m=err, cells=grid.n, spacing_m=grid.h))
    for stage in args.stages.split(','):
        result = {'mask_source': stage_mask_source, 'centre_jet': stage_centre_jet,
                  'turbulence': stage_turbulence, 'paper_errors': stage_paper_errors,
                  'shear_layer': stage_shear_layer,
                  'figures': lambda *a: stage_figures(*a, output=args.output)}[stage](grid, config, CASES, scratch)
        (args.output/f'{stage}.json').write_text(json.dumps(result, indent=1, default=float))
        write_progress(progress, stage, {'file': f'{stage}.json', 'complete': True})
        print('stage complete', stage, flush=True)


if __name__ == '__main__':
    main()
