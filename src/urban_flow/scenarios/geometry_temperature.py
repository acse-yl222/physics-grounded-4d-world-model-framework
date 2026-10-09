"""Controlled clear-sky, frozen-wind temperature using existing South Ken physics.

No measured-weather claim; no publication. Reuses original surface energy balance,
boundary kernels and state-carrying advection/diffusion. Input geometry height is a
thermal column approximation; wind comes from an actual completed MAC checkpoint.
"""
import argparse,ast,datetime,hashlib,json,math,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
import torch.nn.functional as F
from urban_flow.physics.diurnal_solver import solve_from_state
from urban_flow.physics.solar.model import ShadowNet,sun_position,ground_irradiance

ROOT=Path(__file__).resolve().parents[3]
LEGACY=ROOT/'src/urban_flow/physics/environment-integration/members/yiqi_temperature/models/physical_model/south_kensington_temperature_3d.py'


def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def kernel():
 # Load exact existing pure functions without importing notebook/geodata/UI stacks.
 names={'shift_with_edge_torch','impose_boundary_conditions_3d_torch','solve_surface_temperature_excess_c'}
 tree=ast.parse(LEGACY.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
 assert len(nodes)==len(names)
 env={'np':np,'torch':torch};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(LEGACY),'exec'),env)
 original=env['impose_boundary_conditions_3d_torch']
 def guarded_boundary(temperature_c,solid_mask,roof_mask,study_area_3d,roof_surface_temperature_excess_3d,current_ambient_temp_c,current_inflow_temp_c):
  # Zero-gradient extrapolation is valid only when the inward neighbour is fluid.
  original(temperature_c,solid_mask,roof_mask,study_area_3d,roof_surface_temperature_excess_3d,current_ambient_temp_c,current_inflow_temp_c)
  fluid=(~solid_mask)&study_area_3d
  for boundary,inside in [((slice(None),slice(None),-1),(slice(None),slice(None),-2)),((slice(None),0,slice(None)),(slice(None),1,slice(None))),((slice(None),-1,slice(None)),(slice(None),-2,slice(None)))]:
   bad=fluid[boundary]&~fluid[inside]
   temperature_c[boundary][bad]=current_ambient_temp_c
 env['impose_boundary_conditions_3d_torch']=guarded_boundary
 return SimpleNamespace(**{n:env[n]for n in names})


def fields(solid,wind,ambient,exchange):
 roof=solid.copy();roof[:-1]&=~solid[1:];roof[-1]=False
 f={'u':wind[None,0],'v':wind[None,1],'w':wind[None,2],'solid_mask_3d':solid,'roof_mask_3d':roof,'study_area_mask_2d':np.ones(solid.shape[1:],bool)}
 b={'surface_exchange_coeff_per_s':np.full(solid.shape[1:],exchange,np.float32),'ground_surface_temperature_excess_c':np.zeros(solid.shape[1:],np.float32),'roof_surface_temperature_excess_3d':np.zeros_like(solid,np.float32),'ambient_temp_series_c':np.array([ambient,ambient],np.float32),'inflow_temp_series_c':np.array([ambient,ambient],np.float32),'surface_forcing_layer_count':np.array([1])}
 return f,b


def thermal_config(config,device,seconds):
 return SimpleNamespace(temperature_solver_device=device,block_solid_advection=True,velocity_scale=1.,max_courant=.25,diffusion_coeff_m2_s=config['diffusivity_m2_s'],frame_duration_s=seconds)


def self_test():
 m=kernel();shape=(8,12,12);solid=np.zeros(shape,bool);wind=np.zeros((3,*shape),np.float32);f,b=fields(solid,wind,20.,.001);v=SimpleNamespace(model_resolution_m=32.,height_scale_m=16.);cfg={'diffusivity_m2_s':1.};state=np.full(shape,20.,np.float32)
 cold,_,_=solve_from_state(m,f,b,v,thermal_config(cfg,'cpu',10.),state)
 b['ground_surface_temperature_excess_c'][:]=10
 hot,_,_=solve_from_state(m,f,b,v,thermal_config(cfg,'cpu',10.),state)
 assert np.isfinite(hot).all()and hot[0,5,5]>cold[0,5,5]
 a=m.solve_surface_temperature_excess_c(np.array([0,400.],np.float32),np.array([.95,.95]),np.zeros(2),np.zeros(2),np.full(2,12.),5.670374419e-8*293.15**4,20.,0.)
 assert abs(a[0])<1e-6 and a[1]>0
 solid[:,5:7,5:7]=True;wind[0]=5;f,b=fields(solid,wind,20.,0.);b['roof_surface_temperature_excess_3d'][:]=30
 # A hot solid slab cannot inject scalar by advection when diffusivity is zero.
 f['roof_mask_3d']=solid.copy()
 out,fluid,_=solve_from_state(m,f,b,v,thermal_config({'diffusivity_m2_s':0.},'cpu',10.),state)
 assert np.max(out[fluid])<=20.10001 and np.min(out[fluid])>=19.89999
 return {'solid_advection_block_fixture':True,'closed_solid_no_advected_heat':True,'physical_surface_heating':True,'positive_ground_exchange_warms_air':True,'finite':True,'unforced_center_c':float(cold[0,5,5]),'heated_center_c':float(hot[0,5,5]),'surface_excess_400W_m2':float(a[1])}


def geometry_height(folder,config):
 meta=json.loads((folder/'metadata.json').read_text());height=np.load(folder/'height_m.npy');spacing=meta.get('spacing_xyz_m',[meta.get('cell_m')]*3)[0];origin=meta['origin_xyz_m'];dx=config['dx_m'];nx=config['shape_yx'][1];ny=config['shape_yx'][0];factor=round(dx/spacing)
 assert factor>=1 and abs(factor*spacing-dx)<1e-8
 ix=(config['origin_xy_m'][0]-origin[0])/spacing;iy=(config['origin_xy_m'][1]-origin[1])/spacing
 assert abs(ix-round(ix))<1e-6 and abs(iy-round(iy))<1e-6
 ix=round(ix);iy=round(iy);assert ix>=0 and iy>=0;a=height[iy:iy+ny*factor,ix:ix+nx*factor]
 assert a.shape==(ny*factor,nx*factor)and np.isfinite(a).all()
 return a.reshape(ny,factor,nx,factor).max(axis=(1,3)).astype('f4'),meta


def frozen_wind(path,config,shape):
 if path.suffix=='.npy':
  meta=json.loads((path.parent/'metadata.json').read_text());assert meta['complete']
  array=np.load(path,mmap_mode='r');assert array.shape[0]==3 and np.isfinite(array).all()
  origin=meta['origin_enu_m'];h=meta['cell_m'];gridshape=array.shape[1:]
  centered_tensor=torch.from_numpy(np.array(array,copy=True))
  evidence={'source_kind':'SCALED pretrained surrogate final decoded3D velocity','source_model_step':meta['sample_model_steps'][-1],'source_interpreted_time_s':meta['sample_model_steps'][-1]*100,'source_time_semantics':meta['time_semantics'],'source_limitations':meta['limitations'],'velocity_sha256':sha(path),'metadata_sha256':sha(path.parent/'metadata.json'),'frozen_forcing':True,'thermal_clock':'independent600s controlled response; not evolvingwind029 timeline'}
 else:
  checkpoint=torch.load(path,map_location='cpu',weights_only=True);faces=checkpoint['velocity_faces'];origin=checkpoint['origin_xyz_m'];h=checkpoint['cell_m'];speed=json.loads((path.parent/'configuration.json').read_text())['inlet_m_s'];centered=[]
  for c,face in enumerate(faces):
   previous=torch.roll(face,1,2-c);sl=[slice(None)]*3;sl[2-c]=0;previous[tuple(sl)]=speed if c==0 else 0;centered.append((face+previous)*.5)
  gridshape=faces[0].shape;centered_tensor=torch.stack(centered)
  evidence={'checkpoint_time_s':checkpoint['time_s'],'checkpoint_sha256':sha(path),'solid_sha256':checkpoint['solid_sha256'],'frozen_forcing':True}
 nz,ny,nx=shape;xs=config['origin_xy_m'][0]+(np.arange(nx)+.5)*config['dx_m'];ys=config['origin_xy_m'][1]+(np.arange(ny)+.5)*config['dx_m'];zs=(np.arange(nz)+.5)*config['dz_m']
 for a,o,n in zip([xs,ys,zs],origin,gridshape[::-1]):assert a.min()>=o+.5*h and a.max()<=o+(n-.5)*h
 zz,yy,xx=np.meshgrid(zs,ys,xs,indexing='ij');grid=np.stack([(xx-origin[0])/(gridshape[2]*h)*2-1,(yy-origin[1])/(gridshape[1]*h)*2-1,(zz-origin[2])/(gridshape[0]*h)*2-1],-1).astype('f4');w=F.grid_sample(centered_tensor[None],torch.from_numpy(grid)[None],mode='bilinear',padding_mode='border',align_corners=False)[0].numpy()
 return w,evidence


def run(config,geometry,wind_checkpoint,output,device):
 output=Path(output);output.mkdir(parents=True,exist_ok=False);start=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat();frozen_sources={str(p):sha(p) for p in [Path(__file__),LEGACY,Path(__file__).parents[1]/'physics/diurnal_solver.py',Path(__file__).parents[1]/'physics/solar/model.py']};write(output/'runtime_identity.json',{'started_utc':started,'source_hashes':frozen_sources,'torch':torch.__version__,'device':device});torch.set_num_threads(4);m=kernel();height,gmeta=geometry_height(Path(geometry),config);nz=config['layers'];dz=config['dz_m'];solid=(np.arange(nz)[:,None,None]+.5)*dz<height[None];wind,wmeta=frozen_wind(Path(wind_checkpoint),config,solid.shape);wind[:,solid]=0
 water_path=Path(config['water_mask']);water_raw=np.load(water_path);assert water_raw.shape==(500,500);water=water_raw.reshape(125,4,125,4).mean(axis=(1,3))>=.5;water&=height<.01;np.savez_compressed(output/'inputs.npz',height=height,solid=solid,wind=wind,water=water);write(output/'config.json',config);write(output/'input_provenance.json',{'water_sha256':sha(water_path),'water_rule':'majority 8m cells per32m cell, no building override; prescribed20C water surface, no water dynamics','geometry_metadata':gmeta,'height_sha256':sha(Path(geometry)/'height_m.npy'),'wind':wmeta,'diurnal_solver_sha256':sha(Path(__file__).parents[1]/'physics/diurnal_solver.py'),'solar_sha256':sha(Path(__file__).parents[1]/'physics/solar/model.py'),'legacy_kernel_sha256':sha(LEGACY),'runner_sha256':sha(Path(__file__))})
 ambient=config['ambient_c'];f,b=fields(solid,wind,ambient,config['exchange_per_s']);velocity=SimpleNamespace(model_resolution_m=config['dx_m'],height_scale_m=dz);state=np.full(solid.shape,ambient,np.float32);shadow=ShadowNet(height,config['dx_m'],device);indices=[int(x//dz)for x in config['sample_heights_m']];times=np.arange(0,config['duration_s']+1,config['interval_s']).astype(float);air=[state[indices].copy()];surfaces=[];irradiances=[];checks=[];epoch=datetime.datetime.fromisoformat(config['epoch_utc']);emissivity=np.full(height.shape,config['emissivity'],np.float32)
 for i,t in enumerate(times):
  dtm=epoch+datetime.timedelta(seconds=float(t));hour=dtm.hour+dtm.minute/60+dtm.second/3600;alt,az=sun_position(config['latitude'],config['longitude'],dtm.year,dtm.month,dtm.day,hour);shade=shadow(alt,az);ghi,_,_=ground_irradiance(shade,torch.ones_like(shade,dtype=torch.float32),alt,dtm.month);ghi=ghi.cpu().numpy();excess=m.solve_surface_temperature_excess_c((1-config['albedo'])*ghi,emissivity,np.zeros_like(ghi),np.full_like(ghi,config['storage_fraction']),np.full_like(ghi,config['convective_w_m2_k']),5.670374419e-8*(ambient+273.15)**4,ambient,0.)
  excess[water]=0.
  surfaces.append(ambient+excess);irradiances.append(ghi)
  if i==len(times)-1:break
  b['ground_surface_temperature_excess_c']=excess;b['roof_surface_temperature_excess_3d']=f['roof_mask_3d']*excess[None]
  state,fluid,report=solve_from_state(m,f,b,velocity,thermal_config(config,device,float(times[i+1]-t)),state)
  if not np.isfinite(state).all():raise ValueError('Nonfinite physical thermal state')
  air.append(state[indices].copy());checks.append(dict(report,time_s=float(times[i+1]),air_min_c=float(state[fluid].min()),air_max_c=float(state[fluid].max())));write(output/'progress.json',{'intervals':checks,'wall_seconds':time.monotonic()-start});print('temperature',times[i+1],float(state[fluid].min()),float(state[fluid].max()),flush=True)
 assert all(sha(Path(p))==h for p,h in frozen_sources.items()),'Source changed during simulation'
 np.save(output/'air_temperature.npy',np.asarray(air,dtype='<f4'));np.save(output/'surface_temperature.npy',np.asarray(surfaces,dtype='<f4'));np.save(output/'shortwave.npy',np.asarray(irradiances,dtype='<f4'));np.save(output/'air_invalid.npy',solid[indices].astype('u1'));np.save(output/'final_temperature_zyx.npy',state.astype('<f4'));write(output/'times_s.json',times.tolist());write(output/'metadata.json',{'complete':True,'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'origin_xy_m':config['origin_xy_m'],'cell_m':config['dx_m'],'shape_yx':config['shape_yx'],'actual_heights_m':[(i+.5)*dz for i in indices],'air_axes':'THYX','surface_axes':'TYX','epoch_utc':config['epoch_utc'],'wind_forcing':wmeta,'time_semantics':'Physical thermal seconds under frozen final decoded wind; thermal clock independent of sourcewind clock','duration_s':float(times[-1]),'wall_seconds':time.monotonic()-start,'surface_location':'topographic surface height from aggregated geometry, not uniformly ground','limits':['Controlled clear-sky and20C ambient, not observed weather.','Existing first-order advection/diffusion/linearized radiative balance, not calibrated urban heat model.','Uniform land material/storage/exchange parameters; OSM water prescribed20C, no vegetation evaporation, water thermal inertia or wall radiation.','32m thermal column approximation fills undercrofts; no temperature values in occupied air cells.','Roof conduction is diffusion from prescribed hot solid cells; separate bottom exchange applies only ground-fluid columns, so no duplicate roof exchange.','Advection masks solid upwind interfaces; scalar is advective-form, not a conservative finite-volume heat budget.','Boundary zero-gradient copying is restricted to fluid neighbours; blocked boundary uses ambient.','Frozen wind is specified controlled forcing, not fabricated intermediate wind observations; inherited sourcewind limitations recorded in wind_forcing.','Sky-view factor set1 for diffuse component; geometry shadows only direct component.']});return output

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--config',type=Path);p.add_argument('--geometry',type=Path);p.add_argument('--wind-checkpoint',type=Path);p.add_argument('--output',type=Path);p.add_argument('--device',default='cpu');a=p.parse_args()
 if a.self_test:print(json.dumps(self_test(),indent=2))
 else:
  try:run(json.loads(a.config.read_text()),a.geometry,a.wind_checkpoint,a.output,a.device)
  except Exception as exc:
   if a.output.exists():write(a.output/'failure.json',{'complete':False,'error':repr(exc),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
   raise
