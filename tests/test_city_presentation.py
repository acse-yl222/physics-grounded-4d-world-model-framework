import json
import shutil
import unittest

import test_export
from common.contract import validate
from common.export import package_export
from common.pipeline.package_city_preview import package
from common.runs import promote_bundle


class CityPresentationTests(unittest.TestCase):
    def setUp(self):
        test_export.ExportTests.setUp(self)
        bundle = package_export(self.storage, self.source, self.config, "source_1")
        promote_bundle(self.storage, bundle)
        path = self.source / "scene.json"
        scene = json.loads(path.read_text())
        scene["id"] = "test"
        scene["layers"]["wind"]["frames"] = 2
        path.write_text(json.dumps(scene))
        self.settings = self.root / "presentation.json"
        self.settings.write_text(json.dumps({"title": "Retained city"}))

    def package(self):
        return package(
            self.storage, "test", "run_source_1", self.source, "display_1", self.settings
        )

    def test_bundle_survives_scratch_removal_and_keeps_source_unchanged(self):
        source_manifest = self.storage.run("test", "source_1_wind") / "manifest.json"
        before = source_manifest.read_bytes()
        self.package()
        retained = self.storage.run("test", "display_1")
        scene = json.loads((retained / "data/scene.json").read_text())
        self.assertEqual(scene["layers"]["wind"]["time_s"], [0, 1])
        self.assertEqual(scene["title"], "Retained city")
        with self.assertRaises(FileExistsError):
            self.package()
        shutil.rmtree(self.storage.cache_root)
        validate(retained / "manifest.json")
        self.assertEqual(source_manifest.read_bytes(), before)

    def test_modified_display_array_cannot_be_retained_as_original_data(self):
        (self.source / "physics/wind.npy").write_bytes(b"changed data")
        with self.assertRaisesRegex(ValueError, "differs from the retained"):
            self.package()
        self.assertFalse(self.storage.run("test", "display_1").exists())

    def test_frame_count_must_match_recorded_times(self):
        path = self.source / "scene.json"
        scene = json.loads(path.read_text())
        scene["layers"]["wind"]["frames"] = 3
        path.write_text(json.dumps(scene))
        with self.assertRaisesRegex(ValueError, "Frame count"):
            self.package()
        self.assertFalse(self.storage.run("test", "display_1").exists())
