from pathlib import Path
import json,hashlib,struct,zipfile,shutil
import numpy as np
from shapely.geometry import Polygon,MultiPoint
from shapely.ops import unary_union
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/wintergarden-massing-001';r=json.loads((R/'references/wintergarden_massing_study.json').read_text());g=json.loads((R/'geometry.json').read_text());checks=[]
for q in r['objects']:
 old=next(b for b in g['buildings'] if b['id']==q['building_id']);p=Polygon(old['geometry'][0]['outer']);new=unary_union([Polygon([q['vertices'][i][:2] for i in face]) for face in q['roof_faces'] if all(abs(q['vertices'][i][2])<1e-9 for i in face)]);err=new.symmetric_difference(p).area;checks.append(dict(id=q['building_id'],rounded_authored_footprint_symdiff_m2=err));assert err<1e-5
blob=(O/'wintergarden.glb').read_bytes();n=struct.unpack_from('<I',blob,12)[0];glb=json.loads(blob[20:20+n]);nodes=[q for q in glb['nodes'] if 'mesh' in q];assert {q['extras']['building_id'] for q in nodes}==set(r['replace_ids']);assert all(q['extras']['aggregate_alias_id']==r['parent_id'] for q in nodes);assert len(glb['materials'])==1;assert glb['materials'][0].get('alphaMode','OPAQUE')=='OPAQUE';verify=json.loads((O/'verification.json').read_text());verify.update(footprint_checks=checks,owner_ids_verified=True,parent_aliases_verified=True,glb_materials=glb['materials'],visual_inspection=['overview.png','roof.png','rear.png','wintergarden_arch_fit.png'],visual_result='Continuous asymmetric arch; no clipped flat tail. Approximate curved surface discretized at0.25m. Neutral display material; glazing optical response and frames not modeled.');(O/'verification.json').write_text(json.dumps(verify,indent=2)+'\n')
for f in ['wintergarden_arch_fit.png','wintergarden_roof_review.png']:shutil.copy2(R/'references'/f,O/f)
report=dict(scope=r['scope'],replace_ids=r['replace_ids'],parent_id=r['parent_id'],fit=r['arch_fit'],side_and_center_metrics=r['zone_diagnostics'],parent_union_symdiff_m2=r['parent_union_symdiff_m2'],interfaces=r['interfaces'],datum_odn_m=r['datum_odn_m'],architectural_height_warning=r['architectural_height_warning'],limitations=r['limitations'],primary_sources=r['primary_sources'],verification=verify,hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [O/'wintergarden.blend',O/'wintergarden.glb',R/'references/wintergarden_massing_study.json']});(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(O/'report.md').write_text('''# East Wintergarden / The Pelligon estimated roof group

Three mapped parts retained independently with parent alias50661885-b2a8-40ca-a0ed-c5e23e253b61. Easternd8c9283a and western90846e8d are narrow side wings, not the central glazed barrel roof. Original6/18/6 m values are floor-count ×3 m assumptions. The three-part union differs from raw parent by0.078793 m²; child boundaries are preserved rather than silently forced to parent.

Estimated eastern/western roof16.35/16.38 m ODN becomes scene12.06999979/12.09999979. Central continuous ellipse fits the broad curved DSM support; crown~35.61 m ODN(~31.33scene). Shared datum4.28000021 is retained. Primary CWG2018 text says27m-high arch and glass exterior, while2024 CWG brochure identifies The Pelligon at43BankStreet. Architectural27 m is not treated as ODN or scene z; true public floor and base remain unresolved.

The initial clipped-ellipse diagnostic was rejected: it produced an unsupported flat tail. Final radius encloses the whole mapped section with strictly positive radicand, continuous through both ends. Fitted west/east edge predictions26.53/16.91 m ODN are uncertain. Boundary-strip median residuals−1.63/−3.40 m, RMSE5.27/5.94 m, so edge accuracy is not claimed. Full central724cells retain all returns:534within1m, median absolute residual0.071m, RMSE5.059m. The two side roofs have197/298 and196/298 within1m. No residual cells discarded; robust fitting uses the2m inset and all full-footprint errors remain reported.

NorthernTrust shared35.001641 m edge is exact and has zero mapped plan overlap; its57.82scene body is unchanged. Western neighbord2b07e0e shared35.001640 m and both internal part seams likewise have zero positive-area overlap. No extension crosses these boundaries.

Three closed editable massing components; native reopen, GLB reimport, all owner IDs, parent aliases, opaque neutral material and bounds verified. Actual overview/roof/rear and arch-fit plot inspected. No arbitrary glazing pane/frame count, entrances, internal structures or facade reconstruction. Neutral opaque material is a display proxy; primary text supports glass roof identity, but measured optics are unavailable. Closed components retain shared internal walls rather than claiming a boolean-union simulation volume.

Composite LiDAR acquisition vintage remains unresolved. Primary publication dates are not image capture dates. No new imagery acquired, no copyright photo derived, and no original imagery redistributed. Overture/OpenStreetMap ODbL and EA DSM/DTM OGL attribution retained in authoring JSON. Source scripts require retained geographic inputs whose hashes are recorded.
''')
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in [P/'review_wintergarden_roof.py',P/'fit_wintergarden_roof.py',P/'prepare_wintergarden_massing.py',P/'build_wintergarden_massing.py',P/'package_wintergarden_study.py']:z.write(f,'scripts/'+f.name)
 for f in (R/'references').glob('wintergarden*.json'):z.write(f,'references/'+f.name)
 for f in [O/'report.md',O/'report.json',O/'verification.json']:z.write(f,f.name)
print(json.dumps(report['hashes'],indent=2))
