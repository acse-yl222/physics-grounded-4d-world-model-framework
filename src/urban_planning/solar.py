"""Direct-beam occlusion by elevated horizontal rectangular panels.

The immutable background is sampled from the existing solar solver. Ray/plane
intersection adds panel shadows without replacing terrain by solid columns.
Diffuse/reflected light, thermal response, trees and structural design are outside
this pilot. Receptors lie on the ground, not at human-body height.
"""
import numpy as np


def panel_occlusion(receptors, panels, altitude_deg, azimuth_deg):
    """Return [time, receptor] union of opaque panel intersections in ENU metres."""
    receptors = np.asarray(receptors, dtype=float)
    alt = np.asarray(altitude_deg, dtype=float)
    az = np.asarray(azimuth_deg, dtype=float)
    if receptors.ndim != 2 or receptors.shape[1] != 3 or alt.shape != az.shape or alt.ndim != 1:
        raise ValueError('Expected receptors [N,3] and matching 1-D sun angles')
    if not all(np.isfinite(a).all() for a in (receptors, alt, az)):
        raise ValueError('Non-finite geometry or angles')
    result = np.zeros((len(alt), len(receptors)), dtype=bool)
    daylight = alt > 0
    tangent = np.tan(np.deg2rad(np.clip(alt, 0.001, 89.999999)))[:, None]
    ux, uy = np.sin(np.deg2rad(az))[:, None], np.cos(np.deg2rad(az))[:, None]
    for p in panels:
        if not all(np.isfinite(p[k]) for k in ('x_m', 'y_m', 'z_m', 'width_m', 'depth_m')):
            raise ValueError('Non-finite panel')
        if p['width_m'] <= 0 or p['depth_m'] <= 0:
            raise ValueError('Panel dimensions must be positive')
        dz = p['z_m'] - receptors[:, 2]
        distance = dz[None, :] / tangent
        x = receptors[None, :, 0] + distance * ux
        y = receptors[None, :, 1] + distance * uy
        result |= (daylight[:, None] & (dz[None, :] > 0)
                   & (np.abs(x - p['x_m']) <= p['width_m'] / 2)
                   & (np.abs(y - p['y_m']) <= p['depth_m'] / 2))
    return result


def reduced_energy(direct_w_m2, duration_s, occlusion):
    direct = np.asarray(direct_w_m2, dtype=float)
    duration = np.asarray(duration_s, dtype=float)
    if direct.shape != occlusion.shape or duration.shape != (direct.shape[0],):
        raise ValueError('Energy array dimensions disagree')
    if not np.isfinite(direct).all() or (direct < 0).any() or not np.isfinite(duration).all() or (duration <= 0).any():
        raise ValueError('Invalid radiation or duration')
    return (direct * duration[:, None] * occlusion).sum(axis=0) / 3.6e6
