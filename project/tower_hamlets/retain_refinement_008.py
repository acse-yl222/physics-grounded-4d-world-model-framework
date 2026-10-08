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
export = root / 'exports/refinement-008'
run = scene / 'runs/canary_wharf_refinement_008'
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
status = '''# Canary Wharf refinement 008

Retained run: runs/canary_wharf_refinement_008. Full selected inventory remains represented; detailed reconstruction remains incomplete.

Crossrail Place now uses a partial open assembly: observed LiDAR roof patches, an explicitly estimated central diagrid, and a provisional thin garden-level deck. Removed the previous 9 m central solid and 28 m enclosing residual massing, which contradicted the observed roof/dock distributions. Source parent and part identities remain separately represented. Parent owns only observed roof patches within its residual footprint, including partial ends and side strips; no artificial lower facade closes these areas.

Garden deck elevation17.1m ODN is inferred from paper SSL117.1 and Crossrail100m datum convention; it is not a direct survey measurement. Scene deck top13.1209m subtracts the same local median DTM as the roof. Its0.30m thickness and horizontal extent are provisional. Lower facades, supports, end-frame continuation, garden landscaping, connections and true ETFE panel/opening boundaries remain unresolved. Candidate grid layouts and timber sections are estimates. Missing measured patches may include transparent materials or poor returns, not just physical openings.

Closed deck geometry and individual members are distinct from intentional open roof patches. Native master reopened, GLB independently imported, overview and full-context roof views inspected. LiDAR source dates differ from2026 footprint; no current-year survey accuracy claimed. Prior Cabot, DLR, Poplar and stepped-roof refinements retained. No Google-derived geometry or photographic textures.
'''
(root/'docs/STATUS.md').write_text(status)
progress=read(root/'progress.json')
progress['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
for row in progress['buildings']:
    if row['id'] in ('overture-building-7d04c4cc-c183-4597-bb98-063679b2ec63','overture-part-c9f4e448-eff2-39ad-ac25-e7f6cf708826'):
        row.update(stage='integrated_numerical_checks_passed',evidence_reviewed='lidar_and_primary_text_partial_assembly',full_image_verification=False)
progress.update(stage='crossrail_partial_refinement_008_numerically_checked', current_retained_run=run.name, detailed_image_verified_buildings=0, visual_reviewed=False, delivered=False)
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
    z.write(scene/'render_crossrail_assembly.py','render_crossrail_assembly.py')
    for filename in ('acquire_lidar_subset.py','inspect_lidar_subset.py','analyze_cabot_lidar.py','plot_lidar_height_comparison.py','analyze_jemstock_lidar.py','analyze_blockwharf_lidar.py','analyze_crossrail_lidar.py','analyze_crossrail_lower_interface.py','prepare_crossrail_assembly.py'):
        z.write(scene/filename,filename)
manifest=read(scene/'runs/canary_wharf_refinement_007/manifest.json')
from collections import Counter
manifest['provenance']['parameters']['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
manifest.update(run_id=run.name,created_at=datetime.now(timezone.utc).isoformat())
for record in manifest['provenance']['inputs']:
    if record['id']=='authoring_geometry':record['sha256']=sha(root/'geometry.json')
for kind in ('dsm','dtm'):
    manifest['provenance']['inputs'].append({'id':'ea_lidar_'+kind+'_1m','sha256':sha(root/('references/ea_'+kind+'_1m.tif'))})
manifest['provenance']['inputs']=list({x['id']:x for x in manifest['provenance']['inputs']}.values())
manifest['provenance']['parameters']['representation']='partial_crossrail_assembly_and_prior_refinements'
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'}
manifest['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(run.iterdir()) if p.name!='region.glb']
write(run/'manifest.json',manifest)
write(scene/'views/canary_wharf_refinement_008.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · roof refinement 008','time_alignment':'relative','runs':[run.name],'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]})
print(run)
