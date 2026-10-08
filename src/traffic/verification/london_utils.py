"""
London Road Network Centerline Resampling Tool (for matching the training model)
"""

import numpy as np

TARGET_SPACING_CELLS = 13.0 / 25.0


def resample_uniform(poly, spacing=TARGET_SPACING_CELLS):
    poly = np.asarray(poly, dtype=float)
    if len(poly) < 2:
        return poly
    seg = poly[1:] - poly[:-1]
    seg_len = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = cum[-1]
    if total <= spacing:
        return poly
    ts = np.arange(spacing, total, spacing)
    idx = np.searchsorted(cum, ts, side="right") - 1
    idx = np.clip(idx, 0, len(poly) - 2)
    frac = (ts - cum[idx]) / seg_len[idx]
    pts = poly[idx] + frac[:, None] * seg[idx]
    return np.vstack([poly[0], pts, poly[-1]])
