"""Verification of solar_np: sun position vs NOAA reference, shadow network vs brute-force ray march, pole shadow length,
canyon sky-view factor vs the analytical integral."""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from solar_np import ShadowNet, HorizonNet, sun_position  # noqa: E402

dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
rep = {}


def test_sun_position():
    # NOAA solar calculator reference values, London (51.4984 N, -0.1769 E), 2026-06-21 12:00 UTC: altitude ~61.9, azimuth ~178-179
    alt, az = sun_position(51.4984, -0.1769, 2026, 6, 21, 12.0)
    alt2, az2 = sun_position(51.4984, -0.1769, 2026, 12, 21, 12.0)
    rep['sun_position'] = {'jun21_12utc': {'altitude': alt, 'azimuth': az}, 'dec21_12utc': {'altitude': alt2, 'azimuth': az2},
                           'pass': abs(alt - 61.9) < 0.5 and abs(az - 178.7) < 2 and abs(alt2 - 15.1) < 0.5}


def test_brute_force():
    rng = np.random.default_rng(0)
    ny, nx, dx = 96, 128, 2.0
    H = np.zeros((ny, nx), np.float32)
    for _ in range(40):
        y, x = rng.integers(0, ny - 8), rng.integers(0, nx - 8); H[y:y + rng.integers(2, 8), x:x + rng.integers(2, 8)] = rng.uniform(4, 30)
    H += rng.uniform(0, 0.5, H.shape).astype(np.float32)
    sn = ShadowNet(H, dx, dev)
    worst = 0.0; res = {}
    for alt, az in [(30, 135), (12, 200), (55, 90), (8, 350)]:
        s = sn(alt, az).cpu().numpy()
        # brute force: march along the exact ray in 1-cell steps, nearest-cell heights (flat-topped columns, one sample per cell)
        ta = math.tan(math.radians(alt)); d = np.array([math.sin(math.radians(az)), math.cos(math.radians(az))])
        ys, xs = np.mgrid[0:ny, 0:nx]; ref = np.zeros_like(s)
        for k in range(1, int(max(nx, ny))):
            sm = k * dx
            px = xs * dx + sm * d[0]; py = ys * dx + sm * d[1]
            cx, cy = px / dx, py / dx
            inside = (cx >= 0) & (cx <= nx - 1) & (cy >= 0) & (cy <= ny - 1)
            xi = np.clip(np.rint(cx).astype(int), 0, nx - 1); yi = np.clip(np.rint(cy).astype(int), 0, ny - 1)
            hh = H[yi, xi]
            ref |= inside & (hh > H + sm * ta + 1e-3)
        dis = float((s != ref).mean()); worst = max(worst, dis)
        res[f'alt{alt}_az{az}'] = {'shaded_fraction_net': float(s.mean()), 'shaded_fraction_bruteforce': float(ref.mean()), 'disagreement_fraction': dis}
    rep['brute_force_shadow'] = {**res, 'worst_disagreement': worst, 'pass': worst < 0.02}


def test_pole():
    ny, nx, dx = 200, 400, 1.0
    H = np.zeros((ny, nx), np.float32); H[98:102, 198:202] = 20.0     # 4 m x 4 m, 20 m tall block
    sn = ShadowNet(H, dx, dev)
    out = {}
    for alt in (10, 30, 60):
        s = sn(alt, 270).cpu().numpy()          # sun in the west -> shadow towards the east (+x)
        row = s[100]; xs = np.where(row)[0]
        length = float(xs.max() - 201) if len(xs) else 0.0
        out[f'alt{alt}'] = {'shadow_length_m': length, 'analytic_m': 20.0 / math.tan(math.radians(alt))}
    rep['pole_shadow'] = {**out, 'pass': all(abs(v['shadow_length_m'] - v['analytic_m']) <= 0.06 * v['analytic_m'] + 1.5 for v in out.values())}


def test_canyon_svf():
    """Infinite E-W canyon, width W = 20 m, height 20 m: SVF at the floor centre vs the isotropic integral of cos^2(beta(phi))."""
    ny, nx, dx = 60, 400, 1.0
    W, Hb = 20, 20.0
    H = np.zeros((ny, nx), np.float32); H[:20] = Hb; H[40:] = Hb
    sn = ShadowNet(H, dx, dev); hn = HorizonNet(sn, n_azimuth=32, altitudes_deg=tuple(range(1, 90, 2)))
    svf, hz = hn()
    num = float(svf[30, 150:250].mean().item())
    phis = np.linspace(0, 2 * np.pi, 3600, endpoint=False)
    beta = np.arctan(2 * Hb * np.abs(np.cos(phis)) / W)          # canyon axis E-W: obstruction distance W/2 / |cos(phi)| (phi from north)
    ana = float(np.mean(np.cos(beta) ** 2))
    oke = math.cos(math.atan(Hb / (0.5 * W)))
    rep['canyon_svf'] = {'numeric': num, 'analytic_isotropic_integral': ana, 'oke_1981_cos_formula': oke, 'pass': abs(num - ana) < 0.03}


if __name__ == '__main__':
    t0 = time.time()
    for fn in (test_sun_position, test_brute_force, test_pole, test_canyon_svf):
        s = time.time(); fn(); rep[list(rep)[-1]]['seconds'] = time.time() - s
    rep['all_pass'] = all(v['pass'] for v in rep.values() if isinstance(v, dict)); rep['device'] = str(dev); rep['total_seconds'] = time.time() - t0
    rep = json.loads(json.dumps(rep, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o)))
    print(json.dumps(rep, indent=2))
    if '--out' in sys.argv:
        out = Path(sys.argv[sys.argv.index('--out') + 1]); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(rep, indent=2))
