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
assert sha==hashlib.file_digest(src.open('rb'),'sha256').hexdigest();d={'regional_native':str(src),'sha256':sha,'source_unchanged':True,'site_meshes':names,'checks':out,'scope':'Vertical rays against actual regional site-support mesh at centre+4insetcorners; no invented terrain or automatic patch.'};(O/'fff_boundary-site-interface.json').write_text(json.dumps(d,indent=2));print(d)
