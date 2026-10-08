from pathlib import Path
import json,hashlib,shutil,zipfile
from shapely.geometry import Polygon
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';P=R.parent.parent;O=R/'exports/water8-massing-001';g=json.loads((R/'geometry.json').read_text());r=json.loads((R/'references/water8_study.json').read_text());f=next(f for f in g['buildings'] if f['id']==r['building_id']);p=Polygon(f['geometry'][0]['outer']);neighbors=[]
for q in g['buildings']:
 if q['id']==f['id'] or q.get('kind')=='site':continue
 for shape in q['geometry']:
  pp=Polygon(shape['outer'],shape.get('holes',[]))
  if p.distance(pp)<.01:
   shared=p.boundary.intersection(pp.boundary);neighbors.append({'id':q['id'],'name':q.get('name'),'overlap_area_m2':p.intersection(pp).area,'shared_length_m':shared.length,'shared_geometry_wkt':shared.wkt,'neighbor_source_height_m':q.get('height_m'),'note':'No facade additions; adjacent owner untouched. Native neighbor height not independently inferred from sourceheight.'})
r['neighbor_interfaces']=neighbors;r['native_audit']='water8_native.json';r['source_native_sha256']=json.loads((R/'references/water8_native.json').read_text())['sha256'];(R/'references/water8_study.json').write_text(json.dumps(r,indent=2))
(O/'visual_review.json').write_text(json.dumps({'actual_inspected':['overview.png','front-after.png','roof-after.png'],'finding':'Coherent whole-footprint central body and two lower ends; no added facades or small rooftop structures. Broad clean silhouette remains descriptive rather than surveyed.','limitations':r['limitations']},indent=2))
S=O/'source_snapshot';S.mkdir(exist_ok=True)
for pp in list(P.glob('*water8*.py'))+list((R/'references').glob('water8*'))+[O/'verification.json',O/'visual_review.json']:
 if pp.is_file():shutil.copy2(pp,S/pp.name)
shutil.copy2(R/'geometry.json',S/'geometry.json');shutil.copy2(Path('cache/tower_hamlets/water8_roof.npz'),S/'water8_roof.npz')
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for pp in sorted(S.iterdir()):z.write(pp,pp.relative_to(O))
print(neighbors);print(hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest())
