from pathlib import Path
import json,hashlib,zipfile
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/quay1-facade-study-001'
s=next(x for x in json.load(open(R/'references/sources.json')) if x['id']=='pexels_ollie_11491155');(O/'sources.json').write_text(json.dumps([s],indent=2));c=json.load(open(O/'checks.json'));c['visual_reviewed']=True;c['inspected_views']=['overview.png','detail.png','upper.png','rear.png','roof.png'];c['limitations']='Partial facade scope and inherited blank base/roof remain conspicuous; no whole-building completion claim.';c['shared_segment_jamb_deduplication']='Removed6shaft+6upper duplicate segment-end jambs, keeping each following segment start. No footprint smoothing or roof edit.';(O/'checks.json').write_text(json.dumps(c,indent=2))
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in ['build_quay1_facade001.py','audit_quay1_photo_independent001.py','package_quay1_facade001.py']:z.write(P/n,n)
 for n in ['authoring.json','checks.json','neighbor-interface.json','sources.json','report.md']:z.write(O/n,n)
 for n in ['audit.json','report.md','neighbor-bearing-context.png']:z.write(R/'exports/quay1-photo-independent-001'/n,'identification/'+n)
h={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='hashes.json' and p.suffix!='.blend1'};(O/'hashes.json').write_text(json.dumps(h,indent=2));print(json.dumps(c,indent=2));print({k:v for k,v in h.items() if k.endswith(('.blend','.glb'))})
