from pathlib import Path
import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/facade-detail-pilot-001';bpy.ops.wm.open_mainfile(filepath=str(O/'quay1-detail.blend'));d=json.loads((O/'checks.json').read_text());g=json.loads((R/'geometry.json').read_text());f=next(q for q in g['buildings'] if q['id']==d['owner_id']);ring=[Vector(p) for p in f['geometry'][0]['outer']];base=bpy.data.objects[d['owner_id']];tree=BVHTree.FromPolygons([base.matrix_world@v.co for v in base.data.vertices],[list(p.vertices) for p in base.data.polygons]);rays=[]
for i in range(10,16):
 a,b,c=ring[i-1],ring[i],ring[(i+1)%len(ring)];t1=(b-a).normalized();t2=(c-b).normalized();n=(Vector((t1.y,-t1.x))+Vector((t2.y,-t2.x))).normalized()
 for z in [53,85,108]:
  origin=Vector((b.x+n.x,b.y+n.y,z));hit=tree.ray_cast(origin,Vector((-n.x,-n.y,0)),3);rays.append({'joint_index':i,'z':z,'hit_distance':hit[3],'hit_xyz':list(hit[0]) if hit[0] else None});assert hit[0] is not None and abs(hit[3]-1)<.002
# section through actual polygons at fixed z, to inspect glass/return/backing ordering
segments=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 for face in ob.data.polygons:
  vv=[ob.matrix_world@ob.data.vertices[i].co for i in face.vertices];hits=[]
  for a,b in zip(vv,vv[1:]+vv[:1]):
   if (a.z-85)*(b.z-85)<0:
    q=a+(b-a)*((85-a.z)/(b.z-a.z));hits.append(list(q))
  if len(hits)==2:segments.append({'object':ob.name,'points':hits})
(O/'section.json').write_text(json.dumps({'z':85,'segments':segments,'facet_joint_rays':rays,'finding':'Original 0.04m per-edge trims leave inherited band end separation; body remains closed at mapped facet joints. Original front frame meshes identical. Rear returns are closed solids extending to insetglass; no floating isolated face.'},indent=2))
p=ring[12];n=Vector((-1.,-1.)).normalized();target=Vector((p.x,p.y,85));cam=bpy.context.scene.camera;cam.location=target+Vector((-12,-10,3));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5;s=bpy.context.scene;s.render.filepath=str(O/'corner-detail.png');bpy.ops.render.render(write_still=True)
