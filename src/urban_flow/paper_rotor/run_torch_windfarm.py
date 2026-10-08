"""Execute recorded-geometry TorchRotor-RANS with ADM or rotating ALM."""
import argparse,json,math,time,shutil,traceback
from pathlib import Path
import numpy as np
import torch
from common.export import write,digest
from common.runtime import trial_root
from common.storage import Storage
from common.provenance import snapshot_sources
from urban_flow.solvers.rans.terrain import TerrainRANS
from urban_flow.solvers.rans.transport import face_pair
from .rotor import WeightedRotor
from .scene_parameters import rotor_parameters


class FarmRotors:
    def __init__(self,solver,geometry,config):
        self.m=solver;self.config=config;self.disks=[];h=solver.h
        origin=np.array(geometry['origin_xyz_m'])
        for t in geometry['turbines']:
            axis=np.array(t['normal_xyz'],dtype=float);axis/=np.linalg.norm(axis)
            hub=np.array(t['hub_xyz_m']);radius=t['radius_m']
            parameters=rotor_parameters(config,radius)
            extent=parameters['sigma_m']*config['cutoff_sigma']*abs(axis)+radius*np.sqrt(np.maximum(0,1-axis**2))
            lo=np.floor((hub-extent-origin)/h).astype(int)-2
            hi=np.ceil((hub+extent-origin)/h).astype(int)+2
            if np.any(lo<1) or np.any(hi>=np.array(solver.shape[::-1])-1):raise ValueError('Rotor touches boundary')
            sl=tuple(slice(int(a),int(b)) for a,b in zip(lo[::-1],hi[::-1]))
            xyz=torch.stack(torch.meshgrid(*[torch.arange(int(a),int(b),device=solver.k.device,dtype=solver.k.dtype)*h+h/2+o for a,b,o in zip(lo[::-1],hi[::-1],origin[::-1])],indexing='ij'),-1).flip(-1)
            rotor=WeightedRotor(radius,parameters['sigma_m'],config['ct'],parameters['inner_radius_m'],config['cutoff_sigma'],config['rho_kg_m3'])
            self.disks.append((t,sl,xyz,rotor,axis))

    def loads(self,ramp=1.,time_s=None):
        m=self.m;u=m.centred();face_acc=[torch.zeros_like(m.k) for _ in range(3)];rows=[]
        for t,sl,xyz,rotor,axis in self.disks:
            fluid=m.f[sl];velocity=torch.stack([v[sl] for v in u],-1)
            result=rotor(xyz,velocity,fluid*m.h**3,t['hub_xyz_m'],axis)
            target=-result['body_force']*ramp;errors=[]
            for c in range(3):
                local=result['acceleration'][...,c]*fluid*ramp
                # Correct masked face interpolation so total applied force equals thrust.
                a=2-c;l,r=face_pair(local,a)
                interpolated=.5*(l+r).narrow(a,1,local.shape[a])*m.mac.opened(c)[sl]
                applied=interpolated.double().sum()*m.h**3*self.config['rho_kg_m3']
                if abs(float(target[c]))>1e-10:
                    if abs(float(applied))<1e-20:raise ValueError('No open rotor force faces')
                    interpolated*=target[c]/applied
                else:interpolated.zero_()
                face_acc[c][sl]+=interpolated
                errors.append(abs(float(interpolated.double().sum()*m.h**3*self.config['rho_kg_m3']-target[c])))
            rows.append(dict(id=t['id'],disc_speed_m_s=float(result['disc_speed']),thrust_N=float(result['thrust'])*ramp,force_error_N=max(errors)))
        return face_acc,rows


@torch.inference_mode()
def run(args):
    torch.set_num_threads(8);torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    root=trial_root('windfarm','torch_rotor_rans');root.mkdir(parents=True)
    cfg=json.loads(args.config.read_text());g=json.loads((args.geometry/'metadata.json').read_text())
    cfg.update(model_name='TorchRotor-RANS',model_version=cfg.get('model_version','0.1'),turbulence_model='kEpsilon',target_seconds=args.seconds,save_interval_s=args.save_every,shape_zyx=g['shape_zyx'],origin_xyz_m=g['origin_xyz_m'],cell_m=g['cell_m'],dtype='float32',experimental_accuracy_validated=False,steady_convergence_verified=False)
    for name in ['solid.npy','ground.npy','terrain_valid.npy','metadata.json']:
        shutil.copy2(args.geometry/name,root/name)
    write(root/'configuration.json',cfg)
    revision=snapshot_sources(Storage.load().root,root/'source_snapshot.tar.gz')
    write(root/'provenance.json',dict(code_revision=revision,dirty=True,geometry_hashes={n:digest(root/n) for n in ['solid.npy','ground.npy','terrain_valid.npy','metadata.json']},source_snapshot_sha256=digest(root/'source_snapshot.tar.gz')))
    alm=cfg.get('rotor_model')=='actuator_line'
    if alm:
        blade_source=Storage.load().root/cfg['blade_input_directory']
        shutil.copytree(blade_source,root/'blade_inputs')
    initial=getattr(args,'initial_state',None)
    if initial:
        parent=root/'parent_state';parent.mkdir()
        for name in ('checkpoint.pt','configuration.json','provenance.json','source_snapshot.tar.gz'):
            shutil.copy2(initial/name,parent/name)
        old=json.loads((initial/'provenance.json').read_text())
        for name in ('solid.npy','metadata.json'):
            if digest(root/name)!=old['geometry_hashes'][name]:raise ValueError('Initial-state geometry differs')
    print(root,flush=True);start=time.monotonic();step=0
    try:
        solid=np.load(root/'solid.npy');ground=np.load(root/'ground.npy');valid=np.load(root/'terrain_valid.npy')
        m=TerrainRANS(torch.as_tensor(~solid,device=args.device),g['cell_m'],cfg['inlet_m_s'],cfg['kinematic_viscosity_m2_s'],cfg['turbulence_intensity'],cfg['turbulence_length_m'])
        if initial:
            state=torch.load(root/'parent_state/checkpoint.pt',map_location=args.device,weights_only=True)
            if state['configuration_sha256']!=digest(root/'parent_state/configuration.json'):raise ValueError('Initial checkpoint identity differs')
            for target,value in zip(m.mac.vel,state['velocity']):target.copy_(value)
            m.k.copy_(state['k']);m.epsilon.copy_(state['epsilon']);m.last_pressure=m.project()
            write(root/'initial_state_provenance.json',dict(parent_run_id=initial.name,parent_time_s=state['time_s'],checkpoint_sha256=digest(root/'parent_state/checkpoint.pt'),interpretation='New model-transition trial clock starts at zero using the parent flow state; not a same-model continuation.'))
        if alm:
            from urban_flow.solvers.actuator_line import RotatingFarm
            rotors=RotatingFarm(m,g,cfg,root/'blade_inputs')
            write(root/'rotor_parameters.json',dict(model='quasi-steady rotating actuator lines',elements_per_blade=cfg['alm_elements'],prescribed_tsr=cfg['alm_tsr'],sigma_m=rotors.sigma,pitch_deg=cfg['alm_pitch_deg']))
        else:
            rotors=FarmRotors(m,g,cfg)
            write(root/'rotor_parameters.json',[dict(id=t['id'],diameter_m=2*t['radius_m'],**rotor_parameters(cfg,t['radius_m'])) for t in g['turbines']])
        out=root/'movie';out.mkdir();data=root/'data';data.mkdir()
        nz,ny,nx=solid.shape;yy,xx=np.indices((ny,nx));z=(ground+cfg['slice_agl_m']-g['origin_xyz_m'][2])/m.h-.5
        zi=np.floor(z).astype(int);fraction=z-zi;inside=(zi>=0)&(zi<nz-1);zi=np.clip(zi,0,nz-2)
        sample_valid=valid&inside&~solid[zi,yy,xx]&~solid[zi+1,yy,xx]
        indices=tuple(torch.as_tensor(v,device=args.device) for v in (zi,yy,xx));frac=torch.as_tensor(fraction,device=args.device,dtype=m.k.dtype)
        frames=[];times=[];speeds=[];history=[];next_save=args.save_every;next_checkpoint=60.;previous_state=None
        def checkpoint():
            temporary=root/'checkpoint.pt.tmp'
            torch.save(dict(velocity=m.mac.vel,k=m.k,epsilon=m.epsilon,time_s=m.time,configuration_sha256=digest(root/'configuration.json')),temporary)
            temporary.replace(root/'checkpoint.pt')
        def save(info):
            nonlocal previous_state
            u=m.centred();iz,iy,ix=indices
            temporal={}
            fields=[*u,m.k,m.epsilon]
            if previous_state is not None:
                for name,current,previous in zip(('u','v','w','k','epsilon'),fields,previous_state):
                    delta=(current[m.f]-previous[m.f]).double()
                    temporal[name]={'rms_change':float(delta.square().mean().sqrt()),'relative_l2_change':float(torch.linalg.vector_norm(delta)/torch.linalg.vector_norm(current[m.f].double()).clamp_min(1e-20))}
            previous_state=[q.clone() for q in fields]
            uvw=torch.stack([(1-frac)*v[iz,iy,ix]+frac*v[iz+1,iy,ix] for v in u]).cpu().numpy()
            uvw[:,~sample_valid]=np.nan
            if not np.isfinite(uvw[:,sample_valid]).all():raise RuntimeError('Nonfinite sampled wind')
            filename=f'frame-{len(times):04d}.npy';np.save(data/filename,uvw[None].astype('<f4'))
            saved_acc,loads=rotors.loads(min(m.time/cfg['startup_ramp_s'],1.))
            alm_audit=rotors.grid_audit(saved_acc) if alm else None
            times.append(m.time);frames.append(uvw[0]);speeds.append([r['disc_speed_m_s'] for r in loads])
            row=dict(step=step,time_s=m.time,wall_seconds=time.monotonic()-start,pressure=info,max_speed_sum_m_s=m.mac.maxsum(),rotors=loads,full_domain_change_since_previous_sample=temporal)
            if alm:row['actuator_line_audit']=alm_audit
            history.append(row);write(root/'history.json',history)
            write(root/'status.json',dict(state='running',step=step,time_s=m.time,target_seconds=args.seconds,wall_seconds=row['wall_seconds']))
            print(json.dumps({k:row[k] for k in ['step','time_s','wall_seconds','max_speed_sum_m_s']}),flush=True)
        save(m.last_pressure)
        while m.time<args.seconds-1e-8:
            dt=min(.25,m.stable_dt(),rotors.stable_dt() if alm else .25,next_save-m.time,args.seconds-m.time)
            if dt<1e-9:next_save+=args.save_every;continue
            acc,_=rotors.loads(min((m.time+dt/2)/cfg['startup_ramp_s'],1.),time_s=m.time+dt/2)
            force_limit=(.3*m.h/max(max(float(a.abs().max()) for a in acc),1e-20))**.5
            if force_limit<dt:
                dt=force_limit
                acc,_=rotors.loads(min((m.time+dt/2)/cfg['startup_ramp_s'],1.),time_s=m.time+dt/2)
            info=m.advance(dt,face_acceleration=acc);step+=1
            if m.mac.maxsum()>80:raise RuntimeError('Velocity guard exceeded')
            if m.time>=next_save-1e-8 or m.time>=args.seconds-1e-8:
                save(info);next_save+=args.save_every
            if m.time>=next_checkpoint-1e-8:
                checkpoint();next_checkpoint+=60.
        checkpoint()
        chunks=[]
        for i,j in enumerate(range(0,len(frames),25)):
            name=f'u-{i}.bin';np.asarray(frames[j:j+25],dtype='<f2').tofile(out/name);chunks.append(name)
        ground.astype('<f4').tofile(out/'ground.bin');np.save(data/'ground.npy',ground.astype('<f4'));np.save(data/'mask.npy',(~sample_valid).astype('u1'))
        rotor_detail='rotating ALM' if alm else 'Ct='+str(cfg['ct'])
        g.update(times=times,display_shape=[ny,nx],display_cell_m=m.h,display_first_center_offset_m=m.h/2,slice_agl_m=cfg['slice_agl_m'],solver=f"TorchRotor-RANS v{cfg['model_version']} / PyTorch k-epsilon",simulation_cell_m=m.h,inlet_m_s=cfg['inlet_m_s'],wind_chunks=chunks,comparison_keys=[],default_model='mac_live',model_labels={'mac_live':f"TORCHROTOR-RANS v{cfg['model_version']} / k–ε"},model_details={'mac_live':f"{m.h:g} m voxel grid · {cfg['inlet_m_s']:g} m/s inlet · {rotor_detail} · PyTorch GPU"},display_note='Exploratory transient · Accuracy/steady state unverified · Rotor spin is display-only · Missing terrain masked',experimental_accuracy_validated=False)
        if alm:
            g.update(rotor_model='actuator_line',rotor_kinematics_asset='rotor-kinematics.json',playback_speed=1.,model_details={'mac_live':f"{m.h:g} m grid · 10 m/s · rotating actuator lines · prescribed TSR {cfg['alm_tsr']:g}"},display_note='Rotating actuator lines · Recorded physical phase · Prescribed speed · Coarse-grid trial; accuracy unverified',rotor_speed_value_semantics='Legacy rotor-speeds contains mean blade-sampled axial flow, not area-averaged disc velocity.')
            write(out/'rotor-kinematics.json',dict(times=times,phase_rad=[[r['phase_rad'] for r in row['rotors']] for row in history],omega_rad_s=[[r['omega_rad_s'] for r in row['rotors']] for row in history],basis_e1_xyz=rotors.e1.tolist(),root_radius_fraction=1.5/63.,prescribed_speed=True))
        write(out/'metadata.json',g);write(out/'rotor-speeds.json',speeds);write(data/'frames.json',dict(times=times))
        write(root/'status.json',dict(state='completed',steps=step,time_s=m.time,wall_seconds=time.monotonic()-start,experimental_accuracy_validated=False,steady_convergence_verified=False))
        print('COMPLETED',root,flush=True)
    except Exception as e:
        write(root/'status.json',dict(state='failed',step=step,error=repr(e),wall_seconds=time.monotonic()-start));raise
    return root

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--geometry',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--device',default='cuda');p.add_argument('--initial-state',type=Path);p.add_argument('--seconds',type=float,default=300.);p.add_argument('--save-every',type=float,default=2.)
    run(p.parse_args())
