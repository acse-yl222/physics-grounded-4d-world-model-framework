"""The Blender expansion scripts must share one run directory and relocatable snapshot keys."""

import ast
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common import layout
from common.storage import Storage

AGENT = ROOT / "src/urban_geometry/agent"
SCRIPTS = ("build_expansion.py", "verify_export.py", "render_expansion.py")


class ExpansionPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # The workspace is not the code checkout, as with a wheel install.
        self.workspace = Path(self.tmp.name) / "workspace"
        self.workspace.mkdir()
        self.env = patch.dict(os.environ, {"P4D_ROOT": str(self.workspace)}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def configure_external(self):
        data = Path(self.tmp.name) / "data"
        cache = Path(self.tmp.name) / "scratch"
        (self.workspace / "storage.local.json").write_text(
            json.dumps({"data_root": str(data), "cache_root": str(cache)})
        )
        return data, cache

    def assert_snapshot_keys(self, data_root):
        authoring = data_root / "project/south_ken/geometry/authoring"
        self.assertEqual(layout.authoring_path(), authoring)
        self.assertEqual(
            layout.snapshot_key(layout.agent_src() / "build_expansion.py"),
            "src/urban_geometry/agent/build_expansion.py",
        )
        self.assertEqual(
            layout.snapshot_key(layout.agent_src() / "buildings/urban.py"),
            "src/urban_geometry/agent/buildings/urban.py",
        )
        self.assertEqual(
            layout.snapshot_key(layout.authoring_path("src/modules.json")),
            "src/urban_geometry/agent/modules.json",
        )
        self.assertEqual(
            layout.snapshot_key(layout.authoring_path("references/sources.json")),
            "project/south_ken/geometry/authoring/references/sources.json",
        )
        with self.assertRaises(ValueError):
            layout.snapshot_key(data_root / "project/south_ken/input/grid.npy")

    def test_snapshot_keys_with_explicit_workspace(self):
        self.assert_snapshot_keys(self.workspace)

    def test_snapshot_keys_with_external_data_root(self):
        data, _ = self.configure_external()
        self.assert_snapshot_keys(data)

    def test_run_dir_is_the_geometry_scratch_dir(self):
        for external in (False, True):
            if external:
                _, cache = self.configure_external()
            else:
                cache = self.workspace / "cache"
            run = layout.expansion_run_dir("review-017")
            self.assertEqual(run, Storage.load().scratch("south_ken", "geometry", "review-017"))
            self.assertEqual(run, cache / "south_ken/geometry/review-017")
            self.assertFalse(run.exists())
        for invalid in ("", "../review-005", "review/005", "-review", "review 005", None):
            with self.subTest(run=invalid), self.assertRaises(ValueError):
                layout.expansion_run_dir(invalid)

    def test_build_verify_and_render_share_the_run_dir(self):
        for name in SCRIPTS:
            with self.subTest(script=name):
                tree = ast.parse((AGENT / name).read_text())
                calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
                shared = [c for c in calls if getattr(c.func, "id", None) == "expansion_run_dir"]
                self.assertEqual(len(shared), 1, "run directory must come from the shared helper")
                self.assertEqual(ast.unparse(shared[0].args[0]), "args.run")
                self.assertFalse(
                    [c for c in calls if getattr(c.func, "attr", None) == "scratch"],
                    "run directory must not be derived separately",
                )
                self.assertNotIn(
                    "exports",
                    {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)},
                    "runs are not read from or written to the retained authoring exports",
                )

    def test_build_names_snapshot_hashes_and_copies_alike(self):
        tree = ast.parse((AGENT / "build_expansion.py").read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertFalse(
            [c for c in calls if getattr(c.func, "attr", None) == "relative_to"],
            "snapshot paths must not depend on the workspace or authoring location",
        )
        snapshot = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "snapshot"
        )
        copy = next(
            n
            for n in tree.body
            if isinstance(n, ast.For) and ast.unparse(n.target) == "source_file"
        )
        for node in (snapshot, copy):
            self.assertIn(
                "snapshot_key",
                {getattr(n.func, "id", None) for n in ast.walk(node) if isinstance(n, ast.Call)},
            )


if __name__ == "__main__":
    unittest.main()
