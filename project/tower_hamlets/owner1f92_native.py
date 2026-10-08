from pathlib import Path
import bpy,json,hashlib
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';src=P/'runs/canary_wharf_appearance_norwood_001/region.blend';bid='overture-building-1f9270f4-be48-427a-8b63-886838c77ec9';h=hashlib.sha256(src.read_bytes()).hexdigest()
with bpy.data.libraries.load(str(src),link=False) as (a,b):b.objects=[n for n in a.objects if n==bid]
rows=[]
for o in b.objects:
 vs=[list(o.matrix_world@v.co) for v in o.data.vertices];rows.append({'name':o.name,'properties':{k:str(o[k]) for k in o.keys()},'vertices':vs,'faces':[list(p.vertices) for p in o.data.polygons],'materials':[m.name for m in o.data.materials]})
assert len(rows)==1
report={'source':str(src),'source_sha256':h,'source_unchanged':h==hashlib.sha256(src.read_bytes()).hexdigest(),'objects':rows}
(R/'references/owner1f92_native.json').write_text(json.dumps(report,indent=2));print('Source owner z range:',min(v[2] for v in vs),max(v[2] for v in vs))
