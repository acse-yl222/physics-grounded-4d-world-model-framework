"""Retain roof refinement without overwriting the first baseline."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import shutil
import zipfile

scene=Path(__file__).resolve().parent;repo=scene.parents[1]
root=scene/'input/canary_wharf_20261007';export=root/'exports/refinement-003a'
run=scene/'runs/canary_wharf_refinement_003'
run.mkdir(parents=True,exist_ok=False)
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
modules=json.loads((root/'src/modules.json').read_text())
verification=json.loads((export/'verification.json').read_text())
assert verification['numerical_export_verified']
for p in export.iterdir():
    if p.suffix in ('.png','.glb','.json') or p.name=='region.blend':shutil.copy2(p,run/p.name)
counts=dict(Counter(modules.values()))
status='''# Canary Wharf refinement 003

Current retained run: runs/canary_wharf_refinement_003. Entire selected area and 439 original building/part identities remain represented. Full detailed reconstruction is incomplete.

All seven mapped DLR round-roof parts now have curved geometry. The five previously flat complex polygons preserve original corners, concavities and triangulated plan area. Closed massing geometry checks verify finite coordinates, paired/oppositely directed edges, positive volume and source height bounds. All seven roofs are intentionally open surfaces. Unsupported auxiliary end walls were removed after the first interior review showed false corridor blockages; auxiliary glazing extrapolates station appearance and remains individually unverified. Central roof includes photo-informed red truss structure.

New actual image evidence: Geograph photo 5620872 by N Chadwick, indexed CC BY-SA2.0; supplied 640x426 JPEG was retrieved and visually inspected. It shows red curved trusses with diagonal webs, light-transmitting canopy and an open platform corridor. Capture date and exact camera pose are unknown. Central-canopy assignment is an interpretation. The model includes 9 illustrative frame stations and 963 cylinder members. Bay spacing, member cross-sections, 3–18 m height interval and 6 m roof rise are inferred, not measured. Edge support columns terminate on an assumed platform plane z=3; platforms, tracks and foundations are not yet modeled. Source metadata page returned no scraping; no further requests made.

Master reopened and GLB independently reimported. Overview, canopy top/oblique and opposing understructure renders inspected. These verify visible red structure and open roof representation, not survey accuracy or complete station detail. Old low-angle views from refinement002 are not reused to certify this version. Image textures are not embedded; shaders illustrative. Opaque massing elsewhere remains explicitly incomplete.

Next: refine remaining stations/site interfaces, platform support levels and rail corridor from evidence; acquire permitted elevation/aerial references for major-building glazing, openings and architectural projections. Do not mark whole reconstruction delivered.
'''
(root/'docs/STATUS.md').write_text(status)
progress=json.loads((root/'progress.json').read_text());progress.update(stage='roof_refinement_003_numerically_checked',
 current_retained_run=run.name,module_counts=counts,roof_refinements_this_batch=7,newly_curved_parts=5,inspected_image_count=1,
 detailed_image_verified_buildings=0,visual_reviewed=False,delivered=False,
 pending='Platform/site interfaces and image-backed facade/entrance reconstruction')
for row in progress['buildings']:
    if modules.get(row['id']) in ('dlr_central_frame','dlr_side_canopy'):
        row.update(stage='integrated_numerical_checks_passed',evidence_reviewed='mapped_shape_and_station_photo_context',full_image_verification=False)
write(root/'progress.json',progress)
review={'master_sha256':sha(run/'region.blend'),'module_counts':counts,
 'numerical_export_verified':True,'detailed_reconstruction_delivered':False,
 'overview_inspected':True,'targeted_views_inspected':True,'source_image_comparison':True,'source_image_comparison_scope':'Central canopy material/structural type only; dimensions and full building remain unverified',
 'facades_and_entrances_verified':False,'camera_note':'Overview and opposing canopy interior views inspected; cameras are illustrative, not calibrated to the source photo.',
 'limitations':['DLR height/rise and roof orientation inferred, not measured.','Central roof intentionally open; supports terminate on assumed platform plane; platforms/rails not modeled.',
 'Only central canopy qualitative image evidence; building facades and entrances unverified.']}
write(run/'visual_review.json',review)
shutil.copy2(root/'docs/STATUS.md',run/'STATUS.md')
shutil.copy2(root/'references/ATTRIBUTION.md',run/'ATTRIBUTION.md')
shutil.copy2(repo/'cache/tower_hamlets/geometry/selection-20261007/repository-tests.log',run/'repository-tests.log')
with zipfile.ZipFile(run/'source_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob('*'):
        if p.is_file() and not any(v in p.relative_to(root).parts for v in ('exports','renders','__pycache__')):
            z.write(p,'authoring/'+str(p.relative_to(root)))
    for p in (repo/'src/urban_geometry/region_authoring').glob('*.py'):z.write(p,'repository-src/'+p.name)
    z.write(Path(__file__),'retain_refinement_003.py')
    z.write(scene/'render_dlr_review.py','render_dlr_review.py')
manifest=json.loads((scene/'runs/canary_wharf_massing_20261007/manifest.json').read_text())
manifest['run_id']=run.name;manifest['created_at']=datetime.now(timezone.utc).isoformat()
manifest['provenance']['parameters'].update(representation='partial_photo_informed_canopy_and_mapped_roofs',imagery_used=True,module_counts=counts,
                                          detailed_reconstruction_complete=False)
manifest['provenance']['inputs'].extend([{'id':'geograph_dlr_5620872','sha256':sha(root/'references/dlr-geograph-5620872.jpg')},{'id':'authoring_geometry','sha256':sha(root/'geometry.json')}])
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown','.log':'text/plain'}
manifest['artifacts']=[{'id':'source_snapshot' if p.suffix=='.zip' else p.stem.replace('-','_'),
                       'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]}
                      for p in sorted(run.iterdir()) if p.name!='region.glb']
write(run/'manifest.json',manifest)
view={'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Canary Wharf · roof refinement 003',
      'time_alignment':'relative','runs':[run.name],'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]}
write(scene/'views/canary_wharf_refinement_003.json',view)
# Preserve the existing default view; the new view is explicitly selectable.
print(json.dumps({'run':str(run),'modules':counts,'triangles':verification['triangles']}))
