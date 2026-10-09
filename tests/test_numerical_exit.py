"""Numerical failures must reach CI while retaining the complete JSON report."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CHECKERS = {
    "flood": (
        "test_flood_swe.py",
        "report",
        (
            "lake_at_rest",
            "rain_mass_balance",
            "stoker_dam_break",
            "manning_uniform_flow",
            "urban_slope",
        ),
    ),
    "solar": (
        "test_solar_np.py",
        "rep",
        ("test_sun_position", "test_brute_force", "test_pole", "test_canyon_svf"),
    ),
}


@unittest.skipUnless(importlib.util.find_spec("torch"), "Requires the flow environment")
class NumericalExitTests(unittest.TestCase):
    def test_pass_and_failure_status_preserve_all_case_reports(self):
        import numpy as np

        for label, (filename, report_name, cases) in CHECKERS.items():
            spec = importlib.util.spec_from_file_location(
                label + "_checker", ROOT / "src/urban_flow/physics" / filename
            )
            module = importlib.util.module_from_spec(spec)
            with patch.object(sys, "path", list(sys.path)):
                spec.loader.exec_module(module)
            report = getattr(module, report_name)
            # Reuse the same runner: a previous failure must not contaminate a later pass.
            for failed in (True, False):
                report["previous_run"] = {"pass": False}
                with (
                    self.subTest(checker=label, failed=failed),
                    tempfile.TemporaryDirectory() as directory,
                    contextlib.ExitStack() as stack,
                ):
                    for index, name in enumerate(cases):

                        def check(name=name, index=index):
                            report[name] = {"pass": np.bool_(not (failed and index == 0))}

                        check.__name__ = name
                        stack.enter_context(patch.object(module, name, check))
                    output = Path(directory) / "nested/report.json"
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout):
                        status = module.main(["--out", str(output)])
                    document = json.loads(stdout.getvalue())
                    self.assertEqual(status, 1 if failed else 0)
                    self.assertEqual(document["all_pass"], not failed)
                    self.assertNotIn("previous_run", document)
                    self.assertEqual(json.loads(output.read_text()), document)
                    self.assertTrue(all(name in document for name in cases))
                    self.assertTrue(all("seconds" in document[name] for name in cases))

    def test_solar_executable_exit_status_with_a_failed_reference_check(self):
        script = ROOT / "src/urban_flow/physics/test_solar_np.py"
        launcher = """
import pathlib, runpy, sys, torch
torch.set_num_threads(2)
torch.cuda.is_available = lambda: False
script, output, fail = sys.argv[1:]
sys.path.insert(0, str(pathlib.Path(script).parent))
if fail == 'yes':
    import solar_np
    solar_np.sun_position = lambda *args: (0., 0.)
sys.argv = [script, '--out', output]
runpy.run_path(script, run_name='__main__')
"""
        for fail in ("yes", "no"):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "report.json"
                result = subprocess.run(
                    [sys.executable, "-I", "-c", launcher, str(script), str(output), fail],
                    cwd=directory,
                    env=dict(os.environ),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 1 if fail == "yes" else 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["all_pass"], fail == "no")
                self.assertEqual(report["sun_position"]["pass"], fail == "no")
                self.assertEqual(json.loads(output.read_text()), report)
