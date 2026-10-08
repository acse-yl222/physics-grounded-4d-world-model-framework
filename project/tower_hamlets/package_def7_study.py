from pathlib import Path
import json,hashlib,struct,zipfile,shutil
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/def7-massing-001';r=json.loads((R/'references/def7_massing_study.json').read_text());blob=(O/'def7.glb').read_bytes();n=struct.unpack_from('<I',blob,12)[0];g=json.loads(blob[20:20+n]);nodes=[q for q in g['nodes'] if 'mesh' in q];assert len(nodes)==3 and all(q['extras']['building_id']==r['parent_id'] for q in nodes);v=json.loads((O/'verification.json').read_text());v.update(glb_owner_ids_verified=True,materials=g['materials'],visually_inspected=['overview.png','roof.png','rear.png','def7_zone_support.png'],visual_findings='Clean partial stepped envelope with deliberately uncertain interior recess. No facade claim.');(O/'verification.json').write_text(json.dumps(v,indent=2)+'\n')
for name in ['def7_zone_support.png','def7_roof_review.png','def7_geometry_checks.json']:shutil.copy2(R/'references'/name,O/name)
report={k:v for k,v in r.items() if k!='objects'};report.update(verification=v,hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [O/'def7.blend',O/'def7.glb',R/'references/def7_massing_study.json']});(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(O/'report.md').write_text('''# Anonymous def7f49e partial roof study

Source owner overture-building-def7f49e-93a6-4c95-8178-d91e152b4d52, OSMw1426095806@1 updated2025-08-30. No name, metric height, floor count or parent. Current9m is pure fallback. Location−0.0241770,51.5016874 lies southeast of mapped Landmark East tower and north of Block Wharf. Association with a Landmark low-rise block is spatial inference only, not verified address attribution. Historical planning text mentions8-storey Landmark blocks but no dimension or identity is borrowed from that statement.

Three observed plateaus16.73/27.96/31.82m ODN become scene12.44999979/23.67999979/27.53999979 with shared ODN4.28000021. Original outer footprint preserved; vertical body toscene0 inherited and illustrative. No local-ground renormalization.

54coherent interior cells below8ODN indicate possible courtyard/transparent/no-roof returns. Their buffered convex envelope is left open as an explicitly uncertain recess rather than filled with high roof. The source footprint has no mapped hole: this is a topology hypothesis, not a verified courtyard. Its domain includes nearby high/boundary cells, all separately reported. Exact opening shape and depth require independent evidence. Root should review this limitation before integration.

All plateau-domain residuals and conditional3fold spatial holdouts are retained; no residual cell rejection. Low/middle/upper support is listed in report.json, alongside the separate recess-domain samples. Roof breaklines are approximate mapped-axis estimates from actual native spatial plots; roofs and facade completeness are not certified.

No touching neighboring footprint; closest12.8473m, all tested nearby overlaps zero. Three closed components with native reopen/GLB reimport and owner-ID checks passed. Actual overview, roof, rear and support plot inspected. No generic windows, supports or original photographs added. Raster vintage unresolved; OSM update is not construction date and current as-built status remains unverified. Geometry is standalone only; source regional scene unchanged.

Attribution: Overture/OpenStreetMap ODbL and EA DSM/DTM OGL; exact source hashes in report.json. Primary context-only planning source: https://towerhamlets.moderngov.co.uk/documents/s15052/40%20Marsh%20Wall%20Appendices.pdf. No imagery from that document was derived.
''')
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in [P/'review_def7_roof.py',P/'fit_def7_group.py',P/'prepare_def7_massing.py',P/'build_def7_massing.py',P/'check_def7_massing.py',P/'package_def7_study.py']:z.write(f,'scripts/'+f.name)
 for f in (R/'references').glob('def7*.json'):z.write(f,'references/'+f.name)
 for f in [O/'report.json',O/'report.md',O/'verification.json']:z.write(f,f.name)
print(json.dumps(dict(hashes=report['hashes'],recess=r['recess_all_cells'],support=[(q['zone'],q['within_1m_cells'],q['all_cells']) for q in r['zone_diagnostics']]),indent=2))
