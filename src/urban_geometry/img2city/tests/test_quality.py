"""Acceptance policy: offline tests with no model calls or Blender."""
import json
from unittest.mock import Mock

import pytest

from img2city.city import quality as q


CONTRACT = {k: ["reference-backed reconstruction"] for k in
            ("criteria", "critical_defects", "permissible_limitations")}


def decision(verdict="pass", issues=None):
    return {"verdict": verdict, "reason": "Roof matches the reference", "issues": issues or []}, {}


def test_serious_objection_cannot_be_averaged_away(monkeypatch):
    objection = {"severity": "major", "evidence": "Reference wing absent",
                 "action": "learn", "fix": "Represent missing wing"}
    monkeypatch.setattr(q, "_ask", Mock(side_effect=[decision(), decision(), decision("repair", [objection])]))
    result = q.votes(CONTRACT, {}, [], "test")
    assert not result["passed"] and result["issues"] == [objection]


def test_insufficient_evidence_blocks_acceptance(monkeypatch):
    monkeypatch.setattr(q, "_ask", Mock(side_effect=[decision(), decision(), decision("insufficient_evidence")]))
    assert not q.votes(CONTRACT, {}, [], "test")["passed"]


def test_supported_votes_pass(monkeypatch):
    monkeypatch.setattr(q, "_ask", Mock(return_value=decision()))
    assert q.votes(CONTRACT, {}, [], "test")["passed"]


def test_malformed_decision_fails_closed(monkeypatch):
    monkeypatch.setattr(q, "_ask", Mock(return_value=({"verdict": "pass"}, {})))
    with pytest.raises(ValueError):
        q.votes(CONTRACT, {}, [], "test")


def test_contract_frozen_and_cached_contract_validated(tmp_path, monkeypatch):
    ask = Mock(return_value=(dict(CONTRACT), {}))
    monkeypatch.setattr(q, "_ask", ask)
    assert q.contract(tmp_path, "a") == q.contract(tmp_path, "b")
    assert ask.call_count == 1
    (tmp_path / "quality/contract.json").write_text('{}')
    with pytest.raises(ValueError):
        q.contract(tmp_path, "b")


def test_stale_assembly_invalidates_previous_pass_without_spending_tokens(tmp_path, monkeypatch):
    q._write(tmp_path / "quality/latest.json", {"status": "PASS"})
    monkeypatch.setattr(q, "scene_signature", lambda _: "current")
    ask = Mock(side_effect=AssertionError("must not call model"))
    monkeypatch.setattr(q, "_ask", ask)
    result = q.assess(tmp_path, "test")
    assert result["status"] == "INCOMPLETE"
    assert "stale" in result["errors"][0]["error"]
    assert json.loads((tmp_path / "quality/latest.json").read_text())["status"] == "INCOMPLETE"
    ask.assert_not_called()


def test_changed_scene_image_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "scene_signature", lambda _: "current")
    for name in q.SCENE_VIEWS:
        (tmp_path / name).write_bytes(b"original")
    q.record_assembly(tmp_path)
    (tmp_path / q.SCENE_VIEWS[0]).write_bytes(b"changed")
    result = q.assess(tmp_path, "test")
    assert result["status"] == "INCOMPLETE"
    assert "images" in result["errors"][0]["error"]


def prepared_scene(tmp_path, monkeypatch, *, complete=True, fallback=False):
    from img2city.city import make_city
    monkeypatch.setattr(q, "scene_signature", lambda _: "current")
    for name in (*q.SCENE_VIEWS, "block_sat_bbox.png"):
        (tmp_path / name).write_bytes(b"image")
    q.record_assembly(tmp_path)
    q._write(tmp_path / "buildings.json", {"buildings": [{"id": 1}]})
    if fallback:
        q._write(tmp_path / "buildings/1/gate.json", {"fallback": True})
    monkeypatch.setattr(make_city, "verify", lambda _: {
        "ok": True, "coverage": {"buildings": 1, "specs": int(complete)},
        "layers": {"roads": True}})
    monkeypatch.setattr(q, "_ask", Mock(return_value=decision()))
    q._write(tmp_path / "quality/contract.json", CONTRACT)
    monkeypatch.setattr(q, "review_building", lambda *args: {
        "id": 1, "passed": True, "issues": []})


def test_full_evidence_and_all_buildings_required(tmp_path, monkeypatch):
    prepared_scene(tmp_path, monkeypatch)
    assert q.assess(tmp_path, "test")["status"] == "PASS"


def test_partial_coverage_is_not_success(tmp_path, monkeypatch):
    prepared_scene(tmp_path, monkeypatch, complete=False)
    result = q.assess(tmp_path, "test")
    assert result["status"] == "INCOMPLETE"
    q._ask.assert_not_called()


def test_all_shells_cannot_be_passed_as_reconstruction(tmp_path, monkeypatch):
    prepared_scene(tmp_path, monkeypatch, fallback=True)
    result = q.assess(tmp_path, "test")
    assert result["status"] == "INCOMPLETE" and len(result["limitations"]) == 1


def test_scene_change_during_review_is_not_success(tmp_path, monkeypatch):
    prepared_scene(tmp_path, monkeypatch)
    monkeypatch.setattr(q, "scene_signature", Mock(side_effect=["current", "changed"]))
    result = q.assess(tmp_path, "test")
    assert result["status"] == "INCOMPLETE"
    assert "changed during" in result["errors"][0]["error"]
