"""Solar illumination of an urban height field in NN4PDEs style: every operator is a fixed-weight network layer on GPU tensors.

Physics: for a height field H(x) (DTM + buildings) the direct beam from direction d (unit horizontal vector) and altitude a
reaches x iff no point along the ray is above it:  max_s [H(x + s d) - s tan a] <= H(x). With the tilted field
G(x) = H(x) - tan a (x . d) this is  max_{1<=s<=S} G(x + s d) <= G(x):  a running maximum along d, i.e. the solution of the
1-D transport / visibility sweep. The running maximum is evaluated by a doubling recursion
    M_1 = T_d G,   M_{2k} = max(M_k, T_{k d} M_k)      (T = shift/sampling layer, max = morphological activation),
so a ray of S metres costs log2(S) layers (ShadowNet). The horizon angle in a given azimuth is found by the same layer bank at a
set of altitudes (HorizonNet), the sky-view factor is the isotropic-sky integral of the horizon, and clear-sky irradiance is a
pointwise layer (ASHRAE clear-sky model with monthly A, B, C). Nothing is trained; all weights come from geometry.

Arrays: [ny, nx], row 0 = south, col 0 = west, metres. Azimuth: degrees clockwise from north (0 = N, 90 = E).
"""

import math

import torch
import torch.nn.functional as F

NEG = -1.0e4


def sun_position(lat_deg, lon_deg, year, month, day, hour_utc):
    """NOAA solar position (degrees): returns (altitude, azimuth clockwise from north). hour_utc may be fractional."""
    # Julian day
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    jd = jdn + (hour_utc - 12.0) / 24.0
    jc = (jd - 2451545.0) / 36525.0
    gmls = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360.0
    gmas = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    ecc = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    seqc = (
        math.sin(math.radians(gmas)) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
        + math.sin(math.radians(2 * gmas)) * (0.019993 - 0.000101 * jc)
        + math.sin(math.radians(3 * gmas)) * 0.000289
    )
    stl = gmls + seqc
    sal = stl - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * jc))
    moe = 23.0 + (26.0 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60.0) / 60.0
    oc = moe + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * jc))
    decl = math.degrees(math.asin(math.sin(math.radians(oc)) * math.sin(math.radians(sal))))
    vy = math.tan(math.radians(oc / 2)) ** 2
    eqt = 4 * math.degrees(
        vy * math.sin(2 * math.radians(gmls))
        - 2 * ecc * math.sin(math.radians(gmas))
        + 4 * ecc * vy * math.sin(math.radians(gmas)) * math.cos(2 * math.radians(gmls))
        - 0.5 * vy * vy * math.sin(4 * math.radians(gmls))
        - 1.25 * ecc * ecc * math.sin(2 * math.radians(gmas))
    )
    tst = (hour_utc * 60.0 + eqt + 4 * lon_deg) % 1440.0
    ha = tst / 4.0 - 180.0 if tst / 4.0 >= 0 else tst / 4.0 + 180.0
    lat, dec, h = map(math.radians, (lat_deg, decl, ha))
    zen = math.acos(
        max(
            -1.0,
            min(1.0, math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(h)),
        )
    )
    alt = 90.0 - math.degrees(zen)
    if abs(math.sin(zen)) < 1e-9:
        az = 180.0
    else:
        c = (math.sin(lat) * math.cos(zen) - math.sin(dec)) / (math.cos(lat) * math.sin(zen))
        az = math.degrees(math.acos(max(-1.0, min(1.0, c))))
        az = (az + 180.0) % 360.0 if ha > 0 else (540.0 - az) % 360.0
    # atmospheric refraction (NOAA)
    if alt > 85:
        refr = 0.0
    elif alt > 5:
        t = math.tan(math.radians(alt))
        refr = 58.1 / t - 0.07 / t**3 + 0.000086 / t**5
    elif alt > -0.575:
        refr = 1735 + alt * (-518.2 + alt * (103.4 + alt * (-12.79 + alt * 0.711)))
    else:
        refr = -20.772 / math.tan(math.radians(alt))
    return alt + refr / 3600.0, az


class ShadowNet(torch.nn.Module):
    """Running-maximum network along a ray: shadow mask for one sun direction on a height field (metres per cell = dx).
    The ray direction is approximated by an integer cell vector p = (px, py) (|p| 16..32 cells, angle error < 1 deg) so that
    every shift layer is an exact integer translation (no interpolation). Stage 0 takes the nearest-cell samples along the
    first |p| cells of the ray; stage k doubles the covered range by shifting with 2^k p."""

    def __init__(self, height, dx, device, max_vec=32, min_vec=16):
        super().__init__()
        self.H = torch.as_tensor(height, dtype=torch.float32, device=device)
        self.ny, self.nx = self.H.shape
        self.dx = float(dx)
        self.max_vec, self.min_vec = max_vec, min_vec
        ys, xs = torch.meshgrid(
            torch.arange(self.ny, device=device, dtype=torch.float32),
            torch.arange(self.nx, device=device, dtype=torch.float32),
            indexing="ij",
        )
        self.xs, self.ys = xs, ys  # cell coordinates
        self.hrange = float(self.H.max() - self.H.min())
        self._cache = {}

    def int_direction(self, azimuth_deg):
        """Integer cell vector closest in angle to the azimuth (x east, y north), norm between min_vec and max_vec."""
        key = round(azimuth_deg, 3)
        if key in self._cache:
            return self._cache[key]
        az = math.radians(azimuth_deg)
        ux, uy = math.sin(az), math.cos(az)
        best = None
        for px in range(-self.max_vec, self.max_vec + 1):
            for py in range(-self.max_vec, self.max_vec + 1):
                n = math.hypot(px, py)
                if n < self.min_vec or n > self.max_vec:
                    continue
                err = math.acos(max(-1.0, min(1.0, (px * ux + py * uy) / n)))
                if (
                    best is None
                    or err < best[0] - 1e-12
                    or (abs(err - best[0]) <= 1e-12 and n < best[3])
                ):
                    best = (err, px, py, n)
        self._cache[key] = best[1:]
        return best[1:]

    def shift(self, f, ox, oy):
        """T layer: out[y, x] = f[y + oy, x + ox] (integer cells), outside the domain -> NEG (no obstruction)."""
        out = torch.full_like(f, NEG)
        ys0, ys1 = max(0, -oy), min(self.ny, self.ny - oy)
        xs0, xs1 = max(0, -ox), min(self.nx, self.nx - ox)
        if ys1 > ys0 and xs1 > xs0:
            out[ys0:ys1, xs0:xs1] = f[ys0 + oy : ys1 + oy, xs0 + ox : xs1 + ox]
        return out

    def running_max(self, G, px, py, S_cells):
        """max over s in (0, S] of G(x + s d), d = p/|p|: stage 0 = nearest samples along p, then doubling with 2^k p."""
        n = math.hypot(px, py)
        m = int(round(n))
        M = None
        for s in range(1, m + 1):
            sh = self.shift(G, int(round(s * px / n)), int(round(s * py / n)))
            M = sh if M is None else torch.maximum(M, sh)
        k = 1
        while k * n < S_cells:
            M = torch.maximum(M, self.shift(M, k * px, k * py))
            k *= 2
        return M

    def forward(self, altitude_deg, azimuth_deg, max_range_m=None):
        """Returns shadow mask (True = shaded) for the sun at (altitude, azimuth)."""
        if altitude_deg <= 0:
            return torch.ones_like(self.H, dtype=torch.bool)
        px, py, n = self.int_direction(azimuth_deg)
        ux, uy = px / n, py / n
        ta = math.tan(math.radians(altitude_deg))
        G = self.H - ta * self.dx * (self.xs * ux + self.ys * uy)
        S = max_range_m or min(self.hrange / max(ta, 1e-3), max(self.nx, self.ny) * self.dx)
        M = self.running_max(G, px, py, max(1, int(math.ceil(S / self.dx))))
        return M > G + 1e-3


class HorizonNet(torch.nn.Module):
    """Horizon angle per azimuth via a bank of ShadowNet layers at increasing altitudes; sky-view factor for an isotropic sky."""

    def __init__(self, shadow: ShadowNet, n_azimuth=16, altitudes_deg=tuple(range(2, 90, 5))):
        super().__init__()
        self.sn = shadow
        self.n_az = n_azimuth
        self.alts = list(altitudes_deg)

    def horizon(self, azimuth_deg):
        """Lowest tested altitude at which the sun is visible; cells shaded at all altitudes get 90."""
        h = torch.full_like(self.sn.H, 90.0)
        for a in reversed(self.alts):  # from high to low: visible at a -> horizon <= a
            vis = ~self.sn(a, azimuth_deg)
            h = torch.where(vis, torch.full_like(h, float(a)), h)
        return h

    def forward(self):
        """SVF = (1/K) sum_k cos^2(beta_k) (isotropic sky, K azimuths); also returns the horizon stack [K, ny, nx] (deg)."""
        hs = []
        for k in range(self.n_az):
            hs.append(self.horizon(360.0 * k / self.n_az))
        H = torch.stack(hs)
        svf = torch.cos(torch.deg2rad(H)) ** 2
        return svf.mean(0), H


# ASHRAE clear-sky coefficients (A W/m^2, B, C) for the 21st of each month, 1 .. 12
ASHRAE = {
    1: (1230, 0.142, 0.058),
    2: (1215, 0.144, 0.060),
    3: (1186, 0.156, 0.071),
    4: (1136, 0.180, 0.097),
    5: (1104, 0.196, 0.121),
    6: (1088, 0.205, 0.134),
    7: (1085, 0.207, 0.136),
    8: (1107, 0.201, 0.122),
    9: (1151, 0.177, 0.092),
    10: (1192, 0.160, 0.073),
    11: (1221, 0.149, 0.063),
    12: (1233, 0.142, 0.057),
}


def clear_sky(altitude_deg, month):
    """Direct normal and diffuse horizontal irradiance (W/m^2), ASHRAE clear-sky model."""
    if altitude_deg <= 0:
        return 0.0, 0.0
    A, B, C = ASHRAE[month]
    dni = A * math.exp(-B / math.sin(math.radians(altitude_deg)))
    return dni, C * dni


def ground_irradiance(shadow, svf, altitude_deg, month, canopy_transmittance=None, albedo=0.2):
    """Global horizontal irradiance on each cell: direct (unshaded) + diffuse * SVF + ground-reflected from the obstructed sky part."""
    dni, dhi = clear_sky(altitude_deg, month)
    direct = (~shadow).float() * dni * math.sin(math.radians(altitude_deg))
    if canopy_transmittance is not None:
        direct = direct * canopy_transmittance
    ghi_open = dni * math.sin(math.radians(altitude_deg)) + dhi
    reflected = albedo * ghi_open * (1.0 - svf)
    return direct + dhi * svf + reflected, dni, dhi
