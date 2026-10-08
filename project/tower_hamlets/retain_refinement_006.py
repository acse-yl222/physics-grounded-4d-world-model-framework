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
export = root / 'exports/refinement-006'
run = scene / 'runs/canary_wharf_refinement_006'
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
status = '''# Canary Wharf refinement 006

Retained run: runs/canary_wharf_refinement_006. Entire prior area inventory remains represented. Detailed reconstruction is incomplete.

Cabot Place dome now follows a robust shifted paraboloid fitted to paired Environment Agency 1 m LiDAR evidence. This replaces the unsupported 9 m flat cylinder with a broad dome apex at scene z=34.679364 m. Fitted apex elevation is 42.019364 m ODN; local DTM median 7.34 m is subtracted as an explicit relative convention, not a global datum change. Exact mapped footprint is preserved. Edge lower clipping at 31.8 m ODN is estimated from an observed outer plateau and is not a surveyed eave. Source roof_height=27 m remains recorded but is not used as a dimensional constraint.

Fit used 546 interior raster cells, including sparse low glass returns with robust loss. Alternating spatial-block holdout has 276 samples: p95 absolute residual 1.355 m, RMSE 4.977 m. These residuals do not establish geographic or current-year survey accuracy. The broad curve is supported; glazing subdivisions and framing are unresolved. Facade and closed solid below the dome remain opaque massing with illustrative materials. Surrounding podium height remains its prior source value.

Closed-edge winding, positive volume, original projected area and height checks pass. Master reopened, GLB independently imported, current overview and three Cabot views inspected. Full facades/entrances remain unverified. Previous DLR and Poplar refinements retained. LiDAR source vintage mixes 2017–2018 and 2020 survey extents; current footprint correspondence and per-pixel date attribution remain uncertain. No Google-derived geometry.
'''
(root/'docs/STATUS.md').write_text(status)
progress=read(root/'progress.json')
progress['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
for row in progress['buildings']:
    if row['id']=='overture-part-a3461c5d-098b-382d-b1d8-a6fbe5e6db1d':
        row.update(stage='integrated_numerical_checks_passed',evidence_reviewed='lidar_roof_fit',full_image_verification=False)
progress.update(stage='cabot_lidar_refinement_006_numerically_checked', current_retained_run=run.name, detailed_image_verified_buildings=0, visual_reviewed=False, delivered=False)
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
    z.write(scene/'render_cabot_review.py','render_cabot_review.py')
    for filename in ('acquire_lidar_subset.py','inspect_lidar_subset.py','analyze_cabot_lidar.py','plot_lidar_height_comparison.py'):
        z.write(scene/filename,filename)
manifest=read(scene/'runs/canary_wharf_refinement_005/manifest.json')
from collections import Counter
manifest['provenance']['parameters']['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
manifest.update(run_id=run.name,created_at=datetime.now(timezone.utc).isoformat())
for record in manifest['provenance']['inputs']:
    if record['id']=='authoring_geometry':record['sha256']=sha(root/'geometry.json')
for kind in ('dsm','dtm'):
    manifest['provenance']['inputs'].append({'id':'ea_lidar_'+kind+'_1m','sha256':sha(root/('references/ea_'+kind+'_1m.tif'))})
manifest['provenance']['parameters']['representation']='partial_canopy_and_lidar_fitted_cabot_dome'
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'}
manifest['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(run.iterdir()) if p.name!='region.glb']
write(run/'manifest.json',manifest)
write(scene/'views/canary_wharf_refinement_006.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · roof refinement 006','time_alignment':'relative','runs':[run.name],'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]})
print(run)
