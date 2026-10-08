from pathlib import Path
import json,hashlib,zipfile
P=Path('project/tower_hamlets');R=P/'input/canary_wharf_20261007';O=R/'exports/mcgraw-massing-003'
(O/'visual_review.json').write_text(json.dumps({'actual_inspected':['detail.png','context-review.png','references/mcgraw_low_bands.png'],'assessment':'Independent continuous-fold comparison ready for coordinator review; two modeled valleys smoother transversely than002 hardsteps. Still abruptestimated longitudinal ends. No complete roof claim.','evidence':'references/mcgraw_mesh_comparison.json','limitations':['Source DSM native1m; lowbands identified from same raster, conditional holdout does not independently validate architecture.','Southernlowband and centralotherreturns unresolved. Actual raster vintage unknown.','Common sceneODNminus4.28000021; internal coincidentwalls retained in separate closed meshes.','No photo-derived identity, facade or equipment assertion.']},indent=2))
files=list(P.glob('mcgraw*.py'))+list((R/'references').glob('mcgraw*.json'))+list((R/'references').glob('mcgraw*.png'))+[P/'prepare_water8_study.py',R/'geometry.json'];(O/'source_snapshot.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2))
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,str(f))
 for n in ['verification.json','context_mesh_check.json','visual_review.json','source_snapshot.json']:z.write(O/n,n)
(O/'archive_sha256.json').write_text(json.dumps({'sources.zip':hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest()},indent=2))
