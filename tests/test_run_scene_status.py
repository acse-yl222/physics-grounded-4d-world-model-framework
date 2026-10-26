"""A scene run that skips a requested stage or retains nothing must not exit 0."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common.pipeline import run_scene

spec = importlib.util.spec_from_file_location("e2e_fixture", ROOT / "tools/e2e_fixture.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class RunSceneStatusTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.workspace = fixture.create_workspace(base)
        self.config = json.loads((self.workspace / "pipeline.json").read_text())
        # A reused trial whose geometry stage already finished, so no stage subprocess runs.
        self.trial = base / "scratch/south_ken/pipeline/trial"
        geometry = self.trial / "geometry/voxel_1m"
        geometry.mkdir(parents=True)
        source = base / "data/project/south_ken/input/fixture.glb"
        (geometry / "metadata.json").write_text(
            json.dumps(
                {
                    "spacing_xyz_m": [1, 1, 1],
                    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "shape_zyx": [4, 8, 8],
                }
            )
        )

    def run_scene(self, stages, *options):
        self.config["stages"] = stages
        (self.workspace / "pipeline.json").write_text(json.dumps(self.config))
        argv = ["run_scene", "pipeline.json", "--run-id", "trial", *options]
        output = io.StringIO()
        with (
            mock.patch.dict(os.environ, {"P4D_ROOT": str(self.workspace)}),
            mock.patch.object(sys, "argv", argv),
            mock.patch("common.provenance.snapshot_sources", return_value="test-revision"),
            mock.patch.object(run_scene.subprocess, "run", side_effect=AssertionError),
            contextlib.redirect_stdout(output),
        ):
            try:
                run_scene.main()
                code = 0
            except SystemExit as exc:
                code = exc.code
        status = json.loads((self.trial / "pipeline_status.json").read_text())
        return code, output.getvalue(), status

    def test_skipped_requested_stage_exits_nonzero_with_reason(self):
        # The fixture leaves georeference.confirmed false, so solar cannot run.
        code, output, status = self.run_scene(["geometry", "solar"])
        self.assertNotIn(code, (0, 1, 2), "distinct from success, failure and usage errors")
        self.assertEqual(code, run_scene.EXIT_INCOMPLETE)
        self.assertFalse(status["complete"])
        self.assertEqual(status["stages"]["solar"]["status"], "skipped")
        self.assertIn("INCOMPLETE", output)
        self.assertIn("solar: georeference.confirmed must be true", output)

    def test_all_requested_stages_done_exits_zero(self):
        # solar is still blocked, but it was not requested.
        code, output, status = self.run_scene(["geometry"])
        self.assertEqual(code, 0)
        self.assertTrue(status["complete"])
        self.assertIn("requested stages finished", output)
        self.assertNotIn("INCOMPLETE", output)

    def test_retain_of_incomplete_run_exits_nonzero(self):
        code, output, status = self.run_scene(["geometry", "solar"], "--retain")
        self.assertNotEqual(code, 0)
        self.assertEqual(code, run_scene.EXIT_INCOMPLETE)
        self.assertFalse(status["complete"])
        self.assertIn("nothing was retained", output)
        self.assertFalse((self.trial / "protocol").exists())

    def test_retain_without_visualize_stage_exits_nonzero(self):
        code, output, status = self.run_scene(["geometry"], "--retain")
        self.assertNotEqual(code, 0)
        self.assertEqual(code, run_scene.EXIT_INCOMPLETE)
        self.assertTrue(status["complete"])
        self.assertIn("nothing was retained", output)
        self.assertIn("visualize", output)


if __name__ == "__main__":
    unittest.main()
