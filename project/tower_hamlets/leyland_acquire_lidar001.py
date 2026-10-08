import json,math,hashlib,urllib.request,urllib.parse,datetime
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union,transform
from pyproj import Transformer
import rasterio,numpy as np
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';D=R/'references';g=json.loads((R/'geometry.json').read_text());ids=['8a7116a4'];p=unary_union([Polygon(q['outer'],q.get('holes',[])) for f in g['buildings'] if any(k in f['id'] for k in ids) for q in f['geometry']]);t=Transformer.from_crs(g['crs'],27700,always_xy=True);bounds=transform(t.transform,p.buffer(8)).bounds;bb=[math.floor(bounds[0]),math.floor(bounds[1]),math.ceil(bounds[2]),math.ceil(bounds[3])];plan=json.loads((D/'lidar_acquisition_plan.json').read_text());records=[]
for product in ['dsm','dtm']:
 cfg=plan['products'][product];pars=[('service','WCS'),('version','2.0.1'),('request','GetCoverage'),('coverageId',cfg['coverage_id']),('format','image/tiff'),('subset',f'E({bb[0]},{bb[2]})'),('subset',f'N({bb[1]},{bb[3]})')];url=cfg['endpoint']+'?'+urllib.parse.urlencode(pars);out=D/f'leyland_ea_{product}_1m_001.tif';rec={'product':product,'url':url,'requested_bounds_epsg27700':bb,'filename':out.name,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'capture_date':None,'license_url':'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/','attribution':'Contains Environment Agency information © Environment Agency copyright and/or database right 2022. Open Government Licence.','geometry_derivation':'allowed','export_texture_use':'not_applicable','kind':'lidar','provider':'Environment Agency','viewpoint':None,'rights_review':'Existing official EA catalogue OGL records; two bounded WCS requests only; unchanged coverage identifiers.','mixed_composite_note':'Actual local flight date unknown. Same named composite coverage as previous raster; retrieval date is not flight date.'}
 try:
  if out.exists():raise RuntimeError('Refuse overwrite existing output')
  with urllib.request.urlopen(url,timeout=45) as response:
   rec['http_status']=response.status;rec['content_type']=response.headers.get('Content-Type');data=response.read(4*1024*1024+1)
  if len(data)>4*1024*1024:raise RuntimeError('bounded transfer exceeded')
  from rasterio.io import MemoryFile
  with MemoryFile(data) as mem,mem.open() as ds:
   if ds.crs.to_epsg()!=27700:raise RuntimeError('Unexpected CRS')
   rec.update(crs=ds.crs.to_string(),bounds=list(ds.bounds),shape=[ds.height,ds.width],transform=list(ds.transform),nodata=ds.nodata,dtype=ds.dtypes[0],valid_cells=int(ds.read(1,masked=True).count()))
  out.write_bytes(data);rec.update(status='retrieved_validated',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:rec.update(status='failed_no_retry',error=str(e));records.append(rec);break
 records.append(rec)
(D/'leyland_lidar_sources001.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
