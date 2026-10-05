"""Deterministic judge anchors: silhouette extraction + IoU/profile score and
the offline critic. Perceptual (DreamSim) and depth anchors need torch weights
and are exercised live, not here."""
import numpy as np
import pytest
from PIL import Image, ImageDraw

from img2city.judge.evaluator import (MockCritic, SilhouetteEvaluator, _to_canvas,
                                      silhouette_from_image)


def _tower(path, w=120, h=400, bg="white", fill=(115, 105, 88), size=(300, 640)):
    """Base block plus a narrower shaft: the width profile must vary, or the
    profile correlation is undefined (constant vector) and reads as 0."""
    W, H = size
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    cx = W // 2
    base_h = h // 4
    d.rectangle([cx - w // 2, H - 20 - base_h, cx + w // 2, H - 20], fill=fill)
    d.rectangle([cx - w // 4, H - 20 - h, cx + w // 4, H - 20 - base_h], fill=fill)
    im.save(path)
    return str(path)


def test_silhouette_on_white_and_black_backgrounds(tmp_path):
    p_white = _tower(tmp_path / "w.png")
    p_black = _tower(tmp_path / "b.png", bg="black")
    m_w = silhouette_from_image(p_white)
    m_b = silhouette_from_image(p_black)
    assert m_w.dtype == bool and m_w.shape == (640, 300)
    assert m_w.sum() == pytest.approx(121 * 101 + 61 * 300, rel=0.03)
    assert (m_w == m_b).mean() > 0.995, "auto background detection must agree"


def test_silhouette_drops_grey_axis_text_on_white(tmp_path):
    p = tmp_path / "t.png"
    im = Image.new("RGB", (300, 640), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([100, 200, 200, 600], fill=(115, 105, 88))
    d.rectangle([10, 10, 60, 20], fill=(150, 150, 150))     # grey label
    d.rectangle([10, 30, 60, 40], fill=(0, 0, 0))           # black axis
    im.save(p)
    m = silhouette_from_image(str(p))
    assert m[15, 30] is np.False_ and m[35, 30] is np.False_
    assert m[400, 150]


def test_canvas_is_bbox_cropped_height_normalised_and_centred(tmp_path):
    m = silhouette_from_image(_tower(tmp_path / "a.png", w=100, h=200))
    c = _to_canvas(m, H=600, W=700)
    assert c.shape == (600, 700)
    assert c[0].any() and c[-1].any(), "scaled to full canvas height"
    cols = np.where(c.any(0))[0]
    assert abs((cols[0] + cols[-1]) / 2 - 350) <= 1, "horizontally centred"
    assert _to_canvas(np.zeros((10, 10), bool)) is None


def test_evaluator_scores_identity_one_and_degrades(tmp_path):
    ref = _tower(tmp_path / "ref.png", w=120, h=400)
    ev = SilhouetteEvaluator(ref)
    same = ev.score(_tower(tmp_path / "same.png", w=120, h=400))
    assert same == {"iou": 1.0, "profile_corr": 1.0, "score": 1.0}
    # same aspect but different absolute size normalises to the same silhouette
    scaled = ev.score(_tower(tmp_path / "scaled.png", w=60, h=200))
    assert scaled["iou"] > 0.97
    # a wider tower overlaps less
    wide = ev.score(_tower(tmp_path / "wide.png", w=240, h=400))
    assert wide["iou"] < same["iou"] and wide["score"] < same["score"]
    assert 0.0 <= wide["score"] <= 1.0
    # nothing in the render -> zero, never NaN
    blank = tmp_path / "blank.png"
    Image.new("RGB", (300, 640), "white").save(blank)
    assert ev.score(str(blank)) == {"iou": 0.0, "profile_corr": 0.0, "score": 0.0}


def test_mock_critic_thresholds_and_zero_usage():
    c = MockCritic()
    texts = []
    for s in (0.1, 0.7, 0.95):
        msg, usage = c.critique("r", "ref", {"score": s}, 1)
        assert usage == {"prompt_tokens": 0, "completion_tokens": 0}
        texts.append(msg)
    assert len(set(texts)) == 3, "three distinct bands of advice"
