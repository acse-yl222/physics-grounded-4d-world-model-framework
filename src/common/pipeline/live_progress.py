"""Refresh progress figures after completed wind steps; no GPU required."""

# Compatibility for direct source-script execution.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.locations import code_path
from common.layout import repo_root
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from common.pipeline.paths import ROOT, project_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="configs/white_city/scaled_latent.json")
    args = ap.parse_args()
    cfg = json.loads(project_path(args.config).read_text())
    run = project_path(cfg["output"])
    last = -1
    while True:
        metrics = run / "wind/metrics.json"
        rows = json.loads(metrics.read_text())["steps"] if metrics.exists() else []
        step = rows[-1]["step"] if rows else 0
        if step and step != last:
            subprocess.run(
                [
                    sys.executable,
                    str(code_path("src/common/pipeline/plot_scene.py")),
                    "--config",
                    args.config,
                    "--step",
                    str(step),
                ],
                cwd=ROOT,
                check=True,
            )
            record = {
                "completed_steps": step,
                "total_steps": cfg["wind_steps"],
                "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "free_gib": shutil.disk_usage(run).free / 1024**3,
                "preview": "figures/wind_latest.png",
                "convergence": "figures/wind_convergence.png",
            }
            tmp = run / "visual_progress.json.partial"
            tmp.write_text(json.dumps(record, indent=2))
            tmp.replace(run / "visual_progress.json")
            print(json.dumps(record), flush=True)
            last = step
        if step >= cfg["wind_steps"]:
            break
        pid = json.loads((run / "process.json").read_text())["pid"]
        try:
            os.kill(pid, 0)
            status = Path(f"/proc/{pid}/status")
            if status.exists() and any(
                line.startswith("State:") and "Z" in line
                for line in status.read_text().splitlines()
            ):
                break
        except ProcessLookupError:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
