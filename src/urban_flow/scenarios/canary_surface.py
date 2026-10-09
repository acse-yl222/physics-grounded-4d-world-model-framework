"""Controlled4m Canary solar and measured-terrain rainfall shallow-water runs.

Solar uses existing geometric shadow/horizon model. Flood never fabricates terrain;
unknown cells are masked walls, with a one-cell draining boundary on valid terrain.
"""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np
import torch
from urban_flow.physics.solar.model import ShadowNet,HorizonNet,sun_position,ground_irradiance
from urban_flow.physics.flood.model import ShallowWater

def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inputs(config):
 g=Path(config['geometry']);meta=json.loads((g/'metadata.json').read_text());assert meta['spacing_xyz_m']==[4.,4.,4.] and meta['origin_xyz_m'][:2]==[-2048.,-2048.];height=np.load(g/'height_m.npy');foot=np.load(g/'near_ground_building_mask.npy').astype(bool)
 if height.shape==(1024,1024):height=height[12:1012,12:1012];foot=foot[12:1012,12:1012]
 assert height.shape==foot.shape==(1000,1000)
 return height,foot

def solar(c,out,device):
 height,foot=inputs(c);sn=ShadowNet(height,4,device);svf,_=HorizonNet(sn,n_azimuth=16,altitudes_deg=tuple(range(2,90,5)))();times=np.arange(0,601,60);frames=[];shadows=[];sun=[]
 for t in times:
  alt,az=sun_position(51.5053,-.0188,2026,6,21,12+t/3600);sun.append({'time_s':int(t),'utc_hour':12+float(t)/3600,'local_bst_hour':13+float(t)/3600,'altitude_deg':float(alt),'azimuth_deg':float(az)});shadow=sn(alt,az);ghi,_,_=ground_irradiance(shadow,svf,alt,6);frames.append(ghi.cpu().numpy());shadows.append(shadow.cpu().numpy());print('solar',int(t),flush=True)
 np.save(out/'values.npy',np.array(frames,dtype='<f4'));np.save(out/'invalid.npy',np.zeros(height.shape,'u1'));np.save(out/'svf.npy',svf.cpu().numpy());np.save(out/'shadow.npy',np.array(shadows,'<f4'));np.save(out/'surface_height_m.npy',height);write(out/'times.json',times.tolist());write(out/'sun_positions.json',sun);return {'kind':'sunlight','unit':'W/m²','epoch':'2026-06-21T12:00:00Z','limits':['Controlledclear sky, not measuredweather.','4m actualgeometryheights; horizontal topsurface irradiance, not facadeirradiance.','16azimuth/5degree sampledskyview; no treecanopy or clouds.','Flatlocalground outsidebuildinggeometry; terrainnotintegratedintosolar.']}

def flood(c,out,device):
 from scipy.ndimage import binary_erosion
 _,foot=inputs(c);p=Path(c['terrain']);terrain=np.load(p/'terrain_odn_m.npy');valid=np.load(p/'terrain_valid.npy');water=np.load(p/'water_4m.npy');valid=valid&~water;ys,xs=np.where(valid);y0,y1=max(0,ys.min()-1),min(1000,ys.max()+2);x0,x1=max(0,xs.min()-1),min(1000,xs.max()+2);sl=np.s_[y0:y1,x0:x1];v=valid[sl];solid=~v|foot[sl];bed=np.where(v,terrain[sl],0);boundary=v&~binary_erosion(v)&~solid;solver=ShallowWater(bed,solid,4,np.full(v.shape,.035,np.float32),device,cg_tol=1e-7,cg_max=400);source=torch.as_tensor(np.where(~solid&~boundary,50/1000/3600,0).astype('f4'),device=device);absorb=torch.as_tensor(boundary,device=device);t=0.;nextsave=60.;frames=[np.zeros((1000,1000),'<f4')];times=[0.];records=[];totals={'source':0.,'outflow':0.,'neg_clamped':0.};start=time.monotonic()
 while t<600-1e-7:
  dt=min(solver.stable_dt(1.,cfl=.5),nextsave-t,600-t);record=solver.step(dt,source=source,absorb=absorb);t+=dt
  for k in totals:totals[k]+=record.get(k,0.)
  if abs(t-nextsave)<1e-7:
   a=solver.h.cpu().numpy();assert np.isfinite(a).all()and(a>=0).all();full=np.zeros((1000,1000),'<f4');full[sl]=a;frames.append(full);times.append(t);records.append({'time_s':t,'volume_m3':solver.volume(),'max_depth_m':float(a.max()),'cumulative':dict(totals),'max_speed_m_s':solver.max_speed(),'last_cg_iters':solver.last_cg_iters});nextsave+=60;print('flood',t,float(a.max()),flush=True)
 invalid=~valid|foot;np.save(out/'values.npy',np.array(frames,dtype='<f4'));np.save(out/'invalid.npy',invalid.astype('u1'));np.save(out/'terrain_odn_m.npy',terrain);write(out/'times.json',times);balance=solver.volume()-totals['source']+totals['outflow']-totals['neg_clamped'];write(out/'mass_balance.json',{'records':records,'final_residual_m3':balance,'relative_source_residual':balance/max(totals['source'],1e-9),'wall_s':time.monotonic()-start});return {'kind':'flooding','unit':'m','valid_ground_cells':int((~invalid).sum()),'limits':['Controlled50mm/h600s rain, no measuredhazardforecast.','OnlylicensedEA DTMcoveragevalid; outsideunknown andinvalid.','EA ODNbed usedunchanged; overlaydepth doesnotclaimlocalgeometryverticalregistration.','Buildings impermeable, no roofrunofftransfer, sewers/infiltration/tides/bathymetry.','OSMwaterexcluded; validterrainboundarydrains, artificialboundaryaffectslocalresults.','UniformManning.035; dryinitialsurface.']}

def main(c,out,mode,device):
 out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);start=time.monotonic();paths=[Path(__file__),Path(__file__).parents[1]/'physics/solar/model.py',Path(__file__).parents[1]/'physics/flood/model.py'];hashes={str(p):sha(p)for p in paths};write(out/'source_identity.json',hashes);write(out/'configuration.json',c);info=(solar if mode=='solar'else flood)(c,out,device);assert all(sha(Path(p))==h for p,h in hashes.items());info.update(complete=True,origin_xy_m=[-2000,-2000],cell_m=4,shape_yx=[1000,1000],axes='TYX',wall_s=time.monotonic()-start,runner_sha256=sha(__file__));write(out/'metadata.json',info)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['solar','flood'],required=True);p.add_argument('--device',default='cpu');a=p.parse_args();main(json.loads(a.config.read_text()),a.output,a.mode,a.device)
