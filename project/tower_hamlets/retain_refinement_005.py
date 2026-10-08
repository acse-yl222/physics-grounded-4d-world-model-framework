"""Retain the inspected longitudinal canopy refinement with reproducible sources."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import zipfile

scene = Path(__file__).resolve().parent
repo = scene.parents[1]
root = scene / 'input/canary_wharf_20261007'
export = root / 'exports/refinement-005'
run = scene / 'runs/canary_wharf_refinement_005'
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
status = '''# Canary Wharf refinement 005

Retained run: runs/canary_wharf_refinement_005. Entire prior area inventory remains represented. Detailed reconstruction is incomplete.

Poplar Bowls Club House now uses its mapped gabled roof type, replacing a flat top. Its exact 12-corner concave outline, source total height 5.447809 m, brown colour and wood facade assignment remain. A single longitudinal ridge and 1.25 m roof rise are explicitly estimated; topology and pitch are not image-verified. Microsoft ML source height is not a survey measurement. The new closed solid passes edge winding, positive volume, projected area, original corner and height-bound checks. See references/poplar_bowls_report.json and executable building module in source_snapshot.zip.

Master reopened and GLB independently imported. Current overview and three full-context Poplar roof views were inspected. These are model consistency checks, not complete facade/entrance verification. Prior DLR geometry remains; its platforms, tracks and foundations remain absent. Most area buildings still have massing geometry.

Cabot Place dome remains unresolved: mapped roof_height=27 m exceeds the current assumed total height of 9 m. Architect text corroborates a dome but gives no measured eave/apex heights. The conflict is recorded in references/cabot_dome_evidence_audit.json; no unsupported reinterpretation applied.

One station photograph has been inspected previously. A paired Environment Agency 1 m DSM/DTM subset has been acquired and inspected as height evidence; it is not yet applied to geometry. No aerial/satellite optical image has been inspected. Google-derived geometry is not used. Continue evidence acquisition and detailed area reconstruction.
'''
(root/'docs/STATUS.md').write_text(status)
progress=read(root/'progress.json')
progress.update(stage='longitudinal_canopy_refinement_005_numerically_checked', current_retained_run=run.name, detailed_image_verified_buildings=0, visual_reviewed=False, delivered=False)
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
    z.write(scene/'render_poplar_bowls_review.py','render_poplar_bowls_review.py')
    for filename in ('acquire_lidar_subset.py','inspect_lidar_subset.py'):
        z.write(scene/filename,filename)
manifest=read(scene/'runs/canary_wharf_refinement_004/manifest.json')
from collections import Counter
manifest['provenance']['parameters']['module_counts']=dict(Counter(read(root/'src/modules.json').values()))
manifest.update(run_id=run.name,created_at=datetime.now(timezone.utc).isoformat())
manifest['provenance']['parameters']['representation']='partial_photo_informed_canopy_and_mapped_poplar_gable'
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'}
manifest['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]} for p in sorted(run.iterdir()) if p.name!='region.glb']
write(run/'manifest.json',manifest)
write(scene/'views/canary_wharf_refinement_005.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · roof refinement 005','time_alignment':'relative','runs':[run.name],'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]})
print(run)
