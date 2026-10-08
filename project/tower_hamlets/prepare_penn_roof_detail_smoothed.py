"""Retain observed support shape; do not bridge low-return holes with a rectangle."""
from pathlib import Path
import json,math,hashlib
import numpy as np
from shapely.geometry import box,Polygon
from shapely.ops import unary_union,transform
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/penn_envelope_study.json').read_text());hi=json.loads((R/'references/penn_high_returns.json').read_text());rr=json.loads((R/'references/penn_roof_review.json').read_text())['parts'][0];c=rr['plane_fits']['2']['coefficients'];cx,cy=rr['center_local_xy_m'];datum=r['datum_odn_m'];cluster=max(hi['thresholds']['0.4']['components'],key=lambda a:a['cells']);pts=np.array(cluster['cells_local_x_y_odn_residual']);d=pts[:,None,:2]-pts[None,:,:2];pairs=d[(d[:,:,0]>.8)&(d[:,:,0]<1.2)&(abs(d[:,:,1])<.1)];axis=np.median(pairs,axis=0);theta=math.atan2(axis[1],axis[0]);co,si=math.cos(theta),math.sin(theta);origin=pts[0,:2];uv=np.column_stack([(pts[:,0]-origin[0])*co+(pts[:,1]-origin[1])*si,-(pts[:,0]-origin[0])*si+(pts[:,1]-origin[1])*co]);grid=np.rint(uv);assert np.max(abs(grid-uv))<.003
p=unary_union([box(u-.5,v-.5,u+.5,v+.5) for u,v in grid]);p=transform(lambda u,v:(origin[0]+u*co-v*si,origin[1]+u*si+v*co),p);parts=list(p.geoms) if hasattr(p,'geoms') else [p];top=float(np.median(pts[:,2])-datum);records=[]
for j,p in enumerate(parts):
 if p.area<3:continue
 raw=p;p=p.simplify(.75,preserve_topology=True);verts=[];roof=[];walls=[];bottom=[];idxs={}
 def bottomz(x,y):return c[0]+c[1]*(x-cx)+c[2]*(y-cy)-datum
 def idx(x,y,z):
  key=tuple(round(float(a),8) for a in [x,y,z])
  if key not in idxs:idxs[key]=len(verts);verts.append(list(key))
  return idxs[key]
 for tri in constrained_delaunay_triangles(p).geoms:
  xy=list(tri.exterior.coords)[:-1];roof.append([idx(x,y,top) for x,y in xy]);bottom.append([idx(x,y,bottomz(x,y)) for x,y in reversed(xy)])
 for ring in [p.exterior,*p.interiors]:
  xy=list(ring.coords)
  for (x,y),(xx,yy) in zip(xy,xy[1:]):walls.append([idx(x,y,bottomz(x,y)),idx(xx,yy,bottomz(xx,yy)),idx(xx,yy,top),idx(x,y,top)])
 r['objects'].append({'name':f'Penn_unidentified_roof_return_{j+1}','building_id':hi['building_id'],'basis':'Estimated raised surface over main20cell group. Simplified0.75m outline approximates17cell core, not a verified physical boundary; constant top is descriptive median. No equipment identity.','vertices':verts,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom,'mapped_area_m2':p.area});records.append({'component':j+1,'estimated_outline_area_m2':p.area,'source_support_area_m2':raw.area,'outline_symmetric_difference_m2':p.symmetric_difference(raw).area,'outline_simplification_m':.75})
r['scope']+=' Main face-connected high-return core represented by estimated raised cell-support surfaces;2cell secondary group remains unmodelled. No bounding rectangle fills lower-return space.';r['source_hashes']['references/penn_high_returns.json']=hashlib.sha256((R/'references/penn_high_returns.json').read_bytes()).hexdigest();r['roof_detail']={'source_cells':len(pts),'top_odn_m':top+datum,'cell_grid_rotation_deg':math.degrees(theta),'max_grid_snap_m':float(np.max(abs(grid-uv))),'components':records,'omitted_support':'One1cell and one2cell face-disconnected fringe, plus separate2cell southern group, remain unmodelled.'};(R/'references/penn_roof_detail_smoothed_study.json').write_text(json.dumps(r,indent=2)+'\n');print(r['roof_detail'])
