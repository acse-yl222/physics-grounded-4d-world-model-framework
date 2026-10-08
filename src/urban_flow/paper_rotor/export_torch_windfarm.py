"""Validate and retain a completed TorchRotor-RANS run; completion is not accuracy."""
import argparse,json,shutil
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from common.export import write,digest
from common.storage import Storage
from common.contract import validate
from common.runs import promote


def export(root):
    root=Path(root).resolve();s=Storage.load()
    status=json.loads((root/'status.json').read_text());cfg=json.loads((root/'configuration.json').read_text())
    if status['state']!='completed' or abs(status['time_s']-cfg['target_seconds'])>1e-8:raise ValueError('Incomplete run')
    g=json.loads((root/'movie/metadata.json').read_text());hist=json.loads((root/'history.json').read_text());times=g['times']
    if len(times)!=len(hist) or not np.all(np.diff(times)>0):raise ValueError('Inconsistent time records')
    divergence=max(r['pressure']['divergence_rms'] for r in hist)
    force=max(t['force_error_N']/max(t['thrust_N'],1.) for r in hist for t in r['rotors'])
    if divergence>=1e-5 or force>2e-6:raise ValueError(('Numerical screening failed',divergence,force))
    mask=np.load(root/'data/mask.npy');frames=sorted((root/'data').glob('frame-*.npy'))
    if len(frames)!=len(times):raise ValueError('Missing samples')
    allstats=[]
    for p in frames:
        a=np.load(p)
        if not np.isfinite(a[:,:,mask==0]).all():raise ValueError('Nonfinite valid sample')
        allstats.append([float(np.nanmin(a[0,0])),float(np.nanmean(a[0,0])),float(np.nanmax(a[0,0]))])
    audit=dict(model=f"TorchRotor-RANS v{cfg.get('model_version','0.1')}",numerical_screen_passed=True,divergence_rms_max_per_s=divergence,relative_rotor_force_error_max=force,frame_count=len(times),first_time_s=times[0],last_time_s=times[-1],axial_slice_min_mean_max_m_s=allstats,experimental_accuracy_validated=False,steady_convergence_verified=False,limitations=['Finite startup transient, not a steady-state prediction.','8 m voxel-grid independence not verified.','Terrain wall/corner extension is exploratory; wind-tunnel accuracy does not validate this scene.','Float16 movie is a presentation derivative; protocol fields retain float32.'])
    if cfg.get('rotor_model')=='actuator_line':
        names=('relative_force_error','relative_global_moment_error','relative_work_error')
        checks={name:max(row['actuator_line_audit'][name] for row in hist) for name in names}
        if max(checks.values())>1e-5:raise ValueError('Actuator-line conservation check failed')
        kinematics=json.loads((root/'movie/rotor-kinematics.json').read_text())
        phase=np.asarray(kinematics['phase_rad']);omega=np.asarray(kinematics['omega_rad_s'])
        if phase.shape!=(len(times),len(g['turbines'])) or omega.shape!=phase.shape or kinematics['times']!=times:raise ValueError('Kinematic dimensions differ')
        increments=np.diff(times)[:,None]*.5*(omega[1:]+omega[:-1])
        # Recorded phases come from float32 products; differencing amplifies
        # their rounding error. Bound that error in radians, not rad/s.
        phase_error=np.abs(np.diff(phase,axis=0)-increments)
        roundoff=4*np.finfo(np.float32).eps*(np.abs(phase[1:])+np.abs(phase[:-1])+np.abs(increments)+1.)
        if not np.isfinite(phase).all() or not np.isfinite(omega).all() or np.any(phase_error>roundoff):raise ValueError('Recorded phase does not match angular speed')
        checks['phase_increment_roundoff_max_rad']=float(phase_error.max())
        audit.update(rotor_model='actuator_line',actuator_line_conservation_maxima=checks,recorded_phase_verified=True,mechanical_power_only=True)
    write(root/'numerical_audit.json',audit)
    shutil.copy2(s.root/cfg.get('model_card','project/windfarm/torch_rotor_rans_v01.md'),root/'model_card.md')
    shutil.copy2(Path(__file__),root/'exporter_source.py')
    provenance=json.loads((root/'provenance.json').read_text())
    layer=dict(id='velocity',kind='vector_field',format='npy_frames',asset='data/frames.json',sampling='linear',field=dict(name='velocity',unit='m/s'),encoding=dict(coordinate_frame='ENU',dtype='<f4',shape=[len(times),3,*g['display_shape']],axes='TCYX',origin_m=[*g['origin_xyz_m'][:2],cfg['slice_agl_m']],spacing_m=[g['cell_m']]*2,sample_location='cell_center',byte_order='little',compression='none',frame_assets=[str(p.relative_to(root)) for p in frames],height_asset='data/ground.npy',height_dtype='<f4',mask_asset='data/mask.npy',mask_dtype='|u1',mask_semantics='invalid_nonzero'),display=dict(widget='vector_field',capabilities=['pick','legend','opacity']))
    artifacts=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.name=='manifest.json' or p.is_relative_to(root/'data'):continue
        aid='source_snapshot' if p==root/'source_snapshot.tar.gz' else 'artifact_'+str(len(artifacts))
        artifacts.append(dict(id=aid,asset=str(p.relative_to(root)),sha256=digest(p),media_type='application/octet-stream'))
    manifest=dict(schema_version='1.1.0',scene_id='windfarm',simulation='torch_rotor_rans',run_id=root.name,status='complete',created_at=datetime.now(timezone.utc).isoformat(),spatial=json.loads((s.metadata('windfarm')/'project.json').read_text())['spatial'],time=dict(unit='s',samples=times),layers=[layer],artifacts=artifacts,provenance=dict(code_revision=provenance['code_revision'],dirty=True,parameters=cfg,inputs=[dict(id=k.replace('.','_'),sha256=v) for k,v in provenance['geometry_hashes'].items()]))
    write(root/'manifest.json',manifest);validate(root/'manifest.json');destination=promote(s,root)
    write(s.metadata('windfarm')/'views'/f'torch_rotor_rans_{root.name.lower()}.json',dict(schema_version='1.1.0',scene_id='windfarm',title=f"TorchRotor-RANS v{cfg.get('model_version','0.1')} · {cfg['target_seconds']:g} s exploratory transient",time_alignment='relative',runs=[root.name],layers=[dict(run_id=root.name,layer_id='velocity',visible=True)]))
    print(destination);return destination

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);export(p.parse_args().run)
