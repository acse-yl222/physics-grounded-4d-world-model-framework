"""Quantify fit/raw shared XY boundaries without changing heights."""
from pathlib import Path
import json
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references';report=json.loads((R/'north_quay_allowners_constrained_roof_candidate.json').read_text())
def obj(name):
 v=[];f=[]
 for l in (R/name).read_text().splitlines():
  if l.startswith('v '):v.append(list(map(float,l.split()[1:])))
  if l.startswith('f '):f.append([int(q)-1 for q in l.split()[1:]])
 return np.array(v),f
rows=[]
for fitted in [q for q in report['objects'] if q['representation']=='fitted_supported_roof']:
 owner=fitted['id'].removesuffix('__fitted');raw=next(q for q in report['objects'] if q['id']==owner+'__raw_remainder');fv,ff=obj(fitted['obj']);rv,rf=obj(raw['obj']);polys=[Polygon(fv[f,:2]) for f in ff];shape=unary_union(polys);errs=[];coords=[]
 for vert in rv:
  point=Point(vert[:2])
  if shape.boundary.distance(point)>1e-6:continue
  for face,poly in zip(ff,polys):
   if poly.distance(point)>1e-6:continue
   xyz=fv[face];coef=np.linalg.solve(np.column_stack([xyz[:,:2],np.ones(3)]),xyz[:,2]);dz=vert[2]-coef@[vert[0],vert[1],1];errs.append(float(dz));coords.append(vert.tolist());break
 e=np.array(errs);rows.append({'id':owner,'matched_boundary_vertices':len(e),'abs_median_m':float(np.median(abs(e))) if len(e) else None,'abs_p95_m':float(np.percentile(abs(e),95)) if len(e) else None,'abs_max_m':float(max(abs(e))) if len(e) else None,'over_0_3m':int((abs(e)>.3).sum()),'samples':[{'position_enu_m':p,'raw_minus_fit_m':d} for p,d in zip(coords,errs)]})
(R/'north_quay_allowners_constrained_fit_seams.json').write_text(json.dumps({'geometry_modified':False,'scope':'Sampled exact projected fit/raw boundaries. Seam discontinuities are model mismatch, not evidence of actual vertical walls.','owners':rows},indent=2)+'\n');print([{k:v for k,v in q.items() if k!='samples'} for q in rows])
