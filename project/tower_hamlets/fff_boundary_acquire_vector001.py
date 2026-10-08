from pathlib import Path
import json,urllib.request,hashlib,datetime,io
import pyarrow.parquet as pq,pyarrow.dataset as ds,pyarrow.compute as pc,pyarrow.fs as fs
from shapely import from_wkb
from shapely.geometry import mapping
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references';bbox=json.loads((R/'fff_boundary-vector-bbox.json').read_text());release='2026-09-23.1';url=f'https://stac.overturemaps.org/{release}/collections.parquet';rec={'bbox_wgs84':bbox,'release':release,'stac_url':url,'capture_date':None,'accessed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'provider':'Overture Maps Foundation official STAC/S3','kind':'vector','license_url':'https://docs.overturemaps.org/attribution/','attribution':'© OpenStreetMap contributors, Overture Maps Foundation','rights_review':'Official bbox client documentation and attribution inspected. ODbL building theme, per-feature provenance retained. No Overpass request or alternate denial route.','geometry_derivation':'allowed','export_texture_use':'not_applicable','local_raw_parquet':'No relevant cached regional parquet located; local GeoJSON excludes western neighbor.'}
try:
 with urllib.request.urlopen(url,timeout=30) as response:
  b=response.read(8*1024*1024+1);rec['index_status']=response.status
 if len(b)>8*1024*1024:raise RuntimeError('STAC index exceeded8MiB cap; stop')
 table=pq.read_table(io.BytesIO(b));xmin,ymin,xmax,ymax=bbox;flt=(pc.field('bbox','xmin')<xmax)&(pc.field('bbox','xmax')>xmin)&(pc.field('bbox','ymin')<ymax)&(pc.field('bbox','ymax')>ymin);tab=table.filter((pc.field('collection')=='building')&(pc.field('type')=='Feature')&flt);paths=[x['aws']['alternate']['s3']['href'][5:] for x in tab['assets'].to_pylist()];rec['selected_files']=paths;rec['index_sha256']=hashlib.sha256(b).hexdigest()
 if not 1<=len(paths)<=3:raise RuntimeError('Outside bounded selected-file cap')
 # No fallback/global listing; exactly STAC-selected files, anonymous no requester-pays, single retry attempt.
 filesystem=fs.S3FileSystem(anonymous=True,region='us-west-2',connect_timeout=15,request_timeout=30,retry_strategy=fs.AwsStandardS3RetryStrategy(max_attempts=1));dataset=ds.dataset(paths,filesystem=filesystem);rows=[]
 for batch in dataset.to_batches(filter=flt,use_threads=False,batch_readahead=0,fragment_readahead=0):
  rows.extend(batch.to_pylist())
  if len(rows)>100:raise RuntimeError('More than100bounded features; stop')
 feats=[]
 for row in rows:
  geom=row.pop('geometry');feats.append({'type':'Feature','id':row['id'],'geometry':mapping(from_wkb(geom)),'properties':row})
 out=R/'fff_boundary-buildings001.geojson';out.write_text(json.dumps({'type':'FeatureCollection','features':feats},default=str));rec.update(status='retrieved',feature_count=len(feats),filename=out.name,sha256=hashlib.sha256(out.read_bytes()).hexdigest())
except Exception as e:rec.update(status='failed_stopped_no_fallback_or_retry',error=str(e))
(R/'fff_boundary-vector-source001.json').write_text(json.dumps(rec,indent=2));print(json.dumps(rec,indent=2))
