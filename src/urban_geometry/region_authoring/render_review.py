"""Render supplementary massing inspection views without altering the master."""
import argparse
import sys
from pathlib import Path
import bpy
from mathutils import Vector

p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.run.resolve()
bpy.ops.wm.open_mainfile(filepath=str(root/'region.blend'))
scene=bpy.context.scene;cam=scene.camera
scene.render.resolution_x=1200;scene.render.resolution_y=900
views=[('north-overview',(1100,1300,1100),(0,0,70),1550),
       ('roof-overview',(0,0,1800),(0,0,0),1450),
       ('one-canada-square-roof',(-220,-320,330),(-47,-41,200),280)]
for name,position,target,scale in views:
    cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(root/(name+'.png'));bpy.ops.render.render(write_still=True)
