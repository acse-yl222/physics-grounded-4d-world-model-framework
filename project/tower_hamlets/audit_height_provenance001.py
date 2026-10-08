"""Read-only source-height provenance audit; never interprets supplied height as survey."""
from pathlib import Path
import json, hashlib, collections, bpy
S=Path(__file__).resolve().parent
R=S/'input/canary_wharf_20261007'
src=S/'runs/canary_wharf_appearance_owner836_001/region.blend'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(src)
g=json.loads((R/'geometry.json').read_text())['buildings']
bpy.ops.wm.open_mainfile(filepath=str(src))
owned=collections.defaultdict(list)
for o in bpy.data.objects:
 if o.type=='MESH' and o.get('building_id'):
  owned[o['building_id']].append({'name':o.name,'height_basis':o.get('height_basis'),'coverage':o.get('coverage'),'top_z_m':max((o.matrix_world@v.co).z for v in o.data.vertices) if o.data.vertices else None})
rows=[]
for b in g:
 if b.get('kind') not in ['building','part']:continue
 sources=b.get('source_properties',{}).get('sources',[])
 hs=[q for q in sources if q.get('property') in ['/properties/height','/height','height']]
 ml=any('microsoft' in str(q.get('dataset','')).lower() or q.get('provider')=='microsoft' for q in hs)
 basis=b.get('height_basis','')
 category='machine_learning_height' if ml else ('floor_count_assumption' if 'floor' in basis else ('unknown_height_assumption' if 'assumed' in basis else 'other_source_or_derived_height'))
 rows.append({'id':b['id'],'input_height_m':b.get('height_m'),'input_height_basis':basis,'height_source_records':hs,'source_category':category,'native_meshes':owned.get(b['id'],[]),'generic_source_label_on_ml':ml and basis=='source_reported_height','limitation':'Category describes input provenance, not necessarily latest derived roof; supplied height does not imply surveyed height.'})
assert before==sha(src)
report={'native_source':str(src),'native_sha256':before,'geometry_sha256':sha(R/'geometry.json'),'source_unchanged':True,'counts':dict(collections.Counter(q['source_category'] for q in rows)),'ml_generic_label_count':sum(q['generic_source_label_on_ml'] for q in rows),'rows':rows,'geometry_changed':False,'action':'Clarify ML origin when using baseline heights; do not overwrite refined geometry or infer measured accuracy from source_reported_height.'}
(R/'references/height_provenance_audit001.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['counts','ml_generic_label_count','source_unchanged']},indent=2))
