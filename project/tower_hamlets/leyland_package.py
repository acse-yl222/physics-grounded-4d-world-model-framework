from pathlib import Path
import json,hashlib,zipfile
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';O=R/'exports/leyland-massing-001';study=json.loads((R/'references/leyland_study.json').read_text());ev=json.loads((O/'full_domain_evaluation.json').read_text());ver=json.loads((O/'numerical_verification.json').read_text());jo=json.loads((O/'join_check.json').read_text())
report={'owner':study['replacement_ids'][0],'name':'Leyland House','scope':study['scope'],'mesh_count':len(ver['native']),'triangles':sum(x['triangles'] for x in ver['native']),'full_domain':ev['groups'],'join_max_difference_m':jo['maximum_join_difference_m'],'missing_cell_projections':ev['missing_top_projections'],'limitations':study['limitations'],'native_glb_passed':ver['passed'],'source_properties':study['source_properties'],'source_ids':study['source_ids'],'actual_views_reviewed':['overview.png','rear.png','context-review.png','full_domain_evaluation.png','leyland_domains.png','leyland_fit.png'],'visual_findings':['Pitched ridges/hips form connected five-wing roof; mapped courtyard remains open.','Minor eave offsets/notches follow mapped footprint and estimated roof intersection, not photographed facade detail.','Plain facade materials are placeholders; roofshapes useful, eaveextent notverified.'],'status':'Frozen independent candidate; not retained.'}
(O/'report.json').write_text(json.dumps(report,indent=2))
(O/'report.md').write_text('''# Leyland House estimated pitched roof candidate

Owner 8a7116a4-439b-4097-bee2-b8a1b7ad4f7d. Five spatially evidenced pitched roof wings replace the original flat 12.43655777 m scene extrusion. Full mapped footprint, including the open courtyard, is preserved. Roof planes are approximately 0.67–0.75 rise/run with ridges 23.11–23.26 m ODN; scene elevations subtract the unchanged 4.28000021 m datum. No windows, chimneys or arbitrary equipment were invented.

The northern wing required two bounded official EA WCS requests (56 ×100 m); DSM and DTM each exactly match all4,032 overlapping pixels in the original grids. Source sidecar records URLs, hashes, OGLv3, projection, bounds and attribution. Original rasters remain untouched. Actual flight date unknown; retrieval date is not acquisition date.

All1,292 valid owner DSM cells were evaluated against the frozen native mesh's highest actual triangle intersection, without height/error rejection. Missing projections:0. Full-domain RMSE improves5.4503→4.3249 m, median absolute error4.8699→0.0876 m; P95 worsens9.9587→13.0735 m. Boundary cells retain substantial low/mixed returns. Inner2 m RMSE0.6976 m is not a substitute for full-domain error. Terminal156cells RMSE4.4910 m; corner306cells4.0260 m; inner-corner164cells0.7077 m. Terminal and corner domains include all their valid cells.

26 closed planar roof cells,656 triangles. Native reopened; independent GLB geometry, IDs, materials and bounds verified. Source roof-plane joins agree within0.0000082 m at shared edges. Actual Blender projected coverage has only float-scale boundary discrepancies: missing0.0005483 m², outside0.0005294 m², and no missing area at0.1 mm tolerance. These are not designed holes. Internal partition walls are intentionally coincident. Neighbor BVH reports0 contacts, nearest sampled vertex distance7.6339 m; this is not a solid boolean proof.

Overview, rear, neighboring context, DSM/DTM profiles and equal-scale final-mesh comparison were actually inspected. The roof network is visually coherent and the courtyard remains open. Eave offsets, overhangs, small roof fixtures and hidden facades remain unverified. Flatbase0 is illustrative; local DTM is not a foundation measurement. Candidate is appropriate only as an estimated research model. No regional retention or global progress changes are made by this package.

EA attribution: Contains Environment Agency information © Environment Agency copyright and/or database right2022, Open Government Licencev3. Overture/OSM source geometry follows the existing ODbL provenance. The source archive contains scripts and derived reports, not raster pixels or photos.
''')
files=list(S.glob('leyland_*.py'))+list((R/'references').glob('leyland*.json'))+list((O).glob('*.json'))+[O/'report.md']
with zipfile.ZipFile(O/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,str(p.relative_to(S)))
print(hashlib.sha256((O/'sources.zip').read_bytes()).hexdigest())
