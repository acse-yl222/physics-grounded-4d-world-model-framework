from pathlib import Path
import json,numpy as np
from collections import Counter
from shapely.geometry import Polygon
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((R/'geometry.json').read_text());r=json.loads((R/'references/north_quay_east_fit.json').read_text());theta=np.deg2rad(r['rotation_degrees']);rot=np.array([[np.cos(theta),np.sin(theta)],[-np.sin(theta),np.cos(theta)]])
def clip(points,c):
 out=[]
 for a,b in zip(points,points[1:]+points[:1]):
  da=c[:2]@a+c[2];db=c[:2]@b+c[2]
  if da<=1e-10:out.append(a)
  if (da<0)!=(db<0):out.append(a+(b-a)*da/(da-db))
 return out
rows=[]
for rec in r['features']:
 f=next(f for f in g['buildings'] if f['id']==rec['id']);b=rec['parameters_ridge_odn_ridge_u_slope_w_slope_e_south_at_v0_south_slope_north_at_v0_north_slope'];vc=rec['v_origin_m'];planes=np.array([[b[2],0,b[0]-b[2]*b[1]],[b[3],0,b[0]-b[3]*b[1]],[0,b[5],b[4]-b[5]*vc],[0,b[7],b[6]-b[7]*vc]])
 verts=[];roof=[];walls=[];bottom=[];lookup={};area=0;expected=0
 def idx(xyz):
  key=tuple(round(float(x),7) for x in xyz)
  if key not in lookup:lookup[key]=len(verts);verts.append(list(key))
  return lookup[key]
 for part in f['geometry']:
  poly=Polygon(part['outer'],part.get('holes',[]));expected+=poly.area
  for tri in constrained_delaunay_triangles(poly).geoms:
   xy=list(tri.exterior.coords)[:-1];bottom.append([idx([*p,0]) for p in reversed(xy)])
   for k,plane in enumerate(planes):
    points=[rot@np.array(p) for p in xy]
    for j,other in enumerate(planes):
     if k!=j and points:points=clip(points,plane-other)
    if len(points)<3 or Polygon(points).area<1e-9:continue
    area+=Polygon(points).area
    roof.append([idx([*(rot.T@p),plane@[*p,1]-r['datum_m_odn']]) for p in points])
 counts=Counter(tuple(sorted((a,b))) for face in roof for a,b in zip(face,face[1:]+face[:1]))
 for (a,b),n in counts.items():
  if n==1:walls.append([idx([*verts[a][:2],0]),idx([*verts[b][:2],0]),b,a])
 assert abs(area-expected)<1e-5
 rows.append(dict(name=rec['name'].replace(' ','_'),building_id=f['id'],vertices=verts,roof_faces=roof,wall_faces=walls,bottom_faces=bottom,area_m2=area))
(R/'references/east_exterior_hypothesis.json').write_text(json.dumps(dict(objects=rows,scope='Estimated full footprint completion of conditional LiDAR four-plane fits. Edge shape, walls, materials and missing openings unverified; appearance draft only.')))
print([(q['name'],q['area_m2']) for q in rows])
