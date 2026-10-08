"""Inspect the modeled central canopy in full context; no invented platform geometry."""
from pathlib import Path
import sys
import json
import bpy
from mathutils import Vector

root=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
run=root/'exports'/(args[0] if args else 'refinement-003a')
sys.path.insert(0,str(root/'src'))
from buildings.dlr_central_frame import FEATURE_ID,frame_data
feature=next(f for f in json.loads((root/'geometry.json').read_text())['buildings'] if f['id']==FEATURE_ID)
_,_,p=frame_data(feature)
u,v=p['axis_u'],p['axis_v'];midu=(p['u_min']+p['u_max'])/2;midv=(p['v_min']+p['v_max'])/2
def xyz(s,t,z):return Vector((u[0]*s+v[0]*t,u[1]*s+v[1]*t,z))
bpy.ops.wm.open_mainfile(filepath=str(run/'region.blend'));scene=bpy.context.scene;cam=scene.camera
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.cycles.samples=48
for name,position,target,kind,scale in [
 ('dlr-canopy-overview',xyz(midu,midv,120),xyz(midu,midv,10),'ORTHO',95),
 ('dlr-canopy-oblique',xyz(midu-10,midv-25,90),xyz(midu,midv,12),'ORTHO',85),
 ('dlr-canopy-understructure',xyz(p['u_min']+5,midv,p['low']+2),xyz(p['u_max']-5,midv,13),'PERSP',22),
 ('dlr-canopy-reverse',xyz(p['u_max']-5,midv,p['low']+2),xyz(p['u_min']+5,midv,13),'PERSP',22)]:
    cam.location=position;cam.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler();cam.data.type=kind
    if kind=='ORTHO':cam.data.ortho_scale=scale
    else:cam.data.lens=scale
    scene.render.filepath=str(run/(name+'.png'));bpy.ops.render.render(write_still=True)
