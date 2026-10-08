"""Closed warehouse exterior hypothesis; measured profiles simplified to architectural ridges."""
from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,box,LineString
from shapely.ops import unary_union,transform,split
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());r=json.loads((R/'references/munich_profile_fit.json').read_text());ids=['overture-building-118734b4-49b7-4a0b-80f8-4f7b33801433'];p=unary_union([Polygon(q['outer'],q.get('holes',[])) for b in g['buildings'] if b['id'] in ids for q in b['geometry']]);origin=np.array([0.,0.]);theta=np.deg2rad(r['rotation_deg']);axis=np.array([np.cos(theta),np.sin(theta)]);cross=np.array([-np.sin(theta),np.cos(theta)]);datum=r['datum_odn_m']
def to_uv(x,y,z=None):return (x-origin[0])*axis[0]+(y-origin[1])*axis[1],(x-origin[0])*cross[0]+(y-origin[1])*cross[1]
p=transform(to_uv,p);rows=[];hip=json.loads((R/'references/munich_hip_end.json').read_text());cap0,slope=hip['coefficients'][-2:];uc=hip['u_center_m']
for name,region,knots in [('Munich',p,[p.bounds[1],179,184,189,194,199,206,p.bounds[3]])]:
 knots=sorted(set(k for k in knots if p.bounds[1]<=k<=p.bounds[3]));heights=np.interp(knots,r['knots_v_m'],r['height_odn_m'])-datum;verts=[];roof=[];walls=[];bottom=[];index={};area=0
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
  def base(v):return float(za+(zb-za)*(v-va)/(vb-va))
  def height(u,v):return min(base(v),cap0+slope*(u-uc)-datum)
  for poly in [cut] if cut.geom_type=='Polygon' else cut.geoms:
   if poly.geom_type!='Polygon':continue
   line=LineString([(uc+(base(v)+datum-cap0)/slope,v) for v in [-1000,1000]])
   pieces=list(split(poly,line).geoms)
   for t in [t for piece in pieces for t in constrained_delaunay_triangles(piece).geoms]:
    xy=list(t.exterior.coords)[:-1];area+=t.area
    if Polygon(xy).exterior.is_ccw is False:xy.reverse()
    face([(u,v,height(u,v)) for u,v in xy],roof)
   edges=poly.boundary.intersection(region.boundary)
   for line in [edges] if edges.geom_type=='LineString' else getattr(edges,'geoms',[]):
    if line.geom_type!='LineString':continue
    for a,b in zip(list(line.coords)[:-1],list(line.coords)[1:]):face([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],height(*b)),(a[0],a[1],height(*a))],walls)
 for t in constrained_delaunay_triangles(region).geoms:
  xy=list(t.exterior.coords)[:-1]
  if Polygon(xy).exterior.is_ccw:xy.reverse()
  face([(u,v,0) for u,v in xy],bottom)
 from collections import Counter
 counts=Counter(tuple(sorted((a,b))) for f in roof for a,b in zip(f,f[1:]+f[:1]));walls=[]
 for (a,b),n in counts.items():
  if n!=1:continue
  lower=[]
  for i in [a,b]:
   key=(verts[i][0],verts[i][1],0.0)
   if key not in index:index[key]=len(verts);verts.append(list(key))
   lower.append(index[key])
  walls.append([lower[0],lower[1],b,a])
 assert abs(area-region.area)<1e-5
 rows.append({'name':name,'vertices':verts,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom,'area_m2':area,'knots_v_m':knots,'heights_m':heights.tolist()})
(R/'references/munich_exterior_hypothesis.json').write_text(json.dumps({'objects':rows,'source_owner_ids':ids,'scope':'Munich appearance hypothesis: simplified three-ridge profile intersected by a fitted western hip plane. Interior fit improves both spatial holdouts; perimeter completion, walls and material remain estimated. Not verified as-built; openings absent.','materials':'Brick/stone/slate palette supported by Historic England text; exact colors estimated.'})+'\n');print([(q['name'],q['area_m2']) for q in rows])
