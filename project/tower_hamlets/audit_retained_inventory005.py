"""Read-only reconciliation of retained meshes with the original object inventory."""
from pathlib import Path
import json,hashlib,bpy
S=Path(__file__).resolve().parent
R=S/'input/canary_wharf_20261007'
p=S/'runs/canary_wharf_appearance_jpm25_001/region.blend'
hash_before=hashlib.sha256(p.read_bytes()).hexdigest()
inv=json.loads((R/'geometry.json').read_text())['buildings']
ids={o['id'] for o in inv}
raw={i.removeprefix('overture-building-').removeprefix('overture-part-'):i for i in ids}
bpy.ops.wm.open_mainfile(filepath=str(p))
represented={};unknown={};empty=[]
for o in bpy.data.objects:
 if o.type!='MESH':continue
 if not o.data.vertices:empty.append(o.name)
 entries=[('building_id',o.get('building_id')),('aggregate_alias_id',o.get('aggregate_alias_id'))]
 entries += [('source_owner_ids',x) for x in o.get('source_owner_ids',[])]
 for kind,val in entries:
  if not val:continue
  val=str(val);canonical=val if val in ids else raw.get(val)
  target=represented if canonical else unknown
  target.setdefault(canonical or val,[]).append({'mesh':o.name,'property':kind})
assert hash_before==hashlib.sha256(p.read_bytes()).hexdigest()
report={'source':str(p),'source_sha256':hash_before,'source_unchanged':True,'inventory_count':len(ids),'building_part_inventory_count':sum(o.get('kind') in ['building','part'] for o in inv),'site_support_count':sum(o.get('kind')=='site' for o in inv),'represented_count':len(represented),'missing_ids':sorted(ids-set(represented)),'unknown_metadata_ids':unknown,'empty_meshes':empty,'representation':represented,'limitation':'Identity presence only; does not certify correct shape, façade detail, accuracy, uniqueness or completion.'}
(R/'references/retained_inventory_reconciliation005.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['representation','unknown_metadata_ids']},indent=2))
