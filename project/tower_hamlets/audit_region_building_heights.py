"""Region-wide conditional height audit; prioritizes review without overwriting models."""
from pathlib import Path
import warnings
warnings.filterwarnings("ignore",category=DeprecationWarning)
import json,hashlib,numpy as np,rasterio
from rasterio.features import geometry_mask
from shapely.geometry import Polygon,mapping
from shapely.ops import unary_union,transform
from pyproj import Transformer
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());modules=json.loads((R/'src/modules.json').read_text());tx=Transformer.from_crs(g['crs'],27700,always_xy=True);rows=[]
with rasterio.open(R/'references/ea_dsm_1m.tif') as a,rasterio.open(R/'references/ea_dtm_1m.tif') as b:
 assert a.transform==b.transform and a.shape==b.shape
 dsm=a.read(1,masked=True);dtm=b.read(1,masked=True);valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm)
 for f in g['buildings']:
  if f['id']=='site-support':continue
  poly=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);inner=poly.buffer(-2);row={'id':f['id'],'name':f.get('name'),'area_m2':poly.area,'module':modules.get(f['id']),'model_height_m':f['height_m'],'height_basis':f['height_basis'],'facade_verified':False,'inset_area_m2':inner.area}
  if not inner.is_empty:
   mask=geometry_mask([mapping(transform(tx.transform,inner))],out_shape=a.shape,transform=a.transform,invert=True)&valid;values=np.asarray(dsm-dtm)[mask];values=values[np.isfinite(values)]
   if len(values)>=12:
    q=np.quantile(values,[.1,.5,.9]);row.update(interior_cells=len(values),inset_sample_area_fraction=float(min(1.,len(values)*abs(a.transform.a*a.transform.e)/inner.area)),surface_minus_terrain_p10_m=float(q[0]),surface_minus_terrain_median_m=float(q[1]),surface_minus_terrain_p90_m=float(q[2]),spread_m=float(q[2]-q[0]),median_minus_model_m=float(q[1]-f['height_m']))
  row['review_priority_score']=float(poly.area*abs(row.get('median_minus_model_m',0))) if modules.get(f['id'])=='baseline' else 0.;rows.append(row)
rows.sort(key=lambda q:q['review_priority_score'],reverse=True)
report={'building_or_part_count':len(rows),'conditional_height_stats_count':sum('interior_cells' in q for q in rows),'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'scope':'2m inset DSM-minus-DTM diagnostics. Not building height truth: vegetation, canopy penetrations, elevated decks and mixed dates affect samples. Parts retain separate ownership. No geometry changed. Priority only targets baseline modules; optional appearance work tracked separately.','buildings':rows};(R/'references/region_building_height_audit.json').write_text(json.dumps(report,indent=2));print('Inventory',len(rows),'sampled',report['conditional_height_stats_count']);print(json.dumps([{k:q.get(k) for k in ['id','name','area_m2','model_height_m','surface_minus_terrain_median_m','spread_m']} for q in rows[:12]],indent=2))

queue=[q for q in rows if q['module']=='baseline' and q.get('interior_cells',0)>=40 and q.get('spread_m',999)<3 and q.get('surface_minus_terrain_median_m',0)>3 and abs(q.get('median_minus_model_m',0))>2]
for q in queue:q['coverage_review_required']=q.get('inset_sample_area_fraction',0)<.9
R.joinpath('references/region_height_review_queue.json').write_text(json.dumps({'scope':'Review only; no automatic height corrections. Coverage below 90% requires explicit partial-support review. Native cell area / geometric inset area is an approximate coverage diagnostic, not accuracy.','candidates':queue},indent=2)+'\n')
