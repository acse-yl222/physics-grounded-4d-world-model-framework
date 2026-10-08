from pathlib import Path
import json,hashlib,struct,zipfile,shutil
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/northern-trust-massing-001';r=json.loads((R/'references/northern_trust_massing_study.json').read_text());blob=(O/'northern_trust.glb').read_bytes();n=struct.unpack_from('<I',blob,12)[0];glb=json.loads(blob[20:20+n]);nodes=[q for q in glb['nodes'] if 'mesh' in q];assert len(nodes)==3;assert all(q['extras']['building_id']==r['parent_id'] for q in nodes);assert len(glb['materials'])==1;assert glb['materials'][0].get('alphaMode','OPAQUE')=='OPAQUE'
vr=json.loads((O/'verification.json').read_text());vr.update(glb_building_ids_equal=True,glb_mesh_count=len(glb['meshes']),glb_materials=glb['materials'],visually_inspected=['overview.png','roof.png','rear.png','northern_trust_zone_support.png'],visual_findings='Clean bounded partial massing; no observed mesh artifacts. Simplified roof envelopes omit complex machinery. Facade and foundation unresolved.');(O/'verification.json').write_text(json.dumps(vr,indent=2)+'\n')
# Correct date language in this task's preliminary review only; numeric data unaffected.
f=R/'references/northern_trust_roof_review.json';a=json.loads(f.read_text());a['limitations'][0]='EA composite DSM/DTM OGL; acquisition vintage unresolved. Overlapping catalog surveys do not prove mixed dates or assign per-building year. 2026 Overture footprints.';a['visual_reviewed']=True;f.write_text(json.dumps(a,indent=2)+'\n')
for name in ['northern_trust_zone_support.png','northern_trust_roof_detail.png','northern_trust_independent_checks.json']:shutil.copy2(R/'references'/name,O/name)
report=dict(identity='Northern Trust,50 Bank Street',replace_ids=r['replace_ids'],scope=r['scope'],footprint_area_m2=r['footprint_area_m2'],roof_odn_m=[62.1,69.55,68.2],roof_scene_z_m=[57.81999979,65.26999979,63.91999979],zone_diagnostics=r['zone_diagnostics'],neighbor_interfaces=r['neighbor_interfaces'],sources=r['primary_sources'],limitations=r['limitations'],verification=vr,hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [O/'northern_trust.glb',O/'northern_trust.blend',R/'references/northern_trust_massing_study.json']});(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(O/'report.md').write_text('''# Northern Trust / 50 Bank Street partial study

Owner `8a6a6456-5ff1-4be7-9a11-7a82b9ed825d`. Exact mapped plan area 2161.034543 m² is retained. Baseline 48 m is 16 floors × assumed 3 m, not measured height. Northern Trust current office page and its March2019 legal certification identify 50 Bank Street; the latter establishes the address by that date, not a roof capture date.

Estimated body roof 62.1 m ODN and two conservative roof envelopes 69.55 /68.2 m ODN become scene z57.81999979 /65.26999979 /63.91999979 using shared ODN4.28000021. No local-ground renormalization. Inherited base z0 remains illustrative.

Central plateau has368/369 native cells within1 m; southern153/153. Remaining body domain has490/1639 within1 m and264 low returns below20 m ODN. It is explicitly incomplete/estimated: north strip and complex equipment are unresolved, not fitted away or rejected. Chosen inset boundaries are approximate, and conditional spatial holdout evaluates height within these domains rather than independently validating boundaries.

East Wintergarden d8c9283a shares35.001641 m, from(28.12873449,-297.11416891) to(22.10179441,-331.59301596). Exact mapped planar intersection is zero; no ornament or extension crosses this edge. Neighbor baseline6 m is unchanged. Native vertex rounding introduces only numerical boundary residue; see independent checks.

Three closed editable components,40 triangles. Native reopen and GLB reimport agree; owner IDs and opaque neutral material verified. Overview, rear, roof and sample/zone plot actually inspected. Layered solids retain touching internal caps; no boolean-union simulation-volume claim.

The licensed local Ollie11491155 panorama was actually re-inspected, but supplies no attributable measurable Northern Trust elevation. No facade arrays, equipment detail or original photography included. Composite raster acquisition vintage remains unresolved; overlapping survey catalog dates do not establish per-building capture date. No new imagery acquisition.

Primary sources: https://www.northerntrust.com/united-states/about-us/locations/gb/london-50-bank-street (undated, checked2026-10-07); https://www.northerntrust.com/documents/legal/usa-patriot-act-global-certification.pdf (document as ofMarch2019, upload date unknown). Geographic source attribution: Overture2026-09-23 /OpenStreetMap ODbL; Environment Agency LiDAR DSM/DTM OGL. Original inputs and regional builds remain untouched.
''')
files=[P/f'{pre}_northern_trust_{post}.py' for pre,post in [('review','roof'),('fit','group'),('prepare','massing'),('build','massing'),('check','massing'),('package','study')]]
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,'scripts/'+f.name)
 for f in (R/'references').glob('northern_trust*.json'):z.write(f,'references/'+f.name)
 for f in [O/'report.md',O/'report.json',O/'verification.json']:z.write(f,f.name)
print(json.dumps(report['hashes'],indent=2))
