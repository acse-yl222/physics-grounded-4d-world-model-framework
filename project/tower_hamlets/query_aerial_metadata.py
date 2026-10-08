"""Two bounded AOI metadata queries; no image acquisition or bulk catalogue."""
from pathlib import Path
import urllib.request,urllib.parse,json,hashlib
r=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references';records=[]
for kind in ['Vertical','Oblique']:
 params={'service':'WFS','version':'2.0.0','request':'GetFeature','typeNames':'dataset-9f0fa3fc-a860-4729-adc9-47fe53f658d0:'+kind+'_photography_index_catalogue','bbox':'537080,179825,538115,180865,EPSG:27700','srsName':'EPSG:27700','outputFormat':'application/json','count':100};url='https://environment.data.gov.uk/spatialdata/survey-index-files/wfs?'+urllib.parse.urlencode(params)
 with urllib.request.urlopen(url,timeout=30) as h:body=h.read(2000001)
 assert len(body)<=2000000
 data=json.loads(body);path=r/('ea_'+kind.lower()+'_aerial_aoi_metadata.json');path.write_bytes(body);records.append({'kind':kind,'url':url,'file':path.name,'sha256':hashlib.sha256(body).hexdigest(),'numberMatched':data.get('numberMatched'),'numberReturned':data.get('numberReturned'),'image_acquired':False});print(kind,data.get('numberMatched'),[f['properties'] for f in data.get('features',[])][:8])
(r/'aerial_metadata_query_receipt.json').write_text(json.dumps(records,indent=2)+'\n')
