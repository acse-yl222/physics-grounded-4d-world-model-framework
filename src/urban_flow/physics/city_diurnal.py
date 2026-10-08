"""Identical solar-forced, state-carrying 3-D thermal diagnostic for either city.

Uses retained 32 m horizontal / 8 m vertical inputs and one frozen 3-D wind
snapshot. This controlled model is not measured weather or a replay of either
city's older thermal experiment.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import uuid
import numpy as np
from common.city import sources, field_spec, register_view
from common.contract import validate
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runs import promote
from common.storage import Storage, within


def block_mean(array, fy, fx):
    array=np.asarray(array);ny,nx=array.shape[-2:]
    if ny%fy or nx%fx: raise ValueError('Grid cannot be block-averaged exactly')
    return array.reshape(*array.shape[:-2],ny//fy,fy,nx//fx,fx).mean(axis=(-3,-1))


def building_columns(height, footprint, factor=4, dz=8, layers=8):
    height=np.asarray(height);footprint=np.asarray(footprint,bool)
    if height.shape!=footprint.shape or not np.isfinite(height).all():raise ValueError('Invalid building height/footprint grid')
    ny,nx=height.shape
    if ny%factor or nx%factor:raise ValueError('Building grid is not divisible by aggregation factor')
    height=np.where(footprint,height,0.).reshape(ny//factor,factor,nx//factor,factor).max(axis=(1,3))
    return np.arange(layers)[:,None,None]*dz<height[None]


def prepare_inputs(storage, scene):
    base, old, meta=sources(storage,scene)
    config=json.loads((storage.root/'sources.local.json').read_text())
    external=Path(config['legacy_output'])
    records=[]
    def record(path): records.append({'path':str(path),'sha256':digest(path)})
    if scene=='south_ken':
        cache=within(external,'core008/physics/scaled_latent/temperature3d_solar/velocity_cache')
        components=[]
        for key in ('u','v','w'):
            path=cache/f'velocity_{key}_3d.npy';a=np.load(path,mmap_mode='r')[-1,:,::-1,:].astype('f4');record(path)
            components.append(-a if key=='v' else a)
        wind=np.stack(components);path=cache/'solid_mask_3d.npy';solid=np.load(path)[:,::-1,:];record(path)
        # Original z=4 m layers -> common z=8 m, restricted to first 64 m.
        wind=wind.reshape(3,8,2,*wind.shape[-2:]).mean(axis=2)
        solid=solid.reshape(8,2,*solid.shape[-2:]).max(axis=1);cell=4
    else:
        path=within(external,'white_city/physics/scaled_latent/wind/wind8m_099.npz')
        with np.load(path) as d: wind=d['uvw'][:,:8].astype('f4')
        record(path)
        # The retained SCALED mask has an artificial fully-solid bottom plane.
        # Temperature needs physical building columns with open-ground exchange.
        path=base/'physics/masks/roof_height_m_2m_yx.npy';height=np.load(path).astype('f4');record(path)
        path=base/'physics/masks/building_footprint_2m_yx.npy';footprint=np.load(path).astype(bool);record(path)
        solid=building_columns(height,footprint);cell=8
    factor=32//cell
    wind=block_mean(wind,factor,factor).astype('f4')
    # Any occupied fine cell is conservatively solid in a coarse cell.
    solid=block_mean(solid.astype('f4'),factor,factor)>0
    solar=field_spec(storage,scene,'solar');path=solar['path'];record(path)
    ghi=np.asarray(np.load(path,mmap_mode='r'),dtype='f4')
    if not np.isfinite(ghi).all(): raise ValueError('Solar forcing contains invalid cells')
    sf=int(32/solar['cell_m']);ghi=block_mean(ghi,sf,sf).astype('f4')
    if ghi.shape[-2:]!=solid.shape[-2:]:raise ValueError('Thermal/solar domains differ')
    out=storage.assets(scene,'input')/('diurnal_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
    np.savez_compressed(out/'inputs.npz',wind=wind,solid=solid,ghi=ghi,time_s=np.asarray(solar['samples']))
    write(out/'provenance.json',{'inputs':records,'epoch':solar['epoch'],'origin_xy':solar['origin_xy'],'dx_m':32,'dz_m':8,
         'wind':'Final preserved 3-D snapshot, frozen for the daylight diagnostic; no missing wind times invented',
         'scope':'Controlled clear-sky forcing; conservative block mask, area-mean irradiance and velocity; no measured validation'})
    write(storage.metadata(scene)/'configs/diurnal.json',{'input_path':str(out.relative_to(storage.assets(scene,'input'))),
         'ambient_c':20.,'albedo':.2,'emissivity':.95,'convective_coefficient_w_m2_k':12.,'exchange_per_s':.001,'diffusivity_m2_s':1.})
    return out


def run(storage,scene,device='cpu'):
    import torch
    from common.pipeline.scene_temperature_physical import load_solver,fields_and_boundary
    from .diurnal_solver import solve_from_state
    torch.set_num_threads(4)
    cfg=json.loads((storage.metadata(scene)/'configs/diurnal.json').read_text())
    source=within(storage.assets(scene,'input'),cfg['input_path']);meta=json.loads((source/'provenance.json').read_text())
    with np.load(source/'inputs.npz') as d:wind=d['wind'];solid=d['solid'];ghi=d['ghi'];times=d['time_s']
    rid='diurnal_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    out=storage.scratch(scene,'diurnal',rid);out.mkdir(parents=True)
    import shutil
    shutil.copy2(source/'inputs.npz',out/'inputs.npz');shutil.copy2(source/'provenance.json',out/'input_provenance.json');write(out/'config.json',cfg)
    revision=snapshot_sources(storage.root,out/'source_snapshot.tar.gz')
    model,_=load_solver();ambient=cfg['ambient_c'];state=np.full(solid.shape,ambient,dtype='f4')
    # North-up original solver coordinates; restore row-south ENU on export.
    wind=wind[:,:,::-1,:].copy();wind[1]*=-1;solid=solid[:,::-1,:].copy()
    fields,boundary=fields_and_boundary(solid,wind[None],ambient,0.,cfg['exchange_per_s'])
    velocity=SimpleNamespace(model_resolution_m=meta['dx_m'],height_scale_m=meta['dz_m'])
    thermal=model.Temperature3DScenarioConfig(temperature_solver_device=device,ambient_temp_c=ambient,
             inflow_temp_c=ambient,diffusion_coeff_m2_s=cfg['diffusivity_m2_s'])
    air=[state[1,::-1,:].copy()];surface=[];checks=[]
    emissivity=np.full(ghi.shape[-2:],cfg['emissivity'],dtype='f4')
    for index in range(len(times)):
        shortwave=(1-cfg['albedo'])*ghi[index,::-1,:]
        excess=model.solve_surface_temperature_excess_c(shortwave,emissivity,np.zeros_like(shortwave),np.zeros_like(shortwave),
               np.full_like(shortwave,cfg['convective_coefficient_w_m2_k']),5.670374419e-8*(ambient+273.15)**4,ambient,0.)
        surface.append((ambient+excess)[::-1,:].copy())
        if index==len(times)-1:break
        boundary['ground_surface_temperature_excess_c']=excess
        boundary['roof_surface_temperature_excess_3d']=fields['roof_mask_3d']*excess[None]
        from dataclasses import replace
        step=replace(thermal,frame_duration_s=float(times[index+1]-times[index]))
        state,fluid,report=solve_from_state(model,fields,boundary,velocity,step,state)
        if not np.isfinite(state).all():raise ValueError('Non-finite thermal solution')
        air.append(state[1,::-1,:].copy());checks.append(report)
        if index%20==0:print(f'{scene}: diurnal {index+1}/{len(times)-1}',flush=True)
    np.save(out/'air.npy',np.asarray(air,dtype='<f4'));np.save(out/'surface.npy',np.asarray(surface,dtype='<f4'))
    np.save(out/'air_invalid.npy',solid[1,::-1,:].astype('u1'))
    write(out/'numerics.json',{'intervals':checks,'state_carried_between_intervals':True,'initial_air_c':ambient})
    layers=[]
    for key,z in [('air',12.),('surface',0.)]:
        encoding={'coordinate_frame':'ENU','dtype':'<f4','shape':[len(times),*ghi.shape[-2:]],'axes':'TYX',
                  'origin_m':[*meta['origin_xy'],z],'spacing_m':[32,32],'sample_location':'cell_center','byte_order':'little','compression':'none'}
        if key=='air':encoding.update(mask_asset='air_invalid.npy',mask_dtype='|u1',mask_semantics='invalid_nonzero')
        layers.append({'id':key,'kind':'scalar_field','format':'npy','asset':key+'.npy','sampling':'linear','field':{'name':'temperature','unit':'degC'},
                       'encoding':encoding,'display':{'widget':'scalar_field','capabilities':['pick','legend','opacity']}})
    artifacts=[{'id':'source_snapshot' if p.name=='source_snapshot.tar.gz' else p.name,'asset':p.name,'sha256':digest(p),'media_type':'application/octet-stream'} for p in out.iterdir() if p.name not in ('air.npy','surface.npy','air_invalid.npy')]
    project=json.loads((storage.metadata(scene)/'project.json').read_text())
    write(out/'manifest.json',{'schema_version':'1.1.0','scene_id':scene,'simulation':'diurnal','run_id':rid,'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),
         'provenance':{'code_revision':revision,'dirty':True,'parameters':dict(cfg,scope=meta['scope'],wind=meta['wind']),
                       'inputs':[{'id':'frozen_inputs','sha256':digest(source/'inputs.npz')}]},'spatial':project['spatial'],
         'time':{'unit':'s','samples':times.tolist(),'epoch':meta['epoch']},'layers':layers,'artifacts':artifacts})
    validate(out/'manifest.json');dest=promote(storage,out)
    register_view(storage,scene,rid.lower(),['legacy_web',rid],[{'run_id':'legacy_web','layer_id':'geometry','visible':True},
         *[{'run_id':rid,'layer_id':l['id'],'visible':l['id']=='air'} for l in layers]],'Daylight thermal diagnostic · controlled forcing')
    write(storage.metadata(scene)/'configs/diurnal_result.json',{'run_id':rid,'view_id':rid.lower()})
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run']);p.add_argument('scene',choices=['south_ken','white_city']);p.add_argument('--device',default='cpu');a=p.parse_args()
    print(prepare_inputs(Storage.load(),a.scene) if a.action=='prepare' else run(Storage.load(),a.scene,a.device))
