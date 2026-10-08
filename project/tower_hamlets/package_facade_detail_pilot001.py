from pathlib import Path
import bpy,json,hashlib,zipfile
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/facade-detail-pilot-001';d=json.loads((O/'checks.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(d['source_native'],link=False) as (a,b):b.objects=list(d['source_signatures'])
for ob in b.objects:bpy.context.collection.objects.link(ob)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'source-selected.blend'),compress=False)
photo=R/'references/pexels-ollie-craig-11491155.jpeg';crop=P.parent.parent/'cache/tower_hamlets/quay1-independent/inspection-crop.png'
review={'inspected':True,'actual_views':['before-detail.png','after-detail.png','corner-detail.png','section.png','cache/tower_hamlets/quay1-independent/inspection-crop.png'],'observations':['Photo horizontal band hierarchy and dark glazing retained; cadence inherited estimated.','Shallow recess visible in identical camera comparison, no major silhouette change.','Boxed frame returns connect existingmetal frontframes to recessed glazing.','Facet band end separation inherited; closedbodyjointverified, exact jointdesignnotphotomeasured.'],'source_photo_sha256':hashlib.file_digest(photo.open('rb'),'sha256').hexdigest(),'native_sha256':hashlib.file_digest((O/'quay1-detail.blend').open('rb'),'sha256').hexdigest(),'glb_sha256':hashlib.file_digest((O/'quay1-detail.glb').open('rb'),'sha256').hexdigest(),'status':'Bounded shallow-curtain-wall detail improvement; not fully verified building'};(O/'visual-review.json').write_text(json.dumps(review,indent=2))
(O/'report.md').write_text('''# Quay1 shallow curtain-wall detail pilot

Owner a6a8ac29 upper southwest curved arc, original edges 9–15, scene z52–109.45 m. Existing licensed Ollie Pexels 11491155 source crop actually inspected. The photograph supports slim projecting horizontal bands, finer vertical mullions and dark glazing; depth cannot be measured from its distant view. Existing cadence remains explicitly estimated.

This pilot creates real shallow body recesses and moves glazing from an overlay into those recesses. Glass front is 0.10 m behind mapped face, body backing 0.18 m behind. Closed metal frame returns bridge to existing frame faces. The front horizontal and vertical frame meshes remain exactly unchanged. Two original meshes change (body, glass); two rear-return meshes are added. Original footprint and roof height111 m remain; lower and hidden elevations untouched.

105 rays across seven faces prove glass first at1.10 m and body behind at1.18 m from1m outside. 18 rays at the six facet joints prove closed backing. Source body, newglass andreturn meshes pass closed manifold/zero-area checks. Independent GLB import matches per-object triangles, owner IDs and material names. Before/after same close camera, cornerdetail and actual polygonsection inspected. This is a small meaningful exterior geometry improvement, not complete facade/entrance or building verification.

Estimated geometry:10cm glass setback,18cm cutdepth and framebackreturns. Glass remains opaque exterior proxy. No exactphotogrammetricdepth, interior, fabricated entrance or new generic baylayout claim. Inherited4cm endtrim leaves visible bandjoint; it is geometrically backed but exactrealjointdesignunknown.

source-selected.blend freezes the four exact source owner meshes selectively extracted from latest retained ownerd42 region. Photo/crops excluded from source archive; source references and hashes retained. Region itself untouched.
''')
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in [P/'build_facade_detail_pilot001.py',P/'review_facade_pilot_corner001.py',P/'plot_facade_pilot_section001.py',P/'package_facade_detail_pilot001.py',O/'source-selected.blend',O/'checks.json',O/'section.json',O/'visual-review.json',O/'report.md',R/'references/quay1_coordinator_photo_review001.json']:z.write(f,f.name)
print('PACKAGED')
