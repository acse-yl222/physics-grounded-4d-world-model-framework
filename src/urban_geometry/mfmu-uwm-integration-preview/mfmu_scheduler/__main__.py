"""Command-line entry point: ``python -m mfmu_scheduler SCENARIO.json``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .api import schedule


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MFMU UAV scheduler integration snapshot")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--output", "-o", type=Path, default=Path("schedule-result.json"))
    parser.add_argument("--backend", choices=("portable_fail_closed", "mean_field"), default="portable_fail_closed")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    scenario = json.loads(args.scenario.read_text())
    result = schedule(scenario, backend=args.backend, device=args.device, run_seed=args.seed)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.output}: accepted={result['validation']['accepted']} rounds={result['diagnostics']['rounds']}")


if __name__ == "__main__":
    main()

