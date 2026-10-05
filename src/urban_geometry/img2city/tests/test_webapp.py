"""Webapp logic that has bitten before: bbox area matching, the make_city
quote regex, job stage inference, and the edit-schema's bilingual integrity."""
import pytest

areas = pytest.importorskip("img2city.webapp.areas")
jobs = pytest.importorskip("img2city.webapp.jobs")
spec_schema = pytest.importorskip("img2city.webapp.schema")


# ---- match_bbox against a synthetic registry (no disk dependence)
FAKE = [{"name": "city_x", "bbox": [51.4939, -0.1764, 51.4976, -0.1706],
         "specs": 100, "stale": False, "has_blend": True},
        {"name": "city_stale", "bbox": [51.4939, -0.1764, 51.4976, -0.1706],
         "specs": 999, "stale": True, "has_blend": True}]


def test_match_bbox_hits_same_area(monkeypatch):
    monkeypatch.setattr(areas, "list_areas", lambda: FAKE)
    m = areas.match_bbox(51.4939, -0.1764, 51.4976, -0.1706)
    assert m and m["name"] == "city_x"


def test_match_bbox_ignores_stale_and_misses_far_bbox(monkeypatch):
    monkeypatch.setattr(areas, "list_areas", lambda: FAKE)
    m = areas.match_bbox(51.4939, -0.1764, 51.4976, -0.1706)
    assert m["name"] != "city_stale"
    assert areas.match_bbox(52.20, 0.11, 52.21, 0.12) is None


def test_quote_regex_parses_real_scope_line():
    import re
    line = ("[make-city] scope: 234 buildings; 234 specs to write; paid stages "
            "~129M tokens upper bound (specs 11.7M + refine-iters-2 worst case "
            "117M -- gate-skips reduce it)")
    m = re.search(jobs.QUOTE_RX, line)
    assert m
    assert m.group(1) == "234" and m.group(3) == "129"


def test_stage_inference_ignores_stale_preview_blend():
    j = jobs.Job("generate", "unit_test_area")
    j.status = "running"
    # specs done, refine in progress, but a stale LoD1 preview blend exists:
    # the stage must still read as refine (bug fixed 08-20)
    p = {"bootstrap": True, "total": 10, "specs": 10, "refined": 3,
         "scene_layers": True, "assembled": True, "verdict": None}
    assert j.stage_of(p) == "refine"
    p2 = dict(p, verdict="PASS")
    assert j.stage_of(p2) == "verify"
    p3 = dict(p, specs=4)
    assert j.stage_of(p3) == "specs"


def test_schema_fields_are_labelled_and_typed():
    sc = spec_schema.get_schema()
    for g in sc["groups"]:
        assert g.get("title")
        for f in g["fields"]:
            assert f.get("label"), f["path"]
            assert f["type"] in ("int", "float", "bool", "enum", "color")
            if f["type"] == "enum":
                assert f.get("choices")
    for key, entry in sc["lists"].items():
        assert entry.get("title"), key
