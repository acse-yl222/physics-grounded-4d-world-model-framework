"""Per-iteration token-usage logging for the agent harness.

Records prompt/completion tokens for every LLM call (planner + critic), writes a
CSV table and a cumulative-usage plot. This is the quantitative "how much model
effort did each iteration cost" metric -- it lets progress across iterations be
measured rather than only described.
"""
from __future__ import annotations
import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TokenRecord:
    iteration: int
    role: str            # "planner" or "critic"
    model: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class TokenLogger:
    records: List[TokenRecord] = field(default_factory=list)

    def log(self, iteration: int, role: str, model: str,
            prompt_tokens: int, completion_tokens: int) -> None:
        self.records.append(TokenRecord(
            iteration, role, model, int(prompt_tokens), int(completion_tokens)))

    @property
    def total_prompt(self) -> int:
        return sum(r.prompt_tokens for r in self.records)

    @property
    def total_completion(self) -> int:
        return sum(r.completion_tokens for r in self.records)

    @property
    def total_tokens(self) -> int:
        return self.total_prompt + self.total_completion

    def per_iteration(self) -> Dict[int, int]:
        agg: Dict[int, int] = {}
        for r in self.records:
            agg[r.iteration] = agg.get(r.iteration, 0) + r.total
        return dict(sorted(agg.items()))

    def to_csv(self, path: str) -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["iteration", "role", "model",
                        "prompt_tokens", "completion_tokens", "total"])
            for r in self.records:
                w.writerow([r.iteration, r.role, r.model,
                            r.prompt_tokens, r.completion_tokens, r.total])
        return path

    def plot(self, path: str):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except Exception:
            return None
        per = self.per_iteration()
        if not per:
            return None
        its, toks = list(per.keys()), list(per.values())
        cum, s = [], 0
        for t in toks:
            s += t
            cum.append(s)
        fig, ax1 = plt.subplots(figsize=(7, 4))
        ax1.bar(its, toks, color="#1f77b4", alpha=0.7)
        ax1.set_xlabel("iteration")
        ax1.set_ylabel("tokens / iteration", color="#1f77b4")
        ax2 = ax1.twinx()
        ax2.plot(its, cum, color="#d62728", marker="o", ms=3)
        ax2.set_ylabel("cumulative tokens", color="#d62728")
        ax1.set_title("Token usage per iteration")
        fig.tight_layout()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, dpi=130)
        plt.close(fig)
        return path

    def summary(self) -> str:
        return (f"{len(self.records)} LLM calls over {len(self.per_iteration())} "
                f"iterations | prompt={self.total_prompt} "
                f"completion={self.total_completion} total={self.total_tokens}")


def provenance(**extra) -> dict:
    """Reproducibility stamp for any result file: when, which code revision,
    which Python, plus whatever the caller knows (model ids, Blender version).
    Only facts that can be queried are recorded; unknowns are omitted."""
    import datetime
    import platform
    import subprocess
    import sys
    stamp = {"time_utc": datetime.datetime.now(datetime.timezone.utc)
             .isoformat(timespec="seconds"),
             "python": sys.version.split()[0],
             "platform": platform.platform()}
    try:
        from img2city import config
        root = str(config.PROJECT_ROOT)
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                             capture_output=True, text=True, timeout=5)
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "."],
                               cwd=root, capture_output=True, text=True, timeout=5)
        if rev.returncode == 0:
            stamp["git"] = rev.stdout.strip() + ("+dirty" if dirty.stdout.strip() else "")
    except Exception:
        pass
    stamp.update({k: v for k, v in extra.items() if v is not None})
    return stamp
