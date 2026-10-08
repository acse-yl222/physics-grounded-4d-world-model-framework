from pathlib import Path
import json,hashlib,zipfile,shutil
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/appearance-morgan-visibility-correction-001';v=json.loads((O/'verification.json').read_text());evidence=R/'exports/morgan-south-facade-002/visibility-diagnostic.json';shutil.copy2(evidence,O/'visibility-diagnostic.json');shutil.copy2(evidence.with_name('report.md'),O/'visibility-study-report.md')
visual={'inspected':True,'asset_sha256':v['artifact_sha256'],'images':{'overview.png':'Actual overview inspected; existing scene geometry retained.','morgan-corrected-context.png':'FAILED visual coverage: nearby tower occludes target. Retained as diagnostic, not acceptance.','morgan-corrected-context-revised.png':'Actual revised local camera inspected; edge13 body wall visible without the unsupported two-bay facade detail. Other surrounding geometry remains present; no hide workaround.'},'claim':'Removal correction only; no new geographically verified facade, no completed-building increment.'};(O/'agent_visual_review.json').write_text(json.dumps(visual,indent=2))
(O/'report.md').write_text('''# Morgan facade visibility correction comparison

The retained edge13 two-bay facade placement failed a source-camera visibility check. In the subsequent diagnostic,20/24 sampled rays hit Morgan_podium_curved_low25–33.5 m before their target. Blender and analytical camera projections agree within0.000204 px, so this is body occlusion, not a camera conversion mismatch. The prior001 facade's exact edge13 placement is unsupported. New002 candidate remains held; it is not imported here.

This comparison starts from exact retained canary_wharf_appearance_owner1f92_001. Removes only morgan_south_black_frames216tri, dark_glass24tri, dark_spandrel24tri, pale_stone_accents180tri, stone_piers48tri:5meshes/492triangles. All2608 other meshes preserve geometry, materials, custom properties and UV fingerprints, including all Morgan bodies/roofs and1f92. Historic files remain untouched. No0085 integration.

Native reopen and independentGLB metadata/aliases, triangles, used material names and per-objectbounds checks passed, maxbounds discrepancy1.5259e−5 m. Source native unchanged. Actual overview inspected. Initial context view is occluded and fails coverage; revised local camera shows the plain retained edge13 wall after removal without hiding scene geometry. Rendering camera changes not saved into regionasset. This corrects unsupported detail and does not claim new facade verification or completed buildings.

No retention, progress/source/status/view changes or publication. Visibility diagnostic and originating report copied as supporting evidence. Source archive includes correction code and derived records, no source photographs.
''')
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in [P/'assemble_morgan_visibility_correction_scene.py',P/'render_morgan_visibility_correction.py',Path(__file__)]+list(O.glob('*.json'))+list(O.glob('*.md')):z.write(p,str(p.relative_to(P)))
print(hashlib.sha256((O/'source.zip').read_bytes()).hexdigest())
