"""Claude transports: the Claude Agent SDK (Claude Code CLI login, bills a
Pro/Max subscription) and the Anthropic Messages API (``ANTHROPIC_API_KEY``,
pay-as-you-go).

Prerequisites for ``claude-sdk`` (macOS):
    npm i -g @anthropic-ai/claude-code      # Claude Code CLI (the SDK shells out to it)
    pip install claude-agent-sdk anyio      # Python SDK (Python 3.10+)
    unset ANTHROPIC_API_KEY                  # if set, the key takes precedence
                                             # and you pay API rates
    claude login                             # choose your Pro/Max plan

Vision note: the Agent SDK's query() has no direct image-content input, so we
enable the built-in **Read** tool and pass absolute image PATHS; Claude opens
them with Read and reasons over them as vision.  Token usage is read from
ResultMessage.  ``claude-api`` sends images inline as base64 blocks.

Both SDKs are imported lazily (inside the call) so the rest of the package
imports fine when neither is installed.  Returns model text only.
"""
from __future__ import annotations
import base64
import os
import subprocess
import time

from img2city import config


def image_block(path: str) -> dict:
    """Anthropic image content block (base64).  Picks media type by extension."""
    mt = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}}


def api_call(system, user, images, model, *, max_tokens=2500, timeout_s=None):
    """``(text, usage, cost_usd, response_id)`` via the Messages API.  The
    client reads ``ANTHROPIC_API_KEY`` (and ``ANTHROPIC_BASE_URL``) from the
    environment; the key is never handled here."""
    from anthropic import Anthropic                  # pip install anthropic
    kw = {"base_url": config.ANTHROPIC_BASE_URL} if config.ANTHROPIC_BASE_URL else {}
    if timeout_s:
        kw["timeout"] = float(timeout_s)
    client = Anthropic(**kw)
    content = [{"type": "text", "text": user}] + [image_block(p) for p in images]
    resp = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                                  messages=[{"role": "user", "content": content}])
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    usage = {"prompt_tokens": resp.usage.input_tokens,
             "completion_tokens": resp.usage.output_tokens}
    return text, usage, None, getattr(resp, "id", None)


def sdk_call(system, user, images, model, *, max_turns=6, timeout_s=300.0):
    """``(text, usage, cost_usd, response_id)`` via the Agent SDK.  A stalled
    call is bounded by ``timeout_s`` (2026-07-27: a hung multi-image vision
    call has NO natural timeout and froze a synchronous refine batch for
    hours -- the trivial-text healthcheck can't see it; a hard deadline turns
    the hang into a retryable TimeoutError instead)."""
    import anyio
    from claude_agent_sdk import (query, AssistantMessage, TextBlock,
                                  ResultMessage, ClaudeAgentOptions)

    abspaths = [os.path.abspath(p) for p in images if p]
    prompt = user
    if abspaths:
        listing = "\n".join(f"- {p}" for p in abspaths)
        prompt = (f"{user}\n\nFirst use the Read tool to open the image file(s) "
                  f"below, then answer based on what you actually see:\n{listing}")

    async def _run():
        texts, usage, cost, sid = [], {"prompt_tokens": 0, "completion_tokens": 0}, 0.0, None
        opts = ClaudeAgentOptions(
            system_prompt=system,
            allowed_tools=["Read"],
            permission_mode="bypassPermissions",   # non-interactive: don't prompt for Read
            max_turns=max_turns,
            **({"model": model} if model else {}),
        )
        with anyio.fail_after(timeout_s):          # hard deadline on a stalled call
            async for m in query(prompt=prompt, options=opts):
                if isinstance(m, AssistantMessage):
                    for b in m.content:
                        if isinstance(b, TextBlock):
                            texts.append(b.text)
                elif isinstance(m, ResultMessage):
                    u = m.usage or {}
                    # Claude Code caches the big system prompt + tool schemas, so
                    # most input arrives as cache-read tokens; fold them in.
                    inp = (int(u.get("input_tokens", 0) or 0)
                           + int(u.get("cache_read_input_tokens", 0) or 0)
                           + int(u.get("cache_creation_input_tokens", 0) or 0))
                    usage = {"prompt_tokens": inp,
                             "completion_tokens": int(u.get("output_tokens", 0) or 0)}
                    cost = float(m.total_cost_usd or 0.0)
                    sid = getattr(m, "session_id", None)
        return "".join(texts), usage, cost, sid

    # The SDK/CLI occasionally returns a transient error result ("Claude Code returned
    # an error result: ..."); retry a couple of times with backoff so one blip doesn't
    # abort a whole multi-iteration run.
    last_err = None
    for attempt in range(3):
        try:
            return anyio.run(_run)
        except Exception as e:                     # noqa: BLE001 -- retried, then re-raised
            last_err = e
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_err


def cli_healthcheck(model=None) -> tuple[bool, str]:
    """Probe the Claude Code CLI with a trivial prompt and return (ok, reason).
    The SDK collapses a usage-limit result into an opaque 'error result:
    success'; the CLI in --print mode returns the HUMAN-READABLE reason as
    normal output, so we read it here to tell a limit from a transient error."""
    cmd = [config.CLAUDE_CLI, "--print"] + (["--model", model] if model else [])
    try:
        out = subprocess.run(cmd, input="Reply with the single word OK.",
                             capture_output=True, text=True, timeout=120)
    except Exception as e:                         # noqa: BLE001 -- the reason is the result
        return False, f"could not run the claude CLI: {e}"
    txt = (out.stdout or out.stderr or "").strip()
    low = txt.lower()
    if "reached your" in low and "limit" in low:      # "You've reached your ... limit."
        return False, txt.splitlines()[0]
    if "invalid api key" in low or "please run" in low or "login" in low:
        return False, txt.splitlines()[0]
    if "ok" in low and len(txt) < 40:
        return True, txt
    return (out.returncode == 0), (txt[:160] or f"exit {out.returncode}")
