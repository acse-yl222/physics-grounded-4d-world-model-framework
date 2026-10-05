"""The model layer is configuration: provider + model per role come from
.env / the environment, callers only ever talk to img2city.agent.llm."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from img2city import config
from img2city.agent import llm
from img2city.agent import openai_backend as ob


# ---- config -------------------------------------------------------------------
def test_parse_dotenv_accepts_export_quotes_and_comments():
    text = """
    # keys
    export GOOGLE_MAPS_API_KEY=abc
    OPENAI_BASE_URL="https://proxy.example/v1"   # trailing
    IMG2CITY_MODEL='gpt-6'  # quoted
    IMG2CITY_LLM_TIMEOUT=300 # comment
    not a line
    =novalue
    """
    assert config.parse_dotenv(text) == {
        "GOOGLE_MAPS_API_KEY": "abc", "OPENAI_BASE_URL": "https://proxy.example/v1",
        "IMG2CITY_MODEL": "gpt-6", "IMG2CITY_LLM_TIMEOUT": "300"}


def test_load_dotenv_never_overrides_the_process_environment(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("IMG2CITY_TEST_A=file\nIMG2CITY_TEST_B=file\nIMG2CITY_TEST_C=\n")
    monkeypatch.setenv("IMG2CITY_TEST_A", "shell")
    monkeypatch.delenv("IMG2CITY_TEST_B", raising=False)
    monkeypatch.delenv("IMG2CITY_TEST_C", raising=False)
    applied = config.load_dotenv(env)
    assert applied == {"IMG2CITY_TEST_B": "file"}          # empty KEY= is "unset", not ""
    assert "IMG2CITY_TEST_C" not in __import__("os").environ
    assert config.load_dotenv(tmp_path / "missing.env") == {}


# ---- provider resolution -------------------------------------------------------
def test_resolve_precedence_prefix_over_backend_over_config(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "codex")
    monkeypatch.setattr(config, "DEFAULT_MODEL", "gpt-6-astra")
    assert llm.resolve() == ("codex", "gpt-6-astra")
    assert llm.resolve("m", "api") == ("claude-api", "m")
    assert llm.resolve("claude-sdk:claude-sonnet-5", "openai") == ("claude-sdk", "claude-sonnet-5")
    assert llm.resolve(None, None, default_model="judge-x") == ("codex", "judge-x")
    with pytest.raises(ValueError, match="unknown LLM provider"):
        llm.resolve("m", "bedrock")


def test_vision_call_dispatches_on_provider_only(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "MODEL_LOG_DIR", tmp_path / "receipts")
    seen = []
    def fake(system, user, images, model, *, transport, max_tokens, timeout_s):
        seen.append((transport, model, images))
        return "answer", {"prompt_tokens": 3, "completion_tokens": 1}, "resp-1"
    monkeypatch.setattr(ob, "vision_call", fake)
    monkeypatch.setattr(config, "LLM_PROVIDER", "openai")
    text, usage, cost = llm.vision_call("sys", "user", [], "any-model-name")
    assert (text, cost) == ("answer", None) and usage["prompt_tokens"] == 3
    llm.vision_call("sys", "user", [], "codex:other")
    assert [s[:2] for s in seen] == [("openai", "any-model-name"), ("codex", "other")]
    receipts = [json.loads(p.read_text()) for p in (tmp_path / "receipts").glob("*.json")]
    assert sorted(r["provider"] for r in receipts) == ["codex", "openai"]
    assert all(r["response_id"] == "resp-1" and r["output"] == "answer" for r in receipts)


def test_empty_answer_is_an_error_not_a_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "MODEL_LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "LLM_PROVIDER", "codex")
    monkeypatch.setattr(ob, "vision_call", lambda *a, **k: ("  ", {}, None))
    with pytest.raises(RuntimeError, match="no answer"):
        llm.vision_call("sys", "user", [], "m")


def test_healthcheck_uses_the_same_transport(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "MODEL_LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "LLM_PROVIDER", "codex")
    monkeypatch.setattr(ob, "vision_call", lambda *a, **k: ("OK", {}, None))
    assert llm.healthcheck("gpt-6-astra") == (True, "OK")
    def fail(*a, **kw):
        raise RuntimeError("backend unavailable")
    monkeypatch.setattr(ob, "vision_call", fail)
    assert llm.healthcheck("gpt-6-astra") == (False, "backend unavailable")


# ---- callers go through llm ----------------------------------------------------
def test_planner_and_critic_use_the_configured_model(monkeypatch, tmp_path):
    from img2city.agent.planner import Context, LLMAgent
    from img2city.judge.evaluator import LLMCritic
    calls = []
    def fake(system, user, images, model=None, **kw):
        calls.append(model)
        return '{"param":"dome_r","delta":0.1}', {"prompt_tokens": 8, "completion_tokens": 4}, None
    monkeypatch.setattr(llm, "vision_call", fake)
    monkeypatch.setattr(config, "SPEC_MODEL", "spec-x")
    monkeypatch.setattr(config, "JUDGE_MODEL", "judge-x")
    ctx = Context(goal="test", iteration=1, last_score=None, last_critique="", state={})
    action, usage = LLMAgent().plan(ctx)
    assert action.params_delta == {"dome_r": 0.1} and usage["prompt_tokens"] == 8
    text, usage = LLMCritic().critique("render", "photo", 0, 1)
    assert "dome_r" in text
    assert calls == ["spec-x", "judge-x"]


def test_legacy_backend_argument_only_overrides_when_given(monkeypatch):
    from img2city.building.generate import _vision
    seen = []
    def fake(system, user, images, model=None, **kw):
        seen.append(model)
        return "answer", {"prompt_tokens": 3}, None
    monkeypatch.setattr(llm, "vision_call", fake)
    monkeypatch.setattr(config, "LLM_PROVIDER", "codex")
    assert _vision("", "", [], None, "gpt-6-astra")[0] == "answer"
    _vision("", "", [], "api", "m")
    _vision("", "", [], "openai", "openai:m2")
    assert seen == ["codex:gpt-6-astra", "claude-api:m", "openai:m2"]


def test_photo_roles_follow_configuration():
    from img2city.webapp import photo
    assert photo.CARD_MODEL == config.PHOTO_CARD_MODEL
    assert photo.SPEC_MODEL == config.PHOTO_SPEC_MODEL


def test_spec_prompt_and_validation_share_real_material_palette(monkeypatch):
    from img2city.building import generate
    from img2city.kit import material_names
    def call(system, *args, **kwargs):
        assert all(name in system for name in material_names())
        return '{"footprint":[20,10]}', {}
    monkeypatch.setattr(generate, "_vision", call)
    generate.gen_spec([], None, None, None, None, "gpt-6-astra")
    _, errs = generate.validate_desc(json.dumps({"footprint": [20, 10],
        "extra_parts": [{"type": "platform_canopy", "roof_material": "invented_metal"}]}))
    assert any("invented_metal" in err for err in errs)
    assert generate.component_errors({"result": "[components] part 3 failed: no material"})
    assert generate.component_errors({"result": "[components] assembled 3 objects"}) is None


# ---- openai transports ----------------------------------------------------------
def test_codex_attaches_images_and_uses_subscription(monkeypatch, tmp_path):
    photo = tmp_path / "photo.png"
    photo.write_bytes(b"reference")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    monkeypatch.setenv("CODEX_API_KEY", "must-not-inherit")
    monkeypatch.setattr(config, "MODEL_LOG_DIR", tmp_path / "receipts")
    monkeypatch.setattr(config, "LLM_PROVIDER", "codex")
    monkeypatch.setattr(config, "CODEX_BIN", "/opt/codex")
    monkeypatch.setattr(config, "LLM_REASONING", "medium")
    def run(cmd, **kw):
        assert cmd[0] == "/opt/codex"
        assert cmd[cmd.index("--model") + 1] == "gpt-6-astra"
        assert cmd[cmd.index("--image") + 1] == str(photo)
        assert "OPENAI_API_KEY" not in kw["env"]
        assert "CODEX_API_KEY" not in kw["env"]
        assert 'forced_login_method="chatgpt"' in cmd
        assert 'model_reasoning_effort="medium"' in cmd
        assert "read-only" in cmd
        Path(cmd[cmd.index("--output-last-message") + 1]).write_text('{"floors": 1}')
        return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
            "type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 7}}))
    monkeypatch.setattr(ob.subprocess, "run", run)
    text, usage, cost = llm.vision_call("spec", "image 1", [photo], "gpt-6-astra")
    assert json.loads(text) == {"floors": 1}
    assert usage["prompt_tokens"] == 12 and cost is None
    receipt = json.loads(next((tmp_path / "receipts").glob("*.json")).read_text())
    assert receipt["model"] == "gpt-6-astra" and receipt["provider"] == "codex"
    assert len(receipt["images"][0]["sha256"]) == 64


def test_failed_codex_does_not_accept_partial_answer(monkeypatch):
    def run(cmd, **kw):
        Path(cmd[cmd.index("--output-last-message") + 1]).write_text("partial")
        return SimpleNamespace(returncode=1, stdout="", stderr="usage limit")
    monkeypatch.setattr(ob.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="usage limit"):
        ob._codex("", "", [], "gpt-6-astra", 10)


def test_responses_api_uses_configured_endpoint_and_rejects_incomplete_output(monkeypatch, tmp_path):
    import requests
    from PIL import Image
    photo = tmp_path / "reference.png"
    Image.new("RGB", (2, 2)).save(photo)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr(config, "OPENAI_BASE_URL", "https://proxy.example/v1")
    monkeypatch.setattr(config, "LLM_REASONING", "low")
    def post(url, **kw):
        assert url == "https://proxy.example/v1/responses"
        payload = kw["json"]
        assert payload["model"] == "gpt-6-astra"
        assert payload["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")
        assert payload["reasoning"]["effort"] == "low"
        assert "temperature" not in payload
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}})
    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(RuntimeError, match="incomplete"):
        ob._responses("system", "user", [str(photo)], "gpt-6-astra", 150, 10)


def test_openai_backend_refuses_unknown_transport():
    with pytest.raises(ValueError, match="transport"):
        ob.vision_call("s", "u", [], "m", transport="claude-sdk")
