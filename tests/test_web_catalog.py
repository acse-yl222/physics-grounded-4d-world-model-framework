import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from common.storage import Storage
from common.web_catalog import load_web_catalog


class WebCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.storage = Storage(root, root / "external-data", root / "scratch")
        self.config = root / "project/test_campus/configs/web_entry.json"
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            json.dumps(
                {
                    "title": "Test Campus",
                    "description": "Fixture",
                    "run_id": "preview_1",
                    "launch": {"phase": "temp", "lite": "0"},
                }
            )
        )
        self.run = self.storage.run("test_campus", "preview_1")

    def retain_fixture(self, status="complete"):
        self.run.mkdir(parents=True)
        (self.run / "scene.json").write_text("{}")
        (self.run / "model.glb").write_bytes(b"fixture")
        (self.run / "manifest.json").write_text(
            json.dumps(
                {
                    "scene_id": "test_campus",
                    "run_id": "preview_1",
                    "simulation": "city_presentation",
                    "status": status,
                    "layers": [{"asset": "model.glb"}],
                    "artifacts": [{"id": "city_scene", "asset": "scene.json"}],
                }
            )
        )

    def test_explicit_completed_run_is_added_and_preserves_published_entries(self):
        baseline = load_web_catalog(self.storage)
        self.retain_fixture()
        result = load_web_catalog(self.storage)
        self.assertEqual(result["scenes"][:-1], baseline["scenes"])
        item = result["scenes"][-1]
        self.assertEqual(item["scene_id"], "test_campus")
        self.assertEqual(
            parse_qs(urlsplit(item["viewer_url"]).query),
            {"scene": ["test_campus"], "run": ["preview_1"], "phase": ["temp"], "lite": ["0"]},
        )

    def test_missing_or_running_data_does_not_create_a_broken_entry(self):
        count = len(load_web_catalog(self.storage)["scenes"])
        self.retain_fixture("running")
        self.assertEqual(len(load_web_catalog(self.storage)["scenes"]), count)

    def test_missing_descriptor_and_path_escape_are_rejected(self):
        self.retain_fixture()
        m = json.loads((self.run / "manifest.json").read_text())
        m["artifacts"][0]["asset"] = "missing.json"
        (self.run / "manifest.json").write_text(json.dumps(m))
        self.assertNotIn(
            "test_campus", [x["scene_id"] for x in load_web_catalog(self.storage)["scenes"]]
        )
        m["artifacts"][0]["asset"] = "../../outside.json"
        (self.run / "manifest.json").write_text(json.dumps(m))
        with self.assertLogs("common.web_catalog", level="WARNING"):
            catalog = load_web_catalog(self.storage)
        self.assertNotIn("test_campus", [x["scene_id"] for x in catalog["scenes"]])

    def test_bad_local_config_does_not_change_other_scene_links(self):
        baseline = load_web_catalog(self.storage)
        for content in ["{broken-json", "null", "[]", json.dumps({"title": "Missing run"})]:
            self.config.write_text(content)
            with self.assertLogs("common.web_catalog", level="WARNING"):
                self.assertEqual(load_web_catalog(self.storage), baseline)

    def test_malformed_manifest_does_not_break_published_entries(self):
        baseline = load_web_catalog(self.storage)
        self.retain_fixture()
        valid = json.loads((self.run / "manifest.json").read_text())
        for manifest in [None, [], {**valid, "artifacts": [None]}, {**valid, "layers": {}}]:
            (self.run / "manifest.json").write_text(json.dumps(manifest))
            with self.assertLogs("common.web_catalog", level="WARNING"):
                self.assertEqual(load_web_catalog(self.storage), baseline)

    def test_missing_model_hides_only_its_local_entry(self):
        baseline = load_web_catalog(self.storage)
        self.retain_fixture()
        (self.run / "model.glb").unlink()
        self.assertEqual(load_web_catalog(self.storage), baseline)
