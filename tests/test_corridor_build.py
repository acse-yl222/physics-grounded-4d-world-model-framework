"""Guard the legacy adapter's checked build and selective resource packaging."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "corridor_build", ROOT / "tools/build_corridor_site.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CorridorBuildTests(unittest.TestCase):
    def test_local_and_published_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export = root / "export"
            (export / "data").mkdir(parents=True)
            data = b'{"fixture":true}'
            (export / "data/scene-meta.json").write_bytes(data)
            (export / "private.txt").write_text("not selected")
            local = root / "local"
            builder.build(export, local)
            self.assertEqual((local / "data/scene-meta.json").read_bytes(), data)
            self.assertFalse((local / "private.txt").exists())
            catalog = json.loads((local / "resources.json").read_text())
            self.assertEqual(catalog["assets"][0]["sha256"], hashlib.sha256(data).hexdigest())
            script = (local / "app.mjs").read_text()
            self.assertIn("S = recordedSampler(t, r.dt)", script)
            self.assertNotIn("return { routes: EM(await w.json()) }", script)
            self.assertNotIn("% po.duration", script)
            remote = root / "remote"
            url = "https://raw.githubusercontent.com/owner/repo/" + "a" * 40 + "/data"
            builder.build(export, remote, url)
            self.assertFalse((remote / "data").exists())
            self.assertIn(url, (remote / "app.mjs").read_text())
            with self.assertRaises(ValueError):
                builder.build(
                    export, root / "bad", "https://raw.githubusercontent.com/owner/repo/main/data"
                )
