from pathlib import Path
import json,hashlib,zipfile
P=Path('project/tower_hamlets');R=P/'input/canary_wharf_20261007';O=R/'exports/mcgraw-massing-001'
r=json.loads((R/'references/mcgraw_study.json').read_text());(O/'visual_review.json').write_text(json.dumps({'actual_inspected':['overview.png','detail.png','context-review.png','references/mcgraw_structure.png','references/mcgraw_aligned.png'],'assessment':'Coherent broad setback envelope, exact mapped outline retained. Central structured low returns are flattened in this control and remain unresolved. HOLD as coarse comparison candidate; not complete roof reconstruction.','geometry_status':'3 closed zone solids,156 triangles, independentGLB IDs/bounds/materials and closure passed;27 neighborpairs zero surface intersections.','limitations':r['limitations'],'whole_owner_errors_reference':'references/mcgraw_central_review.json'},indent=2))
files=list(P.glob('mcgraw_*.py'))+list((R/'references').glob('mcgraw*.json'))+list((R/'references').glob('mcgraw*.png'))+[P/'prepare_water8_study.py',R/'geometry.json']
manifest={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files};(O/'source_snapshot.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,str(f))
 for name in ['source_snapshot.json','verification.json','context_mesh_check.json','visual_review.json']:z.write(O/name,name)
(O/'archive_sha256.json').write_text(json.dumps({'sources.zip':hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest()},indent=2))
print((O/'sources.zip').resolve())
