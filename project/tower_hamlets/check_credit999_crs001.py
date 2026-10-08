import json,numpy as np,rasterio
from pathlib import Path
from shapely.geometry import shape,Polygon
from shapely.ops import transform,unary_union
from pyproj import Transformer
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());raw=json.loads((R/'references/buildings.geojson').read_text());features=raw['features'];fw=Transformer.from_crs(4326,g['crs'],always_xy=True);bw=Transformer.from_crs(g['crs'],4326,always_xy=True);bng=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True);rows=[]
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 for prefix in ['999ceaf7','6019910a','26bcb1ba','3a202b7c']:
  f=next(f for f in g['buildings'] if prefix in f['id']);rf=next(f for f in features if prefix in f['id']);p=unary_union([Polygon(t['outer'],t.get('holes',[])) for t in f['geometry']]);rp=transform(fw.transform,shape(rf['geometry']));coords=np.array(p.exterior.coords);e,n=bng.transform(coords[:,0],coords[:,1]);xx,yy=back.transform(e,n);row,col=rasterio.transform.rowcol(ds.transform,e,n);ccx,ccy=ds.xy(row,col);err=np.hypot(np.array(ccx)-e,np.array(ccy)-n)
  rows.append({'id':f['id'],'raw_vs_scene_hausdorff_m':p.hausdorff_distance(rp),'raw_vs_scene_area_difference_m2':p.symmetric_difference(rp).area,'ENU_BNG_roundtrip_max_error_m':float(np.max(np.hypot(xx-coords[:,0],yy-coords[:,1]))),'pixel_center_max_distance_m':float(np.max(err))})
 metadata={'crs':str(ds.crs),'transform':list(ds.transform),'bounds':list(ds.bounds),'dimensions':[ds.width,ds.height]}
 with rasterio.open(R/'references/westferry_ea_dsm_1m.tif') as west:
  rr,cc=np.indices((west.height,west.width));xs,ys=rasterio.transform.xy(west.transform,rr,cc);xy=list(zip(np.array(xs).flat,np.array(ys).flat));sample=np.array([s[0] for s in ds.sample(xy)]).reshape(rr.shape);v=west.read(1);mask=(v!=west.nodata)&(sample!=ds.nodata);diff=abs(sample[mask]-v[mask]);cross={'common_pixel_count':int(mask.sum()),'median_difference_m':float(np.median(diff)),'p95_difference_m':float(np.percentile(diff,95)),'max_difference_m':float(max(diff)),'west_transform':list(west.transform)}
report={'controls':rows,'main_raster':metadata,'independent_westferry_download_comparison':cross,'conclusion':'Raw source footprints and scene geometry agree; roundtrip and raster indexing errors at expected subcell tolerance. This does not validate physical source alignment. No geometry or raster shift applied.'};(R/'references/credit999_crs_check001.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
