"""OpenAI-family transports: the local Codex CLI (ChatGPT subscription login)
and the Responses API (``OPENAI_API_KEY``).

Returns model text only; :mod:`img2city.agent.llm` owns routing and
receipts, the callers own parsing.  No geometry is authored here.
"""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile

from img2city import config

TRANSPORTS = ("codex", "openai")


def vision_call(system, user, images, model=None, *, transport=None, max_tokens=8192,
                timeout_s=None):
    """``(text, usage, response_id)`` via ``transport`` (default: the configured
    provider when it is one of ours)."""
    model = model or config.VISION_MODEL
    transport = transport or config.LLM_PROVIDER
    if transport not in TRANSPORTS:
        raise ValueError(f"openai_backend transport must be one of {TRANSPORTS}, got {transport!r}")
    timeout_s = timeout_s or config.LLM_TIMEOUT
    images = [str(Path(p).resolve(strict=True)) for p in images if p]
    if transport == "codex":
        return _codex(system, user, images, model, timeout_s)
    return _responses(system, user, images, model, max_tokens, timeout_s)


def _codex(system, user, images, model, timeout_s):
    env = dict(os.environ)
    # Explicitly retain subscription authentication rather than inherit an API key.
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    with tempfile.TemporaryDirectory(prefix="img2city-inference-") as work:
        answer = Path(work) / "answer.txt"
        cmd = [config.CODEX_BIN, "exec", "--ignore-user-config", "--ephemeral",
               "--skip-git-repo-check", "--sandbox", "read-only", "--json",
               "--model", model, "--cd", work, "--output-last-message", str(answer),
               "-c", 'forced_login_method="chatgpt"',
               "-c", "model_reasoning_effort=" + json.dumps(config.LLM_REASONING)]
        for p in images:
            cmd.extend(["--image", p])
        cmd.append("-")
        prompt = ("You are a model inference step inside Img2City. Return only the "
                  "requested response. Do not run tools, edit files, or take over "
                  "the pipeline. Images are attached in the given order.\n\n"
                  + system + "\n\n" + user)
        proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True,
                              env=env, timeout=timeout_s)
        usage, response_id, completed = {}, None, False
        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "thread.started":
                response_id = event.get("thread_id")
            if event.get("type") == "turn.completed":
                u = event.get("usage") or {}
                usage = {"prompt_tokens": u.get("input_tokens", 0),
                         "completion_tokens": u.get("output_tokens", 0),
                         "cached_input_tokens": u.get("cached_input_tokens", 0)}
                completed = True
        if proc.returncode or not completed or not answer.exists():
            raise RuntimeError("Codex inference failed: " + (proc.stderr or proc.stdout)[-2000:])
        return answer.read_text(), usage, response_id


def _responses(system, user, images, model, max_tokens, timeout_s):
    import requests
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required for IMG2CITY_LLM_PROVIDER=openai")
    content = [{"type": "input_text", "text": user}]
    for p in images:
        from PIL import Image
        with Image.open(p) as im:
            mime = Image.MIME[im.format]
        data = base64.b64encode(Path(p).read_bytes()).decode("ascii")
        content.append({"type": "input_image", "image_url": f"data:{mime};base64,{data}",
                        "detail": "high"})
    response = requests.post(
        config.OPENAI_BASE_URL + "/responses",
        headers={"Authorization": "Bearer " + key},
        json={"model": model, "instructions": system, "store": False,
              "input": [{"role": "user", "content": content}],
              "reasoning": {"effort": config.LLM_REASONING},
              "max_output_tokens": max(16384, max_tokens)}, timeout=timeout_s)
    response.raise_for_status()
    result = response.json()
    if result.get("status") != "completed":
        raise RuntimeError(f"response {result.get('status')}: {result.get('incomplete_details')}")
    text = "".join(c["text"] for item in result.get("output", [])
                   if item.get("type") == "message" for c in item.get("content", [])
                   if c.get("type") == "output_text")
    u = result.get("usage") or {}
    return text, {"prompt_tokens": u.get("input_tokens", 0),
                  "completion_tokens": u.get("output_tokens", 0)}, result.get("id")
