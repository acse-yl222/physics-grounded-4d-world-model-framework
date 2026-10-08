import functools
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common.storage import Storage
from common.server import ViewerHandler
from common.catalog import view


class RegistryServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        (self.root / "AGENTS.md").write_text("fixture")
        shutil.copytree(ROOT / "schemas", self.root / "schemas")
        run = self.root / "project/south_ken/runs/synthetic_v1"
        shutil.copytree(ROOT / "examples/contract-v1", run)
        m = json.loads((run / "manifest.json").read_text())
        p = run.parents[1]
        (p / "project.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.1.0",
                    "scene_id": "south_ken",
                    "title": "Synthetic",
                    "spatial": m["spatial"],
                    "inputs": [],
                    "default_view": "default",
                }
            )
        )
        (p / "views").mkdir()
        self.viewpath = p / "views/default.json"
        self.v = {
            "schema_version": "1.1.0",
            "scene_id": "south_ken",
            "title": "Test",
            "time_alignment": "relative",
            "runs": ["synthetic_v1"],
            "layers": [{"run_id": "synthetic_v1", "layer_id": "mesh", "visible": True}],
        }
        self.viewpath.write_text(json.dumps(self.v))
        self.storage = Storage.load(self.root)

    def test_registry(self):
        self.assertEqual(view(self.storage, "south_ken", "default")[0]["title"], "Test")

    def test_missing_layer_rejected(self):
        self.v["layers"][0]["layer_id"] = "missing"
        self.viewpath.write_text(json.dumps(self.v))
        with self.assertRaises(ValueError):
            view(self.storage, "south_ken", "default")

    def test_absolute_time_requires_epoch(self):
        self.v["time_alignment"] = "absolute"
        self.viewpath.write_text(json.dumps(self.v))
        with self.assertRaises(ValueError):
            view(self.storage, "south_ken", "default")

    def test_range_and_project_mount(self):
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(ViewerHandler, storage=self.storage)
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_port}/project/south_ken/runs/synthetic_v1/data/mesh.json"
        request = urllib.request.Request(url, headers={"Range": "bytes=2-9"})
        with urllib.request.urlopen(request) as r:
            self.assertEqual(r.status, 206)
            self.assertEqual(len(r.read()), 8)
            self.assertTrue(r.headers["Content-Range"].startswith("bytes 2-9/"))
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=999999-"}))
        self.assertEqual(error.exception.code, 416)
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(
                f"http://127.0.0.1:{server.server_port}/.history/repositories/secrets"
            )

    def test_resources_are_independent_of_workspace_and_missing_catalogue_is_empty(self):
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(ViewerHandler, storage=self.storage)
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base + "/src/visualization/viewer/main.mjs") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"createWidget", response.read())
        with urllib.request.urlopen(base + "/project/index.json") as response:
            self.assertEqual(json.load(response), {"default": None, "scenes": []})

    def test_directory_index_symlink_cannot_escape_run(self):
        run = self.storage.run("south_ken", "synthetic_v1")
        outside = Path(self.tmp.name) / "outside.html"
        outside.write_text("external fixture")
        (run / "index.html").symlink_to(outside)
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(ViewerHandler, storage=self.storage)
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(
                f"http://127.0.0.1:{server.server_port}/project/south_ken/runs/synthetic_v1/"
            )
        self.assertEqual(error.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
