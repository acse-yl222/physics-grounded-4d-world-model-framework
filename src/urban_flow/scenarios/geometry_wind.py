"""Controlled geometry-driven incompressible MAC wind pilot, not validated CFD.

CLI: python -m urban_flow.scenarios.geometry_wind --config CONFIG --geometry DIR
--output NEW_DIR [--device cuda] [--self-test]. No scene publication or defaults.
"""
import argparse,datetime,hashlib,json,math,time
from pathlib import Path
import numpy as np
import torch
from urban_flow.solvers.mac_torch import MAC


def write(path,data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()


def clock():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def centred(m):
    fields=[]
    for c,face in enumerate(m.vel):
        axis=2-c
        previous=torch.roll(face,1,axis)
        index=[slice(None)]*3;index[axis]=0
        previous[tuple(index)]=m.inlet if c==0 else 0
        fields.append((face+previous)*.5)
    return torch.stack(fields)*m.f[None]


def diagnostics(m,projection):
    finite=all(bool(torch.isfinite(v).all())for v in m.vel)
    blocked=max(float(v.masked_select(~m.opened(c)).abs().max())if bool((~m.opened(c)).any())else 0. for c,v in enumerate(m.vel))
    if not finite or blocked>1e-7 or projection['divergence_rms']>5e-5:
        raise RuntimeError({'finite':finite,'blocked_normal_velocity':blocked,'projection':projection})
    return dict(projection,finite=finite,blocked_normal_velocity_max_m_s=blocked)


@torch.inference_mode()
def self_test(device='cpu'):
    results={}
    for kind in ('uniform','block'):
        fluid=torch.ones((16,32,32),dtype=torch.bool,device=device)
        if kind=='block':fluid[0:7,12:20,12:20]=False
        m=MAC(fluid,2.,torch.full((16,32),5.,device=device),open_top=True)
        m.vel[0].copy_(m.opened(0)*5.)
        p=m.project(rtol=1e-6,maxiter=240);diagnostics(m,p)
        for _ in range(4):m.advect(.05);p=m.project(rtol=1e-6,maxiter=240)
        d=diagnostics(m,p)
        if kind=='uniform':
            error=float((centred(m)[0]-5).abs().max());assert error<1e-5;d['uniform_speed_error']=error
        else:
            assert float(m.vel[1].abs().max()+m.vel[2].abs().max())>0
            d['obstacle_deflects_flow']=True
        results[kind]=d
    return results


@torch.inference_mode()
def run(config,geometry,output,device='cuda'):
    geometry=Path(geometry);output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4);torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    started=time.monotonic();cfg=dict(config)
    identity={'runner_sha256':sha(Path(__file__)),'mac_solver_sha256':sha(Path(__file__).parents[1]/'solvers/mac_torch.py'),'torch_version':torch.__version__,'device':device,'started_utc':clock()}
    write(output/'runtime_identity.json',identity)
    meta=json.loads((geometry/'metadata.json').read_text())
    if meta.get('shape_zyx')!=cfg['shape_zyx'] or meta.get('origin_xyz_m')!=cfg['origin_xyz_m'] or meta.get('spacing_xyz_m')!=[cfg['cell_m']]*3 or meta.get('frame')!='ENU':
        write(output/'status.json',{'state':'failed','stage':'geometry_contract','metadata':meta})
        raise ValueError('Geometry metadata shape/origin/spacing/ENU mismatch')
    solid=np.load(geometry/'solid.npy')
    expected=tuple(cfg['shape_zyx'])
    if solid.shape!=expected or solid.dtype!=np.bool_:raise ValueError('Expected configured boolean ZYX solid')
    if solid[:,:,0].any():raise ValueError('Inlet boundary obstructed; padding must be checked')
    h=float(cfg['cell_m']);origin=cfg['origin_xyz_m'];solid_hash=sha(geometry/'solid.npy')
    write(output/'configuration.json',cfg);write(output/'geometry_input.json',{'directory':str(geometry.resolve()),'solid_sha256':solid_hash,'metadata':json.loads((geometry/'metadata.json').read_text())if(geometry/'metadata.json').exists()else None})
    heights=cfg['sample_heights_m'];indices=[min(solid.shape[0]-1,max(0,int(math.floor((v-origin[2])/h))))for v in heights]
    actual=[origin[2]+(i+.5)*h for i in indices]
    np.save(output/'sample_invalid.npy',solid[indices]);write(output/'sample_heights.json',{'requested_m':heights,'actual_m':actual,'actual_heights_m':actual,'indices':indices,'tie_policy':'upper cell on exact grid boundary','vertical_reference':'scene-local ENU z, not surveyed AGL'})
    fluid=torch.as_tensor(~solid,device=device);inlet=torch.full(fluid.shape[:2],float(cfg['inlet_m_s']),device=device)*fluid[:,:,0]
    m=MAC(fluid,h,inlet,open_top=True);m.vel[0].copy_(m.opened(0)*cfg['inlet_m_s'])
    initstart=time.monotonic();write(output/'status.json',{'state':'initial_projection','utc':clock()})
    try:
        p=m.project(rtol=cfg['pressure_rtol'],maxiter=cfg['pressure_maxiter'])
        init=diagnostics(m,p);init['wall_seconds']=time.monotonic()-initstart
        write(output/'initial_projection.json',init)
    except Exception as exc:
        write(output/'initial_projection.json',{'failed':True,'error':repr(exc),'wall_seconds':time.monotonic()-initstart})
        write(output/'status.json',{'state':'failed','stage':'initial_projection','error':repr(exc),'utc':clock()})
        raise
    elapsed=0.;step=0;records=[];times=[];samples=[];target=float(cfg['target_seconds']);smoke=float(cfg['smoke_seconds']);goal_selected=False;next_save=0.;simulation_started=time.monotonic()
    def save():
        times.append(elapsed);samples.append(centred(m)[:,indices].cpu().numpy().astype('<f4'))
        np.save(output/'velocity_samples.npy',np.stack(samples));write(output/'sample_times_s.json',times)
    def checkpoint(label):
        torch.save({'time_s':elapsed,'step':step,'velocity_faces':[v.cpu()for v in m.vel],'projection_potential':m.p.cpu(),'projection_potential_not_pressure_pa':True,'solid_sha256':solid_hash,'configuration_sha256':sha(output/'configuration.json'),'origin_xyz_m':origin,'cell_m':h},output/(label+'.pt'))
    save();next_save=float(cfg['save_interval_s'])
    try:
        while elapsed<target-1e-8:
            if time.monotonic()-started>cfg['wall_budget_s']:
                break
            dt=min(cfg['dt_max_s'],cfg['cfl']*h/max(m.maxsum(),.01),target-elapsed,next_save-elapsed)
            if elapsed<smoke:dt=min(dt,smoke-elapsed)
            m.advect(dt);p=m.project(rtol=cfg['pressure_rtol'],maxiter=cfg['pressure_maxiter']);elapsed+=dt;step+=1
            d=diagnostics(m,p);records.append(dict(d,time_s=elapsed,dt_s=dt,step=step,wall_seconds=time.monotonic()-simulation_started))
            write(output/'progress.json',{'records':records,'target_seconds':target,'time_s':elapsed,'wall_seconds':time.monotonic()-started})
            if elapsed>=next_save-1e-8 or elapsed>=target-1e-8:
                save();next_save=elapsed+cfg['save_interval_s']
            if not goal_selected and elapsed>=smoke-1e-8:
                checkpoint('smoke_checkpoint');goal_selected=True
                rate=(time.monotonic()-simulation_started)/max(elapsed,.001)
                if rate*(target-elapsed)>cfg['wall_budget_s']-(time.monotonic()-started)-30:
                    target=max(elapsed,float(cfg['fallback_seconds']))
                write(output/'benchmark.json',{'smoke_time_s':elapsed,'simulation_wall_seconds':time.monotonic()-simulation_started,'seconds_wall_per_physical_second':rate,'selected_target_seconds':target,'reason':'bounded startup duration, never assumed steady state'})
            if step%10==0:print(f'wind {elapsed:.3f}/{target:g}s, div={p["divergence_rms"]:.3g}',flush=True)
        if times[-1]!=elapsed:save()
        checkpoint('final_checkpoint')
        status='complete_startup' if elapsed>=target-1e-8 else 'bounded_walltime_partial'
    except Exception as exc:
        checkpoint('failure_checkpoint');write(output/'status.json',{'state':'failed','error':repr(exc),'time_s':elapsed,'step':step});raise
    assert sha(Path(__file__))==identity['runner_sha256'] and sha(Path(__file__).parents[1]/'solvers/mac_torch.py')==identity['mac_solver_sha256'], 'Solver source changed during execution'
    write(output/'metadata.json',{'complete':status=='complete_startup','origin_enu_m':origin,'cell_m':h,'shape_zyx':list(solid.shape),'source_geometry':str(geometry.resolve()),'solid_sha256':solid_hash,'configuration_sha256':sha(output/'configuration.json'),'solver_sha256':sha(Path(__file__)),'mac_solver_sha256':sha(Path(__file__).parents[1]/'solvers/mac_torch.py'),'torch_version':torch.__version__,'device':device,'sample_layout':'T3HYX','time_semantics':'physical seconds after initial projection','actual_heights_m':actual})
    summary={'state':status,'time_s':elapsed,'step':step,'requested_target_seconds':config['target_seconds'],'selected_target_seconds':target,'wall_seconds':time.monotonic()-started,'initial_projection':init,'max_divergence_rms':max([r['divergence_rms']for r in records],default=init['divergence_rms']),'all_finite':True,'blocked_normal_velocity_max_m_s':max([r['blocked_normal_velocity_max_m_s']for r in records],default=0),'sample_shape_tchyx':list(np.stack(samples).shape),'actual_sample_heights_m':actual,'time_semantics':'physical seconds after initial divergence-free projection','steady_convergence_verified':False,'limitations':[f'Controlled uniform {cfg["inlet_m_s"]:g} m/s west-to-east scenario, not measured weather.','Inviscid first-order upwind MAC, numerical diffusion; no turbulence closure, wall friction, heat or buoyancy.',f'{h:g} m solid-mask geometry cannot resolve facade/plant details; no pedestrian comfort certification.','Scene-local vertical datum; sample heights are not surveyed terrain-following AGL.','Finite startup only; no steady-state or grid-convergence claim.']}
    write(output/'summary.json',summary);write(output/'status.json',{'state':status,'time_s':elapsed,'utc':clock()});return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path);p.add_argument('--geometry',type=Path);p.add_argument('--output',type=Path);p.add_argument('--device',default='cuda');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:print(json.dumps(self_test(a.device),indent=2));return
    if not all((a.config,a.geometry,a.output)):p.error('config, geometry and output required')
    print(json.dumps(run(json.loads(a.config.read_text()),a.geometry,a.output,a.device),indent=2))

if __name__=='__main__':main()
