from pathlib import Path
import bpy,json,hashlib,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent; R=P/'input/canary_wharf_20261007'; O=R/'exports/cabot-facade-correspondence-001';O.mkdir(exist_ok=True)
src=R/'exports/cabot-place-photo-study-001/cabot_place.blend';before=hashlib.file_digest(src.open('rb'),'sha256').hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(src));obs=[o for o in bpy.data.objects if o.type=='MESH'];cam=json.loads((R/'references/cabot_place_anna_camera.json').read_text());a=cam['parameters_xy_yaw_pitch_logf'];C=Vector((a[0],a[1],2));yaw,pitch,lf=a[2:];fw=Vector((math.cos(yaw)*math.cos(pitch),math.sin(yaw)*math.cos(pitch),math.sin(pitch)));right=Vector((math.sin(yaw),-math.cos(yaw),0));up=right.cross(fw)
def proj(v):
 d=v-C;return [684+math.exp(lf)*d.dot(right)/d.dot(fw),912-math.exp(lf)*d.dot(up)/d.dot(fw)]
trees=[];out=[]
for ob in obs:
 vv=[ob.matrix_world@v.co for v in ob.data.vertices];trees.append((ob.name,BVHTree.FromPolygons(vv,[list(p.vertices) for p in ob.data.polygons])));out.append({'name':ob.name,'pixels':[proj(v) for v in vv],'edges':[list(e.vertices) for e in ob.data.edges]})
samples=[]
for ob in obs:
 if 'glass' not in ob.name:continue
 for p in ob.data.polygons:
  target=ob.matrix_world@p.center;delta=target-C
  if (ob.matrix_world.to_3x3()@p.normal).dot(-delta)<=0:continue
  hits=[]
  for name,tree in trees:
   loc,normal,idx,dist=tree.ray_cast(C,delta.normalized(),delta.length-.003)
   if loc is not None:hits.append({'object':name,'distance_before_target_m':delta.length-dist})
  samples.append({'xyz':list(target),'pixel':proj(target),'blockers':hits})
report={'source_native':str(src),'source_sha256':before,'source_unchanged':before==hashlib.file_digest(src.open('rb'),'sha256').hexdigest(),'camera':cam,'projected_objects':out,'glass_face_center_rays':samples,'limitations':['Local actual-mesh ray tests only; neighbor occlusion not tested.','Stored camera has only three approximate tower-roof centroid controls; small fit residual is not foreground calibration.','No geometry authored or changed; physical rays do not establish photo correspondence.']}
(O/'audit.json').write_text(json.dumps(report,indent=2));print('audit',len(samples),'blocked',sum(bool(q['blockers']) for q in samples))
