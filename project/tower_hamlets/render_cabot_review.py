"""Full-context roof inspection cameras; source dimensions remain uncalibrated."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
run=root/'exports/refinement-006'
b=next(b for b in json.loads((root/'geometry.json').read_text())['buildings'] if b['id']=='overture-part-a3461c5d-098b-382d-b1d8-a6fbe5e6db1d')
pts=[p for part in b['geometry'] for p in part['outer']]
x=(min(p[0] for p in pts)+max(p[0] for p in pts))/2
y=(min(p[1] for p in pts)+max(p[1] for p in pts))/2
z=25
bpy.ops.wm.open_mainfile(filepath=str(run/'region.blend'))
scene=bpy.context.scene;cam=scene.camera
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.cycles.samples=48
for name,offset,scale in [('roof',(0,0,100),70),('south',(0,-20,50),48),('north',(0,20,50),48)]:
    cam.location=Vector((x+offset[0],y+offset[1],z+offset[2]));target=Vector((x,y,z))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale
    scene.render.filepath=str(run/('cabot-dome-'+name+'.png'));bpy.ops.render.render(write_still=True)
