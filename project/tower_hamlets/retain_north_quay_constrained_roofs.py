"""Register inspected measured roofs as an optional protocol layer, not final buildings."""
from pathlib import Path
import json,hashlib,shutil,subprocess,zipfile
from datetime import datetime,timezone
s=Path(__file__).resolve().parent;r=s/'input/canary_wharf_20261007';o=r/'exports/north-quay-constrained-roofs-001';dest=s/'runs/canary_wharf_north_quay_constrained_roofs_001'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
v=read(o/'verification.json');assert v['master_reopened'] and v['independent_glb_import_verified'];assert read(o/'visual_review.json')['render_inspected'];dest.mkdir(exist_ok=False)
for p in o.iterdir():
 if p.is_file():shutil.copy2(p,dest/p.name)
with zipfile.ZipFile(dest/'source_snapshot.zip','a',compression=zipfile.ZIP_DEFLATED) as z:z.write(Path(__file__),Path(__file__).name)
m=read(s/'runs/canary_wharf_transport_inspection_001/manifest.json');m.update(run_id=dest.name,created_at=datetime.now(timezone.utc).isoformat());m['provenance']['code_revision']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();m['provenance']['parameters']={'representation':'fitted_roofs_with_estimated_boundary_transitions','architectural_enclosures':False,'owner_count':9,'vertical_conversion':'scene_z = DSM_ODN -4.28000020980835m retained museum local reference','limitations':'Historical native 1m raster with fitted interior roof patches. Boundary triangles adjusted to match raw heights; transitions are estimates, not additional measurements. Unknown gaps retained, no facades or terrain.'};m['provenance']['inputs']=[{'id':k,'sha256':val} for k,val in v['source_hashes'].items()];m['spatial']['bounds_m']={'min':v['bounds_enu_m'][0],'max':v['bounds_enu_m'][1]};m['layers'][0].update(id='observed_roofs',asset='north-quay-roof.glb');types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'};m['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else (p.stem+p.suffix.replace('.','_')).replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(dest.iterdir()) if p.suffix in types];write(dest/'manifest.json',m);write(s/'views/canary_wharf_north_quay_constrained_roofs.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'North Quay · constrained roof candidates','time_alignment':'relative','runs':[dest.name],'layers':[{'run_id':dest.name,'layer_id':'observed_roofs','visible':True}]});print(dest)
