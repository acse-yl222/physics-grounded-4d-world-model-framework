"""img2city/judge/perceptual.py -- DreamSim perceptual distance as a deterministic judge anchor.

Why DreamSim (research pass 2026-07-11, related_work_methods.md §J): CLIP render-
similarity carries no usable quality signal on 3D renders (chance-level agreement
with a validated judge, arXiv 2606.18451) and PSNR/SSIM cannot compare a clean
render to a real photo (arXiv 2506.12563); DreamSim (NeurIPS 2023) is the metric
that survives -- an ensemble of CLIP/OpenCLIP/DINO embeddings fine-tuned on human
perceptual judgements, recommended for render-vs-real comparison.

Measured on OUR data before being given any authority (53 refined city buildings,
pano-matched street render vs street-view photo): Spearman -0.33 against the
checklist pass-rate across buildings, and correctly ordered within-building
iterations on the spot checks -- a real but MODERATE signal, and the distances
cluster high (~0.5-0.9) because the untextured-render-vs-photo domain gap is large
(a documented caveat of the metric). It is therefore used as a TIE-BREAK and a
regression guard beside the checklist, never as the primary score.

Degrades gracefully: if dreamsim/torch are not installed, dreamsim_dist() returns
None and every caller falls back to the pre-DreamSim behaviour.
    pip install dreamsim   (first call downloads ~1.2 GB of backbone weights)
"""
from __future__ import annotations
import os
import threading

_DS = None      # None = not loaded yet; False = unavailable; else (model, pre, torch)
_LOCK = threading.Lock()    # parallel refine (08-04): one lazy load, one inference
                            # at a time -- the model is shared, not thread-safe


def dreamsim_dist(render_path, photo_path):
    """Perceptual distance between two images (LOWER = more similar), or None if
    DreamSim is unavailable. Model loads lazily on first call (~10 s warm)."""
    global _DS
    if _DS is False or not (render_path and photo_path):
        return None
    if not (os.path.exists(render_path) and os.path.exists(photo_path)):
        return None
    try:
        with _LOCK:
            if _DS is None:
                import torch
                from dreamsim import dreamsim as _load
                from img2city import config
                cache = str(config.CACHE_DIR / "dreamsim")
                model, pre = _load(pretrained=True, device="cpu", cache_dir=cache)
                _DS = (model, pre, torch)
            model, pre, torch = _DS
            from PIL import Image
            ta = pre(Image.open(render_path).convert("RGB"))
            tb = pre(Image.open(photo_path).convert("RGB"))
            with torch.no_grad():
                return round(float(model(ta, tb)), 4)
    except Exception:
        _DS = False
        return None
