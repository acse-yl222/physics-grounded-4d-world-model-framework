"""img2city/judge/depth_anchor.py -- Depth Anything V2 depth-agreement as a second deterministic
judge anchor beside DreamSim (research pass 2026-07-15, related_work_methods.md
P/Q item 2).

Why: DreamSim's backbone is documented as colour/style-sensitive, so an untextured
render carries an irreducible appearance penalty against a photo. Depth agreement
compares the SHAPE the photo implies with the shape the render shows -- appearance
never enters. Verified on this platform: the official DA-V2 code auto-selects MPS
(Apple Silicon), and Apple ships Core ML conversions (Apache-2.0); here we use the
HF transformers port (depth-anything/Depth-Anything-V2-Small-hf) which the
installed transformers stack loads directly.

depth_agreement(render, photo) -> float in [-1, 1] (Spearman rank correlation of
the two monocular depth maps at 96x96), or None when torch/transformers are not
available -- every caller degrades gracefully, exactly like perceptual.dreamsim_dist.
Monocular depth is affine-ambiguous, so rank correlation (not absolute error) is
the right comparison.
"""
from __future__ import annotations
import threading

_PIPE = {}
_LOCK = threading.Lock()    # parallel refine (08-04): shared pipeline, one lazy
                            # load / one inference at a time


def _pipe():
    if "p" not in _PIPE:
        import torch
        from transformers import pipeline
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        _PIPE["p"] = pipeline("depth-estimation",
                              model="depth-anything/Depth-Anything-V2-Small-hf",
                              device=dev)
    return _PIPE["p"]


def _depth(pipe, path, size=96):
    from PIL import Image
    import numpy as np
    im = Image.open(path).convert("RGB")
    d = pipe(im)["depth"].resize((size, size), Image.BILINEAR)
    return np.asarray(d, dtype=float).ravel()


def depth_agreement(render_png, photo_png):
    """Spearman correlation of the two depth maps; None if the stack is missing."""
    try:
        import numpy as np
        with _LOCK:
            p = _pipe()
            a, b = _depth(p, render_png), _depth(p, photo_png)
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
        ra -= ra.mean(); rb -= rb.mean()
        denom = float(np.sqrt((ra * ra).sum() * (rb * rb).sum())) or 1.0
        return round(float((ra * rb).sum() / denom), 4)
    except Exception:
        return None


if __name__ == "__main__":
    import sys
    print(depth_agreement(sys.argv[1], sys.argv[2]))
