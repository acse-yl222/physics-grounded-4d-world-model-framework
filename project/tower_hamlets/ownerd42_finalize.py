from pathlib import Path
import json,hashlib,zipfile,shutil
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/ownerd42-massing-001';v=json.loads((O/'verification.json').read_text());s=json.loads((R/'references/ownerd42_study.json').read_text());f=json.loads((O/'full_domain_evaluation.json').read_text());c=json.loads((O/'context_mesh_check.json').read_text());assert hashlib.sha256(Path(s['source_baseline']).read_bytes()).hexdigest()==s['source_baseline_sha256']
text='''# Owner d42 roof massing candidate 001

Editable uncompressed Blender and GLB, 36 closed per-domain prisms, 584 triangles. Independent GLB IDs/materials/triangles/bounds match native (bounds difference zero). Every mesh has zero nonmanifold edges and zero degenerate faces, with positive volume. Microscopic polygon spikes from floating-point planar-envelope unions were repaired before final export using 1 micrometre planar precision and 20 micrometre mesh welding. Internal coincident partition walls are intentional; these are massing domains, not rooms.

The source five-floor × assumed 3 m baseline was a flat 15 m scene body. Existing EA 1 m DSM supports a broad main plane at 24.800 ODN, central hip-like slopes, a lower eastern notch, and a southwest shallow roof. Common datum is scene z = ODN − 4.28000021 m. Base remains scene 0, with ground contact unresolved. Footprint is complete and uncut; no courtyard created.

All 1,815 valid owner DSM cells are evaluated against final frozen native triangles without elevation/residual filtering. RMSE improves 7.5688 → 4.5326 m and median absolute error 5.6660 → 0.0640 m. P95 worsens 11.7101 → 13.5565 m. Outer 2 m band RMSE worsens 7.3356 → 9.3706 m, so this is not whole-building verification. No missing top projections. Microscopic projected missing/outside area 0.001672 / 0.000475 m²; missing area at 0.1 mm tolerance zero.

Central 842-cell model RMSE 0.3195 m; spatial u/v holdout pooled RMSE 0.4049 / 0.4096 m. Eastern notch 118-cell RMSE 0.5733 m. The fitted transition is a continuous steep ramp (5.37 m/m), not a vertical shaft or wall assertion. Slope 2 / 3 / 8 / 100 controls give notch RMSE 0.8969 / 0.6816 / 0.6333 / 0.9049 m. Half-metre boundary shifts give 0.6116–0.8128 m. One spatial holdout cannot robustly locate the ledge outer edge. Small modeled slivers are estimated intersections of planes; 1 m mixed edge returns do not recover precise architectural breaklines or shaft identity. Southwest core plane holdout ~0.106 m but broad SW edge domain RMSE 5.36 m; outer transitions are uncertain.

Actual final overview, rear, source diagnostic, transition residual, notch sensitivity profiles, full frozen-mesh residual, and context render inspected by authoring agent. Final context includes three nearest mapped neighbours, 108 mesh pairs, no BVH surface intersections; sampled minimum distance 17.397 m. BVH is a surface test, not a proof of complete volumetric compatibility.

No windows, doorways, roof equipment, entrances, detailed materials, or ground changes invented. Colors are illustrative. No optical facade verification; source raster flight vintage unknown. Sources: existing Environment Agency DSM/DTM under OGL and mapped Overture footprint under ODbL; input hashes retained. Google imagery not used to derive geometry. Standalone candidate only; coordinator decides regional retention. No global progress, source ledger, or default view changed.
'''
(O/'report.md').write_text(text)
for path in [R/'references/ownerd42_study.json',R/'references/ownerd42_transition.json',R/'references/ownerd42_transition.png',R/'references/ownerd42_swfit.json',R/'references/ownerd42_fit002.json',R/'references/ownerd42_native.json',R/'references/ownerd42_neighbors.json']:
 shutil.copy2(path,O/path.name)
review={'inspected':True,'native_sha256':v['hashes']['ownerd42.blend'],'glb_sha256':v['hashes']['ownerd42.glb'],'views':['overview.png','rear.png','context-review.png','full_domain_evaluation.png','notch_sensitivity.png'],'scope':'Agent actual visual inspection; standalone roof massing only, facade/entrance unverified','source_native_unchanged':True};(O/'visual_review.json').write_text(json.dumps(review,indent=2))
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as archive:
 for path in [P/'d42_review.py',*P.glob('ownerd42*.py'),R/'geometry.json',R/'references/ea_dsm_1m.tif',R/'references/ea_dtm_1m.tif',*R.glob('references/ownerd42*.json')]:archive.write(path,path.relative_to(P))
 for path in O.iterdir():
  if path.suffix in ['.json','.md','.png']:archive.write(path,path.relative_to(P))
hashes={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in O.iterdir() if path.is_file() and path.name!='hashes.json'};(O/'hashes.json').write_text(json.dumps(hashes,indent=2));print(json.dumps({k:hashes[k] for k in ['ownerd42.blend','ownerd42.glb','source.zip']},indent=2))
