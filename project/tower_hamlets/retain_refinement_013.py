"""Retain inspected North Quay roof integration; preserve prior run and status history."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,zipfile,subprocess
from collections import Counter
s=Path(__file__).resolve().parent;repo=s.parents[1];r=s/'input/canary_wharf_20261007';o=r/'exports/refinement-013';dest=s/'runs/canary_wharf_refinement_013'
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=read(o/'verification.json');assert v['numerical_export_verified'];assert read(o/'visual_review.json')['targeted_views_inspected'];dest.mkdir(exist_ok=False)
for p in o.iterdir():
 if p.suffix in ['.json','.png','.glb'] or p.name=='region.blend':shutil.copy2(p,dest/p.name)
with (r/'docs/STATUS.md').open('a') as f:f.write('\nRefinement013 integrates North Quay nine-owner partial roof assembly into full region, replacing generic solids for those IDs. Facades/supports remain explicitly absent; old regional012 preserved.440inventory IDs verified; native master and independentGLB passed; actual overview and North Quay context inspected. Whole-area detailed reconstruction incomplete.\n')
shutil.copy2(r/'docs/STATUS.md',dest/'STATUS.md');shutil.copy2(r/'references/ATTRIBUTION.md',dest/'ATTRIBUTION.md')
progress=read(r/'progress.json');ids={i for i,m in read(r/'src/modules.json').items() if m=='north_quay_partial_roofs'}
for row in progress['buildings']:
 if row['id'] in ids:row.update(stage='integrated_numerical_checks_passed',evidence_reviewed='conditional_lidar_roofs',full_image_verification=False,coverage='partial roof only; facades absent')
progress.update(current_retained_run=dest.name,module_counts=dict(Counter(read(r/'src/modules.json').values())),stage='north_quay_partial_roofs_integrated_013',delivered=False,visual_reviewed=False);write(r/'progress.json',progress)
with zipfile.ZipFile(dest/'source_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in r.rglob('*'):
  if p.is_file() and not any(t in p.relative_to(r).parts for t in ['exports','renders','__pycache__']):z.write(p,'authoring/'+str(p.relative_to(r)))
 for p in (repo/'src/urban_geometry/region_authoring').glob('*.py'):z.write(p,'repository-src/'+p.name)
 for p in s.glob('*.py'):
  if any(t in p.name for t in ['north_quay','ledger','munich','pizza','refinement_013']):z.write(p,'scene-scripts/'+p.name)
m=read(s/'runs/canary_wharf_refinement_012/manifest.json');m.update(run_id=dest.name,created_at=datetime.now(timezone.utc).isoformat());m['provenance']['parameters']['representation']='North Quay partial roof integration; nine generic solids replaced by evidence-supported open roof surfaces; facades absent';m['provenance']['parameters']['module_counts']=dict(Counter(read(r/'src/modules.json').values()));m['provenance']['code_revision']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
for item in m['provenance']['inputs']:
 if item['id']=='authoring_geometry':item['sha256']=sha(r/'geometry.json')
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'};m['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(dest.iterdir()) if p.name!='region.glb'];write(dest/'manifest.json',m)
write(s/'views/canary_wharf_refinement_013.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · North Quay partial roofs 013','time_alignment':'relative','runs':[dest.name],'layers':[{'run_id':dest.name,'layer_id':'geometry','visible':True}]});print(dest)
