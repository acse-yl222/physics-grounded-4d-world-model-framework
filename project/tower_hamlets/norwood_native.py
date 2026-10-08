import bpy,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';src=R/'exports/appearance-bank40-002/region.blend';bpy.ops.wm.open_mainfile(filepath=str(src));out=[]
for o in bpy.data.objects:
 if o.get('building_id')=='overture-building-980db4c6-949e-4dda-b317-ec9669cf1554':
  v=[o.matrix_world@p.co for p in o.data.vertices];out.append({'name':o.name,'properties':dict(o.items()),'vertices':len(v),'faces':len(o.data.polygons),'bounds':[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]],'unique_z':sorted(set(round(p.z,4) for p in v))})
(R/'references/norwood_native.json').write_text(json.dumps({'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'objects':out},indent=2))
