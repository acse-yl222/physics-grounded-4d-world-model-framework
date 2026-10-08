import bpy,json,hashlib
from pathlib import Path
R=Path('project/tower_hamlets/input/canary_wharf_20261007');p=Path('project/tower_hamlets/runs/canary_wharf_appearance_owner836_001/region.blend');h=hashlib.sha256(p.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(p.resolve()));out=[]
for o in bpy.data.objects:
 if o.type=='MESH' and any(k in str(v) for v in o.values() for k in ['fe66594a','00a6586d','12c79ea8']):
  vs=[list(o.matrix_world@v.co) for v in o.data.vertices];out.append({'name':o.name,'properties':dict(o.items()),'vertices':vs,'faces':[list(f.vertices) for f in o.data.polygons]})
(R/'references/skillion_native001.json').write_text(json.dumps({'source':str(p),'sha256':h,'objects':out},indent=2));print([(o['name'],len(o['vertices'])) for o in out])
