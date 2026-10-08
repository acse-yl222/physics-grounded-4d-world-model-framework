from pathlib import Path
import json,hashlib,shutil,zipfile
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/appearance-owner1f92-001';C=R/'exports/owner1f92-massing-001';v=json.loads((O/'verification.json').read_text())
for name in ['full_domain_evaluation.json','full_domain_evaluation.png','interface_native.json','report.json','report.md','owner1f92_fourth.json']:
 src=C/name
 if not src.exists():src=R/'references'/name
 dest=O/('candidate_'+name if name.startswith('report') else name)
 shutil.copy2(src,dest)
shutil.copy2(C/'sources.zip',O/'candidate_sources.zip')
review={'inspected':True,'scope':'Agent inspected four current regional renders; detail/rear are isolated displays, hide flags not saved to native/GLB. Context includes neighboring buildings.','images':['overview.png','owner1f92-context.png','owner1f92-detail.png','owner1f92-rear.png'],'findings':['Full-region overview retains same geographic alignment and neighborhood.','Four tier silhouette and west recess visible in isolated rear.','Context shows candidate in original footprint adjoining unmodified neighbor; front lower wall partly occluded by existing neighboring roof.','Plain facades and illustrative original base remain, no claim of fully reconstructed building.'],'asset_sha256':v['artifact_sha256']};(O/'agent_visual_review.json').write_text(json.dumps(review,indent=2))
(O/'report.md').write_text('''# Owner1f92 regional comparison

Source retained Norwood SHA 5058fe7683932bea5f3e4f4d7ca2bd56a85311b24d794efb2391cc85c999b9ea. Only owner1f9270f4 replaced: one original flat mesh → four closed stepped roof masses (100 triangles). All 2609 unrelated meshes retain geometry, materials, custom properties and UV fingerprints, verified again after native reopen. Total2613 meshes. Independent GLB owner metadata/aliases, per-object triangles, used materials and bounds checked; max bounds discrepancy1.5259e−5 m. Input source unchanged.

Agent actually inspected current overview, context and isolated detail/rear. Four levels at ODN20.354/17.478/14.634/11.739 m use original fixed datum offset4.28000021 m. Shared mapped wall12.109 m with00851081 retains contact interval z0..9 and exposed candidate interval9..16.074 m; neighbor untouched. Context partly occludes lower frontwall; isolated rear establishes visible roof steps, not a photographic facade verification.

Candidate full-domain608 cells RMSE4.935→2.939 m and P95 6.768→6.498 m. Outer2 m P95 worsens8.671→12.911 m. Narrow ledge boundaries, western low edge, ground contact and all facade details remain uncertain. See candidate report, full-domain evaluation, boundary sensitivity and exact interface records. No global source/progress/status/views edits, no retention or publication.
''')
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in [P/'assemble_owner1f92_scene.py',Path(__file__),O/'candidate_sources.zip']+list(O.glob('*.json'))+list(O.glob('*.md')):z.write(p,str(p.relative_to(P)))
print('source.zip',hashlib.sha256((O/'source.zip').read_bytes()).hexdigest())
