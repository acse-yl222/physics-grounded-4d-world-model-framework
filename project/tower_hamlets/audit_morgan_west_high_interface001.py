from pathlib import Path
import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-west-high001';bpy.ops.wm.open_mainfile(filepath=str(O/'morgan.blend'));source=P/'runs/canary_wharf_appearance_morgan_visibility_correction_001/region.blend'
src=json.loads((R/'references/morgan_massing_study_002.json').read_text());names=[q['name'] for q in src['objects'] if q['name'].lower().find('north_terrace')>=0];print(names)
with bpy.data.libraries.load(str(source),link=False) as(a,b):b.objects=[n for n in names if n in a.objects]
for o in b.objects:bpy.context.collection.objects.link(o)
tier=bpy.data.objects['Morgan_west_high_supported_tier'];roof=bpy.data.objects['Morgan_podium_west_high'];nei=b.objects[0]
def faces(o):return [{'id':p.index,'normal':list((o.matrix_world.to_3x3()@p.normal).normalized()),'vertices':[list(o.matrix_world@o.data.vertices[i].co) for i in p.vertices]} for p in o.data.polygons]
out={'tier_faces':faces(tier),'original_roof_faces':faces(roof),'neighbor_faces':faces(nei),'neighbor_name':nei.name}
# Sample exact coincident interface from actual mesh edges by coordinate-nearness to neighbor sides.
vertical=[f for f in out['tier_faces'] if abs(f['normal'][2])<.1];matches=[]
for f in vertical:
 vv=[Vector(v) for v in f['vertices']];n=Vector(f['normal']);c=sum(vv,Vector())/len(vv)
 for q in out['neighbor_faces']:
  nq=Vector(q['normal'])
  if abs(nq.z)>.1 or n.dot(nq)>-.99:continue
  w=[Vector(v) for v in q['vertices']];dist=max(abs((v-w[0]).dot(nq)) for v in vv)
  if dist<.001:matches.append({'tier_face':f['id'],'neighbor_face':q['id'],'opposed_normal_dot':n.dot(nq),'max_plane_distance_m':dist,'tier_z':[min(v.z for v in vv),max(v.z for v in vv)],'neighbor_z':[min(v.z for v in w),max(v.z for v in w)],'tier_center':list(c),'tier_normal':list(n)})
out['opposed_vertical_interface_matches']=matches
# Reproduce camera-independent visibility test via rays from either side at interior interface heights.
def bvh(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons],all_triangles=False)
bvhs={o.name:bvh(o) for o in [tier,roof,nei]};rays=[]
for mt in matches:
 c=Vector(mt['tier_center']);n=Vector(mt['tier_normal'])
 for dz in [-1,0,1]:
  target=c+Vector((0,0,dz))
  for sign in [-1,1]:
   origin=target+n*sign*100;direction=(target-origin).normalized();hits=[]
   for name,tree in bvhs.items():
    loc,normal,idx,dist=tree.ray_cast(origin,direction,200)
    if loc is not None:hits.append({'object':name,'distance':dist,'face':idx,'hit':list(loc)})
   rays.append({'origin':list(origin),'direction':list(direction),'sorted_hits':sorted(hits,key=lambda h:h['distance'])})
out['cross_interface_rays']=rays
(O/'interface_mesh_audit.json').write_text(json.dumps(out,indent=2));s=bpy.context.scene;target=Vector((-356,-59,79.51));s.camera.location=target+Vector((12,14,8));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=18;s.render.filepath=str(O/'interface-close.png');bpy.ops.render.render(write_still=True)
