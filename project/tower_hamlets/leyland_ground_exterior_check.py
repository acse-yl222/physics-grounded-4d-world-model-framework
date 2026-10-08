from pathlib import Path
import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/leyland-ground-contact-001';bpy.ops.wm.open_mainfile(filepath=str(O/'ground-contact.blend'));g=json.loads((R/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id'].endswith('8a7116a4-439b-4097-bee2-b8a1b7ad4f7d'));segments=[]
for p in f['geometry']:
 for ring in [p['outer'],*p.get('holes',[])]:
  for a,b in zip(ring,ring[1:]+ring[:1]):segments.append((Vector(a),Vector(b)))
def distance(p):
 out=[]
 for a,b in segments:
  v=b-a;t=max(0,min(1,(p-a).dot(v)/v.length_squared)) if v.length_squared else 0;out.append((p-(a+t*v)).length)
 return min(out)
t=next(o for o in bpy.data.objects if o.get('building_id')=='leyland-diagnostic-terrain');t.data.calc_loop_triangles();bvh=BVHTree.FromPolygons([t.matrix_world@v.co for v in t.data.vertices],[tuple(t.vertices) for t in t.data.loop_triangles],all_triangles=True);rows=[]
for o in bpy.data.objects:
 if o.type!='MESH' or o==t:continue
 gaps=[]
 for edge in o.data.edges:
  a,b=[o.matrix_world@o.data.vertices[i].co for i in edge.vertices]
  if a.z<3 and b.z<3 and distance(Vector(((a.x+b.x)/2,(a.y+b.y)/2)))<.0001:
   for frac in [0,.125,.25,.375,.5,.625,.75,.875,1]:
    p=a.lerp(b,frac);hit=bvh.ray_cast(Vector((p.x,p.y,50)),Vector((0,0,-1)),100)[0];gaps.append(float(p.z-hit.z))
 if gaps:rows.append({'mesh':o.name,'samples':len(gaps),'min_m':min(gaps),'max_m':max(gaps),'positive_count':sum(x>1e-5 for x in gaps)})
r={'method':'Actual frozen candidate bottomedges whose XYmidpoint iswithin0.1mm of mapped exterior/interior boundary;9samples peredge; rayactualterrain triangles. Internalcap diagonals excluded.','rows':rows,'global_min_m':min(x['min_m'] for x in rows),'global_max_m':max(x['max_m'] for x in rows),'positive_count':sum(x['positive_count'] for x in rows)};(O/'exterior_base_check.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k!='rows'})
