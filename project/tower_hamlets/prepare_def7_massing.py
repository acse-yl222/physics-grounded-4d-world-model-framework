"""Bounded Northern Trust estimated roof/body study, preserving mapped owner boundary."""
from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon,Point,MultiPoint
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());b=next(x for x in g['buildings'] if 'def7f49e' in x['id'])
def footprint(q):return unary_union([Polygon(a['outer'],a.get('holes',[])) for a in q['geometry']])
p=footprint(b);prof=json.loads((R/'references/def7_spatial_profiles.json').read_text());o=np.array(prof['origin']);u=np.array(prof['u']);v=np.array(prof['v']);data=np.load(R/'references/def7_samples.npz');datum=4.28000021
# Approximate mapped-axis envelopes within the coherent plateaus, not surveyed plant outlines.
def rect(a,c,d,e):return p.intersection(Polygon([o+x*u+y*v for x,y in [(a,c),(d,c),(d,e),(a,e)]]))
# Preserve coherent low-return interior patch as an explicitly uncertain open recess.
inner=data['valid']&(data['z']<8)&np.array([p.buffer(-4).contains(Point(x,y)) for x,y in zip(data['x'].flat,data['y'].flat)]).reshape(data['x'].shape)
lowxy=np.column_stack([data['x'][inner],data['y'][inner]])
recess=MultiPoint(lowxy).convex_hull.buffer(.5,join_style=2).intersection(p)
base=p.difference(recess);middle=rect(-50,-7,50,50).difference(recess);upper=rect(-10,-5.5,14,50).difference(recess)
zones=[('low_roof_body_estimated',base,0,16.73),('middle_roof_estimated',middle,16.73-datum,27.96),('upper_roof_estimated',upper,27.96-datum,31.82)];rows=[];metrics=[]
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
 domain=poly.difference(middle) if name=='low_roof_body_estimated' else poly.difference(upper) if name=='middle_roof_estimated' else poly
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
 if p.distance(pp)>20:continue
 sh=p.boundary.intersection(pp.boundary)
 neighbors.append(dict(id=q['id'],name=q.get('name'),baseline_height_m=q.get('height_m'),distance_m=p.distance(pp),overlap_m2=p.intersection(pp).area,shared_length_m=sh.length,shared_geometry=sh.__geo_interface__,new_massing_plan_overlap_m2=max(poly.intersection(pp).area for _,poly,_,_ in zones)))
 assert p.intersection(pp).area<1e-8
r=dict(objects=rows,parent_id=b['id'],replace_ids=[b['id']],scope='Anonymous def7f49e Landmark-area partial estimated roof/body study. Mapped outer boundary retained, two stepped roof envelopes, uncertain interior low-return recess. No facade or exact named-building attribution.',datum_odn_m=datum,original_metadata={k:v for k,v in b.items() if k!='geometry'},baseline_height_warning='9m is unknown-height fallback; no metric height or floor count source.',vertical_warning='ODN16.73/27.96/31.82 converts to scene12.44999979/23.67999979/27.53999979. Public ground/foundation unknown; base0scene inherited illustrative. No local DTM renormalization.',zone_diagnostics=metrics,footprint_area_m2=p.area,outer_boundary_preserved=True,recess_hypothesis=dict(geometry=recess.__geo_interface__,area_m2=recess.area,basis='Convex support envelope around54 native interior cells below8ODN inside4m geometric inset, buffered0.5m to enclose cell support. Could be courtyard or transparent/no-roof returns; exact topology unresolved.',selected_cells=int(inner.sum()),selected_odn_range=[float(data['z'][inner].min()),float(data['z'][inner].max())],reported_as_estimated=True),neighbor_interfaces=neighbors,identity=dict(name='Unresolved; Landmark development low-rise volume is spatial inference only',location_wgs84=[-0.0241770256637583,51.501687419812825],osm_record='w1426095806@1',osm_update='2025-08-30T20:18:30Z',parent=None),source_ids=['overture_buildings_20260923','ea_lidar_dsm_1m','ea_lidar_dtm_1m'],primary_sources=[dict(url='https://towerhamlets.moderngov.co.uk/documents/s15052/40%20Marsh%20Wall%20Appendices.pdf',publication='Historical planning document; exact date not established in this audit',capture_date=None,facts='Landmark-area development includes two8-storey blocks plus taller towers. Context only; exact owner identity not proven and no dimension adopted.')],limitations=['Composite DSM acquisition vintage unresolved. OSM update date is not construction date. Current as-built status not independently verified.','Roof breaklines are visually estimated from inspected native spatial cells and mapped dominant axes. All plateau-domain cells retained in metrics; conditional spatial holdout does not validate breakline selection.','Interior54cell low-return patch kept open as an uncertain recess; not a verified courtyard or public passage. No invented glazing surface over low returns.','Base0scene is illustrative; fullheight vertical envelope below measured roofs is estimated.','No touching neighbor; nearest mapped boundary12.8473m away.','No attributable licensed photo supports this owner facade. No new imagery acquired; no generic facade arrays.','Closed layered components contain touching internal caps; no boolean-union volume claim.'],source_hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/def7_spatial_profiles.json']})
# Low returns are a separate reported domain, never silently excluded from all-owner diagnostics.
m=data['valid']&np.array([recess.contains(Point(x,y)) for x,y in zip(data['x'].flat,data['y'].flat)]).reshape(data['x'].shape);zz=data['z'][m];r['recess_all_cells']=dict(cells=len(zz),below8odn=int((zz<8).sum()),p10_p50_p90=np.percentile(zz,[10,50,90]).tolist(),excluded_from_plateau_fit_with_reason='Open low-return recess hypothesis, reported separately; not rejected as outliers')
(R/'references/def7_massing_study.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(metrics=metrics,recess=r['recess_all_cells'],neighbors=neighbors),indent=2))
