"""Retain combined Quay1 and One Canada estimated exterior improvements."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,shutil,zipfile
S=Path(__file__).resolve().parent;ROOT=S.parent.parent;R=S/'input/canary_wharf_20261007';O=R/'exports/appearance-exterior-completion-003';D=S/'runs/canary_wharf_appearance_exterior_completion_003'
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
v=read(O/'verification.json');c=read(O/'assembly-config.json');review=read(O/'visual-review.json')
assert v['native_reopened'] and v['independent_glb_verified'] and v['source_unchanged'] and review['inspected']
assert sha(O/'region.blend')==v['native_sha256'] and sha(O/'region.glb')==v['glb_sha256']
assert sha(ROOT/c['source'])==c['source_sha256']
for item in c['components']:assert sha(ROOT/item['native'])==item['sha256']
D.mkdir(exist_ok=False)
for p in O.iterdir():
 if p.is_file():shutil.copy2(p,D/p.name)
shutil.copy2(R/'references/ATTRIBUTION.md',D/'ATTRIBUTION.md')
with zipfile.ZipFile(D/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED)as z:
 seen=set()
 def add(p,arc):
  if arc not in seen:z.write(p,arc);seen.add(arc)
 for name in ['assemble_accelerated_repairs002.py','retain_exterior_completion003.py']:
  add(S/name,'project/tower_hamlets/'+name)
 add(ROOT/c['source'],c['source']);add(O/'assembly-config.json','assembly-config.json')
 for item in c['components']:
  add(ROOT/item['native'],item['native'])
  for name in item['source_files']:add(ROOT/name,name)
 for folder in ['quay1_lower_repair003_independent','one_canada_south_entry_independent003']:
  for p in sorted((R/'exports'/folder).iterdir()):
   if p.is_file()and p.suffix in ['.py','.json','.md']:add(p,'independent-review/'+folder+'/'+p.name)
 for p in [R/'geometry.json',R/'references/sources.json',R/'exports/quay1_lower_repair003/interface_audit.json',R/'exports/quay1_lower_repair003/native_interfaces.json']:
  add(p,str(p.relative_to(ROOT)))
 add(D/'ATTRIBUTION.md','ATTRIBUTION.md')
m=read(S/'runs/canary_wharf_appearance_accelerated_repairs_002/manifest.json');m.update(run_id=D.name,created_at=datetime.now(timezone.utc).isoformat());m['provenance']['parameters']={'representation':'Grounded Quay1 lower exterior plus One Canada exposed lobby, estimated south entrance and estimated roof-face courses; all source-backed interfaces preserved','not_as_built':True,'source_owner_ids':sorted({owner for item in c['components'] for owner in item['owners']}),'limitations':review['limitations']};m['provenance']['inputs']=[{'id':c['source'],'sha256':c['source_sha256']}]+[{'id':x['native'],'sha256':x['sha256']}for x in c['components']];m['spatial']['bounds_m']={'min':v['bounds_enu_m'][0],'max':v['bounds_enu_m'][1]}
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown','.py':'text/x-python'}
m['artifacts']=[{'id':'source_snapshot'if p.name=='source_snapshot.zip'else p.name.replace('-','_').replace('.','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]}for p in sorted(D.iterdir())if p.suffix in types];write(D/'manifest.json',m)
write(S/'views/canary_wharf_appearance_exterior_completion003.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · Quay1 and One Canada exterior details','time_alignment':'relative','runs':[D.name],'layers':[{'run_id':D.name,'layer_id':'geometry','visible':True}],'camera':{'position':[-170,360,205],'target':[0,65,40]}})
print(D)
