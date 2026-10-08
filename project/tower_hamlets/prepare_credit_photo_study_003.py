"""Bounded external neighbor blocker variant; historical002 remains immutable."""
from pathlib import Path
import json,hashlib,collections
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';source=P/'prepare_credit_photo_study_002.py';oldpath=R/'references/credit_photo_study_002.json';oldbytes=oldpath.read_bytes();code=source.read_text()
# Replay without writing historical output and preserve every unblocked primitive.
base=code.split('merged={}')[0];ns0={'__file__':str(source)};exec(base,ns0)
hook="""
_external=json.loads((R/'references/credit3a_authoring001.json').read_text())
_external_zones=[(unary_union([Polygon(q['outer'],q.get('holes',[])) for q in z['geometry']]),z['height_m']) for z in _external['zones']]
"""
newcode=code.replace('for qi,(q,p)',hook+'\nfor qi,(q,p)',1)
needle="    if cover>=h-.02:continue"
newcode=newcode.replace(needle,"    cover=max([cover]+[height for poly,height in _external_zones if poly.buffer(.025).covers(mid)])\n"+needle,1)
newcode=newcode.replace("R/'references/credit_photo_study_002.json'","R/'references/credit_photo_study_003.json'")
ns={'__file__':str(source)};exec(newcode,ns)
assert oldpath.read_bytes()==oldbytes
oldcnt=collections.Counter(json.dumps(q,sort_keys=True) for q in ns0['rows']);newcnt=collections.Counter(json.dumps(q,sort_keys=True) for q in ns['rows']);added=newcnt-oldcnt;removed=oldcnt-newcnt
assert not added,'Unexpected changed/new primitive'
oldintervals=ns0['intervals'];newintervals=ns['intervals'];gone=[i for i in oldintervals if i not in newintervals];assert all(i in oldintervals for i in newintervals)
report=dict(original_sha256=hashlib.sha256(oldbytes).hexdigest(),original_generator_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),neighbor_authoring_sha256=hashlib.sha256((R/'references/credit3a_authoring001.json').read_bytes()).hexdigest(),original_primitives=len(ns0['rows']),new_primitives=len(ns['rows']),removed_primitives=sum(removed.values()),added_or_changed_primitives=sum(added.values()),remaining_primitives_exact=True,removed_intervals=gone,remaining_intervals_exact=True)
d=json.loads((R/'references/credit_photo_study_003.json').read_text());d['scope']='003 interface-only:3a neighbor roofzones used as external blockers; all retained002 primitives/material intentions unchanged. '+d['scope'];d['interface_update']=report;(R/'references/credit_photo_study_003.json').write_text(json.dumps(d,indent=2)+'\n');(R/'references/credit003_interface_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
