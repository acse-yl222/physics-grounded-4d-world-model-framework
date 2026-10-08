"""Create only the conditional interior roof patch; buffer edges are not eaves."""
from pathlib import Path
import json,hashlib
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';group=json.loads((R/'references/britannia_roof_review.json').read_text());part=group['parts'][0];review={'building_id':part['id'],'inset_sensitivity':{'6':{'coefficients':part['plane_fits']['4']['coefficients'],'holdout':part['plane_fits']['4']['holdout']}},'plane':{'center_local_xy_m':part['center_local_xy_m']},'footprint_area_m2':part['area_m2'],'source_hashes':group['source_hashes']};g=json.loads((R/'geometry.json').read_text());f=next(x for x in g['buildings'] if x['id']==review['building_id']);p=unary_union([Polygon(x['outer'],x.get('holes',[])) for x in f['geometry']]).buffer(-4)
c=review['inset_sensitivity']['6']['coefficients'];cx,cy=review['plane']['center_local_xy_m'];datum=4.28000021;verts=[];faces=[];index={}
for tri in constrained_delaunay_triangles(p).geoms:
 face=[]
 for x,y in list(tri.exterior.coords)[:-1]:
  key=(x,y)
  if key not in index:index[key]=len(verts);verts.append([x,y,c[0]+c[1]*(x-cx)+c[2]*(y-cy)-datum])
  face.append(index[key])
 faces.append(face)
assert abs(sum(Polygon([(verts[i][0],verts[i][1]) for i in f]).area for f in faces)-p.area)<1e-7
r={'scope':'Conditional Britannia north wing interior roof-plane candidate. Open surface, 4m inward buffer is a data-support boundary, not a physical roof edge. No perimeter, walls, openings or equipment inferred.','building_id':review['building_id'],'datum_odn_m':datum,'datum_status':'Illustrative shared scene datum; no surveyed building foundation.','area_m2':p.area,'mapped_part_area_m2':review['footprint_area_m2'],'holdout':review['inset_sensitivity']['6']['holdout'],'selection_warning':'Inset size chosen after inspecting residuals; conditional diagnostic errors are not independent accuracy certification.','source_hashes':review['source_hashes']|{'references/britannia_roof_review.json':hashlib.sha256((R/'references/britannia_roof_review.json').read_bytes()).hexdigest()},'objects':[{'name':'Britannia_north_partial_roof','vertices':verts,'roof_faces':faces,'wall_faces':[],'bottom_faces':[]}],'geometry_integrated':False}
(R/'references/britannia_roof_candidate.json').write_text(json.dumps(r,indent=2)+'\n');print(p.area,len(verts),len(faces))
