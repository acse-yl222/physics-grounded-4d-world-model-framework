"""Run FieldFleet/NVMF without a viewer or external IRP checkout."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import platform
from pathlib import Path
import tempfile
import uuid

from common.storage import Storage
from .adapter import schedule


def _publish_json(path: Path, value: dict) -> None:
    """Publish a complete result without overwriting an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".nvmf-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description="FieldFleet / NVMF paired-request scheduler")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--backend", choices=("mean_field", "portable_fail_closed"), default="mean_field")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-rounds", type=int, default=32)
    parser.add_argument("--threads", type=int, default=1, help="PyTorch CPU threads (default: 1)")
    parser.add_argument("--root", type=Path, help="framework workspace, needed for a standalone wheel")
    parser.add_argument("--output", type=Path, help="new JSON file; existing files are never overwritten")
    parser.add_argument("--context", type=Path, help="explicit scene coordinates and seconds per slot for protocol export")
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads must be positive")
    if args.output and args.output.exists():
        parser.error(f"output already exists: {args.output}")
    scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    context = json.loads(args.context.read_text(encoding="utf-8")) if args.context else None
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8]
    storage = Storage.load(args.root)
    scene = context["scene_id"] if context else "nvmf_demo"
    trial = storage.scratch(scene, "uav_scheduling", run_id)
    trial.mkdir(parents=True, exist_ok=False)
    print(f"Run workspace: {trial}", flush=True)
    if args.backend == "mean_field":
        try:
            import torch
        except ImportError:
            parser.error("mean_field requires: pip install -e '.[scheduler]'")
        torch.set_num_threads(args.threads)
    result = schedule(scenario, run_seed=args.seed, backend=args.backend,
                      device=args.device, max_rounds=args.max_rounds,
                      work_directory=trial / "controller")
    output = args.output or trial / "result.json"
    _publish_json(output, result)
    print(f"Result: {output.resolve()}")
    if context:
        from .export import export_run
        import numpy
        versions = {"python": platform.python_version(), "numpy": numpy.__version__}
        if args.backend == "mean_field":
            versions["torch"] = torch.__version__
        manifest = export_run(trial / "bundle" / run_id, scenario, result, context=context,
                              parameters={"run_seed": args.seed, "backend": args.backend,
                                          "device": args.device, "max_rounds": args.max_rounds,
                                          "threads": args.threads, "runtime_versions": versions})
        print(f"Protocol manifest: {manifest}")
    print(json.dumps(result["validation"], sort_keys=True))


if __name__ == "__main__":
    main()
