"""Source files that stages digest or import must not follow the scene workspace."""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
RUNNERS = ("src/common/pipeline", "src/urban_flow/physics")
FROZEN = (
    "src/urban_flow/physics/environment-integration/",
    "src/urban_flow/physics/wind_pollution_code/",
    "src/urban_flow/physics/wind_temperature_teacher/",
)
# A code root joined onto the workspace, also when the join is split across lines.
WORKSPACE_CODE = re.compile(
    r"\b(?:ROOT|repo_root\(\)|workspace_root\(\))\s*/\s*f?[\"'](?:src|pipelines)\b"
)


class CodePathTests(unittest.TestCase):
    maxDiff = None

    def test_surface_solver_digest_resolves_outside_an_empty_workspace(self):
        # Mirror `p4d run`: P4D_ROOT and the working directory name the workspace.
        script = """
import importlib.util, json, sys, types
sys.path.insert(0, sys.argv[1])
if importlib.util.find_spec("torch") is None:
    # Locating the solver source needs no torch; the base environment omits it.
    sys.modules["torch"] = types.ModuleType("torch")
from common.pipeline.scene_surface_physics import solver_source
print(json.dumps({stage: str(solver_source(stage)) for stage in ("solar", "flood")}))
"""
        with tempfile.TemporaryDirectory() as workspace:
            result = subprocess.run(
                [sys.executable, "-I", "-c", script, str(SRC)],
                cwd=workspace,
                env=dict(os.environ, P4D_ROOT=workspace, UWM_ROOT=workspace),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for stage, source in json.loads(result.stdout).items():
                with self.subTest(stage=stage):
                    source = Path(source)
                    self.assertEqual(source, SRC / f"urban_flow/physics/{stage}/model.py")
                    self.assertTrue(source.is_file())

    def test_runners_do_not_resolve_code_under_the_workspace(self):
        offenders = []
        for base in RUNNERS:
            for path in sorted((ROOT / base).rglob("*.py")):
                relative = path.relative_to(ROOT).as_posix()
                if relative.startswith(FROZEN) or "/vendor/" in relative:
                    continue
                text = path.read_text()
                for match in WORKSPACE_CODE.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    offenders.append(f"{relative}:{line}")
        self.assertEqual(offenders, [], "Resolve source files with common.locations.code_path")


if __name__ == "__main__":
    unittest.main()
