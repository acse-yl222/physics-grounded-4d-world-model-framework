"""Short DIGIT inference on matched physical crops of the new 1m/2m geometry.

Runs the supplied rollout unchanged, including its boundary handling and scaling.
This is an out-of-training-resolution smoke test, not a CFD validation.
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT=repo_root()
CODE=ROOT/'src/urban_flow/physics/environment-integration/members/yiqi_temperature/models/velocity_calculation'
sys.path.insert(0,str(CODE))
from south_kensington_jupyter import SouthKensingtonConfig, load_digit_model, run_digit_rollout, scale_back

OUT=ROOT/'output/core008/physics/digit_smoke'
OUT.mkdir(parents=True,exist_ok=True)
torch.manual_seed(0)
torch.set_num_threads(8)
device=torch.device('cuda')
assert torch.cuda.is_available()
cfg=SouthKensingtonConfig(artifact_dir=str(CODE/'assets'),timesteppings=5,num_iterations=5,inlet_flow=.25)
model=load_digit_model(cfg,device)
checkpoint=ROOT/'project/south_ken/input/models/digit.pth'
common={
    'model':'DIGIT UNet_New, 3D, 10 input channels, 3 output channels',
    'checkpoint':str(checkpoint),'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
    'torch':torch.__version__,'gpu':torch.cuda.get_device_name(),'seed':0,
    'scope':'Matched 256m x 256m local crops from both padded domains, full 128m height; NOT full-domain inference.',
    'crop_domain_lower_xyz_m':[2688,1792,0],'crop_domain_upper_xyz_m':[2944,2048,128],
    'predicted_frames':3,'iterations_per_frame':5,'normalized_initial_u':.25,
    'velocity_conversion':'Source scale_back with [-4,4], so physical-style velocity = normalized output * 4.',
    'physical_time_per_frame_s':None,
    'limits':['No CFD or measured reference: accuracy has not been established.',
              'Checkpoint contains learned grid-scale behaviour; 1m/2m transfer has not been validated.',
              'Original code applies local crop boundary conditions, not surrounding-city coupling.',
              'Original code forces the bottom voxel layer solid; supplied solid.npy remains unchanged.',
              'Default source velocity conversion is used; calibration to actual measured wind is unverified.']}
(OUT/'run_config.json').write_text(json.dumps(common,indent=2)+'\n')
metrics=[]
for spacing in (2,1):
    print(f'Start {spacing}m DIGIT inference',flush=True)
    source=ROOT/f'output/core008/geometry/south_kensington_core008_voxel_{spacing}m_domain4096'
    full=np.load(source/'solid.npy',mmap_mode='r')
    solid=np.array(full[:,1792//spacing:2048//spacing,2688//spacing:2944//spacing])
    del full
    fluid=~solid
    fluid[0]=False
    distribution=torch.from_numpy(fluid.astype(np.float32))[None,None]
    cfg.model_resolution_m=spacing;cfg.height_scale_m=spacing
    torch.cuda.reset_peak_memory_stats()
    before=time.time()
    prediction=run_digit_rollout(model,distribution,cfg,device)
    torch.cuda.synchronize()
    elapsed=time.time()-before
    velocity=scale_back(prediction,-4,4).numpy()
    assert np.isfinite(velocity).all()
    assert not np.any(velocity[:,:,~fluid])
    folder=OUT/f'{spacing}m';folder.mkdir(exist_ok=True)
    np.save(folder/'velocity_tczyx.npy',velocity)
    np.save(folder/'solid_zyx.npy',solid)
    np.save(folder/'solver_fluid_zyx.npy',fluid)
    speed=np.linalg.norm(velocity,axis=1)
    # Interior fluid excludes buildings and the one-cell numerical boundary.
    interior=fluid.copy()
    for axis in range(3):
        interior &= np.roll(fluid,1,axis)&np.roll(fluid,-1,axis)
    interior[[0,-1]]=False;interior[:,[0,-1]]=False;interior[:,:,[0,-1]]=False
    records=[]
    for t,v in enumerate(velocity):
        divergence=np.gradient(v[0],spacing,axis=2)+np.gradient(v[1],spacing,axis=1)+np.gradient(v[2],spacing,axis=0)
        records.append({'frame':t+1,'fluid_speed_mean':float(speed[t][fluid].mean()),
                        'fluid_speed_p95':float(np.percentile(speed[t][fluid],95)),
                        'fluid_speed_max':float(speed[t][fluid].max()),
                        'interior_divergence_rms':float(np.sqrt(np.mean(divergence[interior]**2))),
                        'change_from_previous_rms':None if t==0 else float(np.sqrt(np.mean((velocity[t,:,fluid]-velocity[t-1,:,fluid])**2)))})
    entry={'spacing_m':spacing,'shape_zyx':list(solid.shape),'seconds':elapsed,
           'gpu_peak_allocated_GiB':torch.cuda.max_memory_allocated()/1024**3,
           'all_finite':True,'solid_velocity_zero':True,'frames':records}
    (folder/'metrics.json').write_text(json.dumps(entry,indent=2)+'\n')
    metrics.append(entry)
    print(json.dumps(entry),flush=True)
    del prediction,velocity,distribution,speed
    torch.cuda.empty_cache()
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
print('Both inference runs complete.',flush=True)
