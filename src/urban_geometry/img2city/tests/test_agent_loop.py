"""The offline agent loop: planner, tool registry, mock executor, token
logging, and the Harness end to end. No Blender, no API, no tokens."""
import csv
import json
import os

import pytest

from img2city.agent.harness import Harness, HarnessConfig
from img2city.agent.planner import Action, Context, MockAgent
from img2city.agent.tokens import TokenLogger, provenance
from img2city.agent.tools import MockExecutor, PARAMS, Tool, example_registry
from img2city.judge.evaluator import MockCritic, SilhouetteEvaluator


def _ctx(it=1, score=None, critique=""):
    return Context(goal="g", iteration=it, last_score=score,
                   last_critique=critique, state={})


# ---------------- planner

def test_mock_agent_is_deterministic_per_seed():
    a, b = MockAgent(seed=3), MockAgent(seed=3)
    for it in range(1, 6):
        (ax, ux), (bx, ub) = a.plan(_ctx(it)), b.plan(_ctx(it))
        assert ax.params_delta == bx.params_delta
        assert ux == ub


def test_mock_agent_nudges_one_known_param_and_shrinks_with_score():
    agent = MockAgent(step=0.2, seed=0)
    act, usage = agent.plan(_ctx(1, {"score": 0.0}))
    assert len(act.params_delta) == 1
    (k, d), = act.params_delta.items()
    assert k in MockAgent.PARAMS and k in PARAMS
    assert abs(d) == pytest.approx(0.2 * 1.0 + 0.01)
    act2, _ = agent.plan(_ctx(2, {"score": 0.9}))
    (_, d2), = act2.params_delta.items()
    assert abs(d2) == pytest.approx(0.2 * 0.1 + 0.01)
    assert usage["prompt_tokens"] > 0 and usage["completion_tokens"] > 0


# ---------------- tool registry

def test_registry_schemas_are_anthropic_shaped():
    r = example_registry()
    names = r.names()
    assert {"import_mesh", "edit_geometry", "render_compare", "export_mesh"} <= set(names)
    for s in r.schemas():
        assert set(s) == {"name", "description", "input_schema"}
        assert s["input_schema"]["type"] == "object"
    r.register(Tool("x", "d", {"type": "object", "properties": {}}))
    assert r.get("x").name == "x" and "x" in r.names()
    with pytest.raises(KeyError):
        r.get("nope")


# ---------------- mock executor

def test_mock_executor_clamps_and_renders(tmp_path):
    ex = MockExecutor(str(tmp_path))
    st = ex.reset()
    assert set(st) == set(PARAMS)
    render, new = ex.execute(Action(params_delta={"base_w": +5.0, "dome_r": -5.0,
                                                  "unknown": 1.0}), st)
    assert os.path.exists(render)
    assert new["base_w"] == 1.0 and new["dome_r"] == 0.05
    assert "unknown" not in new
    assert st["base_w"] == 0.40, "execute must not mutate the input state"
    ref = ex.make_reference()
    assert os.path.exists(ref)


# ---------------- token logging

def test_token_logger_totals_csv_and_summary(tmp_path):
    t = TokenLogger()
    t.log(1, "planner", "m", 100, 10)
    t.log(1, "critic", "m", 5, 5)
    t.log(2, "planner", "m", 200, "20")          # str counts are coerced
    assert t.total_prompt == 305 and t.total_completion == 35 and t.total_tokens == 340
    assert t.per_iteration() == {1: 120, 2: 220}
    p = t.to_csv(str(tmp_path / "sub" / "tokens.csv"))
    rows = list(csv.DictReader(open(p)))
    assert len(rows) == 3 and rows[0]["total"] == "110"
    assert t.summary().startswith("3 LLM calls over 2 iterations")
    assert TokenLogger().per_iteration() == {}
    assert TokenLogger().plot(str(tmp_path / "none.png")) is None


def test_provenance_records_queryable_facts_only():
    p = provenance(model="x")
    assert {"time_utc", "python", "platform", "model"} <= set(p)
    assert p["model"] == "x"
    if "git_rev" in p:
        assert isinstance(p["git_rev"], str) and p["git_rev"]


# ---------------- the loop

def test_harness_offline_loop_is_monotonic_and_writes_artifacts(tmp_path):
    ex = MockExecutor(str(tmp_path / "work"))
    ref = ex.make_reference()
    cfg = HarnessConfig(reference_path=ref, out_dir=str(tmp_path),
                        max_iters=12, stop_score=0.99)
    h = Harness(cfg, MockAgent(seed=1), ex, SilhouetteEvaluator(ref), MockCritic())
    run_dir, best = h.run(str(tmp_path / "run"))

    bests = [r["best_score"] for r in h.log]
    assert bests == sorted(bests), "best score must never decrease"
    assert h.log[0]["rationale"] == "baseline" and h.log[0]["accepted"]
    for prev, r in zip(h.log, h.log[1:]):
        if r["accepted"]:
            assert r["best_score"] == r["score"]["score"] > prev["best_score"]
        else:
            assert r["score"]["score"] <= prev["best_score"] == r["best_score"]
    assert 0.0 <= best["score"] <= 1.0

    for f in ("run_log.json", "tokens.csv", "snapshots/iter_000.png"):
        assert os.path.exists(os.path.join(run_dir, f)), f
    log = json.load(open(os.path.join(run_dir, "run_log.json")))
    assert log["final_best"] == best
    assert log["iterations_run"] == h.log[-1]["iteration"] <= cfg.max_iters
    assert len(log["iterations"]) == len(h.log)
    # two LLM calls (planner + critic) are logged per refinement iteration
    assert len(h.tokens.records) == 2 * (len(h.log) - 1)
    # snapshots exist exactly for accepted iterations
    snaps = sorted(os.listdir(os.path.join(run_dir, "snapshots")))
    accepted = [r["iteration"] for r in h.log if r["accepted"]]
    assert snaps == [f"iter_{i:03d}.png" for i in accepted]


def test_harness_stops_at_target_score(tmp_path):
    ex = MockExecutor(str(tmp_path / "work"))
    ref = ex.make_reference()
    cfg = HarnessConfig(reference_path=ref, max_iters=50, stop_score=0.0)
    h = Harness(cfg, MockAgent(), ex, SilhouetteEvaluator(ref))
    h.run(str(tmp_path / "run"))
    assert h.log[-1]["iteration"] == 1, "baseline already >= stop_score -> one iteration"
