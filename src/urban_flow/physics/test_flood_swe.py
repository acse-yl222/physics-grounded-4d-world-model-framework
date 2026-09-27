"""Verification of flood_swe.ShallowWater on cases with known answers (runs in seconds on GPU).
1. lake at rest over rough bed with buildings: stays exactly at rest
2. closed basin + rain: volume balance to machine precision
3. Stoker wet-bed dam break: front speed / mid-depth vs the analytical solution
4. uniform Manning flow down a slope: steady depth vs h = (q n / sqrt(S))^(3/5)
5. rain on a slope with buildings: no flow into solid cells, volume balance with drainage and open boundary
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flood_swe import ShallowWater, G  # noqa: E402

dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
report = {}


def t(a):
    return torch.as_tensor(np.asarray(a, np.float32), device=dev)


def lake_at_rest():
    rng = np.random.default_rng(0)
    ny, nx, dx = 64, 96, 2.0
    zb = rng.uniform(0, 1.0, (ny, nx)).astype(np.float32)
    solid = np.zeros((ny, nx), bool); solid[20:30, 40:50] = True; zb[solid] += 10
    sw = ShallowWater(zb, solid, dx, np.full((ny, nx), 0.03), dev)
    eta0 = 1.5
    sw.h = torch.clamp(eta0 - sw.zb, min=0); sw.h[sw.solid] = 0
    v0 = sw.volume()
    for _ in range(200):
        sw.step(0.5)
    eta = (sw.zb + sw.h)[(sw.h > 0)]
    report['lake_at_rest'] = {'max_abs_speed': sw.max_speed(), 'eta_spread_m': float((eta.max() - eta.min()).item()),
                              'volume_change_m3': sw.volume() - v0, 'pass': sw.max_speed() < 1e-5 and abs(sw.volume() - v0) < 1e-3}


def rain_mass_balance():
    rng = np.random.default_rng(1)
    ny, nx, dx = 48, 64, 4.0
    zb = (rng.uniform(0, 2.0, (ny, nx)) + np.linspace(0, 3, nx)[None]).astype(np.float32)
    solid = np.zeros((ny, nx), bool); solid[10:14, 10:20] = True; zb[solid] += 10
    sw = ShallowWater(zb, solid, dx, np.full((ny, nx), 0.03), dev)
    rain = 50e-3 / 3600  # 50 mm/h
    src = torch.full((ny, nx), rain, device=dev); src[sw.solid] = 0
    expected = 0.0
    dt = 0.5; neg = 0.0
    for _ in range(2400):  # 20 min
        o = sw.step(dt, source=src)
        expected += o['source']; neg += o['neg_clamped']
    err = sw.volume() - expected - neg
    report['rain_mass_balance'] = {'rain_volume_m3': expected, 'stored_m3': sw.volume(), 'clamped_m3': neg,
                                   'relative_error': err / expected, 'pass': abs(err / expected) < 1e-4 and neg / expected < 1e-3}


def stoker_dam_break():
    """1-D wet dam break (frictionless), t = 20 s, dx = 1 m, L = 400 m. Two ratios: hr/hl = 0.5 (weak bore, pass criterion)
    and 0.1 (strong bore, informational: the non-conservative velocity form under-predicts strong shock speeds and this
    error does not vanish with refinement; the paper's formulation shares this)."""
    def run(hl, hr, dx=1.0, dt=0.05, T=20.0, L=400.0):
        nx, ny = int(L / dx), 3
        sw = ShallowWater(np.zeros((ny, nx), np.float32), np.zeros((ny, nx), bool), dx, np.zeros((ny, nx)), dev)
        x = (np.arange(nx) + 0.5) * dx - L / 2
        sw.h = t(np.where(x < 0, hl, hr)[None].repeat(ny, 0))
        tt = 0.0
        while tt < T - 1e-9:
            d = min(dt, T - tt); sw.step(d); tt += d
        h = sw.h[1].cpu().numpy()
        cl = math.sqrt(G * hl)
        def f(hm):
            return 2 * (cl - math.sqrt(G * hm)) - (hm - hr) * math.sqrt(G * (hm + hr) / (2 * hm * hr))
        lo, hi = hr, hl
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if f(lo) * f(mid) <= 0: hi = mid
            else: lo = mid
        hm = 0.5 * (lo + hi); cm = math.sqrt(G * hm); s = hm * 2 * (cl - cm) / (hm - hr)
        ha = np.where(x < -cl * T, hl, np.where(x < (2 * cl - 3 * cm) * T, (2 * cl - x / T) ** 2 / (9 * G), np.where(x < s * T, hm, hr)))
        idx = np.where(h > 0.5 * (hm + hr))[0]; front = float(x[idx.max()] + 0.5 * dx)
        mid_num = float(np.median(h[(x > -30) & (x < s * T - 15)]))
        return {'hl': hl, 'hr': hr, 'analytic_middle_depth': hm, 'numeric_middle_depth': mid_num, 'analytic_front_x': s * T,
                'numeric_front_x': front, 'L1_depth_error_m': float(np.mean(np.abs(h - ha)))}
    weak = run(1.0, 0.5); strong = run(1.0, 0.1)
    report['stoker_dam_break'] = {'weak_bore': weak, 'strong_bore_informational': strong,
                                  'pass': abs(weak['numeric_middle_depth'] - weak['analytic_middle_depth']) / weak['analytic_middle_depth'] < 0.03
                                  and abs(weak['numeric_front_x'] - weak['analytic_front_x']) / weak['analytic_front_x'] < 0.06}


def manning_uniform_flow():
    """Channel slope S = 0.01, n = 0.03, inflow q = 0.2 m^2/s: steady depth h = (q n / sqrt S)^(3/5) = 0.128 m."""
    nx, ny, dx = 300, 3, 2.0
    S, n, q = 0.01, 0.03, 0.2
    zb = (S * (nx - np.arange(nx) - 0.5) * dx)[None].repeat(ny, 0).astype(np.float32)   # falls towards +x
    solid = np.zeros((ny, nx), bool)
    sw = ShallowWater(zb, solid, dx, np.full((ny, nx), n), dev)
    src = torch.zeros((ny, nx), device=dev); src[:, 0] = q / dx     # inflow as a source in the first column
    absorb = torch.zeros((ny, nx), dtype=torch.bool, device=dev); absorb[:, -2:] = True
    dt = 0.2
    for _ in range(int(1500 / dt)):
        sw.step(dt, source=src, absorb=absorb)
    h = sw.h[1].cpu().numpy(); u = sw.u[1].cpu().numpy()
    h_an = (q * n / math.sqrt(S)) ** 0.6; u_an = q / h_an
    sl = slice(100, 250)
    report['manning_uniform_flow'] = {'analytic_depth_m': h_an, 'numeric_depth_m': float(h[sl].mean()), 'analytic_velocity': u_an,
                                      'numeric_velocity': float(u[sl].mean()), 'depth_std_m': float(h[sl].std()),
                                      'pass': abs(h[sl].mean() - h_an) / h_an < 0.03 and abs(u[sl].mean() - u_an) / u_an < 0.03}


def urban_slope():
    rng = np.random.default_rng(2)
    ny, nx, dx = 96, 128, 4.0
    zb = (0.01 * np.arange(nx) * dx)[None].repeat(ny, 0) + rng.uniform(0, 0.1, (ny, nx))
    solid = rng.uniform(size=(ny, nx)) < 0.15; solid[:3] = solid[-3:] = solid[:, :3] = solid[:, -3:] = False
    zb = zb.astype(np.float32); zb[solid] += 10
    sw = ShallowWater(zb, solid, dx, np.where(solid, 0.02, 0.02), dev)
    rain = 80e-3 / 3600
    src = torch.full((ny, nx), rain, device=dev); src[sw.solid] = 0
    sink = torch.full((ny, nx), 12e-3 / 3600, device=dev)
    absorb = torch.zeros((ny, nx), dtype=torch.bool, device=dev); absorb[:2] = absorb[-2:] = absorb[:, :2] = absorb[:, -2:] = True
    tot = {'source': 0, 'drained': 0, 'outflow': 0, 'neg_clamped': 0}
    tt = 0.0
    while tt < 1800:
        dt = sw.stable_dt(0.5); o = sw.step(dt, source=src, sink_rate=sink, absorb=absorb); tt += dt
        for k in tot: tot[k] += o[k]
    err = sw.volume() - (tot['source'] - tot['drained'] - tot['outflow'] - tot['neg_clamped'])
    report['urban_slope_rain'] = {**tot, 'stored_m3': sw.volume(), 'balance_error_m3': err, 'water_in_solid': float(sw.h[sw.solid].abs().max().item()),
                                  'max_depth_m': float(sw.h.max().item()), 'max_speed': sw.max_speed(),
                                  'pass': abs(err) < 1e-3 * tot['source'] and float(sw.h[sw.solid].abs().max().item()) == 0.0}


if __name__ == '__main__':
    t0 = time.time()
    for fn in (lake_at_rest, rain_mass_balance, stoker_dam_break, manning_uniform_flow, urban_slope):
        s = time.time(); fn(); report[fn.__name__ if fn.__name__ in report else list(report)[-1]]['seconds'] = time.time() - s
    report['all_pass'] = all(v['pass'] for v in report.values() if isinstance(v, dict))
    report['device'] = str(dev); report['total_seconds'] = time.time() - t0
    report = json.loads(json.dumps(report, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o)))
    print(json.dumps(report, indent=2))
    out = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, indent=2))
