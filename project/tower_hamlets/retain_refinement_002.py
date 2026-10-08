"""Retain roof refinement without overwriting the first baseline."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import shutil
import zipfile

scene=Path(__file__).resolve().parent;repo=scene.parents[1]
root=scene/'input/canary_wharf_20261007';export=root/'exports/refinement-002'
run=scene/'runs/canary_wharf_refinement_002'
run.mkdir(parents=True,exist_ok=False)
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
modules=json.loads((root/'src/modules.json').read_text())
verification=json.loads((export/'verification.json').read_text())
assert verification['numerical_export_verified']
for p in export.iterdir():
    if p.suffix in ('.png','.glb','.json') or p.name=='region.blend':shutil.copy2(p,run/p.name)
counts=dict(Counter(modules.values()))
status='''# Canary Wharf refinement 002

Current retained run: runs/canary_wharf_refinement_002. Whole area and all 439 building/part objects preserved. Full authored detail remains incomplete.

One six-vertex Poplar roof now uses source total height 5 m and roof rise 1.5 m, with inferred long-axis ridge. Two eligible four-corner DLR parts now have 64-segment curved roofs: source shape is round, but 2.7 m roof rise and current 3–9 m interval are assumptions inherited/derived from floor tags. Five complex DLR outlines remain unrefined.

Explicit facade/roof material and color tags are applied where available. Unspecified palettes/shader response remain illustrative, not image-verified. The original height-color legend therefore describes the footprint map only, not every rendered material in this refinement.

Master reopened and GLB independently reimported with IDs/triangles/material presence/bounds checks. Overview and targeted roof/opposing views inspected; DLR low-angle cameras were occluded and raised for roof inspection. Entrance and facade verification still pending. No new licensed source image has been inspected. Google remains discovery-only. Full repository tests did not pass: missing matplotlib/scipy/torch in the test environment; detailed errors retained separately.

Next work: inspect accessible licensed facade/aerial imagery; refine remaining five DLR roof polygons without changing footprints; reconstruct recessed glazing, entrances and major-building facade projections with evidence and explicit uncertainty. Do not mark the whole reconstruction delivered.
'''
(root/'docs/STATUS.md').write_text(status)
progress=json.loads((root/'progress.json').read_text());progress.update(stage='roof_refinement_002_numerically_checked',
 current_retained_run=run.name,module_counts=counts,roof_refinements_this_batch=3,
 detailed_image_verified_buildings=0,visual_reviewed=False,delivered=False,
 pending='Image-backed facade/entrance reconstruction and remaining complex roof geometry')
write(root/'progress.json',progress)
review={'master_sha256':sha(run/'region.blend'),'module_counts':counts,
 'numerical_export_verified':True,'detailed_reconstruction_delivered':False,
 'overview_inspected':True,'targeted_views_inspected':True,'source_image_comparison':False,
 'facades_and_entrances_verified':False,'camera_note':'DLR opposing views are elevated roof inspection views; street-level views obscured by neighbouring buildings.',
 'limitations':['DLR height/rise and roof orientation inferred, not measured.','Other five complex DLR polygons remain flat baseline.',
 'No image-backed glazing or entrance details yet.']}
write(run/'visual_review.json',review)
shutil.copy2(root/'docs/STATUS.md',run/'STATUS.md')
shutil.copy2(root/'references/ATTRIBUTION.md',run/'ATTRIBUTION.md')
shutil.copy2(repo/'cache/tower_hamlets/geometry/selection-20261007/repository-tests.log',run/'repository-tests.log')
with zipfile.ZipFile(run/'source_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob('*'):
        if p.is_file() and not any(v in p.relative_to(root).parts for v in ('exports','renders','__pycache__')):
            z.write(p,'authoring/'+str(p.relative_to(root)))
    for p in (repo/'src/urban_geometry/region_authoring').glob('*.py'):z.write(p,'repository-src/'+p.name)
    z.write(Path(__file__),'retain_refinement_002.py')
manifest=json.loads((scene/'runs/canary_wharf_massing_20261007/manifest.json').read_text())
manifest['run_id']=run.name;manifest['created_at']=datetime.now(timezone.utc).isoformat()
manifest['provenance']['parameters'].update(representation='massing_with_mapped_roof_refinements',module_counts=counts,
                                          detailed_reconstruction_complete=False)
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown','.log':'text/plain'}
manifest['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),
                       'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]}
                      for p in sorted(run.iterdir()) if p.name!='region.glb']
write(run/'manifest.json',manifest)
view={'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · roof refinement 002',
      'time_alignment':'relative','runs':[run.name],'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]}
write(scene/'views/canary_wharf_refinement_002.json',view)
project=json.loads((scene/'project.json').read_text());project['default_view']='canary_wharf_refinement_002'
write(scene/'project.json',project)
print(json.dumps({'run':str(run),'modules':counts,'triangles':verification['triangles']}))
