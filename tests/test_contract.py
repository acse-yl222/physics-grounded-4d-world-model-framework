"""Behavioral regressions for the public interchange boundary."""

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_contract", ROOT / "tools/check_contract.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name) / "run"
        shutil.copytree(ROOT / "examples/contract-v1", self.run)
        self.path = self.run / "manifest.json"
        self.manifest = json.loads(self.path.read_text())

    def check(self):
        self.path.write_text(json.dumps(self.manifest))
        return checker.validate(self.path)

    def reject(self, mutate):
        mutate()
        with self.assertRaises(Exception):
            self.check()

    def test_valid_all_five_kinds(self):
        self.assertEqual(self.check(), 5)

    def test_valid_static_run(self):
        self.manifest["layers"] = self.manifest["layers"][:1]
        self.manifest["time"]["samples"] = []
        self.assertEqual(self.check(), 1)

    def test_unknown_version(self):
        self.reject(lambda: self.manifest.update(schema_version="2.0.0"))

    def test_duplicate_layer(self):
        self.reject(
            lambda: self.manifest["layers"].append(copy.deepcopy(self.manifest["layers"][0]))
        )

    def test_reversed_time(self):
        self.reject(lambda: self.manifest["time"].update(samples=[1, 0]))

    def test_frame_count_mismatch(self):
        self.reject(lambda: self.manifest["time"].update(samples=[0, 1, 2]))

    def test_missing_asset(self):
        self.reject(lambda: self.manifest["layers"][0].update(asset="data/missing.json"))

    def test_parent_escape(self):
        self.reject(lambda: self.manifest["layers"][0].update(asset="../outside.json"))

    def test_symlink_escape(self):
        outside = Path(self.tmp.name) / "outside.json"
        shutil.copy(self.run / "data/mesh.json", outside)
        link = self.run / "data/escape.json"
        link.symlink_to(outside)
        self.reject(lambda: self.manifest["layers"][0].update(asset="data/escape.json"))

    def test_nonfinite_payload(self):
        self.reject(
            lambda: (self.run / "data/scalar_field.json").write_text(
                '{"positions":[[0,0,1]],"values":[[NaN],[291]]}'
            )
        )

    def test_mesh_out_of_bounds(self):
        self.reject(
            lambda: (self.run / "data/mesh.json").write_text(
                '{"positions":[[0,0,0]],"triangles":[[0,1,2]]}'
            )
        )

    def test_missing_unit(self):
        self.reject(lambda: self.manifest["layers"][1]["field"].pop("unit"))

    def test_duplicate_json_key(self):
        self.reject(
            lambda: (self.run / "data/mesh.json").write_text(
                '{"positions":[],"positions":[[0,0,0]],"triangles":[[0,0,0]]}'
            )
        )


if __name__ == "__main__":
    unittest.main()
