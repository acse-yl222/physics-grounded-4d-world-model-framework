import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/jpm25-roof-study-001';E=R/'exports/jpm25-evidence-001';bpy.ops.wm.open_mainfile(filepath=str(O/'jpm25-candidate.blend'));vs=[];fs=[]
for o in bpy.data.objects:
 if o.type=='MESH':
  o.data.calc_loop_triangles();off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in t.vertices) for t in o.data.loop_triangles)
bvh=BVHTree.FromPolygons(vs,fs,all_triangles=True);rows=[]
for x,y,z in json.load(open(E/'jpm25-ray-input.json')):
 loc,n,idx,dist=bvh.ray_cast(Vector((x,y,300)),Vector((0,0,-1)),400);rows.append({'x':x,'y':y,'dsm_odn':z,'mesh_top_scene':float(loc.z) if loc else None,'error':float(loc.z)+4.28000021-z if loc else None})
e=[q['error'] for q in rows if q['error'] is not None];se=sorted(abs(v) for v in e);out={'total_cells':len(rows),'hit_cells':len(e),'rmse':math.sqrt(sum(v*v for v in e)/len(e)),'mae':sum(abs(v) for v in e)/len(e),'p95_absolute':se[int(.95*(len(se)-1))],'within1m':sum(abs(v)<=1 for v in e),'samples':rows};(E/'jpm25-final-mesh-error.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='samples'})
