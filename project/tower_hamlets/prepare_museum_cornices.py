"""Estimated stone cornices, supported in type by Historic England text."""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';d=json.loads((R/'references/warehouse_junctions_repaired.json').read_text());reports=[]
for q in list(d['objects']):
 if q['name'] not in ['west','east']:continue
 v=q['vertices'];p=unary_union([Polygon([v[i][:2] for i in f]) for f in q['roof_faces']]);ring=p.buffer(.16,join_style=2).difference(p.buffer(-.08,join_style=2));z=min(v[i][2] for f in q['roof_faces'] for i in f)-.35;verts=[];faces=[];idx={}
 def vi(x,y,z):
  key=(round(x,8),round(y,8),round(z,8))
  if key not in idx:idx[key]=len(verts);verts.append(list(key))
  return idx[key]
 for poly in [ring] if ring.geom_type=='Polygon' else ring.geoms:
  for t in constrained_delaunay_triangles(poly).geoms:
   xy=list(t.exterior.coords)[:-1];faces.append([vi(x,y,z+.25) for x,y in xy]);faces.append([vi(x,y,z) for x,y in reversed(xy)])
  for edge in [poly.exterior,*poly.interiors]:
   coords=list(edge.coords)
   for (x,y),(a,b) in zip(coords,coords[1:]):faces.append([vi(x,y,z),vi(a,b,z),vi(a,b,z+.25),vi(x,y,z+.25)])
 d['objects'].append({'name':q['name']+'_stone_cornice_estimated','vertices':verts,'roof_faces':[],'wall_faces':faces,'bottom_faces':[]});reports.append({'section':q['name'],'bottom_z_m':z,'height_m':.25,'projection_m':.16,'basis':'Historic England1242440 describes cornices and stone dressings; dimensions, location and profile estimated.'})
d['scope']+=' Museum stone cornices added as explicitly estimated appearance detail; shared section ends require architectural verification.';(R/'references/warehouse_cornice_study.json').write_text(json.dumps(d));(R/'references/museum_cornice_parameters.json').write_text(json.dumps(reports,indent=2))
