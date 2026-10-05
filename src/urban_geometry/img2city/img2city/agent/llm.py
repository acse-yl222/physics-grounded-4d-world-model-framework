"""One front door for every model call in the pipeline.

Every agent stage (vision, spec, judge, learning) calls :func:`vision_call`
with a system prompt, a user prompt and image paths, and gets text back.
Which *provider* answers is configuration, never code:

    IMG2CITY_LLM_PROVIDER   codex | openai | claude-sdk | claude-api   (.env)
    IMG2CITY_<ROLE>_MODEL   the model name per role

A model string may carry an explicit provider prefix, ``<provider>:<model>``
(``claude-api:claude-sonnet-5``), which wins over the ``backend`` argument,
which wins over the configured provider.  ``sdk`` / ``api`` are accepted as
short aliases of ``claude-sdk`` / ``claude-api`` (the historical ``--backend``
values).

This module returns model text only -- parsing, validation, rendering,
judging and adoption stay with the callers.  Every successful call writes a
JSON receipt (prompt, output, usage, image hashes; never keys or image bytes)
to ``config.MODEL_LOG_DIR``.  Transports live in :mod:`openai_backend` and
:mod:`claude_backend` and are imported lazily so the package imports without
either SDK installed.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

from img2city import config

PROVIDERS = config.LLM_PROVIDERS
_ALIASES = {"sdk": "claude-sdk", "api": "claude-api"}
BACKEND_CHOICES = (*PROVIDERS, *_ALIASES)          # for argparse --backend
_OPENAI_FAMILY = ("codex", "openai")


class BackendDownError(RuntimeError):
    """The model backend is unavailable for a reason retries won't fix within a
    run (usage/credit limit, expired auth).  Distinct from a transient blip so
    callers can abort a long batch instead of churning through it."""


def normalize_provider(name: str | None) -> str | None:
    if name is None:
        return None
    p = _ALIASES.get(name, name)
    if p not in PROVIDERS:
        raise ValueError(f"unknown LLM provider {name!r}; expected one of {BACKEND_CHOICES}")
    return p


def split_model(spec: str | None) -> tuple[str | None, str | None]:
    """``'claude-api:claude-sonnet-5'`` -> ``('claude-api', 'claude-sonnet-5')``;
    a bare name -> ``(None, name)``."""
    if not spec:
        return None, None
    head, sep, tail = spec.partition(":")
    if sep and (head in PROVIDERS or head in _ALIASES):
        return normalize_provider(head), tail
    return None, spec


def resolve(model: str | None = None, backend: str | None = None,
            default_model: str | None = None) -> tuple[str, str]:
    """(provider, model) for a call.  Provider precedence: prefix in ``model``
    > ``backend`` > ``config.LLM_PROVIDER``; model falls back to
    ``default_model`` then ``config.DEFAULT_MODEL``."""
    prefix, name = split_model(model)
    provider = prefix or normalize_provider(backend) or normalize_provider(config.LLM_PROVIDER)
    return provider, name or default_model or config.DEFAULT_MODEL


def is_claude(provider: str) -> bool:
    return provider.startswith("claude")


def vision_call(system: str, user: str, images, model: str | None = None, *,
                backend: str | None = None, max_tokens: int = 2500,
                timeout_s: float | None = None, max_turns: int = 6):
    """One vision-grounded turn.  Returns ``(text, usage, cost_usd)`` with
    ``usage = {'prompt_tokens', 'completion_tokens', ...}``; ``cost_usd`` is
    ``None`` for subscription transports (never a fabricated charge).  Raises
    on an empty answer: callers never fall back to invented geometry."""
    provider, model = resolve(model, backend)
    images = [str(p) for p in images if p]
    timeout_s = timeout_s or config.LLM_TIMEOUT
    started = time.time()
    cost = None
    if provider in _OPENAI_FAMILY:
        from img2city.agent import openai_backend
        text, usage, response_id = openai_backend.vision_call(
            system, user, images, model, transport=provider,
            max_tokens=max_tokens, timeout_s=timeout_s)
    elif provider == "claude-sdk":
        from img2city.agent import claude_backend
        text, usage, cost, response_id = claude_backend.sdk_call(
            system, user, images, model, max_turns=max_turns, timeout_s=timeout_s)
    else:                                          # claude-api
        from img2city.agent import claude_backend
        text, usage, cost, response_id = claude_backend.api_call(
            system, user, images, model, max_tokens=max_tokens, timeout_s=timeout_s)
    if not text.strip():
        raise RuntimeError(f"{provider}:{model} returned no answer; no fallback geometry accepted")
    _receipt(provider, model, response_id, system, user, images, text, usage, cost, started)
    return text, usage, cost


def _receipt(provider, model, response_id, system, user, images, text, usage, cost, started):
    """Immutable per-call record for reproducibility.  Secrets and image bytes
    are never logged; a failure to write never fails the call."""
    try:
        from img2city.agent.tokens import provenance
        logdir = Path(config.MODEL_LOG_DIR)
        logdir.mkdir(parents=True, exist_ok=True)
        rec = provenance(model=model, provider=provider, response_id=response_id)
        rec.update(system=system, user=user, output=text, usage=usage, cost_usd=cost,
                   started_unix=started, elapsed_seconds=round(time.time() - started, 3),
                   reasoning_effort=config.LLM_REASONING if provider in _OPENAI_FAMILY else None,
                   images=[{"path": p, "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest()}
                           for p in images if os.path.isfile(p)])
        (logdir / (uuid.uuid4().hex + ".json")).write_text(json.dumps(rec, indent=2))
    except Exception as exc:                       # noqa: BLE001 -- logging must not break a run
        print(f"[llm] receipt not written: {str(exc)[:80]}")


def healthcheck(model: str | None = None, backend: str | None = None) -> tuple[bool, str]:
    """Cheap reachability probe for the configured provider: (ok, reason).
    A usage limit or expired login comes back as ``(False, <human-readable
    reason>)`` so batch drivers can wait for quota instead of churning."""
    provider, model = resolve(model, backend)
    if provider == "claude-sdk":
        from img2city.agent import claude_backend
        return claude_backend.cli_healthcheck(model)
    try:
        text, _, _ = vision_call("Reply only OK.", "Backend health check.", [], f"{provider}:{model}",
                                 max_tokens=16, timeout_s=120)
        return text.strip().upper().startswith("OK"), text.strip()[:160]
    except Exception as exc:                       # noqa: BLE001 -- the reason is the result
        return False, str(exc)[:300]
