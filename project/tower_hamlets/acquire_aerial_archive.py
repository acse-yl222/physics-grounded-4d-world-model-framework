"""Single official historical RGB archive request,256MiB cap,no retries."""
from pathlib import Path
import urllib.request,json,hashlib
r=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references';d=json.loads((r/'ea_aerial_tile_search.json').read_text());q=next(q for q in d['results'] if q['product']['id']=='vertical_aerial_photography_tiles_rgb' and q['year']['id']=='2008');target=r/'ea_rgb_2008_TQ38se.zip';assert not target.exists();cap=256*1024*1024;receipt={'url':q['uri'],'request_cap_bytes':cap,'request_count':1,'prior_attempt':'64MiB cap reached; previous body not retained','status':'pending'}
try:
 with urllib.request.urlopen(q['uri'],timeout=45) as h:
  receipt.update(http_status=h.status,content_type=h.headers.get('Content-Type'),content_length=h.headers.get('Content-Length'))
  if h.headers.get('Content-Length') and int(h.headers['Content-Length'])>cap:raise ValueError('Archive exceeds256MiB cap; not downloaded')
  data=h.read(cap+1)
  if len(data)>cap:raise ValueError('Stream exceeded256MiB cap; not retained')
  if not data.startswith(b'PK'):raise ValueError('Response is not ZIP; no imagery retained')
  target.write_bytes(data);receipt.update(status='archive_retrieved_not_inspected',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),file=target.name)
except Exception as e:receipt.update(status='not_acquired',error=str(e))
(r/'aerial_download_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt)
