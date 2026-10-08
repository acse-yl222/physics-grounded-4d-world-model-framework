from pathlib import Path
import json,shutil,zipfile,hashlib
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/aace-south-roof-001';r=json.loads((R/'references/aace_south_roof_study.json').read_text());v=json.loads((O/'verification.json').read_text());v['limitations']='Roof-only4closedthinplane shells withsharedsectorseams; no walls/base. Notfullownerreplacement. Capturevintageunknown. Nozclamp; allverticesabovebase. Testsverifygeometry notrooftruth.';(O/'verification.json').write_text(json.dumps(v,indent=2));(O/'visual_review.json').write_text(json.dumps({'actual_inspected':['overview.png'],'finding':'Visible12.097mcontinuousridge withasymmetric hipends; nofourplanesinglepeak. No walls added. Allvertices4.96736..10.55759m above scenezero.','recommendation':'Standalone roof-only research, no owner removal/integration interface. Exactnorthernhip termination ambiguous becauseopen-northhip performsnearlyequally.','limitations':r['limitations']},indent=2));S=O/'source_snapshot';S.mkdir(exist_ok=True)
for p in list(P.glob('aace*.py'))+list((R/'references').glob('aace*'))+[P/'review_aace_roof.py',R/'geometry.json',O/'verification.json',O/'visual_review.json']:
 if p.is_file():shutil.copy2(p,S/p.name)
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(S.iterdir()):z.write(p,p.relative_to(O))
print(v['total_triangles']);print(hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest())
