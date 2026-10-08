"""Closed warehouse exterior hypothesis; measured profiles simplified to architectural ridges."""
from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,box
from shapely.ops import unary_union,transform
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());r=json.loads((R/'references/museum_roof_fit.json').read_text());ids=[r['building_id'],r['child_id']];p=unary_union([Polygon(q['outer'],q.get('holes',[])) for b in g['buildings'] if b['id'] in ids for q in b['geometry']]);origin=np.array(r['origin_local_m']);axis=np.array(r['long_axis']);cross=np.array(r['cross_axis']);datum=r['ground_m_odn']
def to_uv(x,y,z=None):return (x-origin[0])*axis[0]+(y-origin[1])*axis[1],(x-origin[0])*cross[0]+(y-origin[1])*cross[1]
p=transform(to_uv,p);rows=[]
for name,region,knots in [('west',p.intersection(box(-1000,-1000,-10,1000)),[-20,-13,-7,-2,2,6,12,20]),('east',p.intersection(box(-10,-1000,1000,1000)),[-20,-9,-3,3,8,14,20])]:
 profile=r['independent_profiles']['profiles'][name]['profile_odn_m'];heights=np.interp(knots,r['cross_profile_knots_v_m'],profile)-datum;verts=[];roof=[];walls=[];bottom=[];index={};area=0
 def face(points,dest):
  ids=[]
  for u,v,z in points:
   xy=origin+u*axis+v*cross;key=(round(float(xy[0]),8),round(float(xy[1]),8),round(float(z),8))
   if key not in index:index[key]=len(verts);verts.append(list(key))
   ids.append(index[key])
  dest.append(ids)
 for va,vb,za,zb in zip(knots,knots[1:],heights,heights[1:]):
  cut=region.intersection(box(-1000,va,1000,vb))
  if cut.is_empty:continue
  def height(v):return float(za+(zb-za)*(v-va)/(vb-va))
  for poly in [cut] if cut.geom_type=='Polygon' else cut.geoms:
   if poly.geom_type!='Polygon':continue
   for t in constrained_delaunay_triangles(poly).geoms:
    xy=list(t.exterior.coords)[:-1];area+=t.area
    if Polygon(xy).exterior.is_ccw is False:xy.reverse()
    face([(u,v,height(v)) for u,v in xy],roof)
   edges=poly.boundary.intersection(region.boundary)
   for line in [edges] if edges.geom_type=='LineString' else getattr(edges,'geoms',[]):
    if line.geom_type!='LineString':continue
    for a,b in zip(list(line.coords)[:-1],list(line.coords)[1:]):face([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],height(b[1])),(a[0],a[1],height(a[1]))],walls)
 for t in constrained_delaunay_triangles(region).geoms:
  xy=list(t.exterior.coords)[:-1]
  if Polygon(xy).exterior.is_ccw:xy.reverse()
  face([(u,v,0) for u,v in xy],bottom)
 assert abs(area-region.area)<1e-5
 rows.append({'name':name,'vertices':verts,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom,'area_m2':area,'knots_v_m':knots,'heights_m':heights.tolist()})
(R/'references/museum_exterior_hypothesis.json').write_text(json.dumps({'objects':rows,'source_owner_ids':ids,'scope':'Simplified three-ridge profile completion over exact mapped union. Missing peripheral roof shape extrapolated; longitudinal level split estimated from fit. Full walls added; openings unknown. Hipped ends not resolved in this draft.','materials':'Brick/stone/slate palette supported by Historic England text; exact colors estimated.'})+'\n');print([(q['name'],q['area_m2']) for q in rows])
