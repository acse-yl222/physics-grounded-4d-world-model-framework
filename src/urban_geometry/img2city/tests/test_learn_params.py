"""Learned-prior parameter vector: range clamping, normalise/denormalise
round-trip, and the vec -> build_building description bridge."""
import pytest

P = pytest.importorskip("img2city.prior.params")


def test_roundtrip_normalize_denormalize():
    mid = [(lo + hi) / 2 for _, lo, hi, _ in P.PARAM_RANGES]
    back = P.denormalize(P.normalize(mid))
    for a, b, (_, _, _, is_int) in zip(mid, back, P.PARAM_RANGES):
        expected = round(a) if is_int else a       # int params round by design
        assert b == pytest.approx(expected, rel=1e-6, abs=1e-6)


def test_normalized_midpoint_is_half():
    mid = [(lo + hi) / 2 for _, lo, hi, _ in P.PARAM_RANGES]
    for v in P.normalize(mid):
        assert v == pytest.approx(0.5, abs=1e-9)


def test_vec_to_desc_produces_buildable_description():
    mid = [(lo + hi) / 2 for _, lo, hi, _ in P.PARAM_RANGES]
    d = P.vec_to_desc(mid)
    assert isinstance(d["footprint"], list) and len(d["footprint"]) == 2
    L, W = d["footprint"]
    lo_L = [r for r in P.PARAM_RANGES if r[0] == "L"][0]
    assert lo_L[1] <= L <= lo_L[2]
    assert d["masses"], "prior description must carry masses"
    for m in d["masses"]:
        assert m["floors"] >= 1


def test_int_params_come_out_integral():
    mid = [(lo + hi) / 2 for _, lo, hi, _ in P.PARAM_RANGES]
    d = dict(zip(P.NAMES, P.denormalize(P.normalize(mid))))
    for name, lo, hi, is_int in P.PARAM_RANGES:
        if is_int:
            assert float(d[name]).is_integer(), name
