"""Pure helpers of the imagery layer (no network, no keys)."""
import pytest

from img2city.imagery.acquire_view import _parse_judge
from img2city.imagery.maps_fetch import _bearing, latin_only


def test_parse_judge_extracts_json_anywhere_in_text():
    ok, score, note = _parse_judge('Sure. {"visible": true, "score": 0.8, "note": "clear"} bye')
    assert ok is True and score == 0.8 and note == "clear"
    ok, score, note = _parse_judge('{"visible": false}')
    assert (ok, score, note) == (False, 0.0, "")


def test_parse_judge_falls_back_on_garbage():
    text = "no json here " * 10
    ok, score, note = _parse_judge(text)
    assert (ok, score) == (False, 0.0) and note == text[:60]
    ok, _, note = _parse_judge("{not: json}")
    assert ok is False and note.startswith("{not")


def test_latin_only_strips_non_latin_and_truncates():
    assert latin_only("Café Müller") == "Café Müller"
    assert latin_only("寿司 Sushi Bar") == "Sushi Bar"
    assert latin_only("寿司") == "(non-Latin name)"
    assert latin_only(None) == "(non-Latin name)"
    assert len(latin_only("x" * 100, n=28)) == 28


def test_bearing_cardinal_directions():
    lat, lng = 51.5, -0.17
    assert _bearing(lat, lng, lat + 0.01, lng) == pytest.approx(0.0, abs=0.01)
    assert _bearing(lat, lng, lat, lng + 0.01) == pytest.approx(90.0, abs=0.1)
    assert _bearing(lat, lng, lat - 0.01, lng) == pytest.approx(180.0, abs=0.01)
    assert _bearing(lat, lng, lat, lng - 0.01) == pytest.approx(270.0, abs=0.1)
