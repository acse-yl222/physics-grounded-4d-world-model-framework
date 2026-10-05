"""Local Img2City display adapter step. See docs/framework/img2city-full-viewer.md. No Git operations."""
import argparse
from pathlib import Path
_parser=argparse.ArgumentParser()
_parser.add_argument('--root',type=Path,default=Path.cwd())
_args=_parser.parse_args()
_ROOT=_args.root.resolve()
import concurrent.futures,hashlib,io,json,time,urllib.request
from pathlib import Path
from PIL import Image
import numpy as np
BASE='https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/'
OUT=(_ROOT/'project/south_ken/runs/img2city_original_page_20261005')
INDEX=json.loads((_ROOT/'project/south_ken/runs/img2city_original_page_20261005/reference_source/frames.json').read_text())
records=[]
C=json.loads((_ROOT/'project/south_ken/runs/img2city_original_page_20261005/reference_crop.json').read_text());X=C['x'];Y=C['y'];W=C['width'];H=C['height']
def download(item):
 url,rel,kind=item;p=OUT/rel
 if kind=='unchanged' and p.exists():return {'url':BASE+url,'asset':rel,'operation':kind,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 p.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(3):
  try:
   data=urllib.request.urlopen(BASE+url,timeout=60).read();break
  except Exception:
   if attempt==2:raise
   time.sleep(1)
 record={'url':BASE+url,'source_sha256':hashlib.sha256(data).hexdigest(),'asset':rel,'operation':kind}
 if kind=='crop_png':
  im=Image.open(io.BytesIO(data));assert im.size==(768,704);im.crop((X,Y,X+W,Y+H)).save(p)
 elif kind=='crop_npy':
  a=np.load(io.BytesIO(data));np.save(p,a[...,Y:Y+H,X:X+W])
 else:p.write_bytes(data)
 record['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
 return record
items=[]
for key,meta in INDEX['layers'].items():
 if key.startswith(('solar_','shadow_')):continue
 for i in range(meta['frames']):
  rel=f'physics/web/{key}/{i:03}.png';items.append((f'scenes/south_kensington/{rel}',rel,'crop_png'))
for name in ['masks/building_footprint_yx.npy','masks/solid_4m_zyx.npy','temperature2d/study_area_mask_yx.npy']:
 items.append(('scenes/south_kensington/physics/'+name,'physics/'+name,'crop_npy'))
for name in ['stations.json','parking.json','routes.json','hub-bays.json','roads.json','schedule.json','traffic/current_replay.json','traffic/replay/frames_index.json','traffic/replay/traffic_flow.f32','traffic/replay/actors.json','traffic/signal_layer_v2.json','traffic/replay/tls_frames.jsonl','birds_southken/bird_replay.json','birds_southken/bird_states.u8']:
 items.append(('agents/demo_rev02/data/'+name,'replay/data/'+name,'unchanged'))
errors=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 futures={pool.submit(download,item):item for item in items}
 for i,f in enumerate(concurrent.futures.as_completed(futures),1):
  try:records.append(f.result())
  except Exception as e:errors.append({'item':futures[f],'error':str(e)});print('FAILED',futures[f][0],e,flush=True)
  if i%40==0:print(i,'/',len(items),'files',flush=True)
(OUT/'reference-downloads.json').write_text(json.dumps({'records':records,'errors':errors,'crop':C,'note':'Original published simulation outputs, geospatial crop only; NOT recalculated for Img2City.'},indent=2))
print('Completed',len(records),'errors',errors,flush=True)
