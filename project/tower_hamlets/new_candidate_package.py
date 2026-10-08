from pathlib import Path
import json,hashlib,zipfile
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';O=R/'exports/new_candidate-massing-001';r=json.loads((R/'references/new_candidate_study.json').read_text());v=json.loads((O/'numerical_verification.json').read_text());report={'scope':r['scope'],'replacement_ids':r['replacement_ids'],'status':'independent_research_candidate_not_region_integrated','fit':r['fit'],'limitations':r['limitations'],'numerical':{'meshes':len(v['native']),'triangles':sum(x['triangles'] for x in v['native']),'native_and_glb_passed':v['passed'],'footprint_checks':r['checks'],'neighbor_BVH_contacts':0,'neighbor_nearest_vertex_sample_m':27.681215286254883},'visual_inspection':['new_candidate_roof_review.png','new_candidate_profiles.png','new_candidate_fit.png','overview.png','rear.png','context-review.png'],'sources':{'footprint':'Overture2026-09-23.1 / OSM w51946953@9 ODbL-1.0','baseline_height':'Microsoft ML Buildings supplied10.641523m, not surveyed height','DSM':'Environment Agency1m DSM; OGLv3, actualpixelcapturedateunknown','ODN_to_scene_subtract_m':4.28000021},'hashes':{s:hashlib.sha256((R/s).read_bytes()).hexdigest() for s in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']}};(O/'report.json').write_text(json.dumps(report,indent=2)+'\n');(O/'report.md').write_text('''# OMC roof research candidate

Owner dcdb752c-6b8b-43ae-84af-a23667921110, mapped Operations Maintenance Centre. Original current native is one flat roof at scene10.641523m, supplied by Microsoft ML. New independent candidate preserves the exact mapped outline and describes a shallow main double pitch, broader raised band, narrow raised spine and transitional spine. 10 closed meshes,192triangles. No facade openings or roof equipment identity claimed.

Main profile uses1241all-selected points: ODNridge13.1244m,slope0.11010,RMSE0.368m,medianabs0.050m. Broad raisedband297points: ODNridge13.8953m,slope0.12139,RMSE0.217m,medianabs0.022m. These profiles are stable in spatialholdout. Narrowspine77points: ODNridge15.1562m,slope0.59666,RMSE0.214m; slope changes substantially acrossfolds, including a boundhit. Transition36points is weaker. Exact spine shape and step boundaries remainestimated; wholecandidate is a research comparison, not fullyverified replacement.

Uses ODN minus4.28000021m. Scene peaks for main/broad/narrow/transition are8.8444/9.6153/10.8762/9.9035m. Base0 and wall/roof colors are illustrative. Rastercapturedateunknown. No arbitrary new equipment or openings. Internal partitionwalls coincide deliberately.

Native reopen and independentGLB counts/IDs/bounds/materials passed. Native meshes are closed with no zeroarea faces. Footprintpartitionarea check is inJSON. NeighborworldtriangleBVH contacts0; nearestsample27.6812m. This is a surface/samplingcheck, not a generalvolumeproof. Actual sourceprofiles, overview,rear andcontext renders were inspected.

Existingregionalnative andprogress untouched. Sourcearchive contains scripts/reports andprovenance only, no imagery orrasterpixels. Overture/OSM ODbL-1.0; EnvironmentAgency LiDAR OGLv3.
''')
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(S.glob('new_candidate_*.py')):z.write(f,'authoring/'+f.name)
 for f in sorted((R/'references').glob('new_candidate_*.json')):z.write(f,'references/'+f.name)
 for n in ['report.md','report.json','numerical_verification.json','context_mesh_check.json']:z.write(O/n,n)
print(hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest())
