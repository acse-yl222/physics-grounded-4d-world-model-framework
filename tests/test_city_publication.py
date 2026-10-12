import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import test_city_presentation

from common.pipeline.package_city_preview import package

SPEC = importlib.util.spec_from_file_location(
    "city_publication", Path(__file__).resolve().parents[1] / "tools/build_city_publication.py"
)
PUBLICATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PUBLICATION)


class CityPublicationTests(unittest.TestCase):
    def test_transport_preserves_complete_model_and_array_bytes(self):
        test_city_presentation.CityPresentationTests.setUp(self)
        package(self.storage, "test", "run_source_1", self.source, "display_1", self.settings)
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory)
            (resources / "resources.json").write_text(json.dumps({"resources": []}))
            source = self.storage.run("test", "display_1")
            PUBLICATION.build(source, resources)
            base = resources / "project/test/previews/display_1"
            model = json.loads((base / "model/manifest.json").read_text())
            decoded = b"".join(
                gzip.decompress((base / "model" / p["file"]).read_bytes()) for p in model["parts"]
            )
            self.assertEqual(decoded, (source / "data/models/city.glb").read_bytes())
            packed = json.loads((base / "transport.json").read_text())["npy"]["wind.npy"]
            decoded = b"".join(
                gzip.decompress((base / "physics" / p["file"]).read_bytes())
                for p in packed["parts"]
            )
            self.assertEqual(decoded, (source / "data/physics/wind.npy").read_bytes())
            self.assertEqual(
                (base / "provenance/source_manifest.json").read_bytes(),
                (source / "manifest.json").read_bytes(),
            )
            with self.assertRaises(FileExistsError):
                PUBLICATION.build(source, resources)
