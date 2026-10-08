from pathlib import Path
import json,hashlib,zipfile,shutil
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/ownerd42-roof-diagnostic-001';O.mkdir(exist_ok=True);a=json.loads((R/'references/ownerd42_native.json').read_text());f=json.loads((R/'references/ownerd42_full_domain.json').read_text());report={'owner':'overture-building-d42f49e8-7c91-4cf4-b65b-e7d92b3947d4','status':'Evidence diagnostic; geometry authoring held pending eastern transition topology','source_native':a['source'],'source_sha256':a['source_sha256'],'source_unchanged':a['source_unchanged'],'full_domain':f,'actually_inspected':['ownerd42_diagnostic.png','ownerd42_fit.png','ownerd42_profiles.png','ownerd42_full_domain.png'],'geometry_created':False,'limitations':['Dominant hip-like slopes supported; a rectangular hip alone misses coherent eastern return transition.','No roof function or equipment identity inferred.','Known mathematical fit improvement does not establish exact roof topology.','All original mapped footprint and valid DSM cells retained in diagnostic metrics.']};(O/'report.json').write_text(json.dumps(report,indent=2))
(O/'report.md').write_text('''# d42 roof evidence diagnostic

Exact owner d42f49e8-7c91-4cf4-b65b-e7d92b3947d4, OSM w31831771@14, commercial5floors. Latest retained Morgan visibility correction native selectively loaded: one originalflatmesh z0..15m, source unchanged. Height15m derives from5floors×assumed3m, not measured roof.

All1815 valid DSM cells in full1817m² mappedfootprint inspected. Roof has broad~24.8m ODN mainplane, a coherent central raised/sloping domain~500cells, and separateSW raisedpatch~85cells. Thresholds25.5/26.5/28/30m retain coherent components; these are diagnostics, not height-filtered geometry.

Central geographic rectangle compares plane/gables/hip hypotheses with blocked spatialholdout. PlaneRMSE1.522m; hip0.889m, pooled east/north holdout0.900/0.926m. Flattenedhippeak adds parameters but onlyimproves0.011m. Residualmaps expose coherent eastern low/steep region; exact crossprofiles show steeper transition toward main24.8m roof, rather than a confidently flat insetplatform. A simplewholehip orflat replacement would hide this structure.

SW inset geographic core has coherent shallowplaneRMSE0.0915m, spatialholdout~0.106m; broadSWrectangleRMSE2.151m includes real shoulder/edge variability. Wholefootprint mathematical test using explicitlyprovisional hip/SWrectangles improvesRMSE7.569→4.600m and median5.666→0.080m, but P95worsens11.710→13.747m. These are predictive equations only, not authoredmodel/architecturalbreaklines. All boundarycells remainincluded.

Actually inspected DSM/DTM/connected-domain, fitresidual, rawprofiles andfull-domainplots. No Blender/GLB geometry created, no region/global edits. Next useful step is bounded easttransition plane/breakline comparison with residual/sensitivity checks, then SWshoulder boundarytest; no arbitrary equipment or DSMspikes. Ground0/common ODNoffset4.28000021 preserved. Actualflightdateunknown; existingEA1mOGLdata/OvertureOSM ODbL only, no acquisition.
''')
for p in list((R/'references').glob('ownerd42*.json'))+list((R/'references').glob('ownerd42*.png'))+[R/'references/d42_roof_review.json',R/'references/d42_roof_review.png']:shutil.copy2(p,O/p.name)
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in list(P.glob('ownerd42_*.py'))+[P/'d42_review.py']+list(O.glob('*.json'))+[O/'report.md']:z.write(p,str(p.relative_to(P)))
print(hashlib.sha256((O/'source.zip').read_bytes()).hexdigest())
