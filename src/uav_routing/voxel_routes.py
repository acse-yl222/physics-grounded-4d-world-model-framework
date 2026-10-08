"""Geometry-driven WavePDE routes from a native-volume ZYX mask.

No graph-search fallback. Conservative pooled/dilated planning volume; independent
closed-voxel checks on the original volume including vertical takeoff/landing.
"""
import argparse,hashlib,json,time
from dataclasses import asdict
from pathlib import Path
import numpy as np
import torch
from scipy.ndimage import maximum_filter
from wavepde.torch_backend import WaveConfig,plan_paths,waveform_samples
from wavepde.torch_backend.geometry import segment_free,segment_time

def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(config,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4)
 source=Path(config['solid_path']);fine=np.load(source);assert fine.ndim==3 and fine.dtype==bool
 origin=np.array(config['origin_enu_m'],float);cell=float(config['source_cell_m']);factor=config.get('pool_factor',2);z,y,x=fine.shape
 assert all(n%factor==0 for n in fine.shape)
 coarse=fine.reshape(z//factor,factor,y//factor,factor,x//factor,factor).max(axis=(1,3,5))
 coarse=maximum_filter(coarse,size=(1,3,3),mode='constant',cval=1)
 mask=torch.as_tensor(np.ascontiguousarray(coarse.transpose(2,1,0)),device='cuda');original=torch.as_tensor(np.ascontiguousarray(fine.transpose(2,1,0)),device='cuda');spacing=cell*factor
 cfg=WaveConfig(**config['wave']);wave=waveform_samples('gaussian_long',cfg.dt,cfg.n_steps,device='cuda')
 stations={s['id']:s for s in config['stations']};routes=[];start=time.monotonic()
 write(out/'config.json',config);write(out/'identity.json',{'solid_sha256':sha(source),'runner_sha256':sha(__file__),'solver':'wavepde.torch_backend.plan_paths','config':asdict(cfg),'torch':torch.__version__})
 for src in dict.fromkeys(a for a,b in config['routes']):
  dest=[b for a,b in config['routes'] if a==src];anchor=np.array(stations[src]['gate_enu_m'])-origin;queries=np.array([stations[b]['gate_enu_m']for b in dest])-origin
  begin=time.monotonic();result=plan_paths(mask,spacing,anchor,queries,cfg,device='cuda',waveform=wave,smoothing_m=8,step_m=8,terminal_m=32,max_steps=4000)
  for k,dst in enumerate(dest):
   path=result.traces.path(k);status=result.traces.status_names()[k];success=status=='reached'
   if success:path=torch.cat([torch.as_tensor(np.array(stations[src]['enu_m'])-origin,device='cuda')[None],path,torch.as_tensor(np.array(stations[dst]['enu_m'])-origin,device='cuda')[None]])
   clear=bool(segment_free(original,path[:-1],path[1:],cell).all()) if len(path)>1 else False
   pad0=np.array(stations[src]['enu_m'])-origin;pad1=np.array(stations[dst]['enu_m'])-origin
   endpoints=bool(np.allclose(path[0].cpu(),pad0,atol=.001)and np.allclose(path[-1].cpu(),pad1,atol=.001))
   success=success and clear and endpoints;name=f'{src}_{dst}.npy';np.save(out/name,path.cpu().numpy()+origin)
   dt=segment_time(path[1:]-path[:-1]);times=torch.cat([dt.new_zeros(1),dt.cumsum(0)]).cpu().numpy();np.save(out/f'{src}_{dst}_times.npy',times)
   routes.append({'source':src,'target':dst,'status':status,'success':success,'original_closed_voxel_collision_free':clear,'endpoints':endpoints,'path':name,'times':f'{src}_{dst}_times.npy','duration_s':float(times[-1])if success else None,'points':len(path),'raw_pde_arrival_s':float(result.traces.arrivals[k])if torch.isfinite(result.traces.arrivals[k])else None})
  write(out/'progress.json',{'routes':routes,'elapsed_s':time.monotonic()-start});print(src,len(dest),'queries',sum(r['success']for r in routes),'cumulative successes',time.monotonic()-begin,flush=True)
 write(out/'summary.json',{'complete':True,'routes':routes,'successes':sum(r['success']for r in routes),'total':len(routes),'wall_s':time.monotonic()-start,'limitations':['No wind coupling, scheduling or inter-UAV avoidance.','Model-derived flat-plane stations; not surveyed landing facilities.','16m pooled native volume with16m horizontal dilation; all full segments independently checked in original8m closed voxels.','PDE arrival times are uncalibrated; displayed flighttimes integrate anisotropic15m/s horizontal,6up,4down model.']})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(json.loads(a.config.read_text()),a.output)
