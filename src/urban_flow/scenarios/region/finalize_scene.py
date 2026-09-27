"""Apply scene-specific terrain limitations and slice height after web export."""
import json
from pathlib import Path
import numpy as np

root = Path.cwd()
folder = root / 'visualizer/scenes/region'
scene_path = folder / 'scene.json'
scene = json.loads(scene_path.read_text())
meta = json.loads((root / 'output/region/geometry/voxel_8m/metadata.json').read_text())
scene['limits'] = meta['limits'] + [
    'Original model elevation = displayed local elevation + 480 m.',
    'Fields show a horizontal 288–320 m slice above local datum, not height above ground.',
    'Thermal and tracer forcing are controlled assumptions, not local weather or emissions.',
]
scene['focus'] = {'box': [[-1400, -800], [1450, 700]], 'orbit_m': 2800,
                  'label': '23 stationary turbines and mountainous terrain'}
if 'temp' in scene['layers']:
    scene['layers']['temp']['y'] = 296
scene['masks']['study_area'] = 'masks/study_area_8m_yx.npy'
np.save(folder / 'physics/masks/study_area_8m_yx.npy',
        np.load(root / 'output/region/geometry/voxel_8m/study_area_8m_yx.npy'))
scene_path.write_text(json.dumps(scene, indent=2))
manifest_path = folder / 'physics/manifest.json'
manifest = json.loads(manifest_path.read_text())
manifest['limits'] = scene['limits']
manifest['original_vertical_offset_m'] = 480
manifest_path.write_text(json.dumps(manifest, indent=2))
print('Region scene registered, limits and terrain datum applied.')
