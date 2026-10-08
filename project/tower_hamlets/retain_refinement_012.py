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
export = root / 'exports/refinement-012'
run = scene / 'runs/canary_wharf_refinement_012'
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
status = """# Canary Wharf refinement012

Horizon Building main-roof massing corrected from27.447m to40.054m using coherent main plateau43.619m ODN minus local median DTM3.565m. Selected plateau checkerboard holdout83cells RMSE0.047m validates that plateau only, not survey accuracy or footprint edges. Higher northern structures remain unresolved. Exact mapped footprint extrusion remains an approximate envelope with plain facades.

Prior region refinements retained. Native master reopened and GLB independently reimported; overview and Horizon context render inspected. Whole-area detailed reconstruction remains incomplete. EA mixed2017–2020 survey versus2026 footprint, flat scene datum and variable terrain limit precision.
"""
(root/'docs/STATUS.md').write_text(status)
progress=read(root/'progress.json')
progress['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
for row in progress['buildings']:
    if row['id'] in ('overture-building-d046ecdd-0737-4072-aef9-44392df7cb27',):
        row.update(stage='integrated_numerical_checks_passed',evidence_reviewed='lidar_height_context_review',full_image_verification=False)
progress.update(stage='horizon_height_refinement_012_numerically_checked', current_retained_run=run.name, detailed_image_verified_buildings=0, visual_reviewed=False, delivered=False)
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
    z.write(scene/'analyze_horizon_lidar.py','analyze_horizon_lidar.py')
    z.write(scene/'render_horizon.py','render_horizon.py')
    for filename in ('acquire_lidar_subset.py','inspect_lidar_subset.py','analyze_cabot_lidar.py','plot_lidar_height_comparison.py','analyze_jemstock_lidar.py','analyze_blockwharf_lidar.py','analyze_crossrail_lidar.py','analyze_crossrail_lower_interface.py','prepare_crossrail_assembly.py'):
        z.write(scene/filename,filename)
manifest=read(scene/'runs/canary_wharf_refinement_011/manifest.json')
from collections import Counter
manifest['provenance']['parameters']['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
manifest.update(run_id=run.name,created_at=datetime.now(timezone.utc).isoformat())
for record in manifest['provenance']['inputs']:
    if record['id']=='authoring_geometry':record['sha256']=sha(root/'geometry.json')
for kind in ('dsm','dtm'):
    manifest['provenance']['inputs'].append({'id':'ea_lidar_'+kind+'_1m','sha256':sha(root/('references/ea_'+kind+'_1m.tif'))})
manifest['provenance']['inputs']=list({x['id']:x for x in manifest['provenance']['inputs']}.values())
manifest['provenance']['parameters']['representation']='horizon_height_correction_and_prior_refinements'
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'}
manifest['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(run.iterdir()) if p.name!='region.glb']
write(run/'manifest.json',manifest)
write(scene/'views/canary_wharf_refinement_012.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · roof refinement 012','time_alignment':'relative','runs':[run.name],'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]})
print(run)
