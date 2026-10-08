"""Inspect partial Crossrail assembly in unchanged city context."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007';out=root/'exports/refinement-008'
rep=json.loads((root/'references/crossrail_lidar_review.json').read_text());cx,cy=rep['mapped_part_extent']['centroid_local_xy'];u=rep['axis_local_xy'];v=(-u[1],u[0]);target=Vector((cx,cy,15))
bpy.ops.wm.open_mainfile(filepath=str(out/'region.blend'));scene=bpy.context.scene;cam=scene.camera
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.cycles.samples=48
for label,s,t,z,scale in [('roof',0,0,300,355),('north',0,-95,170,350),('end',-100,-90,200,370)]:
    cam.location=target+Vector((s*u[0]+t*v[0],s*u[1]+t*v[1],z));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale
    scene.render.filepath=str(out/('crossrail-'+label+'.png'));bpy.ops.render.render(write_still=True)
