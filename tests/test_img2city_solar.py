import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
try:
    from urban_geometry.img2city_solar import raster_model, calculate
except ImportError:
    raster_model = calculate = None


@unittest.skipIf(calculate is None, 'Install optional CPU solar dependencies: torch, numba, Pillow')
class Img2CitySolarTests(unittest.TestCase):
    def test_world_transforms_are_applied_before_rasterization(self):
        positions = np.array([[0, 10, 0], [8, 10, 0], [0, 10, -8]], dtype='<f4')
        binary = positions.tobytes()
        document = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
                    'nodes': [{'translation': [10, 2, -20], 'children': [1]}, {'mesh': 0}],
                    'meshes': [{'primitives': [{'attributes': {'POSITION': 0}}]}],
                    'buffers': [{'byteLength': len(binary)}], 'bufferViews': [{'buffer': 0, 'byteLength': len(binary)}],
                    'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3'}]}
        payload = json.dumps(document).encode(); payload += b' ' * (-len(payload) % 4)
        content = (struct.pack('<4sII', b'glTF', 2, 28+len(payload)+len(binary))
                   + struct.pack('<I4s', len(payload), b'JSON') + payload
                   + struct.pack('<I4s', len(binary), b'BIN\0') + binary)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'triangle.glb'; path.write_bytes(content)
            height, valid, origin, count = raster_model(path, {'min': [10, 20, 0], 'max': [18, 28, 12]}, 2)
            self.assertEqual(origin, [10, 20])
            self.assertEqual(count, 1)
            self.assertTrue(valid[0, 0])
            self.assertEqual(height[0, 0], 12)
            self.assertFalse(valid[-1, -1])

    def test_flat_surface_is_unshaded_at_noon_and_zero_at_night(self):
        ghi, shadow, sky, hours, frames = calculate(np.zeros((8, 8), np.float32), 4,
                                                   {'latitude': 51.494, 'longitude': -.1744}, '2026-06-21', 60)
        self.assertTrue(np.all(ghi[0] == 0))
        self.assertTrue(np.all(shadow[12] == 0))
        self.assertGreater(ghi[12].min(), 800)
        self.assertGreater(sky.min(), .99)
        self.assertTrue(np.all((hours > 14) & (hours < 19)))
        self.assertEqual(frames[12]['seconds'], 43200)


if __name__ == '__main__':
    unittest.main()
