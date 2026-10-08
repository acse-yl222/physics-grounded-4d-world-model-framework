"""Rebuild only Citi's shared-edge ornaments above a piecewise neighboring roof."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
source=Path(__file__).with_name('prepare_citi_envelope_photo_study.py')
original=(R/'references/citi_envelope_photo_study.json').read_bytes()
interface=json.loads((R/'references/citi_neighbor_shared_interface.json').read_text())
# Execute the retained scene generator with a bounded prism interceptor. Its other
# facade cadence, backing and material grouping remain unchanged.
hook=r'''
from shapely.ops import split
_base_prism=prism
_interface=json.loads((R/'references/citi_neighbor_shared_interface.json').read_text())
_ia,_ib=_interface['line_a'],_interface['line_b'];_length=_interface['length_m']
_ex=(_ib[0]-_ia[0])/_length;_ey=(_ib[1]-_ia[1])/_length
_changed=[];_untouched=[]
def _along(x,y):return (x-_ia[0])*_ex+(y-_ia[1])*_ey
def _point(s,n):return (_ia[0]+s*_ex-n*_ey,_ia[1]+s*_ey+n*_ex)
def _slab(s0,s1):return Polygon([_point(s0,-100),_point(s1,-100),_point(s1,100),_point(s0,100)])
def _poly_parts(p):
 return [p] if p.geom_type=='Polygon' else [q for q in getattr(p,'geoms',[]) if q.geom_type=='Polygon']
def _variable_prism(p,lo,hi,name,kind,owner,roof):
 # Piece is split at both roof/lo and roof/hi crossings before triangulation.
 vertices=[];faces=[];idx={}
 def vi(x,y,z):
  k=(round(x,7),round(y,7),round(z,7))
  if k not in idx:idx[k]=len(vertices);vertices.append(list(k))
  return idx[k]
 for tri in constrained_delaunay_triangles(p).geoms:
  xy=list(tri.exterior.coords)[:-1]
  faces.append([vi(x,y,hi) for x,y in xy]);faces.append([vi(x,y,max(lo,roof(x,y))) for x,y in reversed(xy)])
 for ring in [p.exterior,*p.interiors]:
  for (x,y),(xx,yy) in zip(list(ring.coords),list(ring.coords)[1:]):
   face=[vi(x,y,max(lo,roof(x,y))),vi(xx,yy,max(lo,roof(xx,yy))),vi(xx,yy,hi),vi(x,y,hi)]
   face=list(dict.fromkeys(face))
   if len(face)>=3:faces.append(face)
 rows.append(dict(name=name,kind=kind,building_id=owner,vertices=vertices,roof_faces=faces,wall_faces=[],bottom_faces=[]))
def prism(poly,lo,hi,name,kind,owner):
 ga=globals().get('a');gb=globals().get('b')
 shared=kind!='backing' and ga is not None and gb is not None and math.dist(ga,_ia)<1e-6 and math.dist(gb,_ib)<1e-6
 if not shared:
  _base_prism(poly,lo,hi,name,kind,owner);_untouched.append(rows[-1]);return
 before=len(rows)
 for seg in _interface['segments']:
  s0,s1=seg['s_m_from_a'];h0,h1=seg['top_scene_z_endpoints'];slope=(h1-h0)/(s1-s0)
  roof=lambda x,y,h0=h0,s0=s0,slope=slope:h0+slope*(_along(x,y)-s0)+.02
  pieces=_poly_parts(poly.intersection(_slab(s0,s1)))
  if abs(slope)>1e-12:
   for level in (lo,hi):
    crossing=s0+(level-h0-.02)/slope
    if s0<crossing<s1:
     line=LineString([_point(crossing,-100),_point(crossing,100)])
     pieces=[q for part in pieces for q in _poly_parts(split(part,line))]
  for p in pieces:
   if p.area<1e-10 or roof(p.representative_point().x,p.representative_point().y)>=hi-1e-8:continue
   _variable_prism(p,lo,hi,name,kind,owner,roof)
 _changed.append({'name':name,'original_z':[lo,hi],'pieces':len(rows)-before})
'''
code=source.read_text().replace('main=next(',hook+'\nmain=next(',1)
code=code.replace("R/'references/citi_envelope_photo_study.json'","R/'references/citi_neighbor_interface_study.json'")
ns={'__file__':str(source),'__name__':'__main__'}
exec(compile(code,str(source),'exec'),ns)
assert (R/'references/citi_envelope_photo_study.json').read_bytes()==original
new=json.loads((R/'references/citi_neighbor_interface_study.json').read_text());old=json.loads(original)
assert new['height_zones']==old['height_zones']
for obj in old['objects']:
 if obj['kind'] in ('backing','topglass'):
  assert obj==next(q for q in new['objects'] if q['kind']==obj['kind'])
new['scope']+=' Shared-neighbor ornament clipped above piecewise roof with2cm clearance; all other geometry retained.'
new['interface_update']={'interface':interface,'original_source_sha256':hashlib.sha256(original).hexdigest(),'generator_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'affected_prism_calls':len(ns['_changed']),'unchanged_prism_calls':len(ns['_untouched']),'backing_and_topglass_exactly_preserved':True,'changed_prisms':ns['_changed']}
(R/'references/citi_neighbor_interface_study.json').write_text(json.dumps(new,indent=2)+'\n')
print('Changed',len(ns['_changed']),'shared-edge prism calls; preserved',len(ns['_untouched']))
