"""Formatting must never rewrite tracked assets or historical evidence."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("repository_format", ROOT / "tools/format.py")
formatter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(formatter)


class FormatScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.write(".prettierignore", (ROOT / ".prettierignore").read_text())
        self.write(".gitignore", (ROOT / ".gitignore").read_text())

    def write(self, name, content="fixture\n"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return name

    def test_owned_legacy_code_configs_and_new_files_are_included(self):
        names = [
            "src/common/example.py",
            "src/visualization/legacy/viewer/example.js",
            "project/south_ken/configs/example.json",
            "project/white_city/views/example.json",
            "project/index.json",
            "examples/contract-v1/manifest.json",
            "notebook.ipynb",
            "tools/new file.py",
        ]
        for name in names:
            self.write(name)
        subprocess.run(["git", "add", "src", "project"], cwd=self.root, check=True)
        selected = formatter.selected_files(root=self.root)
        self.assertTrue(set(names) <= set(selected))

    def test_tracked_data_vendor_and_records_stay_excluded(self):
        names = [
            "project/south_ken/input/routes.json",
            "project/white_city/geometry/mesh.json",
            "project/south_ken/runs/run/manifest.json",
            "src/visualization/vendor/three/build/three.module.js",
            "src/urban_flow/physics/example/vendor/scaled/example.py",
            "src/visualization/published-pages/output/example.html",
            "src/visualization/legacy/agents/demo_rev02/serve_demo.py",
            "docs/framework/layout-migration.json",
            "docs/history/README.md",
            "examples/contract-v1/data/trajectories.json",
            "examples/contract-v1.1/frames.json",
            "src/urban_flow/physics/example/SOURCE_INFO.json",
            "src/visualization/legacy/assets/actors/birds/pigeon_geometry_QA.json",
        ]
        for name in names:
            self.write(name)
        subprocess.run(["git", "add", "--force", "."], cwd=self.root, check=True)
        self.assertFalse(set(names) & set(formatter.selected_files(root=self.root)))
        self.assertEqual(formatter.selected_files(names, root=self.root), [])

    def test_local_files_and_symlinks_are_not_rewritten(self):
        for name in ("cache/generated.py", ".history/recovery.py", "storage.local.json"):
            self.write(name)
        (self.root / "linked.py").symlink_to(self.root / "cache/generated.py")
        selected = formatter.selected_files(root=self.root)
        self.assertFalse(
            any(name.endswith(".py") or name == "storage.local.json" for name in selected)
        )

    def test_explicit_hook_filenames_use_the_shared_boundary(self):
        owned = self.write("tools/new file.py")
        other = self.write("tools/other.py")
        data = self.write("project/south_ken/input/routes.json")
        self.assertEqual(formatter.selected_files([owned, data], root=self.root), [owned])
        self.assertNotIn(other, formatter.selected_files([owned], root=self.root))


if __name__ == "__main__":
    unittest.main()
