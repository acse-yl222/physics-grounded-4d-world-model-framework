"""Estimated whole mapped envelopes, separate from conditional roof evidence."""
from pathlib import Path
import json,hashlib
from collections import Counter
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());review=json.loads((R/'references/penn_roof_review.json').read_text());datum=4.28000021;rows=[];checks=[]
for rr in review['parts']:
 f=next(f for f in g['buildings'] if f['id']==rr['id']);p=unary_union([Polygon(a['outer'],a.get('holes',[])) for a in f['geometry']]);label=rr['label'];verts=[];roof=[];walls=[];bottom=[];ix={}
 if label=='1':
  c=rr['plane_fits']['2']['coefficients'];cx,cy=rr['center_local_xy_m'];height=lambda x,y:c[0]+c[1]*(x-cx)+c[2]*(y-cy)-datum;basis='2m-inset conditional plane extended to mapped perimeter; outside inset and across low returns is estimated.'
 elif label=='5':
  height=lambda x,y:f['height_m'];basis='Original baseline retained: mixed neighboring high returns; no single roof height accepted.'
 else:
  h=rr['insets']['4']['dsm_odn_m']['median']-datum;height=lambda x,y:h;basis='Estimated constant roof at unfiltered4m-inset DSM median; full-plane tests failed, perimeter and raised features unverified.'
 def idx(x,y,z):
  key=tuple(round(float(v),8) for v in [x,y,z])
  if key not in ix:ix[key]=len(verts);verts.append(list(key))
  return ix[key]
 for tri in constrained_delaunay_triangles(p).geoms:
  xy=list(tri.exterior.coords)[:-1];roof.append([idx(x,y,height(x,y)) for x,y in xy]);bottom.append([idx(x,y,0) for x,y in reversed(xy)])
 for ring in [p.exterior,*p.interiors]:
  xy=list(ring.coords)
  for (x,y),(xx,yy) in zip(xy,xy[1:]):walls.append([idx(x,y,0),idx(xx,yy,0),idx(xx,yy,height(xx,yy)),idx(x,y,height(x,y))])
 area=sum(Polygon([(verts[i][0],verts[i][1]) for i in face]).area for face in roof);assert abs(area-p.area)<1e-6;edges=Counter()
 for face in roof+walls+bottom:
  for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted([a,b]))]+=1
 assert set(edges.values())=={2}
 rows.append({'name':('Unresolved_' if label=='5' else '')+'Penn Court_part_'+label,'building_id':f['id'],'basis':basis,'vertices':verts,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom,'mapped_area_m2':p.area,'baseline_height_m':f['height_m']});checks.append({'id':f['id'],'area_m2':area,'closed_indexed_edge_incidence':2})
r={'scope':'Penn Court estimated exterior envelope. Conditional2m-inset plane extended to mapped perimeter; walls and shared4.28mODN datum estimated. Original57m floor-count baseline retained in parameters. Scattered high returns omitted, no roof equipment or facade details inferred. Not surveyed current geometry.','datum_odn_m':datum,'datum_status':'Shared illustrative flat-scene datum, not surveyed building bases.','objects':rows,'geometry_checks':checks,'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/penn_roof_review.json','references/penn_roof_review.json']},'geometry_integrated':False}
(R/'references/penn_envelope_study.json').write_text(json.dumps(r,indent=2)+'\n');print('Penn shells',sum(x['area_m2'] for x in checks),'m2')
