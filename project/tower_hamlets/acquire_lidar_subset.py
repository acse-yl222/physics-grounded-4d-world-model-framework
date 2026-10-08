"""Bounded official WCS acquisitions; no retry on service denial."""
from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references'
plan=json.loads((root/'lidar_acquisition_plan.json').read_text())
def fetch(item):
    name,p=item;target=root/('ea_'+name+'_1m.tif')
    if target.exists():raise FileExistsError(target)
    req=urllib.request.Request(p['download_url'],headers={'User-Agent':'CanaryWharfGeometryResearch/1.0'})
    with urllib.request.urlopen(req,timeout=90) as response:
        data=response.read(32*1024*1024+1)
        if len(data)>32*1024*1024:raise ValueError('Transfer cap exceeded')
        if data[:4] not in (b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+'):
            raise ValueError('Response is not TIFF: '+repr(data[:100]))
        target.write_bytes(data)
        return {'product':name,'url':p['download_url'],'filename':target.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'http_status':response.status,'content_type':response.headers.get('Content-Type'),'status':'retrieved_pending_raster_inspection'}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(fetch,plan['products'].items()))
(root/'lidar_download_receipt.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
