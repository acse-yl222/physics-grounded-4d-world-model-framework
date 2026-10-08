"""Read-only plane-support audit; no mesh authored from incomplete/mixed returns."""
import runpy,json,numpy as np,hashlib
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';reports=[]
for key in ['fe665','00a65','12c79']:
 d=runpy.run_path(str(S/f'analyze_{key}_lidar001.py'));p=d['p'];z=d['z'];m=d['m'];x=d['x'];y=d['y'];g=d['g'];f=d['f'];ground=d['ground']
 selected=d['masks']['1'] & (z>13.5)&(z<16) if key!='12c79' else d['masks']['1']&(z>10.6)&(z<11.2)
 A=np.column_stack([x[selected]-p.centroid.x,y[selected]-p.centroid.y,np.ones(selected.sum())]);b=np.linalg.lstsq(A,z[selected],rcond=None)[0];res=z[selected]-A@b
 near=[]
 for nf in g['buildings']:
  if nf['id']==f['id'] or nf['id']=='site-support':continue
  q=unary_union([Polygon(a['outer'],a.get('holes',[])) for a in nf['geometry']]);dist=p.distance(q)
  if dist<5:near.append({'id':nf['id'],'distance_m':dist,'intersection_m2':p.intersection(q).area,'shared_boundary_m':p.boundary.intersection(q.boundary).length})
 rr={'id':f['id'],'source_properties':f['source_properties'],'area_m2':p.area,'valid_cells':int(m.sum()),'approx_valid_fraction':float(m.sum()/p.area),'full_footprint_low_dsm_dtm_lt2m':int((m&(z-ground<2)).sum()),'plane_fit':{'selection':'1m inset;13.5<ODN<16' if key!='12c79' else '1m inset;10.6<ODN<11.2','warning':'Height-conditioned sample fitting is descriptive, not whole-roof verification.','sample_count':int(selected.sum()),'origin_xy':[p.centroid.x,p.centroid.y],'slope_dx_dy_intercept_odn':b.tolist(),'rmse_m':float(np.sqrt(np.mean(res**2))),'p95_abs_residual_m':float(np.percentile(abs(res),95))},'neighbors_under5m':near,'no_geometry_changed':True}
 reports.append(rr)
out={'datum_odn_m':4.28000021,'actual_raster_capture_date':None,'native_review':'references/skillion_native001.json','buildings':reports,'decision':{'fe665':'Hold: very narrow footprint with low returns; mapped skillion direction/pitch unspecified.','00a65':'Hold: raster does not cover northern portion; do not extrapolate full roof plane from partial mixed surface.','12c79':'Hold for paired-boundary resolution: strong flat lower plateau contradicts simple whole-footprint skillion assumption; northern high returns align with school neighbour. Need resolve higher-roof extent, not flatten neighbour or invent arbitrary plane.'}}
(R/'references/skillion_plane_audit001.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
