from pathlib import Path
import json,hashlib,zipfile
P=Path('project/tower_hamlets');R=P/'input/canary_wharf_20261007'
for suffix in ['002','003']:
 O=R/f'exports/kpmg15-massing-{suffix}';v=json.loads((O/'verification.json').read_text());v['limitations']='Independent comparison only; central lowreturns coherent but actual roof/glazingreturn mechanism andpreciseedges unverified.003slopedtransition1.1m estimated.002flatcontrol doesnotassertfeatureabsent. SharedFitchinterface remains unresolved; no regionalintegration.';(O/'verification.json').write_text(json.dumps(v,indent=2));(O/'visual_review.json').write_text(json.dumps({'status':'Independent comparison HOLD','actual_inspected':['003/central-control-001.png','003/central-control-003.png','references/kpmg15_central_audit.png'],'assessment':'003retainslowplateau withslopedtransitions, visually still pronouncedrecess; not claimedlessdeep orvalidatedarchitecture.001verticalwalls unsupportedpreciseedges.002smoothcontrol discards coherent lowgeometry andisnotpreferredonfit.','metrics':'references/kpmg15_mesh_comparison003.json','boundary_sensitivity':'references/kpmg15_central_audit.json','global_edits':False},indent=2))
 files=list(P.glob('kpmg15*.py'))+list((R/'references').glob('kpmg15*.json'))+list((R/'references').glob('kpmg15*.png'))+[P/'prepare_water8_study.py',R/'geometry.json'];(O/'source_snapshot.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2))
 with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in files:z.write(f,str(f))
  for n in ['verification.json','visual_review.json','source_snapshot.json']:z.write(O/n,n)
 (O/'archive_sha256.json').write_text(json.dumps({'sources.zip':hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest()},indent=2))
 print(suffix,v['total_triangles'])
