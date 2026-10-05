import json
import math
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from common.binary import validate_glb
from common.catalog import view
from common.storage import Storage
from urban_geometry.img2city_adapter import align_glb, import_model


class Img2CityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        (self.root / 'AGENTS.md').write_text('test')
        self.storage = Storage.load(self.root)
        self.source = self.root / 'model.glb'
        self.metadata = self.root / 'buildings.json'
        self.anchor = {'lat0': 51.494, 'lon0': -.1744, 'proj': 'equirect'}
        self.metadata.write_text(json.dumps({'anchor': self.anchor}))
        self.project = json.loads((ROOT / 'project/south_ken/project.json').read_text())
        p = self.root / 'project/south_ken'
        p.mkdir(parents=True)
        (p / 'project.json').write_text(json.dumps(self.project))
        self.doc = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
                    'nodes': [{'translation': [10, 2, 30], 'children': [1]},
                              {'mesh': 0, 'scale': [2, 3, 4]}],
                    'meshes': [{'primitives': [{'attributes': {'POSITION': 0}}]}],
                    'accessors': [{'min': [0, 0, 0], 'max': [1, 1, 1]}],
                    'animations': [{'name': 'not_protocol_traffic'}]}
        self.tail = struct.pack('<I4s', 4, b'BIN\x00') + b'abcd'
        self.write_glb()

    def write_glb(self):
        payload = json.dumps(self.doc).encode()
        payload += b' ' * (-len(payload) % 4)
        self.source.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(payload) + len(self.tail))
                                + struct.pack('<I4s', len(payload), b'JSON') + payload + self.tail)

    def test_rebase_nested_transforms_preserves_binary_and_source(self):
        before = self.source.read_bytes()
        dest = self.root / 'aligned.glb'
        bounds, details = align_glb(self.source, dest, self.anchor, self.project['spatial']['origin'])
        sx = details['gltf_scale'][0]
        dx, _, dz = details['gltf_translation']
        self.assertAlmostEqual(bounds['min'][0], dx + 10 * sx)
        self.assertAlmostEqual(bounds['max'][0], dx + 12 * sx)
        self.assertAlmostEqual(bounds['min'][1], -(dz + 34))
        self.assertAlmostEqual(bounds['max'][1], -(dz + 30))
        self.assertEqual([bounds['min'][2], bounds['max'][2]], [2, 5])
        target_lat = self.project['spatial']['origin']['latitude']
        self.assertAlmostEqual(dx, (.002496) * 111320 * math.cos(math.radians(target_lat)))
        self.assertEqual(self.source.read_bytes(), before)
        self.assertTrue(dest.read_bytes().endswith(self.tail))
        self.assertNotIn('animations', validate_glb(dest))
        self.assertEqual(details['animations_omitted'], 1)

    def test_import_adds_view_without_overwriting_scene_and_refuses_repeat(self):
        path = self.root / 'project/south_ken/project.json'
        before = path.read_bytes()
        result = import_model(self.storage, self.source, self.metadata, run_id='img2city_test')
        self.assertTrue(result.is_file())
        _, runs = view(self.storage, 'south_ken', 'img2city_test')
        self.assertEqual(runs['img2city_test']['time']['samples'], [])
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(FileExistsError):
            import_model(self.storage, self.source, self.metadata, run_id='img2city_test')
        self.assertEqual(path.read_bytes(), before)

    def test_unknown_projection_rejected(self):
        with self.assertRaisesRegex(ValueError, 'anchor'):
            align_glb(self.source, self.root / 'bad.glb', {**self.anchor, 'proj': 'unknown'}, self.project['spatial']['origin'])

    def test_escaping_external_texture_rejected(self):
        self.doc['images'] = [{'uri': '../private.jpg'}]
        self.write_glb()
        with self.assertRaisesRegex(ValueError, 'embed'):
            align_glb(self.source, self.root / 'bad.glb', self.anchor, self.project['spatial']['origin'])


if __name__ == '__main__':
    unittest.main()
