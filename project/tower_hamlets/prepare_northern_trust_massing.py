"""Bounded Northern Trust estimated roof/body study, preserving mapped owner boundary."""
from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());b=next(x for x in g['buildings'] if '8a6a6456' in x['id'])
def footprint(q):return unary_union([Polygon(a['outer'],a.get('holes',[])) for a in q['geometry']])
p=footprint(b);prof=json.loads((R/'references/northern_trust_spatial_profiles.json').read_text());o=np.array(prof['origin']);u=np.array(prof['u']);v=np.array(prof['v']);data=np.load(R/'references/northern_trust_samples.npz');datum=4.28000021
# Approximate mapped-axis envelopes within the coherent plateaus, not surveyed plant outlines.
def rect(a,c,d,e):return p.intersection(Polygon([o+x*u+y*v for x,y in [(a,c),(d,c),(d,e),(a,e)]]))
central=rect(-17,-9,20,1);south=rect(3,-19,20,-10)
zones=[('body_roof_estimated',p,0,62.1),('central_roof_envelope_estimated',central,62.1-datum,69.55),('south_roof_envelope_estimated',south,62.1-datum,68.2)];rows=[];metrics=[]
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
 domain=poly.difference(central.union(south)) if name=='body_roof_estimated' else poly
 m=data['valid']&np.array([domain.contains(Point(x,y)) for x,y in zip(data['x'].flat,data['y'].flat)]).reshape(data['x'].shape);z=data['z'][m];err=z-odn
 folds=(np.floor(data['u'][m]/3).astype(int)%3);heldout=[]
 for k in range(3):
  zz=z[folds!=k];test=z[folds==k];fit=float(np.median(zz));ee=test-fit
  heldout.append(dict(fold=k,train_cells=len(zz),test_cells=len(test),training_median_odn_m=fit,test_rmse_m=float(np.sqrt(np.mean(ee**2))),test_within_1m_cells=int((abs(ee)<=1).sum())))
 metrics.append(dict(zone=name,area_m2=domain.area,all_cells=len(z),within_1m_cells=int((abs(err)<=1).sum()),all_rmse_m=float(np.sqrt(np.mean(err**2))),all_median_abs_m=float(np.median(abs(err))),all_p95_abs_m=float(np.percentile(abs(err),95)),excluded_cells=0,low_return_below20odn_cells=int((z<20).sum()),conditional_spatial_holdout=heldout))
neighbors=[]
for q in g['buildings']:
 if q['id']==b['id'] or q.get('kind')=='site':continue
 pp=footprint(q)
 if p.distance(pp)>5:continue
 sh=p.boundary.intersection(pp.boundary)
 neighbors.append(dict(id=q['id'],name=q.get('name'),baseline_height_m=q.get('height_m'),distance_m=p.distance(pp),overlap_m2=p.intersection(pp).area,shared_length_m=sh.length,shared_geometry=sh.__geo_interface__,new_massing_plan_overlap_m2=max(poly.intersection(pp).area for _,poly,_,_ in zones)))
 assert p.intersection(pp).area<1e-8
r=dict(objects=rows,parent_id=b['id'],replace_ids=[b['id']],scope='Northern Trust / 50 Bank Street partial estimated roof and body massing, not facade reconstruction. Exact mapped footprint retained; two conservative inset plateau envelopes only; north and equipment zones explicitly unresolved.',datum_odn_m=datum,original_metadata={k:v for k,v in b.items() if k!='geometry'},baseline_height_warning='48m is16 floors times assumed3m, not explicit metric height.',vertical_warning='ODN62.1/69.55/68.2 converts to scene57.81999979/65.26999979/63.91999979. No local DTM renormalization; body base0scene is inherited illustrative baseline, not detected foundation.',zone_diagnostics=metrics,footprint_area_m2=p.area,footprint_symdiff_m2=0,neighbor_interfaces=neighbors,source_ids=['overture_buildings_20260923','ea_lidar_dsm_1m','ea_lidar_dtm_1m'],primary_sources=[dict(url='https://www.northerntrust.com/united-states/about-us/locations/gb/london-50-bank-street',publication='Undated current location page; checked2026-10-07',capture_date=None,facts='Northern Trust EMEA office address50 Bank Street.'),dict(url='https://www.northerntrust.com/documents/legal/usa-patriot-act-global-certification.pdf',publication='Document labelled as ofMarch2019; upload date unknown',capture_date=None,facts='Northern Trust London branch listed at50 Bank Street byMarch2019, consistent with established building within broad DSM epoch.')],limitations=['Composite raster vintage unresolved; overlapping survey catalog dates do not assign a per-building capture year; primary2019 address is occupancy/address evidence, not roof survey date.','North strip low returns unresolved; continuous body is estimated, not a detected full roof. All cells remain in reported residuals.','Central/south plateau envelopes intentionally conservative and mapped-axis aligned; exact roof boundaries and equipment unresolved. Surrounding omitted high-return equipment is reported through body residuals.','Conditional holdout tests roof heights within manually estimated zones; it does not independently validate chosen breaklines.','Actually inspected licensed Ollie11491155 panorama again: no attributable measurable Northern Trust exterior. No photo-derived facade details or generic arrays authored.','No new image acquired; prior denied sources not retried.','Closed layered components contain touching internal caps; no global boolean-union volume claim.'],source_hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/northern_trust_spatial_profiles.json','references/pexels-ollie-craig-11491155.jpeg']})
(R/'references/northern_trust_massing_study.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(metrics=metrics,neighbors=neighbors,area=p.area),indent=2))
