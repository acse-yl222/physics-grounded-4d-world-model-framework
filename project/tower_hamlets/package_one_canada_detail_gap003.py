from pathlib import Path
import bpy,json,hashlib,zipfile
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/one_canada_detail_gap003';d=json.loads((O/'checks.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(d['source_blend'],link=False) as (a,b):b.objects=[d['original_mesh']]
for ob in b.objects:bpy.context.collection.objects.link(ob)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'source-roof.blend'),compress=False)
review={'inspected':True,'views':['before-close.png','after-close.png','before-whole.png','after-whole.png','cache/tower_hamlets/one_canada_detail_gap003/crown-inspection.png','cache/tower_hamlets/one_canada_detail_gap003/anna-crown-inspection.png'],'decision':'Bounded west louvre support improvement, not wholebuilding completion','findings':['Photo supports vertical posts connecting narrowhorizontalbands.','Altaf alone cannot resolve cardinalorientation; Anna knownwestcontext independentlysupportsedgetreatment.','Originalroof+louvrerings unchanged, postcount29baysestimated.','Initialcoplanartopcaps repaired by5mm embeddedendcaps; correctedclose actuallyinspected.'],'native_sha256':hashlib.file_digest((O/'canada-crown.blend').open('rb'),'sha256').hexdigest(),'glb_sha256':hashlib.file_digest((O/'canada-crown.glb').open('rb'),'sha256').hexdigest()};(O/'visual_review.json').write_text(json.dumps(review,indent=2))
ledger=json.loads((R/'references/sources.json').read_text());sources=[q for q in ledger if q['id'] in d['source_photos']];(O/'source_ledger.json').write_text(json.dumps(sources,indent=2));(O/'report.md').write_text('''# One Canada roof screen detail003

Only roofowner0c84e402-a7c0-399a-a2af-317cf479fcef, mappedwestedge0. Addedone360-triangle mesh containing30closedposts/29estimatedbays connectingtheexistingfivehorizontalrings. Existingroofmesh,pyramidapex235m,base210m andringgeometry/materials/propertiesexact. Forintegration appendONLY Canada_roofscreen_west_uprights_estimated003; sourcecontextroofmustnotreplaceanything.

OriginalAltaf nativecrowncrop actuallyinspected and showsclearwhiteverticalposts interruptinghorizontalopenings. Its symmetricpyramid doesnot uniquelyestablishcardinalface. IndependentAnna westcontext(HSBCleft/OCScenter/Citiright, CabotPlace/fountain) supports westface andvisibleverticalroofbasedivisions. Anna storedcamera usedonlyqualitativebearing, not exactdepth/countregistration. Count29bays/30posts and10cm widths inferred, not measured. Endposts clippedtoedge; depth−.08..+.115m relativemappedface. Z210.005..211.365, endcaps5mm insideextremerings toavoidcoplanar exposedtops.

Actualsamecamera before/aftercloseandwholecrown inspected. Native reopened andGLBindependentlyimported; trianglecounts,ownerIDs andusedmaterials match. Sourceexactcheckpasses. Nofarface,roofseams,cranefixture,entrance orotherbuildingchange. Independentattachmentreview pending. Photo/crops arecache-only referenceandnotincludedinarchive.
''')
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in [P/'build_one_canada_detail_gap003.py',P/'package_one_canada_detail_gap003.py',O/'source-roof.blend',O/'checks.json',O/'visual_review.json',O/'source_ledger.json',O/'report.md',R/'references/cabot_place_anna_camera.json']:z.write(f,f.name)
print(review)
