"""Evaluator: scores a render against the reference image.

Two layers:
  * SilhouetteEvaluator -- fast, deterministic geometric score (no model needed).
    It normalises both silhouettes (crop-to-bbox, scale to a common height,
    centre) and reports silhouette IoU + per-row width-profile correlation. The
    loop uses this to decide accept/reject and to log convergence. The metric is
    intentionally pluggable -- swap in Chamfer distance, F-score, etc.
  * VLMCritic -- a vision-language critic returning a natural-language critique
    that guides the next edit. MockCritic works offline; LLMCritic asks the
    configured vision model.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from img2city import config
from img2city.agent import llm


def _bbox(mask):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _to_canvas(mask, H=600, W=700):
    m = _bbox(mask)
    if m is None:
        return None
    h, w = m.shape
    neww = max(1, int(round(H * (w / h))))
    a = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(
        (neww, H), Image.NEAREST)) > 127
    c = np.zeros((H, W), bool)
    if neww <= W:
        x0 = (W - neww) // 2
        c[:, x0:x0 + neww] = a
    else:
        cx = (neww - W) // 2
        c[:] = a[:, cx:cx + W]
    return c


def silhouette_from_image(path, bg="auto"):
    """Binary tower mask. bg='black' for the segmented photo (tower on black),
    'white' for matplotlib/mock renders (tower on white, drop black axis text)."""
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    mx, mn = im.max(2), im.min(2)
    if bg == "auto":
        bg = "white" if im[0, 0].mean() > 127 else "black"
    if bg == "white":
        white = mx >= 245
        black = mx <= 60
        neutral_dark = ((mx - mn) < 18) & (mx < 200)   # grey anti-aliased text
        return (~white) & (~black) & (~neutral_dark)
    return mx > 25                                       # non-black background


def _profile(c):
    p = c.sum(1).astype(float)
    return p / p.max() if p.max() else p


class SilhouetteEvaluator:
    def __init__(self, reference_path, bg="auto"):
        self.reference_path = reference_path
        self.ref = _to_canvas(silhouette_from_image(reference_path, bg))
        self.refp = _profile(self.ref)

    def score(self, render_path, bg="auto"):
        c = _to_canvas(silhouette_from_image(render_path, bg))
        if c is None:
            return {"iou": 0.0, "profile_corr": 0.0, "score": 0.0}
        inter = (c & self.ref).sum()
        uni = (c | self.ref).sum()
        iou = inter / uni if uni else 0.0
        corr = float(np.corrcoef(_profile(c), self.refp)[0, 1])
        corr = 0.0 if np.isnan(corr) else corr
        score = 0.5 * iou + 0.5 * max(corr, 0.0)
        return {"iou": round(float(iou), 4),
                "profile_corr": round(corr, 4),
                "score": round(float(score), 4)}


class VLMCritic:
    """Base critic. critique(...) -> (text, token_usage_dict)."""
    def critique(self, render_path, reference_path, score, iteration):
        raise NotImplementedError


class MockCritic(VLMCritic):
    """Offline stand-in: rule-based critique from the geometric score."""
    def critique(self, render_path, reference_path, score, iteration):
        s = score["score"]
        if s < 0.6:
            msg = "Proportions off: base too wide / taper wrong; narrow shaft, raise belfry."
        elif s < 0.8:
            msg = "Closer; refine dome curvature and belfry openings."
        else:
            msg = "Good match; sharpen string courses and finial."
        return msg, {"prompt_tokens": 0, "completion_tokens": 0}


class LLMCritic(VLMCritic):
    """Vision-language critic over the configured model (see
    img2city.agent.llm): sends the reference + current render and asks for the
    single most important geometric difference to fix next.  Returns
    (text, real_token_usage)."""
    SYSTEM = "You are a terse vision critic of 3D building silhouettes."

    def __init__(self, model=None, backend=None):
        self.model = model or config.JUDGE_MODEL
        self.backend = backend

    def critique(self, render_path, reference_path, score, iteration):
        prompt = ("Image 1 = reference, Image 2 = current render. "
                  f"Current score {score}. In ONE sentence, name the single most "
                  "important geometric difference to fix next.")
        text, usage, _cost = llm.vision_call(
            self.SYSTEM, prompt, [reference_path, render_path], self.model,
            backend=self.backend, max_tokens=120)
        return text.strip(), usage
