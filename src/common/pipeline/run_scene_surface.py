"""Run confirmed solar and flood experiments sequentially and record status."""

# Compatibility for direct source-script execution.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.locations import code_path
from common.layout import repo_root
import json
from pathlib import Path
import subprocess
import sys

from common.pipeline.paths import ROOT
from common.pipeline.scene_scaled_latent import save_json


def main():
    out = ROOT / "output/white_city/physics"
    completed = []
    for stage in ("solar", "flood"):
        status = out / f"{stage}_experimental/status.json"
        if not status.exists() or not json.loads(status.read_text()).get("complete"):
            save_json(
                out / "surface_workflow_status.json",
                {"complete": False, "stage": stage, "completed": completed},
            )
            with (out / f"{stage}_experimental.log").open("a") as log:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-u",
                        str(code_path("src/common/pipeline/scene_surface_physics.py")),
                        "--stage",
                        stage,
                    ],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            if result.returncode:
                save_json(
                    out / "surface_workflow_status.json",
                    {
                        "complete": False,
                        "failed_stage": stage,
                        "returncode": result.returncode,
                        "completed": completed,
                    },
                )
                raise SystemExit(result.returncode)
        completed.append(stage)
    save_json(
        out / "surface_workflow_status.json",
        {"complete": True, "completed": completed, "experimental_assumptions": True},
    )


if __name__ == "__main__":
    main()
