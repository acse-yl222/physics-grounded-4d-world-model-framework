"""Protocol export checks against a real tiny uniform-control scheduler run.

The fixture exercises the controller, not numerical mean-field effectiveness.
"""
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from common.contract import validate
from common.runs import promote
from common.storage import Storage
from uav_scheduling.adapter import schedule
from uav_scheduling.export import export_run


class NvmfExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.runtime.cleanup)
        cls.scenario = json.loads((ROOT / "examples/nvmf/minimal_scenario.json").read_text())
        cls.context = json.loads((ROOT / "examples/nvmf/minimal_context.json").read_text())
        cls.result = schedule(cls.scenario, backend="portable_fail_closed", run_seed=0,
                              work_directory=Path(cls.runtime.name) / "solver")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / "trial_01"

    def export(self, *, result=None, context=None, target=None):
        return export_run(target or self.target, self.scenario, result or self.result,
                          context=context if context is not None else self.context,
                          parameters={"backend": "portable_fail_closed", "run_seed": 0})

    def test_actual_delivery_events_and_relative_self_contained_assets(self):
        manifest_path = self.export()
        self.assertEqual(validate(manifest_path), 1)
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["status"], "complete")
        layer = manifest["layers"][0]
        self.assertEqual((layer["kind"], layer["sampling"]), ("time_series", "step"))
        slots = sorted({0, *(r["dropoff_service_slot"] for r in self.result["assignments"])})
        self.assertEqual(manifest["time"]["samples"], [s * self.context["slot_seconds"] for s in slots])
        curve = json.loads((self.target / layer["asset"]).read_text())
        expected = [[sum(r["dropoff_service_slot"] <= s for r in self.result["assignments"])] for s in slots]
        self.assertEqual(curve["values"], expected)
        self.assertEqual(curve["values"][-1], [self.result["validation"]["accepted"]])
        for asset in manifest["artifacts"]:
            relative = PurePosixPath(asset["asset"])
            self.assertFalse(relative.is_absolute())
            self.assertNotIn("..", relative.parts)
            contents = (self.target / asset["asset"]).read_bytes()
            self.assertEqual(hashlib.sha256(contents).hexdigest(), asset["sha256"])
        saved = json.loads((self.target / "data/result.json").read_text())
        self.assertNotIn("work_directory", saved["diagnostics"])
        self.assertIn("work_directory", self.result["diagnostics"])
        self.assertEqual(json.loads((self.target / "data/scenario.json").read_text()), self.scenario)
        self.assertFalse(manifest["spatial"]["georeferenced"])

    def test_source_snapshot_recovers_exact_revision_independent_of_cwd(self):
        first = json.loads(self.export().read_text())
        archive_path = self.target / "provenance/source_snapshot.zip"
        digest = hashlib.sha256()
        with ZipFile(archive_path) as archive:
            names = sorted(archive.namelist())
            self.assertIn("uav_scheduling/SOURCE_MANIFEST.json", names)
            self.assertIn("uav_scheduling/NOTICE.md", names)
            self.assertIn("uav_scheduling/export.py", names)
            self.assertTrue(any("/_vendor/" in name for name in names))
            for name in names:
                self.assertFalse(PurePosixPath(name).is_absolute())
                self.assertNotIn("..", PurePosixPath(name).parts)
                digest.update(name.encode() + b"\0" + archive.read(name) + b"\0")
        self.assertEqual(first["provenance"]["code_revision"], "sha256:" + digest.hexdigest())
        before = Path.cwd()
        try:
            os.chdir(self.tmp.name)
            second = json.loads(self.export(target=Path(self.tmp.name) / "trial_02").read_text())
        finally:
            os.chdir(before)
        self.assertEqual(first["provenance"]["code_revision"], second["provenance"]["code_revision"])

    def test_existing_directory_is_never_overwritten(self):
        self.target.mkdir()
        sentinel = self.target / "keep.txt"
        sentinel.write_text("manual work")
        with self.assertRaises(FileExistsError):
            self.export()
        self.assertEqual(sentinel.read_text(), "manual work")

    def test_legacy_scene_aliases_are_canonicalised_without_changing_input(self):
        for alias in ("core008", "south_kensington"):
            with self.subTest(alias=alias):
                context = copy.deepcopy(self.context)
                context["scene_id"] = alias
                target = Path(self.tmp.name) / alias
                manifest_path = self.export(context=context, target=target)
                self.assertEqual(validate(manifest_path), 1)
                manifest = json.loads(manifest_path.read_text())
                self.assertEqual(manifest["scene_id"], "south_ken")
                self.assertEqual(context["scene_id"], alias)
                archived_context = json.loads((target / "provenance/context.json").read_text())
                self.assertEqual(archived_context, context)
                scope = json.loads((target / "provenance/export_scope.json").read_text())
                self.assertEqual(scope["input_scene_id"], alias)
                self.assertEqual(scope["canonical_scene_id"], "south_ken")

    def test_two_cli_runs_for_same_scene_can_both_be_retained(self):
        # Retaining a single run needs no project/view registration. This follows
        # the same promote() path as `p4d retain`, using a fresh isolated workspace.
        workspace = Path(self.tmp.name)
        storage = Storage.load(workspace)
        manifests = []
        for _ in range(2):
            execution = subprocess.run(
                [sys.executable, "-m", "uav_scheduling",
                 str(ROOT / "examples/nvmf/minimal_scenario.json"),
                 "--backend", "portable_fail_closed", "--root", str(workspace),
                 "--context", str(ROOT / "examples/nvmf/minimal_context.json")],
                cwd=workspace,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                capture_output=True, text=True, timeout=30, check=True,
            )
            manifest_lines = [line.removeprefix("Protocol manifest: ")
                              for line in execution.stdout.splitlines()
                              if line.startswith("Protocol manifest: ")]
            self.assertEqual(len(manifest_lines), 1, execution.stdout)
            path = Path(manifest_lines[0])
            manifest = json.loads(path.read_text())
            self.assertEqual(manifest["scene_id"], "nvmf_demo")
            self.assertEqual(manifest["run_id"], path.parent.name)
            self.assertEqual(path.parent.parent.name, "bundle")
            self.assertEqual(validate(path), 1)
            retained = promote(storage, path.parent)
            self.assertEqual(retained, storage.run("nvmf_demo", manifest["run_id"]))
            self.assertEqual(validate(retained / "manifest.json"), 1)
            self.assertEqual((retained / "manifest.json").read_bytes(), path.read_bytes())
            manifests.append((manifest, path, retained))
        self.assertNotEqual(manifests[0][0]["run_id"], manifests[1][0]["run_id"])
        for _, source, retained in manifests:
            self.assertTrue(source.is_file())
            self.assertTrue((retained / "manifest.json").is_file())
        self.assertEqual(len(list(storage.assets("nvmf_demo", "runs").glob("*/manifest.json"))), 2)

    def test_missing_or_invalid_time_and_spatial_declarations_are_rejected(self):
        for seconds in (None, 0, -1, float("nan"), float("inf"), True, "60"):
            with self.subTest(seconds=seconds):
                context = copy.deepcopy(self.context)
                context["slot_seconds"] = seconds
                with self.assertRaises(ValueError):
                    self.export(context=context)
                self.assertFalse(self.target.exists())
        for missing in ("scene_id", "spatial", "slot_seconds"):
            context = copy.deepcopy(self.context)
            del context[missing]
            with self.assertRaises(ValueError):
                self.export(context=context)
        context = copy.deepcopy(self.context)
        context["spatial"]["units"] = "km"
        with self.assertRaises(ValueError):
            self.export(context=context)

    def test_failed_or_missing_certificates_are_rejected(self):
        for key in ("committable", "global_closure", "independent_replay_pass", "dry_run_equals_commit"):
            with self.subTest(key=key):
                result = copy.deepcopy(self.result)
                result["validation"][key] = False
                with self.assertRaises(ValueError):
                    self.export(result=result)
        result = copy.deepcopy(self.result)
        result["validation"]["hard_violation_count"] = 1
        with self.assertRaises(ValueError):
            self.export(result=result)
        self.assertFalse(self.target.exists())

    def test_inconsistent_counts_inputs_and_service_events_are_rejected(self):
        for mutation in ("count", "input", "time", "journey", "duplicate", "missing_collection"):
            with self.subTest(mutation=mutation):
                result = copy.deepcopy(self.result)
                if mutation == "count":
                    result["validation"]["accepted"] += 1
                elif mutation == "input":
                    result["diagnostics"]["input_sha256"] = "0" * 64
                elif mutation == "time":
                    result["assignments"][0]["dropoff_service_slot"] = -1
                elif mutation == "journey":
                    result["journeys"][0]["dropoff_service_slot"] += 1
                elif mutation == "duplicate":
                    result["assignments"].append(result["assignments"][0])
                else:
                    result["journeys"][0]["segments"] = [s for s in result["journeys"][0]["segments"] if s["kind"] != "C_SERVICE"]
                with self.assertRaises(ValueError):
                    self.export(result=result)
                self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
