from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/fff_boundary-evidence-002';src=P/'runs/canary_wharf_appearance_north_pyramid_001/region.blend';sha=hashlib.file_digest(src.open('rb'),'sha256').hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src));vs=[];fs=[];names=[]
for o in bpy.data.objects:
 if o.type=='MESH' and o.get('building_id')=='site-support':
  o.data.calc_loop_triangles();off=len(vs);vs.extend([o.matrix_world@v.co for v in o.data.vertices]);fs.extend([tuple(off+i for i in t.vertices) for t in o.data.loop_triangles]);names.append(o.name)
bvh=BVHTree.FromPolygons(vs,fs,all_triangles=True);a=json.load(open(O/'fff_boundary-audit.json'));out=[]
for prefix in ['fff95900','02ed5509']:
 q=next(q for q in a['nearby_raw_owners'] if q['id'].startswith(prefix));ring=q['geometry_local']['coordinates'][0][:-1];center=[sum(p[i] for p in ring)/len(ring) for i in range(2)];points=[center]+[[center[i]*.15+p[i]*.85 for i in range(2)] for p in ring];hits=[]
 for x,y in points:
  loc,n,index,dist=bvh.ray_cast(Vector((x,y,20)),Vector((0,0,-1)),100);hits.append({'xy':[x,y],'support_z':loc.z if loc else None,'base_zero_gap_m':-loc.z if loc else None})
 out.append({'owner':q['id'],'context_only':prefix=='02ed5509','samples':hits})

# Dense bounded site sampling for comparison with licensed DTM.
rows=[]
for x in range(-513,-492):
 for y in range(352,373):
  loc,n,index,dist=bvh.ray_cast(Vector((x,y,20)),Vector((0,0,-1)),100)
  rows.append({'x':x,'y':y,'site_z':float(loc.z) if loc else None})
(O/'fff_boundary-terrain-site-samples.json').write_text(json.dumps({'source_sha256':sha,'samples':rows},indent=2))
