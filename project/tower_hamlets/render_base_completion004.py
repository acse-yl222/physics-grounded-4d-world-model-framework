"""Correct the HSBC inspection camera without editing the assembled native scene."""
from pathlib import Path
import bpy
import json
import hashlib
import sys
from mathutils import Vector

S = Path(__file__).resolve().parent
O = S/'input/canary_wharf_20261007/exports/appearance-base-completion-004'
native = O/'region.blend'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = sha(native)
bpy.ops.wm.open_mainfile(filepath=str(native))
scene = bpy.context.scene
views = [
    {'name': 'hsbc-entry-context', 'target': [89.707, -14.4905, 3.3],
     'offset': [.3, -4.8, 1.0], 'scale': 10.5, 'local_camera': True},
    {'name': 'hsbc-base-context', 'target': [89.707, -14.4905, 12],
     'offset': [-.68, -3.94, .1], 'scale': 82, 'local_camera': True},
]
scene.render.resolution_x = 1400
scene.render.resolution_y = 1000
scene.cycles.samples = 16
for view in views:
    if '--base-only' in sys.argv and view['name'] != 'hsbc-base-context':
        continue
    target = Vector(view['target'])
    cam = scene.camera
    cam.location = target + Vector(view['offset'])
    cam.rotation_euler = (target-cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = view['scale']
    cam.data.clip_start = .05
    cam.data.clip_end = 3000
    scene.render.filepath = str(O/(view['name']+'.png'))
    bpy.ops.render.render(write_still=True)
assert sha(native) == before
(O/'camera-correction.json').write_text(json.dumps({
    'views': views, 'native_unchanged_sha256': before,
    'reason': 'Moved camera inside verified approach to avoid foreground occlusion; no geometry or lighting changes.',
}, indent=2)+'\n')
