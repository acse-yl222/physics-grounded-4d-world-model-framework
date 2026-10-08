from pathlib import Path
import json,shutil,zipfile,hashlib
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/west_pyramid-massing-002';r=json.loads((R/'references/west_pyramid_study002.json').read_text());r['limitations']=[x for x in r['limitations'] if not x.startswith('Fixed plan-centred')];r['limitations'].append('Asymmetric apex shifts west/south by1.153/0.924m, spatial holdout supports direction but1mDSM cannot establish exactnode. Original fixedcentre model retained001.');(R/'references/west_pyramid_study002.json').write_text(json.dumps(r,indent=2))
(O/'visual_review.json').write_text(json.dumps({'actual_inspected':['overview.png','context-review.png'],'finding':'Twoowners formonecontinuouspyramidalroof; adjacentunselectedhouses remainflat. No visiblefacadeorentrance additions. Offsetapex preservescoherentroof.','limitations':r['limitations'],'native_baseline_confirmed':'two28vertex8face flat6m meshes; earlier targetedbuildingmodules search foundnoexistingcandidate','neighbors':'No BVHtriangle intersections withretainednearbybuildings; nearestsample6.03686m. Surface tests/sparse samples notexactvolumeproof.'},indent=2));S=O/'source_snapshot';S.mkdir(exist_ok=True)
for p in list(P.glob('*west_pyramid*.py'))+list((R/'references').glob('west_pyramid*'))+[R/'geometry.json',O/'verification.json',O/'context_mesh_check.json',O/'visual_review.json']:
 if p.is_file():shutil.copy2(p,S/p.name)
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(S.iterdir()):z.write(p,p.relative_to(O))
print(hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest())
