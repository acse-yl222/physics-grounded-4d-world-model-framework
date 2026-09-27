"""Scene-specific solar and shallow-water solvers on the prepared 2 m mesh grid.

Experimental coordinate/terrain assumptions must be explicitly confirmed in
the configuration before computation. No South Kensington terrain is reused.
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import shutil
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np
import torch

if __package__ in (None,''):
    sys.path.insert(0,str(repo_root()))
from common.pipeline.paths import ROOT,project_path
from common.pipeline.scene_scaled_latent import save_json,save_npz,digest,log


def terrain(cfg):
    g=project_path(cfg['geometry']);cell=cfg['cell_m']
    metadata=json.loads((g/'metadata.json').read_text())
    assert metadata['spacing_xyz_m']==[cell]*3
    h=np.load(g/'height_m.npy');foot=np.load(g/f'footprint_{cell}m_yx.npy')
    ground=np.load(g/'ground_mesh_m_yx.npy')
    canopy=np.repeat(np.repeat(np.load(g/f'canopy_{4*cell}m_yx.npy'),4,0),4,1)
    grass=np.repeat(np.repeat(np.load(g/f'grass_{4*cell}m_yx.npy'),4,0),4,1)
    assert h.shape==foot.shape==ground.shape==canopy.shape==grass.shape
    return np.where(foot,np.maximum(h,ground),ground),foot,(canopy|grass)&~foot,canopy&~foot


def solar(cfg,bed,foot,green,canopy,out):
    from urban_flow.physics.solar.model import ShadowNet,HorizonNet,sun_position,clear_sky
    cell=cfg['cell_m'];settings=cfg['solar'];loc=cfg['assumptions'];ny,nx=bed.shape
    sn=ShadowNet(bed,cell,'cuda');svf,horizon=HorizonNet(sn,n_azimuth=16,altitudes_deg=tuple(range(2,90,5)))()
    np.save(out/'sky_view_factor.npy',svf.cpu().numpy())
    save_npz(out/'horizon.npz',degrees=horizon.cpu().numpy().astype(np.float16))
    trans=torch.as_tensor(np.where(canopy,settings['canopy_transmittance'],1).astype(np.float32),device='cuda')
    solid=torch.as_tensor(foot,device='cuda')
    for date in settings['dates']:
        start=datetime.fromisoformat(date).replace(tzinfo=timezone.utc);d=out/date;d.mkdir(exist_ok=True)
        energy=torch.zeros_like(svf);sunlit=torch.zeros_like(svf);frames=[];coarse=[]
        for minutes in range(0,1440,settings['minutes']):
            stamp=start+timedelta(minutes=minutes)
            alt,az=sun_position(loc['latitude_deg'],loc['longitude_deg'],stamp.year,stamp.month,stamp.day,minutes/60)
            if alt<=0:continue
            shadow=sn(alt,az);dni,dhi=clear_sky(alt,stamp.month)
            direct=(~shadow).float()*trans*dni*np.sin(np.radians(alt))
            ghi_open=dni*np.sin(np.radians(alt))+dhi
            reflected=settings['albedo']*ghi_open*(1-svf)
            ghi=direct+dhi*svf+torch.where(solid,0.,reflected)
            assert torch.isfinite(ghi).all()
            dt=settings['minutes']*60;energy+=ghi*dt;sunlit+=(~shadow).float()*dt
            index=len(frames)
            np.save(d/f'shadow_{index:03d}_packed.npy',np.packbits(shadow.cpu().numpy(),axis=1))
            coarse.append(ghi.reshape(ny//4,4,nx//4,4).mean(dim=(1,3)).cpu().numpy().astype(np.float16))
            frames.append({'index':index,'utc':stamp.isoformat(),'local_time':stamp.astimezone(ZoneInfo('Europe/London')).isoformat(),
                           'altitude_deg':alt,'azimuth_deg':az,'dni_w_m2':dni,'dhi_w_m2':dhi})
        np.save(d/f'ghi_{4*cell}m_tyx.npy',np.stack(coarse));np.save(d/'daily_irradiation_kwh_m2.npy',(energy/3.6e6).cpu().numpy())
        np.save(d/'sunlit_hours.npy',(sunlit/3600).cpu().numpy());save_json(d/'frames.json',frames)
        log(f'Solar {date}: {len(frames)} daylight frames')
    save_json(out/'status.json',{'complete':True,'dates':settings['dates'],'assumed_georeferencing':True})


def flood(cfg,bed,foot,green,canopy,out):
    from scipy.ndimage import distance_transform_edt
    from urban_flow.physics.flood.model import ShallowWater
    s=cfg['flood'];cell=cfg['cell_m'];mmh=1e-3/3600
    solver=ShallowWater(bed,foot,cell,np.where(green,s['manning_green'],s['manning_paved']),'cuda')
    roof_weight=np.zeros_like(bed)
    nearest=distance_transform_edt(foot,return_distances=False,return_indices=True)
    np.add.at(roof_weight,(nearest[0][foot],nearest[1][foot]),1.)
    ground=torch.as_tensor((~foot).astype(np.float32),device='cuda');roofs=torch.as_tensor(roof_weight,device='cuda')
    sink=torch.as_tensor(np.where(foot,0,np.where(green,s['green_infiltration_mm_h'],s['sewer_mm_h']))*mmh,dtype=torch.float32,device='cuda')
    absorb=torch.zeros_like(solver.solid);absorb[:2]=True;absorb[-2:]=True;absorb[:,:2]=True;absorb[:,-2:]=True
    maxima=torch.zeros_like(solver.h);t=0.;next_frame=0.;rows=[];totals=dict(source=0.,drained=0.,outflow=0.,neg_clamped=0.)
    start=time.time()
    while t<s['duration_seconds']-1e-7:
        # Land exactly on rainfall-change, frame and final times.
        boundary=(int(t//900)+1)*900
        dt=min(solver.stable_dt(s['dt_max_seconds']),s['duration_seconds']-t,boundary-t)
        if next_frame>t:dt=min(dt,next_frame-t)
        block=int(t//900);rain=s['rain_mm_h_15min'][block]*mmh if block<len(s['rain_mm_h_15min']) else 0.
        src=rain*ground+max(0.,rain-s['sewer_mm_h']*mmh)*roofs
        stats=solver.step(dt,source=src,sink_rate=sink,absorb=absorb);t+=dt
        for key in totals:totals[key]+=stats[key]
        maxima=torch.maximum(maxima,solver.h)
        if t>=next_frame-1e-6 or t>=s['duration_seconds']-1e-6:
            if shutil.disk_usage(out).free<2*1024**3:raise RuntimeError('Disk reserve reached')
            h=solver.h.cpu().numpy();assert np.isfinite(h).all() and h.min()>=0
            save_npz(out/f'depth_{len(rows):03d}.npz',depth_m=h)
            stored=solver.volume();balance=stored-(totals['source']-totals['drained']-totals['outflow']+totals['neg_clamped'])
            rows.append({'time_seconds':t,'stored_m3':stored,'max_depth_m':float(h.max()),'balance_error_m3':balance,**totals})
            save_json(out/'series.json',rows);save_json(out/'status.json',{'complete':False,'simulated_seconds':t,'total_seconds':s['duration_seconds']})
            log(f'Flood {t/60:.1f} min; max depth {h.max():.3f} m; elapsed {time.time()-start:.1f}s')
            next_frame+=s['frame_seconds']
    np.save(out/'max_depth_m.npy',maxima.cpu().numpy())
    save_json(out/'status.json',{'complete':True,'frames':len(rows),'terrain':'experimental GLB surface, not real DTM','final_balance_error_m3':rows[-1]['balance_error_m3']})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',default='configs/white_city/surface_physics.json')
    ap.add_argument('--stage',choices=['solar','flood'],required=True)
    ap.add_argument('--check',action='store_true',help='Check inputs without running an assumed scenario')
    args=ap.parse_args();cfg=json.loads(project_path(args.config).read_text())
    bed,foot,green,canopy=terrain(cfg)
    if args.check:
        print(json.dumps({'shape_yx':list(bed.shape),'cell_m':cfg['cell_m'],'experimental_assumptions_confirmed':cfg['experimental_assumptions_confirmed']}));return
    if not cfg['experimental_assumptions_confirmed']:
        raise RuntimeError('Coordinate and GLB-terrain assumptions have not been confirmed; no simulation started.')
    out=project_path(cfg['output'])/(args.stage+'_experimental');out.mkdir(exist_ok=True)
    source=ROOT/f'src/urban_flow/physics/{args.stage}/model.py'
    save_json(out/'run_config.json',{'config':cfg,'solver':str(source),'solver_sha256':digest(source),
                                   'geometry_sha256':digest(project_path(cfg['geometry'])/'metadata.json')})
    torch.set_num_threads(8)
    {'solar':solar,'flood':flood}[args.stage](cfg,bed,foot,green,canopy,out)


if __name__=='__main__':main()
