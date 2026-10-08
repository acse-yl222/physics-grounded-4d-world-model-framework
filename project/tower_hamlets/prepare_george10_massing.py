from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import split,unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());b=next(x for x in g['buildings'] if '3a0a73a0' in x['id']);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]);prof=json.loads((R/'references/george10_spatial_profiles.json').read_text());o=np.array(prof['origin']);u=np.array(prof['u']);v=np.array(prof['v']);data=np.load(R/'references/george10_samples.npz');datum=4.28000021
xy=np.array(b['geometry'][0]['outer']);aa=xy[6];bb=xy[16];dv=bb-aa;parts=list(split(p,LineString([aa-dv*5,bb+dv*5])).geoms);podium,tower=sorted(parts,key=lambda q:q.centroid.x)
core=tower.intersection(Polygon([o+a*u+c*v for a,c in [(8,-8),(17,-8),(17,7),(8,7)]]))
zones=[('podium_estimated',podium,0,29.65),('tower_estimated',tower,0,127.22),('roof_core_envelope_estimated',core,127.22-datum,134.4)];rows=[];metrics=[]
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
 domain=poly.difference(core) if name=='tower_estimated' else poly
 m=data['valid']&np.array([domain.contains(Point(x,y)) for x,y in zip(data['x'].flat,data['y'].flat)]).reshape(data['x'].shape);z=data['z'][m];err=z-odn
 metrics.append(dict(zone=name,area_m2=domain.area,all_cells=len(z),within_1m_cells=int((abs(err)<=1).sum()),all_rmse_m=float(np.sqrt(np.mean(err**2))),all_median_abs_m=float(np.median(abs(err))),all_p95_abs_m=float(np.percentile(abs(err),95)),excluded_cells=0,low_return_cells=int((z<20).sum())))
r=dict(objects=rows,parent_id=b['id'],replace_ids=[b['id']],scope='10 George Street partial historical podium/tower massing. Footprint and mapped step retained; three roof envelopes estimated from DSM spatial plateaus. Northern tower returns complex/unreliable; simple envelope is not verified whole roof. No facade arrays or current as-built claim.',datum_odn_m=datum,reported_architectural_height_m=128,original_metadata={k:v for k,v in b.items() if k!='geometry'},height_provenance_correction='Original14.496m property is Microsoft ML-derived, not survey measurement despite generic source_reported_height field.',vertical_warning='128m developer relative architectural statement kept distinct from DSMODN. Tower127.22ODN→122.93999979scene; estimated core134.4ODN→130.11999979scene. Neither substitutes localDTM as datum; ground0scene remains illustrative.',zone_diagnostics=metrics,footprint_symdiff_m2=podium.union(tower).symmetric_difference(p).area,overlap_m2=podium.intersection(tower).area,seam_endpoints=[aa.tolist(),bb.tolist()],source_ids=['overture_buildings_20260923','ea_lidar_dsm_1m','ea_lidar_dtm_1m'],primary_sources=[dict(url='https://cwg.com/press-release/vertus-launches-build-to-rent-apartments-35-floors-high-at-10-george-street-in-canary-wharf-220222/',publication='2022-02-22',capture_date=None,facts='128m GRID podium/tower and35th-floor apartments.'),dict(url='https://cwg.com/wp-content/uploads/2021/04/canary-wharf-group-investment-holdings-plc-year-ended-31-december-2019.pdf',publication='2019 year-end report, published after year end; URL2021 storage',capture_date=None,facts='Building completed, tenants began occupying February2020.')],limitations=['DSM regional2017–2020 context spans construction/opening; exact pixel survey date unresolved. Coherent upper roof returns demonstrate full-height coverage in some cells but do not date all cells.','Mapped step supports approximate easttower/westpodium split; no survey vertical seam proven.','Roof core box is estimated envelope of scattered high support, not exact plant dimensions.','Local licensed photos already inspected show no attributable measurable exterior for this owner; no new image acquired.','Pexels5044520 previously403 denied; no retry or alternate route.'],source_hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/george10_spatial_profiles.json']})
(R/'references/george10_massing_study.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(metrics,indent=2))
