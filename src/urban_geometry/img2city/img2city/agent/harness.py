"""Automated render -> evaluate -> refine harness  (the project's "Agent core").

Realises the reason->act->observe loop from diagram_agent.png / diagram_harness.png:

    context (goal + history + last observation)
      -> Agent.plan        the LLM proposes the next edit          [tokens logged]
      -> Executor.execute   apply it in Blender (MCP) or the mock
      -> render
      -> Evaluator.score    deterministic geometric score
         + VLMCritic.critique  natural-language guidance           [tokens logged]
      -> accept / reject    keep the edit only if the score improves
      -> snapshot           save every accepted iteration
    loop until the score passes a threshold or max-iterations.

Offline demo (no Blender, no API, runs anywhere numpy+PIL+matplotlib exist):

    python -m img2city.agent.harness --demo

Outputs go to runs/<timestamp>/:
    run_log.json, tokens.csv, tokens.png, score_curve.png, snapshots/iter_*.png

Live wiring: swap MockExecutor -> MCPBlenderExecutor and MockAgent -> LLMAgent
(+ LLMCritic) and pass reference_path=../reference.png. See README.md.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass

from img2city import config
from img2city.agent import llm
from img2city.agent.planner import Action, Context, LLMAgent, MockAgent
from img2city.judge.evaluator import LLMCritic, MockCritic, SilhouetteEvaluator
from img2city.agent.tokens import TokenLogger
from img2city.agent.tools import MockExecutor


@dataclass
class HarnessConfig:
    goal: str = "Match the reference silhouette of the Queen's Tower."
    reference_path: str = ""
    out_dir: str = str(config.RUNS_DIR)
    max_iters: int = 25
    stop_score: float = 0.92
    accept_epsilon: float = 0.0
    model: str = config.SPEC_MODEL


class Harness:
    def __init__(self, cfg, agent, executor, evaluator, critic=None):
        self.cfg = cfg
        self.agent = agent
        self.executor = executor
        self.evaluator = evaluator
        self.critic = critic or MockCritic()
        self.tokens = TokenLogger()
        self.log = []

    def _tokens_in_iter(self, it):
        return sum(r.total for r in self.tokens.records if r.iteration == it)

    def _record(self, it, rationale, score, accepted, best_score):
        self.log.append({
            "iteration": it,
            "rationale": rationale,
            "score": score,
            "accepted": accepted,
            "best_score": round(best_score, 4),
            "tokens": self._tokens_in_iter(it),
        })

    def run(self, run_dir):
        snaps = os.path.join(run_dir, "snapshots")
        os.makedirs(snaps, exist_ok=True)

        best_state = self.executor.reset()
        render, best_state = self.executor.execute(Action(), best_state)
        best = self.evaluator.score(render)
        cur_render = render
        critique, _ = self.critic.critique(render, self.evaluator.reference_path, best, 0)
        shutil.copy(render, os.path.join(snaps, "iter_000.png"))
        self._record(0, "baseline", best, True, best["score"])
        print(f"  iter 00  score={best['score']:.3f}  (baseline)")

        for it in range(1, self.cfg.max_iters + 1):
            ctx = Context(self.cfg.goal, it, best, critique, best_state,
                          last_render=cur_render, reference=self.evaluator.reference_path)
            action, usage = self.agent.plan(ctx)
            self.tokens.log(it, "planner", self.cfg.model,
                            usage["prompt_tokens"], usage["completion_tokens"])

            render, new_state = self.executor.execute(action, best_state)
            score = self.evaluator.score(render)

            critique, cusage = self.critic.critique(
                render, self.evaluator.reference_path, score, it)
            self.tokens.log(it, "critic", self.cfg.model,
                            cusage["prompt_tokens"], cusage["completion_tokens"])

            accepted = score["score"] > best["score"] + self.cfg.accept_epsilon
            if accepted:
                best, best_state = score, new_state
                cur_render = render
                shutil.copy(render, os.path.join(snaps, f"iter_{it:03d}.png"))

            self._record(it, action.rationale, score, accepted, best["score"])
            flag = "ACCEPT" if accepted else "  reject"
            print(f"  iter {it:02d}  score={score['score']:.3f}  best={best['score']:.3f}  {flag}")

            if best["score"] >= self.cfg.stop_score:
                print(f"  -> stop: reached target score {self.cfg.stop_score}")
                break

        return self._finalize(run_dir, best)

    def _finalize(self, run_dir, best):
        self.tokens.to_csv(os.path.join(run_dir, "tokens.csv"))
        self.tokens.plot(os.path.join(run_dir, "tokens.png"))
        self._score_curve(os.path.join(run_dir, "score_curve.png"))
        with open(os.path.join(run_dir, "run_log.json"), "w") as fh:
            json.dump({"config": asdict(self.cfg),
                       "final_best": best,
                       "iterations_run": self.log[-1]["iteration"],
                       "tokens_summary": self.tokens.summary(),
                       "iterations": self.log}, fh, indent=2)
        print("\n" + self.tokens.summary())
        print(f"final best score = {best['score']:.3f} "
              f"after {self.log[-1]['iteration']} iterations")
        print(f"outputs -> {run_dir}")
        return run_dir, best

    def _score_curve(self, path):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except Exception:
            return None
        its = [r["iteration"] for r in self.log]
        sc = [r["score"]["score"] for r in self.log]
        bs = [r["best_score"] for r in self.log]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(its, sc, color="#7f7f7f", marker="o", ms=3, lw=1, label="proposed score")
        ax.plot(its, bs, color="#2ca02c", marker="o", ms=3, lw=2, label="best-so-far")
        ax.set_xlabel("iteration")
        ax.set_ylabel("silhouette match score")
        ax.set_title("Render-evaluate-refine convergence")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(path, dpi=130)
        plt.close(fig)
        return path


def _run(args, live):
    run_dir = os.path.join(args.out, time.strftime("%Y%m%d-%H%M%S"))
    work = os.path.join(run_dir, "work")
    os.makedirs(work, exist_ok=True)
    executor = MockExecutor(out_dir=work)            # offline environment (no Blender)
    ref = executor.make_reference()
    evaluator = SilhouetteEvaluator(ref, bg="white")
    cfg = HarnessConfig(reference_path=ref, out_dir=run_dir, model=args.model,
                        max_iters=args.max_iters, stop_score=args.stop_score)
    if live:
        provider, model = llm.resolve(args.model, args.backend)
        print(f"[live] {provider}:{model} + mock env -> {run_dir}")
        print("       provider/model come from .env (IMG2CITY_LLM_PROVIDER, IMG2CITY_*_MODEL); "
              "tokens.csv records usage\n")
        agent = LLMAgent(model=args.model, backend=args.backend)
        critic = LLMCritic(model=args.model, backend=args.backend)
    else:
        print(f"[demo] offline mock loop -> {run_dir}\n")
        agent, critic = MockAgent(seed=args.seed), MockCritic()
    Harness(cfg, agent, executor, evaluator, critic).run(run_dir)


def main():
    ap = argparse.ArgumentParser(description="Agent core: render-evaluate-refine harness")
    ap.add_argument("--demo", action="store_true", help="offline mock loop (no API / Blender)")
    ap.add_argument("--live", action="store_true",
                    help="real vision planner+critic (configured model), mock environment")
    ap.add_argument("--model", default=config.SPEC_MODEL,
                    help="model for --live; '<provider>:<model>' pins the provider")
    ap.add_argument("--backend", choices=llm.BACKEND_CHOICES, default=None,
                    help="override IMG2CITY_LLM_PROVIDER for this run")
    ap.add_argument("--out", default=str(config.RUNS_DIR))
    ap.add_argument("--max-iters", type=int, default=25)
    ap.add_argument("--stop-score", type=float, default=0.92)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    if args.live:
        _run(args, live=True)
    elif args.demo:
        _run(args, live=False)
    else:
        print("Choose a mode:\n"
              "  python -m img2city.agent.harness --demo                                # offline, no API/Blender\n"
              "  python -m img2city.agent.harness --live --max-iters 6                  # configured model (.env)\n"
              "  python -m img2city.agent.harness --live --backend claude-api --max-iters 6   # override the provider")


if __name__ == "__main__":
    main()
