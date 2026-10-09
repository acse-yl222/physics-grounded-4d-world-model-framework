"""Run a 4 m near-ground road-source tracer scenario from retained wind."""
import argparse,json,shutil,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from common.storage import Storage
from common.export import digest,write
from common.provenance import snapshot_sources
from common.contract import validate
from common.runs import promote
from urban_flow.scenarios.near_ground_tracer import PlanarTracer


def run(config_path):
    cfg=json.loads(Path(config_path).read_text());storage=Storage.load();scene=cfg['scene_id']
    out=storage.scratch(scene,'tracer',cfg['run_id']);out.mkdir(parents=True,exist_ok=False)
    (out/'data').mkdir();(out/'provenance').mkdir()
    wr=storage.run(scene,cfg['wind_run']);wm=json.loads((wr/'manifest.json').read_text())
    layer=next(l for l in wm['layers'] if l['id']==cfg['wind_layer']);enc=layer['encoding']
    uv=np.load(wr/layer['asset'],mmap_mode='r')[-1];invalid=np.load(wr/enc['mask_asset']).astype(bool)
    dx=enc['spacing_m'][0];x0,y0,z=enc['origin_m'];ny,nx=invalid.shape
    if dx!=4 or enc['spacing_m']!=[4,4]:raise ValueError('True 4 m input required')
    roads=storage.run(scene,cfg['traffic_run'])/'viewer_traffic/roads.json'
    source=np.zeros((ny,nx),np.float64)
    for lane in json.loads(roads.read_text())['lanes']:
        points=np.asarray(lane['world_xyz'])
        for a,b in zip(points,points[1:]):
            count=max(2,int(np.linalg.norm(b-a)/(dx/2))+1)
            p=a[None]+np.linspace(0,1,count)[:,None]*(b-a)[None]
            ix=np.floor((p[:,0]-x0)/dx).astype(int);iy=np.floor((-p[:,2]-y0)/dx).astype(int)
            valid=(ix>=0)&(ix<nx)&(iy>=0)&(iy<ny)
            source[iy[valid],ix[valid]]=cfg['source_rate_au_s']
    source[invalid]=0
    if not source.any():raise ValueError('No valid mapped road source cells')
    model=PlanarTracer(uv[:2],invalid,dx,cfg['diffusion_m2_s'])
    times=np.arange(0,cfg['duration_s']+1e-6,cfg['save_interval_s']).tolist()
    data=np.lib.format.open_memmap(out/'data/concentration.npy',mode='w+',dtype='<f4',shape=(len(times),ny,nx));data[0]=0
    t=0.;rows=[];emitted=outflow=0.;start=time.monotonic()
    for index,target in enumerate(times[1:],1):
        while t<target-1e-9:
            dt=min(model.dt_max,1.,target-t);row=model.step(dt,source);t+=dt
            emitted+=row['emitted'];outflow+=row['outflow']
        data[index]=model.c
        error=row['mass']-emitted+outflow
        if abs(error)>1e-8*max(1,emitted):raise RuntimeError('Global mass balance failed')
        rows.append(dict(time_s=t,mass=row['mass'],emitted=emitted,outflow=outflow,balance_error=error,maximum=float(model.c.max())))
        write(out/'progress.json',{'time_s':t,'wall_s':time.monotonic()-start});print('tracer',t,flush=True)
    data.flush();del data
    np.save(out/'data/invalid.npy',invalid.astype('u1'));np.save(out/'provenance/source_rate.npy',source.astype('<f4'))
    np.save(out/'provenance/frozen_wind_enu.npy',uv)
    shutil.copy2(roads,out/'provenance/roads.json');shutil.copy2(config_path,out/'provenance/config.json')
    write(out/'provenance/mass_balance.json',rows)
    revision=snapshot_sources(storage.root,out/'source_snapshot.tar.gz')
    limits=['Controlled 2-D near-ground passive tracer, not 3-D dispersion or calibrated pollution/health exposure.',
            'Uniform arbitrary source rate on mapped road cells, not measured emissions or emissions derived from vehicle counts.',
            'Frozen final SCALED near-ground horizontal wind; no vertical exchange, chemistry or deposition.',
            'Scalar-conservative first-order upwind transport with isotropic diffusion; zero exterior inflow concentration and impermeable building faces.']
    artifacts=[{'id':'source_snapshot' if p.name=='source_snapshot.tar.gz' else p.relative_to(out).as_posix(),'asset':p.relative_to(out).as_posix(),'sha256':digest(p),'media_type':'application/octet-stream'} for p in sorted(out.rglob('*')) if p.is_file() and not p.is_relative_to(out/'data')]
    manifest={'schema_version':'1.1.0','scene_id':scene,'simulation':'pollution','run_id':cfg['run_id'],'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),'spatial':wm['spatial'],'time':{'unit':'s','samples':times},'provenance':{'code_revision':revision,'dirty':True,'parameters':{'config':cfg,'limitations':limits,'source_cells':int(np.count_nonzero(source))},'inputs':[{'id':'wind_manifest','sha256':digest(wr/'manifest.json')},{'id':'roads','sha256':digest(roads)}]},'layers':[{'id':'near_ground_tracer','kind':'scalar_field','format':'npy','asset':'data/concentration.npy','sampling':'step','field':{'name':'Near-ground planar road tracer','unit':'a.u.'},'encoding':{'coordinate_frame':'ENU','dtype':'<f4','shape':[len(times),ny,nx],'axes':'TYX','origin_m':[x0,y0,z],'spacing_m':[dx,dx],'sample_location':'cell_center','byte_order':'little','compression':'none','mask_asset':'data/invalid.npy','mask_dtype':'|u1','mask_semantics':'invalid_nonzero'},'display':{'widget':'scalar_field','capabilities':['pick','legend','opacity'],'range':[.001,max(.01,float(model.c.max()))]}}],'artifacts':artifacts}
    write(out/'manifest.json',manifest);validate(out/'manifest.json');return promote(storage,out)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);a=p.parse_args();print(run(a.config))
