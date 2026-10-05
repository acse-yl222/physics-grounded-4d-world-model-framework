"""The planning agent -- the "LLM: reason + plan" box in the reason->act->observe
loop (diagram_agent.png).

Agent.plan(context) -> (Action, token_usage_dict).
  * MockAgent -- offline planner that proposes a small parameter nudge each
                 step (random-restart hill-climb; the harness keeps the edit
                 only if the score improves). Demonstrates the refine loop with
                 no API. Returns simulated token counts so the logging path is
                 exercised.
  * LLMAgent  -- real vision-grounded planner: looks at the reference + the
                 current render and proposes ONE parameter adjustment. Which
                 model / provider answers is configuration (see
                 img2city.agent.llm); the agent returns the real token usage.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from img2city import config
from img2city.agent import llm

PARAMS = ["base_w", "shaft_w", "belfry_w", "dome_r", "spire_h"]


@dataclass
class Action:
    rationale: str = ""
    params_delta: Dict[str, float] = field(default_factory=dict)   # mock executor
    bpy_code: Optional[str] = None                                 # real executor
    tool_call: Optional[Dict[str, Any]] = None


@dataclass
class Context:
    goal: str
    iteration: int
    last_score: Optional[Dict[str, float]]
    last_critique: str
    state: Dict[str, Any]
    last_render: Optional[str] = None      # path to the most recent render (for vision)
    reference: Optional[str] = None        # path to the reference image (for vision)


class Agent:
    def plan(self, ctx: Context):
        raise NotImplementedError


class MockAgent(Agent):
    """Offline planner: nudge one parameter; magnitude shrinks as the score
    approaches 1. The harness accepts only improving edits, so the best score is
    monotonic -- a clean offline demonstration of convergence."""
    PARAMS = PARAMS

    def __init__(self, step=0.18, seed=0):
        self.step = step
        self.rng = random.Random(seed)

    def plan(self, ctx: Context):
        k = self.rng.choice(self.PARAMS)
        s = ctx.last_score["score"] if ctx.last_score else 0.0
        mag = self.step * (1.0 - s) + 0.01
        delta = self.rng.choice([-1, 1]) * mag
        action = Action(
            rationale=f"nudge {k} by {delta:+.3f} | critique: {ctx.last_critique[:48]}",
            params_delta={k: delta})
        usage = {"prompt_tokens": 380 + 14 * ctx.iteration, "completion_tokens": 70}
        return action, usage


def parse_param_delta(text: str, params=PARAMS, clamp: float = 0.25) -> Dict[str, float]:
    """``{"param": ..., "delta": ...}`` from a model reply (first JSON object),
    clamped; an unknown parameter or unparseable reply yields no edit."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        j = json.loads(m.group(0))
        param, delta = j.get("param"), float(j.get("delta", 0.0))
    except (ValueError, TypeError, AttributeError):
        return {}
    return {param: max(-clamp, min(clamp, delta))} if param in params else {}


class LLMAgent(Agent):
    """Vision-grounded ReAct-style planner over the configured model.

    ``model`` may be ``None`` (the configured spec model), a bare name, or
    ``<provider>:<name>``; ``backend`` optionally overrides the provider.
    """
    PARAMS = PARAMS
    SYSTEM = ("You refine a parametric tower silhouette to match a reference "
              "image. Always reply with ONLY the requested JSON.")

    def __init__(self, model: str | None = None, backend: str | None = None):
        self.model = model or config.SPEC_MODEL
        self.backend = backend

    def plan(self, ctx: Context):
        params = ", ".join(f"{k}={v:.2f}" for k, v in ctx.state.items())
        user = (
            f"Goal: {ctx.goal}\n"
            f"Adjustable params (each in [0.05, 1.0]): {', '.join(self.PARAMS)}.\n"
            f"Current params: {params}. Iteration {ctx.iteration}. "
            f"Last score: {ctx.last_score}. Last critique: {ctx.last_critique}\n"
            "Image 1 = REFERENCE target. Image 2 = CURRENT render.\n"
            "Propose ONE small adjustment that makes the current silhouette closer.\n"
            'Reply with ONLY JSON: {"param": "<name>", '
            '"delta": <number in [-0.25, 0.25]>, "why": "<short>"}'
        )
        text, usage, _cost = llm.vision_call(
            self.SYSTEM, user, [ctx.reference, ctx.last_render], self.model,
            backend=self.backend, max_tokens=200)
        return Action(rationale=f"{self.model}: {text[:90]}",
                      params_delta=parse_param_delta(text, self.PARAMS)), usage
