"""Two bounded EA WCS requests covering complete crossing Westferry footprint."""
from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
r=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references';p=json.loads((r/'lidar_acquisition_plan.json').read_text())
def fetch(item):
 kind,d=item;url=d['download_url'].replace('537080%2C538115','537062%2C537129').replace('179825%2C180865','180405%2C180507');target=r/('westferry_ea_'+kind+'_1m.tif')
 if target.exists():raise FileExistsError(target)
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CanaryWharfGeometryResearch/1.0'}),timeout=45) as response:
  data=response.read(1024*1024+1)
  assert len(data)<=1024*1024 and data[:4] in (b'II*\x00',b'MM\x00*')
  target.write_bytes(data)
 return {'product':kind,'url':url,'filename':target.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'status':'retrieved_pending_raster_check'}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(fetch,p['products'].items()))
(r/'westferry_lidar_download_receipt.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
