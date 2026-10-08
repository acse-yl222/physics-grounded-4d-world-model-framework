import bpy,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/fff_boundary-evidence-001';src=P/'runs/canary_wharf_appearance_north_pyramid_001/region.blend';sha=hashlib.file_digest(src.open('rb'),'sha256').hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src));out=[]
for o in bpy.data.objects:
 if o.type=='MESH' and 'fff95900' in str(o.get('building_id','')):
  vv=[o.matrix_world@v.co for v in o.data.vertices];out.append({'name':o.name,'vertices':len(vv),'polygons':len(o.data.polygons),'bounds_enu':[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]],'props':{k:str(o[k]) for k in o.keys()}})
assert sha==hashlib.file_digest(src.open('rb'),'sha256').hexdigest();(O/'fff_boundary-native.json').write_text(json.dumps({'source':str(src),'sha256':sha,'unchanged':True,'meshes':out},indent=2));print(out)
