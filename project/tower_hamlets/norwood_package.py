from pathlib import Path
import json,zipfile,hashlib
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';O=R/'exports/norwood-massing-001';study=json.loads((R/'references/norwood_study.json').read_text());ev=json.loads((O/'full_domain_evaluation.json').read_text());d=R/'references/norwood_diagnostic.json';j=json.loads(d.read_text());j['decision']='Subsequent spatialprofiles establish three slopedwings/two raised connectors; independent sevenpart candidate authored, uncertainties retained.';d.write_text(json.dumps(j,indent=2))
r={'owner':study['replacement_ids'][0],'name':'Norwood House','status':'Frozen independent candidate; no regionalassembly','scope':study['scope'],'source_properties':study['source_properties'],'mesh_count':7,'triangles':136,'full_domain':ev['groups'],'native_glb_passed':True,'neighbor_contacts':0,'neighbor_min_sample_m':10.85560608,'actual_views_reviewed':['overview.png','rear.png','context-review.png','full_domain_evaluation.png','norwood_diagnostic.png','norwood_profiles.png','norwood_domains.png'],'limitations':study['limitations']+['All-domain P95 worsens9.0479→13.6619m; outer low/mixedreturns remain unresolved.','Connector stepwalls are envelope estimates, not identified facade/equipment components.']};(O/'report.json').write_text(json.dumps(r,indent=2))
(O/'report.md').write_text('''# Norwood House estimated roof refinement

Owner980db4c6-949e-4dda-b317-ec9669cf1554. Three offset wing roofs consistently descend eastward at approximately0.26–0.28 m/m, with two locally raised connecting roof surfaces. Spatially selected regions were fit using all valid1.3 m inset cells, no elevation filtering. Mainwing fit RMSE0.056/0.104/0.077 m; spatialholdout RMSE maxima0.113/0.241/0.176 m. Connector planes are restricted to their visible higherdomains rather than extrapolated across entire wing widths. Their fold RMSE maxima0.576/0.133 m. Step boundary placement remains estimated at1 m rasterresolution.

Previous8.57191753 m sceneheight derives from Microsoft ML Buildings; OSMw196769280@5 supplies the named footprint and6floors. Floorcount is context only. Roof elevation uses EA DSM ODN minus the unchanged4.28000021 m regionaldatum. DTM is diagnostic, not a foundation or a perbuildingdatum. Actualflightdateunknown. Source native is appearance-bank40-002.

Seven closed planar masses,136triangles, preserve the fullmappedfootprint. Native reopen and independent GLB ID/triangle/bounds/material checks pass. Actual frozenmesh top projections cover all567 valid owner DSM cells, missing0. Full-domain RMSE improves6.1172→4.4186 m and medianabsolute error6.1401→0.0718 m; P95 worsens9.0479→13.6619 m. Low/mixed boundary returns remain included. Inner2 m RMSE0.3227 m is not a substitute for full-domain error. Transitionstrips include103cells RMSE4.2870 m; their inner2 m subset43cells RMSE0.7517 m/P951.8850 m. These strips were explicitly evaluated rather than omitted as fitgaps.

Floatprecision footprintmissingarea0.000628 m², outsidearea0.000371 m², missingarea at0.1 mm tolerance0. No designed holes. Roofsteps have closed vertical faces; internal shared walls are intentional. Neighbor BVH0contacts, nearest sampled vertex10.8556 m, not a solidbooleanproof.

Overview/rear/context and actual DSM/DTM/profile/finalresidual plots inspected. Three slopes and raised connecting envelopes are visually coherent. Narrow stepfaces, roofedgeextent, hiddenfacades and groundcontact remain unverified. Base0 and plain materials are illustrative. No windows, rooftop equipment or fabricated pitch added without evidence. No regionalassembly/global progress changes.

Existing EA1m DSM/DTM: OGLv3, Contains Environment Agency information © Environment Agency copyright and/or database right2022. Overture/OSM/MicrosoftML provenance ODbL as recorded. No new dataacquisition. Archive contains scripts/derivedreports, no rasterpixels/photos.
''')
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in list(S.glob('norwood_*.py'))+list((R/'references').glob('norwood*.json'))+list(O.glob('*.json'))+[O/'report.md']:z.write(p,str(p.relative_to(S)))
print(hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest())
