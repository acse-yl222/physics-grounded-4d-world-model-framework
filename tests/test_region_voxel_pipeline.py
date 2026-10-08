"""Non-default geometry coarsening required by the Thapar city pipeline."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from common.pipeline.run_scene import commands, legacy_surface_config
from common.city_view import retain
from common.storage import Storage


class RegionVoxelPipelineTests(unittest.TestCase):
    def test_incomplete_pipeline_is_not_exposed_as_city_view(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            storage=Storage(root,root,root/'cache')
            trial=storage.scratch('test','pipeline','trial')
            trial.mkdir(parents=True)
            (trial/'pipeline_status.json').write_text('{"complete":false}')
            with self.assertRaises(ValueError):retain(storage,'test','trial','city',root/'authoring')
            self.assertFalse(storage.scratch('test','city_view','city').exists())

    def test_pipeline_forwards_coarse_factor(self):
        config = {'scene': 'test', 'domain': {'cell_m': 4, 'wind_layers': 64, 'crop_local_m': None},
                  'wind': {'coarse_factor': 2}, 'georeference': {'confirmed': True, 'latitude_deg': 30,
                      'longitude_deg': 76, 'north': 'north', 'terrain': 'flat'}, 'solar': {}, 'flood': {}}
        paths = {'source': Path('/tmp/source.glb'), 'geometry': Path('/tmp/geometry'), 'physics': Path('/tmp/physics')}
        command = commands('geometry', config, paths, None, None)[0]
        self.assertEqual(command[command.index('--coarse-factor') + 1], '2')
        self.assertEqual(legacy_surface_config(config, paths)['coarse_factor'], 2)

    @unittest.skipUnless(importlib.util.find_spec('numba'), 'Voxel test requires numba')
    def test_four_metre_voxels_export_eight_metre_masks(self):
        vertices = np.array([[0, 10, 0], [8, 10, 0], [0, 10, -8]], dtype='<f4')
        binary = vertices.tobytes()
        document = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
                    'nodes': [{'mesh': 0, 'name': 'Mapped building roof'}],
                    'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'mode': 4}]}],
                    'buffers': [{'byteLength': len(binary)}], 'bufferViews': [{'buffer': 0, 'byteLength': len(binary)}],
                    'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3',
                                   'min': vertices.min(axis=0).tolist(), 'max': vertices.max(axis=0).tolist()}]}
        encoded = json.dumps(document).encode()
        encoded += b' ' * (-len(encoded) % 4)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'test.glb'
            source.write_bytes(struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(binary)) +
                               struct.pack('<I4s', len(encoded), b'JSON') + encoded +
                               struct.pack('<I4s', len(binary), b'BIN\0') + binary)
            result = subprocess.run([sys.executable, '-m', 'urban_geometry.voxelization.prepare_glb',
                                     '--source', str(source), '--out', str(root / 'voxel'), '--cell', '4',
                                     '--coarse-factor', '2'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            fine = np.load(root / 'voxel/footprint_4m_yx.npy')
            coarse = np.load(root / 'voxel/footprint_8m_yx.npy')
            expected = fine.reshape(128, 2, 128, 2).any(axis=(1, 3))
            np.testing.assert_array_equal(coarse, expected)
            self.assertGreater(coarse.sum(), 0)
            self.assertFalse((root / 'voxel/footprint_16m_yx.npy').exists())


if __name__ == '__main__':
    unittest.main()
