from pathlib import Path
import json,hashlib,shutil,zipfile
from datetime import datetime,timezone
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';O=R/'exports/appearance-college-neighbor-001';D=S/'runs/canary_wharf_appearance_college_neighbor_001'
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=read(O/'verification.json');assert v['native_reopened'] and v['independent_glb_verified'];assert read(O/'visual_review.json')['inspected'];D.mkdir(exist_ok=False)
for p in O.iterdir():
 if p.is_file():shutil.copy2(p,D/p.name)
shutil.copy2(R/'references/ATTRIBUTION.md',D/'ATTRIBUTION.md')
with zipfile.ZipFile(D/'source_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for name in ['assemble_cc2_appearance_scene.py','retain_cc2_appearance_scene.py']:z.write(S/name,'project/tower_hamlets/'+name)
 for name in v['source_blends']:z.write(R/name,'project/tower_hamlets/input/canary_wharf_20261007/'+name)
 z.write(D/'ATTRIBUTION.md','ATTRIBUTION.md')
 for name in ['college_neighbor_envelope_study.json','college_neighbor_regions.json','college_neighbor_review.json','college_neighbor_opus_review.json','sources.json']:z.write(R/'references'/name,'project/tower_hamlets/input/canary_wharf_20261007/references/'+name)
 z.write(R/'exports/college-neighbor-envelope-study-001/sources.zip','college_neighbor_envelope_sources.zip')
m=read(S/'runs/canary_wharf_refinement_016/manifest.json');m.update(run_id=D.name,created_at=datetime.now(timezone.utc).isoformat());m['provenance']['parameters']={'representation':'Optional appearance study with estimated college neighbor three-level envelope; other buildings mostly baseline or partial roofs','not_as_built':True,'source_owner_ids':sorted(set(q['building_id'] for q in read(R/'references/college_neighbor_envelope_study.json')['objects']))};m['provenance']['inputs']=[{'id':name,'sha256':value} for name,value in v['source_blends'].items()];m['spatial']['bounds_m']={'min':v['bounds_enu_m'][0],'max':v['bounds_enu_m'][1]};types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'};m['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(D.iterdir()) if p.suffix in types];write(D/'manifest.json',m)
write(S/'views/canary_wharf_appearance_college_neighbor.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · estimated college neighbor three-level envelope','time_alignment':'relative','runs':[D.name],'layers':[{'run_id':D.name,'layer_id':'geometry','visible':True}]});print(D)
