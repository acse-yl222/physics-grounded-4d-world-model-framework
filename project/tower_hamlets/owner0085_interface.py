from pathlib import Path
import bpy,json,hashlib
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/owner0085-massing-001';src=P/'runs/canary_wharf_appearance_owner1f92_001/region.blend';bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(src)) as (a,b):b.objects=[n for n in a.objects if n=='Owner1f92_tier0_0']
rows=[]
for o in b.objects:
 vs=[list(o.matrix_world@v.co) for v in o.data.vertices];rows.append({'name':o.name,'building_id':o.get('building_id'),'vertices':vs,'faces':[list(f.vertices) for f in o.data.polygons],'min_z_m':min(v[2] for v in vs),'max_z_m':max(v[2] for v in vs)})
assert len(rows)==1
(O/'interface_native.json').write_text(json.dumps({'source':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'neighbor_objects':rows},indent=2))
