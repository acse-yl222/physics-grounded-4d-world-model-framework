import bpy,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/impounding-evidence-001';src=P/'runs/canary_wharf_appearance_owner836_001/region.blend'
h=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
before=h(src);bpy.ops.wm.open_mainfile(filepath=str(src));out=[]
for o in bpy.data.objects:
 if o.type=='MESH' and '0741fd47' in str(o.get('building_id','')):
  vv=[o.matrix_world@v.co for v in o.data.vertices];out.append({'name':o.name,'properties':{k:str(o[k]) for k in o.keys()},'vertices':len(vv),'faces':len(o.data.polygons),'bounds_enu':[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]],'materials':[m.name for m in o.data.materials]})
assert h(src)==before;(O/'native-audit.json').write_text(json.dumps({'source':str(src),'sha256':before,'unchanged':True,'meshes':out},indent=2));print(out)
