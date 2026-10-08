"""Prepare the same solar planning problem for either retained city scene.

Original high-resolution shadow frames are sampled at hypothetical flat-ground
receptors. This adapter is separate from the historical DTM-based pilot.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
import numpy as np
from common.storage import Storage, within
from common.city import sources
from common.export import write,digest


def prepare_scene(storage,scene):
    base,old,_=sources(storage,scene)
    external=Path(json.loads((storage.root/'sources.local.json').read_text())['legacy_output'])
    cfg=json.loads((storage.metadata(scene)/'configs/planning_city.json').read_text())
    if cfg['scene_id']!=scene:raise ValueError('Planning scene mismatch')
    grid=old['grid'];x0,y0=grid['x0'],-grid['z_south'];cell=old['lite']['cell_m']
    footprint_path=base/'physics'/old['lite']['footprint'];footprint=np.load(footprint_path,mmap_mode='r')
    xmin,ymin,xmax,ymax=cfg['bounds_enu_m']
    if not (x0<=xmin<xmax<=x0+footprint.shape[1]*cell and y0<=ymin<ymax<=y0+footprint.shape[0]*cell):raise ValueError('Planning crop outside scene')
    xx,yy=np.meshgrid(np.arange(xmin+2,xmax,4),np.arange(ymin+2,ymax,4))
    cc=((xx-x0)/cell).astype(int);rr=((yy-y0)/cell).astype(int);keep=~footprint[rr,cc]
    receptors=np.column_stack([xx[keep],yy[keep],np.zeros(keep.sum())])
    sites=[]
    for y in np.arange(ymin+12,ymax-12,20):
        for x in np.arange(xmin+12,xmax-12,20):
            patch=footprint[int(np.floor((y-6-y0)/cell)):int(np.ceil((y+6-y0)/cell)),int(np.floor((x-6-x0)/cell)):int(np.ceil((x+6-x0)/cell))]
            if patch.size and not patch.any():sites.append({'x_m':float(x),'y_m':float(y),'z_m':3.2,'width_m':12,'depth_m':12,'cost_units':1})
    if len(sites)<15:raise ValueError('Not enough footprint-clear hypothetical sites')
    candidates=[dict(sites[int(i)],id=f'p{n:02d}') for n,i in enumerate(np.linspace(0,len(sites)-1,15,dtype=int))]
    arrays={'receptors':receptors};records=[{'id':'footprint','path':str(footprint_path),'sha256':digest(footprint_path)}]
    for season,date in [('summer','2026-06-21'),('winter','2026-12-21')]:
        folder=within(external,'core008/physics/scaled_latent/solar/'+date if scene=='south_ken' else 'white_city/physics/solar_experimental/'+date)
        framepath=folder/'frames.json';frames=json.loads(framepath.read_text());records.append({'id':season+'_frames','path':str(framepath),'sha256':digest(framepath)})
        shadecell=1 if scene=='south_ken' else 2
        rr=((receptors[:,1]-y0)/shadecell).astype(int);cc=((receptors[:,0]-x0)/shadecell).astype(int)
        selected=[]
        for i,frame in enumerate(frames[:-1]):
            hour=frame.get('hour_utc')
            if hour is None:
                stamp=datetime.fromisoformat(frame['utc']);hour=stamp.hour+stamp.minute/60
            if not 10<=hour<16:continue
            following=frames[i+1].get('hour_utc')
            if following is None:
                stamp=datetime.fromisoformat(frames[i+1]['utc']);following=stamp.hour+stamp.minute/60
            dt=(following-hour)*3600
            if abs(dt-600)>1:raise ValueError('Missing 10-minute source interval')
            path=folder/'shadow_1m_packed'/f"shadow_{frame['index']:03d}.npy" if scene=='south_ken' else folder/f"shadow_{frame['index']:03d}_packed.npy"
            packed=np.load(path,mmap_mode='r');shade=((packed[rr,cc//8]>>(7-cc%8))&1).astype(bool)
            direct=frame['dni_w_m2']*max(0,np.sin(np.deg2rad(frame['altitude_deg'])))*(~shade)
            selected.append((frame,hour,dt,direct));records.append({'id':season+str(i),'path':str(path),'sha256':digest(path)})
        if len(selected)<4:raise ValueError('Insufficient recorded sunlight')
        for split,parity in [('development',0),('holdout',1)]:
            part=selected[parity::2];prefix=season+'_'+split+'_'
            arrays[prefix+'direct_w_m2']=np.stack([x[3] for x in part]);arrays[prefix+'duration_s']=np.array([x[2] for x in part])
            arrays[prefix+'hour_utc']=np.array([x[1] for x in part])
            for key in ('altitude_deg','azimuth_deg'):arrays[prefix+key]=np.array([x[0][key] for x in part])
    rid='planning_city_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    out=storage.assets(scene,'input')/rid;out.mkdir(parents=True)
    np.savez_compressed(out/'background.npz',**arrays)
    task=dict(cfg,run_id=rid,candidates=candidates,receptor_count=len(receptors),candidate_count=len(candidates),
              objective='Maximize summer direct-ground-radiation reduction subject to winter-loss and budget constraints',
              interpretation='Hypothetical footprint-clear sites, flat planning plane, uniform receptors and unit costs; not a land-access or pedestrian survey.',
              physical_scope='Opaque horizontal panels, direct solar radiation only; existing background shadow fields fixed.',
              split_note='Alternating clear-sky intervals; correlated holdout, not unseen weather.',source_solver_provenance='legacy-unrecorded')
    write(out/'task.json',task);write(out/'input_provenance.json',records);write(out/'config.json',cfg)
    write(out/'spatial.json',json.loads((storage.metadata(scene)/'project.json').read_text())['spatial'])
    write(storage.metadata(scene)/'configs/planning_city_task.json',{'input_path':rid})
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',choices=['south_ken','white_city']);a=p.parse_args();print(prepare_scene(Storage.load(),a.scene))
