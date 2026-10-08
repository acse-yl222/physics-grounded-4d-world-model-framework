"""Retain the inspected longitudinal canopy refinement with reproducible sources."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import zipfile
from collections import Counter

scene = Path(__file__).resolve().parent
repo = scene.parents[1]
root = scene / 'input/canary_wharf_20261007'
export = root / 'exports/refinement-010'
run = scene / 'runs/canary_wharf_refinement_010'
def read(p): return json.loads(p.read_text())
def write(p, data): p.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
verification = read(export/'verification.json')
assert verification['numerical_export_verified']
assert read(export/'visual_review.json')['targeted_views_inspected']
run.mkdir(exist_ok=False)
for p in export.iterdir():
    if p.suffix in ('.png', '.glb', '.json') or p.name == 'region.blend':
        shutil.copy2(p, run/p.name)
status = """# Canary Wharf refinement010

Novotel height massing corrected from3.829m to120.745m using median upper returns above115m ODN minus local median DTM. This is an approximate envelope over the exact mapped footprint, not reconstructed facade or roof topology. Strong stripe-like DSM dropouts are not interpreted as openings. Operator Accor independently reports127m, confirming tall scale but leaving vertical-reference and exact architectural-top differences unresolved.

Prior region refinements retained. Native master reopened and GLB independently reimported; overview and Novotel context render inspected. Whole-area detailed reconstruction remains incomplete. EA mixed2017–2020 survey versus2026 footprint, flat scene datum and variable terrain limit precision.
"""
(root/'docs/STATUS.md').write_text(status)
progress=read(root/'progress.json')
progress['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
for row in progress['buildings']:
    if row['id'] in ('overture-building-55529b60-0de4-477d-957f-8278f55a225f',):
        row.update(stage='integrated_numerical_checks_passed',evidence_reviewed='lidar_height_context_review',full_image_verification=False)
progress.update(stage='novotel_height_refinement_010_numerically_checked', current_retained_run=run.name, detailed_image_verified_buildings=0, visual_reviewed=False, delivered=False)
write(root/'progress.json',progress)
shutil.copy2(root/'docs/STATUS.md',run/'STATUS.md')
shutil.copy2(root/'references/ATTRIBUTION.md',run/'ATTRIBUTION.md')
with zipfile.ZipFile(run/'source_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob('*'):
        if p.is_file() and not any(v in p.relative_to(root).parts for v in ('exports','renders','__pycache__')):
            z.write(p,'authoring/'+str(p.relative_to(root)))
    for p in (repo/'src/urban_geometry/region_authoring').glob('*.py'):
        z.write(p,'repository-src/'+p.name)
    z.write(Path(__file__),Path(__file__).name)
    z.write(scene/'analyze_novotel_lidar.py','analyze_novotel_lidar.py')
    z.write(scene/'render_novotel.py','render_novotel.py')
    for filename in ('acquire_lidar_subset.py','inspect_lidar_subset.py','analyze_cabot_lidar.py','plot_lidar_height_comparison.py','analyze_jemstock_lidar.py','analyze_blockwharf_lidar.py','analyze_crossrail_lidar.py','analyze_crossrail_lower_interface.py','prepare_crossrail_assembly.py'):
        z.write(scene/filename,filename)
manifest=read(scene/'runs/canary_wharf_refinement_009/manifest.json')
from collections import Counter
manifest['provenance']['parameters']['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
manifest.update(run_id=run.name,created_at=datetime.now(timezone.utc).isoformat())
for record in manifest['provenance']['inputs']:
    if record['id']=='authoring_geometry':record['sha256']=sha(root/'geometry.json')
for kind in ('dsm','dtm'):
    manifest['provenance']['inputs'].append({'id':'ea_lidar_'+kind+'_1m','sha256':sha(root/('references/ea_'+kind+'_1m.tif'))})
manifest['provenance']['inputs']=list({x['id']:x for x in manifest['provenance']['inputs']}.values())
manifest['provenance']['parameters']['representation']='novotel_height_correction_and_prior_refinements'
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'}
manifest['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(run.iterdir()) if p.name!='region.glb']
write(run/'manifest.json',manifest)
write(scene/'views/canary_wharf_refinement_010.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · roof refinement 010','time_alignment':'relative','runs':[run.name],'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]})
print(run)
