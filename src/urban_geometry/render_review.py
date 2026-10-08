"""Render inspection views from saved native geometry without changing the master."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overlay', type=Path)
    parser.add_argument('--views', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    master = args.project / 'exports' / args.run / 'region.blend'
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    master_hash = hashlib.file_digest(master.open('rb'), 'sha256').hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(master.resolve()))
    scene = bpy.context.scene
    overlay_hash = None
    if args.overlay:
        overlay_hash = hashlib.file_digest(args.overlay.open('rb'), 'sha256').hexdigest()
        with bpy.data.libraries.load(str(args.overlay.resolve()), link=False) as (source, target):
            target.objects = source.objects
        for obj in target.objects:
            if obj and obj.get('research_object_id'):
                scene.collection.objects.link(obj)
        bpy.ops.wm.save_as_mainfile(filepath=str((args.output / 'combined_editable.blend').resolve()), compress=False)
    camera = scene.camera
    views = json.loads((args.views or args.project / 'inspection_views.json').read_text())
    reviewed = []
    for view in views:
        if not args.views and not view['id'].startswith(('periphery_', 'exterior_')):
            continue
        target = Vector(view['target'])
        offset = Vector(view['offset'])
        offset *= max(1, 3 * view['scale'] / offset.length)
        camera.location = target + offset
        camera.rotation_euler = (-offset).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = view['scale']
        camera.data.clip_start = .1
        camera.data.clip_end = max(10000, offset.length * 5)
        scene.render.filepath = str((args.output / (view['id'] + '.png')).resolve())
        bpy.ops.render.render(write_still=True)
        reviewed.append({**view, 'offset': list(offset)})
    assert hashlib.file_digest(master.open('rb'), 'sha256').hexdigest() == master_hash
    report = {'master_sha256': master_hash, 'master_unchanged': True,
              'overlay_sha256': overlay_hash,
              'views': reviewed, 'visually_inspected': False,
              'reason': 'Move orthographic camera back without changing projected scale to avoid foreground clipping.'}
    (args.output / 'render_report.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
