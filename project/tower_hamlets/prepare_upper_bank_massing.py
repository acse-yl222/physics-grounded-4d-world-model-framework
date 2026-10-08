from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());prof=json.loads((R/'references/upper_bank_spatial_profiles.json').read_text());data=np.load(R/'references/upper_bank_samples.npz');origin=np.array(prof['origin']);u=np.array(prof['u']);v=np.array(prof['v']);datum=4.28000021;pid='cc72c0ea-7504-42ec-8aec-33daafcd6451';fs=[b for b in g['buildings'] if b.get('parent_id')==pid];ps=[unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]) for b in fs]
def rect(a,b,c,d):return Polygon([origin+x*u+y*v for x,y in [(a,c),(b,c),(b,d),(a,d)]])
# Spatial envelopes are deliberately low-complexity estimates, not equipment digitisation.
tower_core=ps[0].intersection(rect(-15,15,1,7));tower_plant=ps[0].intersection(rect(-36,36,-9,12));lower_plant=ps[1].intersection(rect(-24,27,-72,-52));lower_north=ps[1].intersection(rect(-100,100,-47,100))
zones=[('tower_terrace_estimated',ps[0].difference(tower_plant),147.75,0),('tower_plant_envelope_estimated',tower_plant.difference(tower_core),153.7,0),('tower_high_core_estimated',tower_core,159.5,0),('lower_north_roof_estimated',lower_north,39.2,1),('lower_roof_estimated',ps[1].difference(lower_north).difference(lower_plant),40.4,1),('lower_plant_envelope_estimated',lower_plant,45.1,1)]
rows=[];metrics=[]
for name,p,odn,owner in zones:
 build_poly=p;bottom_scene=0
 if name=='tower_terrace_estimated':build_poly=ps[0]
 elif name=='tower_plant_envelope_estimated':build_poly=tower_plant;bottom_scene=147.75-datum
 elif name=='tower_high_core_estimated':bottom_scene=153.7-datum
 elif name=='lower_north_roof_estimated':build_poly=ps[1]
 elif name=='lower_roof_estimated':build_poly=ps[1].difference(lower_north);bottom_scene=39.2-datum
 elif name=='lower_plant_envelope_estimated':bottom_scene=40.4-datum
 for j,poly in enumerate([build_poly] if build_poly.geom_type=='Polygon' else build_poly.geoms):
  verts=[];faces=[];lookup={}
  def vi(x,y,z):
   key=tuple(round(float(a),7) for a in [x,y,z])
   if key not in lookup:lookup[key]=len(verts);verts.append(list(key))
   return lookup[key]
  hi=odn-datum;lo=bottom_scene # illustrative common ground; not measured foundation
  for tri in constrained_delaunay_triangles(poly).geoms:
   xy=list(tri.exterior.coords)[:-1];faces.append([vi(x,y,hi) for x,y in xy]);faces.append([vi(x,y,lo) for x,y in reversed(xy)])
  for ring in [poly.exterior,*poly.interiors]:
   xy=list(ring.coords)
   for (x,y),(a,b) in zip(xy,xy[1:]):faces.append([vi(x,y,lo),vi(a,b,lo),vi(a,b,hi),vi(x,y,hi)])
  rows.append(dict(name=name+str(j),kind='estimated_massing',building_id=fs[owner]['id'],aggregate_alias_id=pid,vertices=verts,roof_faces=faces,wall_faces=[],bottom_faces=[],top_odn_m=odn))
 m=data['valid']&np.array([p.contains(Point(x,y)) for x,y in zip(data['x'].flat,data['y'].flat)]).reshape(data['x'].shape)
 # Metrics include every spatial cell, including low returns; conditional support separately disclosed.
 z=data['z'][m];err=z-odn;support=abs(err)<=1.0
 metrics.append(dict(zone=name,area_m2=p.area,all_cells=len(z),within_1m_cells=int(support.sum()),all_cell_rmse_m=float(np.sqrt(np.mean(err**2))),all_cell_p95_abs_m=float(np.percentile(abs(err),95)),all_cell_median_abs_m=float(np.median(abs(err))),excluded_from_metric_cells=0,low_return_cells=int((z<20).sum()),conditional_support_median_abs_m=float(np.median(abs(err[support]))) if support.any() else None,warning='Spatial envelope estimated from observed plateau organization; support selection is not whole-zone validation.'))
r=dict(objects=rows,scope='Historical 10 Upper Bank Street group estimated roof/body massing. Exact mapped two-part footprint retained; six low-complexity roof zones represent terraces and plant envelopes. Complex north tower returns and seam filled by estimated envelope, not claimed surveyed roof or open gap. No facade detail; no 2026 as-built claim.',datum_odn_m=datum,parent_id=pid,reported_parent_architectural_height_m=151,reported_height_warning='151m architectural relative height has unknown base/datum correspondence. Highest model roof155.21999979 scene =159.5ODN-4.28000021; do not relabel as measured building height. Ground0scene is illustrative and not localDTM9.5ODN.',replace_ids=[b['id'] for b in fs],parent_raw=prof['raw_parent'],original_parts=[{k:v for k,v in b.items() if k!='geometry'} for b in fs],zone_diagnostics=metrics,footprint_union_symdiff_m2=unary_union([z[1] for z in zones]).symmetric_difference(unary_union(ps)).area,uncertainty=['Tower northern v12..26 and southern seam v-34..-20 low/mixed returns do not support complete roof or void reconstruction.','Central plant envelopes approximate aggregate support, omitting individual equipment and local peaks.','No source photo resolves this group sufficiently for facade modeling.','All sampled elevations reported, including unsupported and low-return cells; no residual rejection hidden.'],source_hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['geometry.json','references/buildings.geojson','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/upper_bank_spatial_profiles.json']})
(R/'references/upper_bank_massing_study.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(metrics,indent=2));print('footprintdiff',r['footprint_union_symdiff_m2'])
