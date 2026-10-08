"""Perspective audit of retained architecture; does not alter any model asset.

The west-facing reference photograph motivates the view, but the camera is an
explicit estimate, not a calibrated reconstruction of its camera parameters.
"""
from pathlib import Path
import hashlib
import json
import argparse
import sys
import bpy
from mathutils import Vector

R = Path(__file__).resolve().parent / 'input/canary_wharf_20261007'
parser = argparse.ArgumentParser()
parser.add_argument('--source', default='exports/appearance-citi-newfoundland-photo-001/region.blend')
parser.add_argument('--out', default='exports/west-architecture-review-001')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
source = R / args.source
out = R / args.out
out.mkdir(exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(source))
s = bpy.context.scene
s.render.engine = 'CYCLES'
s.cycles.samples = 32
s.render.resolution_x = 1800
s.render.resolution_y = 1100
s.render.resolution_percentage = 100
s.world.use_nodes = True
s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.68, .75, .83, 1)
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
cam = s.camera
cam.data.type = 'PERSP'
cam.data.lens = 26
cam.data.clip_end = 4000
position = (-760, -80, 95)
target = (-260, -15, 110)
cam.location = position
cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
s.render.filepath = str(out / 'west-perspective.png')
bpy.ops.render.render(write_still=True)
(out / 'view.json').write_text(json.dumps({
    'source': str(source.relative_to(R)),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'camera_enu_m': position, 'target_enu_m': target, 'lens_mm': 26,
    'camera_calibrated': False, 'geometry_modified': False,
    'scope': 'Whole retained scene from estimated elevated western viewpoint. '
             'No building hidden, moved or improved by this audit. '
             'Reference Pexels Ollie Craig 11491155 is not an exact matched view.',
    'visually_reviewed': False,
}, indent=2) + '\n')
