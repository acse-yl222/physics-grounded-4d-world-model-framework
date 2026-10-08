from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import split,unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());b=next(x for x in g['buildings'] if '89962572' in x['id']);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]);prof=json.loads((R/'references/owner899_spatial_profiles.json').read_text());o=np.array(prof['origin']);u=np.array(prof['u']);v=np.array(prof['v']);data=np.load(R/'references/owner899_samples.npz');datum=4.28000021
def rect(a,b,c,d):return Polygon([o+x*u+y*v for x,y in [(a,c),(b,c),(b,d),(a,d)]])
north=p.intersection(rect(6,32,-100,8));core=p.intersection(rect(-19,4,-100,-2.5));base=p.difference(north).difference(core)
zones=[('outer_roof_estimated',base,54.5-datum-.4,54.5),('north_roof_estimated',north,54.5-datum-.4,56.08),('central_plant_envelope_estimated',core,54.5-datum-.4,59.65)];rows=[];metrics=[]
for name,poly,lo,odn in zones:
 verts=[];faces=[];idx={};hi=odn-datum
 def vi(x,y,z):
  k=tuple(round(float(t),7) for t in [x,y,z])
  if k not in idx:idx[k]=len(verts);verts.append(list(k))
  return idx[k]
 for tri in constrained_delaunay_triangles(poly).geoms:
  q=list(tri.exterior.coords)[:-1];faces.append([vi(x,y,hi) for x,y in q]);faces.append([vi(x,y,lo) for x,y in reversed(q)])
 for ring in [poly.exterior,*poly.interiors]:
  q=list(ring.coords)
  for (x,y),(a,c) in zip(q,q[1:]):faces.append([vi(x,y,lo),vi(a,c,lo),vi(a,c,hi),vi(x,y,hi)])
 rows.append(dict(name=name,kind='estimated_massing',building_id=b['id'],aggregate_alias_id=b['id'],vertices=verts,roof_faces=faces,wall_faces=[],bottom_faces=[],top_odn_m=odn))
 domain=poly
 m=data['valid']&np.array([domain.contains(Point(x,y)) for x,y in zip(data['x'].flat,data['y'].flat)]).reshape(data['x'].shape);z=data['z'][m];err=z-odn
 metrics.append(dict(zone=name,area_m2=domain.area,all_cells=len(z),within_1m_cells=int((abs(err)<=1).sum()),all_rmse_m=float(np.sqrt(np.mean(err**2))),all_median_abs_m=float(np.median(abs(err))),all_p95_abs_m=float(np.percentile(abs(err),95)),excluded_cells=0,low_return_cells=int((z<20).sum())))
r=dict(objects=rows,parent_id=b['id'],replace_ids=[],candidate_owner=b['id'],integration_status='ROOF_ONLY_DIAGNOSTIC_NOT_COMPLETE_OWNER_REPLACEMENT',scope='Owner899, spatially attributed25 Bank Street west podium: partial editable roof-only shell. Roof levels54.5/56.08/59.65mODN estimated from nativeDSM spatial plateaus. Bottom54.1mODN is illustrative0.4m shell thickness, not architectural underside. No supporting body or columns reconstructed.',datum_odn_m=datum,original_metadata={k:v for k,v in b.items() if k!='geometry'},zone_diagnostics=metrics,footprint_symdiff_m2=unary_union([q[1] for q in zones]).symmetric_difference(p).area,source_ids=['overture_buildings_20260923','ea_lidar_dsm_1m','ea_lidar_dtm_1m'],limitations=['Roof-only diagnostic cannot replace full building; actual elevated underside/rail clearance unknown.','West4m strip at~74.3ODN aligns neighboringMorganroof and may be overhang or registration/ownership mismatch; not adopted as this owner roof. Full footprint low roof estimate there is uncertain.','Exact plant outlines and northern end not verified; no facade detailing without visiblelicensedphoto.','No fresh imagery acquired or deniedsource retries.'],source_hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/owner899_spatial_profiles.json']})
(R/'references/owner899_roof_study.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(metrics,indent=2))
