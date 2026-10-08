from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/britannia_envelope_study.json').read_text());low=json.loads((R/'references/britannia_low_returns.json').read_text());g=json.loads((R/'geometry.json').read_text());out=[]
for q in r['objects']:
 f=next(f for f in g['buildings'] if f['id']==q['building_id']);p=unary_union([Polygon(x['outer'],x.get('holes',[])) for x in f['geometry']]);v=np.array(q['vertices']);ids=sorted({i for face in q['roof_faces'] for i in face});roof=v[ids];A=np.column_stack([np.ones(len(roof)),roof[:,:2]]);c=np.linalg.lstsq(A,roof[:,2],rcond=None)[0];verts=[];faces=[]
 for comp in low['components_8_neighbor']:
  for poly in comp['polygons_local_xy']:
   mask=Polygon(poly['outer'],poly.get('holes',[])).intersection(p)
   for tri in constrained_delaunay_triangles(mask).geoms:
    face=[]
    for x,y in list(tri.exterior.coords)[:-1]:face.append(len(verts));verts.append([x,y,float(c@[1,x,y]+.15)])
    faces.append(face)
 if faces:out.append({'name':q['name']+'_uncertainty','building_id':q['building_id'],'vertices':verts,'faces':faces})
(R/'references/britannia_uncertainty_overlay.json').write_text(json.dumps({'scope':'Non-structural diagnostic overlay: original terrain-like raster cell domains projected0.15m above estimated roofs for visibility. Not physical roof patches or material.','objects':out},indent=2)+'\n');print(len(out),'overlay groups')
