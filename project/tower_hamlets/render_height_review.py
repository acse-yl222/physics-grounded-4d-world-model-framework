"""Full-scene inspection of two LiDAR height corrections; no asset relocation."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
run=root/'exports/refinement-007'
features=json.loads((root/'geometry.json').read_text())['buildings']
bpy.ops.wm.open_mainfile(filepath=str(run/'region.blend'));scene=bpy.context.scene;cam=scene.camera
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.cycles.samples=48
for label,ident in [('jemstock','overture-building-2e1384be-3161-4326-a35d-d0ba1327dc7c'),('blockwharf','overture-building-112b6cf0-b1a9-4c9c-9614-f432af4d0902')]:
    b=next(b for b in features if b['id']==ident);pts=[p for part in b['geometry'] for p in part['outer']]
    x=(min(p[0] for p in pts)+max(p[0] for p in pts))/2;y=(min(p[1] for p in pts)+max(p[1] for p in pts))/2
    target=Vector((x,y,b['height_m']/2))
    for name,offset in [('south',(35,-45,95)),('north',(-35,45,95))]:
        if label=='jemstock' and name=='south':offset=(0,-8,140)
        cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=max(80,b['height_m']*1.8)
        scene.render.filepath=str(run/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
