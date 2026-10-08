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
export = root / 'exports/refinement-007'
run = scene / 'runs/canary_wharf_refinement_007'
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
status = '''# Canary Wharf refinement 007

Retained run: runs/canary_wharf_refinement_007. Full selected inventory remains represented; detailed reconstruction is incomplete.

Jemstock 2 and Block Wharf no longer use unsupported uniform 9 m massing. Each now has a two-level roof derived from actual Environment Agency LiDAR plateau evidence, preserving exact mapped exterior footprint. Lower and upper roof elevations are converted from ODN using each footprint's recorded median DTM; scene ground remains unsurveyed z=0. Upper-roof breaklines are coarse estimates from 1 m grids, not surveyed architectural edges. Roof block purpose, facade windows and entrances remain unknown. Source mixed survey vintage is not a current-year record.

Per-building analysis scripts, reviewed plots and numerical reports are in source_snapshot.zip. Their checked meshes preserve source plan area, have closed opposite-wound edges, positive volume and finite heights. Master reopened and GLB independently imported. Current overview and individual full-context views inspected. Prior Cabot dome, DLR canopy and Poplar roofs retained. No Google-derived geometry, no photographic textures. Full area facade and architectural detail remains incomplete.
'''
(root/'docs/STATUS.md').write_text(status)
progress=read(root/'progress.json')
progress['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
for row in progress['buildings']:
    if row['id'] in ('overture-building-2e1384be-3161-4326-a35d-d0ba1327dc7c','overture-building-112b6cf0-b1a9-4c9c-9614-f432af4d0902'):
        row.update(stage='integrated_numerical_checks_passed',evidence_reviewed='lidar_roof_plateaus',full_image_verification=False)
progress.update(stage='stepped_roofs_refinement_007_numerically_checked', current_retained_run=run.name, detailed_image_verified_buildings=0, visual_reviewed=False, delivered=False)
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
    z.write(scene/'render_height_review.py','render_height_review.py')
    for filename in ('acquire_lidar_subset.py','inspect_lidar_subset.py','analyze_cabot_lidar.py','plot_lidar_height_comparison.py','analyze_jemstock_lidar.py','analyze_blockwharf_lidar.py'):
        z.write(scene/filename,filename)
manifest=read(scene/'runs/canary_wharf_refinement_006/manifest.json')
from collections import Counter
manifest['provenance']['parameters']['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
manifest.update(run_id=run.name,created_at=datetime.now(timezone.utc).isoformat())
for record in manifest['provenance']['inputs']:
    if record['id']=='authoring_geometry':record['sha256']=sha(root/'geometry.json')
for kind in ('dsm','dtm'):
    manifest['provenance']['inputs'].append({'id':'ea_lidar_'+kind+'_1m','sha256':sha(root/('references/ea_'+kind+'_1m.tif'))})
manifest['provenance']['inputs']=list({x['id']:x for x in manifest['provenance']['inputs']}.values())
manifest['provenance']['parameters']['representation']='partial_canopy_dome_and_lidar_stepped_roofs'
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'}
manifest['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(run.iterdir()) if p.name!='region.glb']
write(run/'manifest.json',manifest)
write(scene/'views/canary_wharf_refinement_007.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · roof refinement 007','time_alignment':'relative','runs':[run.name],'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]})
print(run)
