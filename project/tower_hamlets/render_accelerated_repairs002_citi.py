from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
S=Path(__file__).resolve().parent;O=S/'input/canary_wharf_20261007/exports/appearance-accelerated-repairs-002';src=O/'region.blend';h=hashlib.file_digest(src.open('rb'),'sha256').hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src));s=bpy.context.scene;s.cycles.samples=24;s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.resolution_percentage=100;cam=s.camera;checks=[]
for name,pos,target,scale in [('citi-context',(-3,-126,205),(47,-141,187),66),('citi-detail',(23,-140,149),(40,-140,146),18)]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.data.clip_start=.05;cam.data.clip_end=3000
 hit,loc,n,face,obj,_=s.ray_cast(bpy.context.evaluated_depsgraph_get(),Vector(pos),(Vector(target)-Vector(pos)).normalized(),distance=500)
 checks.append({'view':name,'position':pos,'target':target,'first_hit':obj.name if hit else None,'owner':obj.get('building_id')if hit else None});assert hit and obj.get('building_id')=='overture-building-12b707fc-a45c-4558-98fc-88e1146fd0ad',checks[-1]
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
assert hashlib.file_digest(src.open('rb'),'sha256').hexdigest()==h
(O/'citi-camera-correction.json').write_text(json.dumps({'native_unchanged':True,'checks':checks,'reason':'Original global camera retreat put One Canada in foreground. New local viewpoints leave geometry unchanged.'},indent=2))
