from pathlib import Path
import json,hashlib,shutil,zipfile
from datetime import datetime,timezone
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';O=R/'exports/appearance-munich-001';D=S/'runs/canary_wharf_appearance_munich_hip_001'
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=read(O/'verification.json');assert v['native_reopened'] and v['independent_glb_verified'];assert read(O/'visual_review.json')['inspected'];D.mkdir(exist_ok=False)
for p in O.iterdir():
 if p.is_file():shutil.copy2(p,D/p.name)
shutil.copy2(R/'references/ATTRIBUTION.md',D/'ATTRIBUTION.md')
with zipfile.ZipFile(D/'source_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for name in ['assemble_munich_appearance_scene.py','retain_munich_hip_appearance_scene.py']:z.write(S/name,'project/tower_hamlets/'+name)
 for name in v['source_blends']:z.write(R/name,'project/tower_hamlets/input/canary_wharf_20261007/'+name)
 z.write(D/'ATTRIBUTION.md','ATTRIBUTION.md')
m=read(S/'runs/canary_wharf_refinement_016/manifest.json');m.update(run_id=D.name,created_at=datetime.now(timezone.utc).isoformat());m['provenance']['parameters']={'representation':'Optional appearance study with estimated Munich hip exterior; other buildings mostly baseline or partial roofs','not_as_built':True,'source_owner_ids':['overture-building-118734b4-49b7-4a0b-80f8-4f7b33801433']};m['provenance']['inputs']=[{'id':name,'sha256':value} for name,value in v['source_blends'].items()];m['spatial']['bounds_m']={'min':v['bounds_enu_m'][0],'max':v['bounds_enu_m'][1]};types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'};m['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(D.iterdir()) if p.suffix in types];write(D/'manifest.json',m)
write(S/'views/canary_wharf_appearance_munich_hip.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · estimated Munich hip exterior','time_alignment':'relative','runs':[D.name],'layers':[{'run_id':D.name,'layer_id':'geometry','visible':True}]});print(D)
