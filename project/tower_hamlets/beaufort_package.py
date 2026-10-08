from pathlib import Path
import json,zipfile,hashlib
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';O=R/'exports/beaufort-massing-001';r=json.loads((R/'references/beaufort_study.json').read_text());ev=json.loads((O/'full_domain_evaluation.json').read_text());v=json.loads((O/'numerical_verification.json').read_text());report={'scope':r['scope'],'replacement_ids':r['replacement_ids'],'fit':r['fit'],'limitations':r['limitations'],'full_domain':ev,'verification':{'native_glb_passed':v['passed'],'meshes':7,'triangles':128,'neighbors_BVH_surface_pairs':0,'nearest_vertex_sample_m':12.519742965698242},'actually_inspected':['references/beaufort_profiles.png','references/beaufort_terraces.png','exports/beaufort-massing-001/overview.png','exports/beaufort-massing-001/rear.png','exports/beaufort-massing-001/context-review.png','exports/beaufort-massing-001/full_domain_evaluation.png'],'provenance':{'footprint':'Overture2026-09-23.1;OSMw352635844@4;ODbL-1.0','baseline_height':'MicrosoftML25.32539176940918m,notmeasuredsurvey','roof':'EA1mDSM OGLv3;actualcaptureunknown','scene_datum':'ODN minus4.28000021m'},'geometry_scope':'Wholeowner closedcontrol withonlyouterterraceschanged. Central lowreturnarea remainsunresolved andisnotnewlyverifiedroof.'};(O/'report.json').write_text(json.dumps(report,indent=2)+'\n');(O/'report.md').write_text('''# Beaufort Court: outer-terrace refinement only

Owner5459df5b-8e56-460d-940b-f526063f95bc. Sevenclosedmeshes,128triangles. Mainheight25.32539177scene is unchanged, including unresolvedcentral lowreturnpatch. No newcourtyard oropenings. Theoriginalmappedfootprint has nohole; lackofhole is notproof thecourtyarddoesnotexist.

Three spatiallycoherent outerterracelevels:18.88965/22.38337/25.76890mODN, translating to14.60965/18.10337/21.48890m scene. Six spatialholdoutfits perlevel vary within0.028/0.015/0.026m respectively. This demonstrates stablelevels, notexactstepboundaries. Allgeometricdomainpoints retained; largeresidualsanddropoutpatches remain. Theholdoutbug fromshadowedUVvariables was correctedbeforepackaging; assets unchanged because heightfits were unaffected.

Frozenmeshall1668validDSMpoints have topintersections. WholeownerRMSE8.78563m versusold10.05528m, medianabs0.35539m versus3.09250m, P9522.38039m. Largecentralerror remainsunchanged. Changedterrace486points improveRMSE9.82578→3.80073m, medianabs7.26039→0.05524m;P959.48990m stilllarge. Do notuse lowmedian toclaim completebuildingaccuracy.

Native reopened, closedtopology/nozeroareafaces and independentGLB IDs/counts/bounds/materials passed. NeighborBVH0surfacecontacts; nearestsample12.51974m, notavolumetricproof. Fullmappedfootprintcovered within0.1mm;exactfloatuniontinyseams documented. Actualoverview,rear,contextandfull-domainplotsinspected. Rearviewshowsrefinedterraces;facadesblankestimated.

Sources:EA1mDSM OGLv3,Overture/OSM ODbL-1.0. OriginalheightfromMicrosoftML,notasurvey. CommonODNoffset4.28000021 unchanged;actualsurveydateunknown. Nopublication/globalchange. Candidateislimitedterracerefinement,notcompletefacade/courtyardreconstruction.
''')
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(S.glob('beaufort_*.py')):z.write(f,'authoring/'+f.name)
 for f in sorted((R/'references').glob('beaufort_*.json')):z.write(f,'references/'+f.name)
 for n in ['report.json','report.md','full_domain_evaluation.json','numerical_verification.json','context_mesh_check.json']:z.write(O/n,n)
print(hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest())
