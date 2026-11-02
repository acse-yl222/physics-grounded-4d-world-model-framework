"""Retain native-resolution display fields, ground context and recorded traffic.
No solver runs, spatial interpolation, missing traffic frames or synthetic samples.
"""
from pathlib import Path
import argparse, gzip, hashlib, json, shutil, os
import numpy as np
from PIL import Image, ImageDraw

def digest(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene_root',type=Path);p.add_argument('destination',type=Path);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
 r=a.scene_root;old=r/'input/local_viewer_20261102';out=a.destination
 if out.exists() and not a.resume:raise FileExistsError(out)
 out.mkdir(parents=True,exist_ok=True)
 for name in ['viewer','vendor','src','agents','tiles']:
  if name=='viewer':shutil.copytree(old/name,out/name,dirs_exist_ok=True)
  elif not (out/name).exists():shutil.copytree(old/name,out/name,copy_function=os.link)
 for name in ['serve.py','start_linux.sh','start_mac.command','start_windows.bat']:shutil.copy2(old/name,out/name)
 (out/'scenes').mkdir(exist_ok=True);shutil.copy2(old/'scenes/index.json',out/'scenes/index.json')
 dest=out/'scenes/imperial_corridor_8km';dest.mkdir(exist_ok=True)
 if not (dest/'models').exists():shutil.copytree(old/'scenes/imperial_corridor_8km/models',dest/'models',copy_function=os.link)
 physics=dest/'physics';(physics/'web').mkdir(parents=True,exist_ok=True);(physics/'web/index.json').write_text('{"layers":{}}')
 scene=json.loads((old/'scenes/imperial_corridor_8km/scene.json').read_text());manifest=json.loads((old/'scenes/imperial_corridor_8km/physics/manifest.json').read_text());transport={};audit=[]
 retained=r/'input/retained_physics_20261102'
 def encode(name,shape,dtype,frames,source):
  dtype=np.dtype(dtype);shape=tuple(shape);block=int(np.prod(shape[1:]));folder=physics/'chunks'/name.removesuffix('.npy');folder.mkdir(parents=True,exist_ok=True)
  entry={'meta':{'descr':dtype.str,'shape':list(shape),'itemsize':dtype.itemsize,'offset':0,'block':block},'total_bytes':int(np.prod(shape))*dtype.itemsize,'parts':[]}
  offset=0;samples=[]
  if name.startswith('masks/'):frames=[np.stack(list(frames))]
  for i,frame in enumerate(frames):
   frame=np.asarray(frame,dtype=dtype);assert frame.shape==(shape if name.startswith('masks/') else shape[1:]),(name,frame.shape,shape)
   raw=frame.tobytes(order='C');f=folder/f'{i:04d}.gz';
   if not f.exists() or gzip.decompress(f.read_bytes())!=raw:f.write_bytes(gzip.compress(raw,compresslevel=1,mtime=0))
   entry['parts'].append({'file':str(f.relative_to(physics)),'offset':offset,'bytes':len(raw)});offset+=len(raw)
   if i in [0,shape[0]-1]:
    flat=frame.reshape(-1);indices=[min(100,len(flat)-1),min(1000,len(flat)-1),len(flat)//2,len(flat)-1];samples.append({'frame':i,'indices':indices,'values':[float(flat[k]) for k in indices],'raw_sha256':hashlib.sha256(raw).hexdigest()})
  assert offset==entry['total_bytes'];transport[name]=entry
  audit.append({'file':name,'shape':shape,'dtype':dtype.str,'source':source,'samples':samples});print('encoded',name,shape,flush=True)
 def encode_file(name,source):
  arr=np.load(source,mmap_mode='r');encode(name,arr.shape,arr.dtype,arr,str(source.relative_to(r)))
 for day in ['20260621','20261221']:
  src=retained/'solar_10min_20261030'/f'{day[:4]}-{day[4:6]}-{day[6:]}'
  encode_file('solar_'+day+'.npy',src/'ghi_hourly_4m_tyx_float16.npy');encode_file('shadow_'+day+'.npy',src/'shadow_hourly_4m_tyx_u8.npy')
 encode_file('poll.npy',retained/'pollution_20261030/concentration.npy')
 flood=retained/'flood_60s_20261030/frames';times=json.loads((flood/'manifest.json').read_text())
 encode('flood.npy',(len(times),2048,2048),'<f2',(np.load(flood/f"depth_{i:03d}_float16.npy",mmap_mode='r') for i in range(len(times))),'retained flood frames')
 encode_file('temp.npy',old/'scenes/imperial_corridor_8km/physics/temp.npy')
 vectors=retained/'scaled_v1_fp32_300_20261030/vectors'
 final=np.load(vectors/'final_ground_4m.npy',mmap_mode='r');encode('wind.npy',(1,*final.shape),final.dtype,[final],'final_ground_4m.npy at model step 300')
 encode('wind_history.npy',(301,3,1024,1024),'<f4',(np.load(vectors/f'planes_{i:04d}.npy',mmap_mode='r')[0] for i in range(301)),'planes_XXXX.npy[0]: exact first saved height, 6 m')
 geom=np.load(r/'geometry/scaled_voxels_4m_20261030/geometry.npy',mmap_mode='r');solid=geom[1]
 for name,arr in [('wind_invalid_zyx.npy',solid[None]),('wind_history_invalid.npy',solid[None,::2,::2]),('poll_invalid.npy',np.load(retained/'pollution_20261030/invalid.npy'))]:
  encode('masks/'+name,arr.shape,arr.dtype,arr,'source occupancy mask at 6 m or source tracer invalid mask')
 # Solar and flood original arrays include valid surface values at buildings; keep only source no-data masks.
 terrain=r/'geometry/terrain_4m_20261030';dtm=np.load(terrain/'dtm_4m_yx.npy',mmap_mode='r');invalid=(~np.isfinite(dtm)).astype('u1')
 for name in ['solar_invalid.npy','shadow_invalid.npy','flood_invalid.npy']:encode('masks/'+name,invalid.shape,invalid.dtype,invalid,'nonfinite dtm_4m_yx.npy only')
 for name in ['temp_invalid.npy','lite_footprint.npy','lite_height.npy']:encode_file('masks/'+name,old/'scenes/imperial_corridor_8km/physics/masks'/name)
 for key in ['solar','poll','flood']:scene['layers'][key]['cell_m']=4.;scene['layers'][key]['label']=scene['layers'][key]['label'].replace('16 m','4 m');scene['layers'][key]['title']=scene['layers'][key]['title'].replace('16 m','4 m')
 scene['layers']['solar']['ghi_label']='Irradiance · 4 m';scene['layers']['solar']['shadow_label']='Shadows · 4 m';scene['layers']['solar']['shadow_cell_m']=4.;scene['layers']['solar']['shadow_packed']=False
 scene['layers']['temp']['label']='Air temperature · grid 32 m · height 8 m';scene['layers']['temp']['title']=scene['layers']['temp']['label']
 history=dict(scene['layers']['wind']);history.update(file='wind_history.npy',cell_m=8.,label='Wind · 8 m saved grid · height 6 m',title='Wind · 8 m time series · height 6 m',offset_x_m=-2,offset_z_m=2)
 scene['wind_history']=history
 scene['layers']['wind'].update(cell_m=4.,frames=1,t0_s=7500,step_s=25,overlay_frame=0,label='Wind · 4 m final snapshot · height 6 m',title='Wind · 4 m snapshot at model t = 7500 s',rate=1)
 scene['layers']['wind'].pop('sample_labels',None)
 scene['protocol_display']={'npy_transport':transport};scene['layers']['poll']['range']=scene['layers']['poll']['range']
 for name,entry in transport.items():
  if name in manifest['arrays']:manifest['arrays'][name]['shape']=entry['meta']['shape']
 manifest['arrays']['wind.npy']['time_s']=[7500];manifest['arrays']['wind_history.npy']={'shape':[301,3,1024,1024],'time_s':[25*i for i in range(301)]}
 (physics/'manifest.json').write_text(json.dumps(manifest))
 context=dest/'context';context.mkdir(exist_ok=True)
 water=np.load(terrain/'water_4m_yx.npy').astype(bool);green=np.load(terrain/'green_4m_yx.npy').astype(bool)
 rgb=np.full((2048,2048,3),[181,178,164],dtype='u1');rgb[green]=[100,142,88];rgb[water]=[66,119,145]
 image=Image.fromarray(rgb[::-1]);draw=ImageDraw.Draw(image);road_count=0
 for part in range(3):
  network=json.loads((a.artifact/f'road_network_{part}.json').read_text())
  for lane in network['lanes']:
   pts=[((p[0]+4096)/4,(4096-p[1])/4) for p in lane['shape']]
   if len(pts)>1:draw.line(pts,fill=(91,94,96),width=max(1,round(lane['width']/4)));road_count+=1
 image.save(context/'surface.png')
 low,high=np.nanpercentile(dtm,[1,99]);v=np.clip((np.asarray(dtm)-low)/(high-low),0,1);e=np.stack([85+v*155,130+v*90,85+v*110],axis=-1).astype('u1');Image.fromarray(e[::-1]).save(context/'elevation.png')
 meta=json.loads((a.artifact/'traffic_am_peak.json').read_text());binary=a.artifact/'traffic-am_peak.wasm';assert digest(binary)==meta['binary']['sha256'];meta['binary']['asset']='traffic-am.bin';shutil.copy2(binary,context/'traffic-am.bin');(context/'traffic-am.json').write_text(json.dumps(meta))
 scene['corridor_context']={'surface':'context/surface.png','elevation':'context/elevation.png','elevation_label':f'EA terrain elevation {low:.1f}–{high:.1f} m ODN (1–99% colour range); flat projection','traffic_meta':'context/traffic-am.json','traffic_binary':'context/traffic-am.bin','roads':road_count,'ground_cell_m':4,'limits':['Surface colours: existing green/water masks and SUMO lane raster. Unsurveyed remaining land uses neutral colour.','Traffic is an existing selected SUMO subset; no missing vehicles or frames invented.','Ground and traffic projected onto the flattened ENU building plane; bridge deck elevations are not represented.']}
 scene['limits']=[s for s in scene['limits'] if 'display grids remain' not in s and 'quantization' not in s]
 scene['limits'].append('Lossless gzip transport of original stored arrays: wind final 4 m, wind history 8 m, solar/tracer/flood 4 m, thermal 32 m. No spatial interpolation. Ground is a flat map aligned with terrain-normalized buildings; traffic uses its independent recorded clock.')
 (dest/'scene.json').write_text(json.dumps(scene,indent=2));(dest/'native-resolution-audit.json').write_text(json.dumps(audit,indent=2));(out/'README.txt').write_text('Native resolution viewer: run python3 serve.py. See scene.json for grid sizes and independent traffic clock.\n')
 print('READY',out,flush=True)
if __name__=='__main__':main()
