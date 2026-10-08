"""Clean roof meshes with evidence planes and explicitly estimated plan partitions."""
from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,box,Point,MultiPoint
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());b=next(b for b in g['buildings'] if b['id']=='overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]);levels=json.loads((R/'references/carpark_level_planes.json').read_text());main=json.loads((R/'references/carpark_main_plane.json').read_text());half=Polygon([(-500,100),(-100,100),(-100,243.7),(-500,371.7)]);mainp=p.intersection(half).intersection(box(-500,100,-262,500));remaining=p.difference(mainp);upper_vertices=[list(map(float,l.split()[1:3])) for l in (R/'references/carpark_plane_upper_observed_band.obj').read_text().splitlines() if l.startswith('v ')];upper_extent=MultiPoint(upper_vertices).minimum_rotated_rectangle.buffer(.5,join_style=2);high=remaining.intersection(upper_extent);low=remaining.difference(high);zones=[('main',mainp,main),('high',high,levels['planes'][2]),('low',low,levels['planes'][0])];rows=[]
for name,shape,r in zones:
 v=[];f=[];lookup={};surface_area=0.;cx,cy=r['center_xy_m'];a,b,c=r['coefficients_odn_m']
 def height(x,y):return a+b*(x-cx)+c*(y-cy)-4.28000021
 def face(points):
  inds=[]
  for pt in points:
   key=tuple(round(float(x),8) for x in pt)
   if key not in lookup:lookup[key]=len(v);v.append(list(pt))
   inds.append(lookup[key])
  f.append(inds)
 for poly in [shape] if shape.geom_type=='Polygon' else shape.geoms:
  for t in constrained_delaunay_triangles(poly).geoms:
   if not poly.covers(t.representative_point()) or t.intersection(poly).area<t.area-1e-7:continue
   surface_area+=t.area
   xy=list(t.exterior.coords)[:-1];xyz=[(x,y,height(x,y)) for x,y in xy]
   if np.cross(np.array(xyz[1])-xyz[0],np.array(xyz[2])-xyz[0])[2]<0:xyz.reverse()
   face(xyz);face([(x,y,z-.28) for x,y,z in reversed(xyz)])
  from shapely.geometry.polygon import orient
  poly=orient(poly,sign=1)
  for ring in [poly.exterior,*poly.interiors]:
   for q,t in zip(list(ring.coords)[:-1],list(ring.coords)[1:]):
    x,y=q;xx,yy=t;z=height(x,y);zz=height(xx,yy);face([(x,y,z-.28),(xx,yy,zz-.28),(xx,yy,zz),(x,y,z)])
 assert abs(surface_area-shape.area)<1e-5,(name,surface_area,shape.area)
 rows.append({'name':name,'vertices':v,'faces':f,'area_m2':shape.area,'geometry':shape.__geo_interface__,'plane':r['coefficients_odn_m'],'center':r['center_xy_m']})
assert abs(sum(q['area_m2'] for q in rows)-p.area)<1e-6
columns={}
for q in json.loads((R/'exports/carpark-cad-001/mesh.json').read_text()):
 if q['kind']!='column':continue
 v=np.array(q['vertices']);x,y=(v[:,:2].min(axis=0)+v[:,:2].max(axis=0))/2
 for name,poly,r in zones:
  if poly.buffer(1e-6).covers(Point(x,y)):
   columns[q['name']]={'plane':r['coefficients_odn_m'],'center':r['center_xy_m']};break
(R/'references/carpark_exterior_roof_005.json').write_text(json.dumps({'zones':rows,'column_upper_planes':columns,'datum_odn_m':4.28000021,'basis':'Observed plane equations; upper platform extent from oriented rectangle of supported observed upper patches plus estimated0.5m margin. Other partitions estimated. Not measured roof breaklines; appearance hypothesis.'})+'\n');print([(q['name'],q['area_m2']) for q in rows])
