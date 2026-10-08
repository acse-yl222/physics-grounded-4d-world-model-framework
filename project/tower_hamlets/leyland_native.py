import bpy,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';src=R/'exports/appearance-owner87aa-001/region.blend';bpy.ops.wm.open_mainfile(filepath=str(src));out=[]
for o in bpy.data.objects:
 if o.get('building_id')=='overture-building-8a7116a4-439b-4097-bee2-b8a1b7ad4f7d':
  v=[o.matrix_world@p.co for p in o.data.vertices];out.append({'name':o.name,'properties':dict(o.items()),'vertices':len(v),'faces':len(o.data.polygons),'bounds':[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]],'unique_z':sorted(set(round(p.z,4) for p in v))})
(R/'references/leyland_native.json').write_text(json.dumps({'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'objects':out},indent=2))
