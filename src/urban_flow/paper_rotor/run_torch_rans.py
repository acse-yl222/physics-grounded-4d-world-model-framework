"""Run a recorded PyTorch RANS rotor tunnel diagnostic, without validation claims."""
import argparse
import json
import math
from pathlib import Path
import time
import torch
from common.storage import Storage
from common.runtime import trial_root
from common.provenance import snapshot_sources
from common.export import digest,write
from .torch_rans import RotorTunnel
from .torch_profiles import export_profiles


def save_checkpoint(solver,out,model):
    temporary=out/'checkpoint.pt.tmp'
    torch.save({'faces':[x.cpu() for x in solver.faces],'k':solver.k.cpu(),
                'epsilon':solver.epsilon.cpu(),'omega':solver.omega.cpu(),
                'model':model,'time_s':solver.time},temporary)
    temporary.replace(out/'checkpoint.pt')


def restore_checkpoint(solver,path):
    state=torch.load(path,map_location=solver.k.device,weights_only=True)
    if state.get('model','kEpsilon')!=solver.model:
        raise ValueError('Checkpoint model mismatch')
    faces=state.get('faces',[])
    if len(faces)!=3:raise ValueError('Checkpoint requires three face velocity fields')
    fields=[*faces,state['k'],state['epsilon']]
    targets=[*solver.faces,solver.k,solver.epsilon]
    if solver.model!='kEpsilon':
        fields.append(state['omega']);targets.append(solver.omega)
    if any(a.shape!=b.shape or a.dtype!=b.dtype or not torch.isfinite(a).all()
           for a,b in zip(fields,targets)):
        raise ValueError('Invalid checkpoint shape, dtype or nonfinite state')
    if any((q<=0).any() for q in fields[3:]):
        raise ValueError('Checkpoint turbulence fields must be positive')
    timestamp=float(state['time_s'])
    if not math.isfinite(timestamp) or timestamp<0:raise ValueError('Invalid checkpoint time')
    solver.faces=faces;solver.k=state['k'];solver.epsilon=state['epsilon']
    if solver.model!='kEpsilon':solver.omega=state['omega']
    solver.time=timestamp


def run(config_path,device='cpu',steps=10,model='kEpsilon',resume=None):
    if steps<1:raise ValueError('Positive step count required')
    torch.set_num_threads(4)
    config=json.loads(Path(config_path).read_text())
    parent=None
    if resume is not None:
        resume=Path(resume).resolve()
        parent=json.loads((resume/'configuration.json').read_text())
        if parent['model']!=model or any(parent.get(key)!=value for key,value in config.items()):
            raise ValueError('Resume configuration or turbulence model mismatch')
    out=trial_root('actuator_lab','torch_rans_diagnostic');out.mkdir(parents=True,exist_ok=False)
    write(out/'configuration.json',config|{'model':model,'device':device,'dtype':'float64',
          'steps_requested':steps,'numerical_method':'Transient explicit first-order transport; FFT pressure projection',
          'experimental_accuracy_validated':False,'resume_from':str(resume) if resume else None})
    revision=snapshot_sources(Storage.load().root,out/'source_snapshot.tar.gz')
    write(out/'provenance.json',{'code_revision':revision,'dirty':True,
          'source_snapshot_sha256':digest(out/'source_snapshot.tar.gz'),'input_sha256':digest(config_path),
          'parent_checkpoint_sha256':digest(resume/'checkpoint.pt') if resume else None})
    print(out,flush=True)
    write(out/'status.json',{'state':'initializing'})
    start=time.perf_counter()
    try:
        solver=RotorTunnel(config,device=device,model=model)
        if resume is not None:
            restore_checkpoint(solver,resume/'checkpoint.pt')
        history=[]
        for index in range(steps):
            load=solver.rotor_load()
            maximum=float(load['acceleration'].abs().max())
            dt=min(solver.stable_dt(),(.3*min(solver.h)/max(maximum,1e-20))**.5)
            result=solver.advance_rotor(dt)
            result.update(step=index+1,wall_seconds=time.perf_counter()-start)
            history.append(result)
            write(out/'status.json',{'state':'running',**result})
            if index%10==0:print(json.dumps(result),flush=True)
            if (index+1)%100==0:
                save_checkpoint(solver,out,model)
                write(out/'history.json',history)
                export_profiles(solver,out/'diagnostics'/f'step_{index+1:07d}')
        save_checkpoint(solver,out,model)
        write(out/'history.json',history)
        export_profiles(solver,out)
        write(out/'status.json',{'state':'diagnostic_finished','steps':steps,'time_s':solver.time,
              'wall_seconds':time.perf_counter()-start,'steady_convergence_verified':False,
              'experimental_accuracy_validated':False})
    except Exception as error:
        write(out/'status.json',{'state':'failed','error':str(error)})
        raise
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config',type=Path)
    parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    parser.add_argument('--steps',type=int,default=10)
    parser.add_argument('--model',choices=['kEpsilon','kOmegaSST','kOmegaSSTLF18'],default='kEpsilon')
    parser.add_argument('--resume',type=Path,help='Previous diagnostic directory; configuration must match')
    args=parser.parse_args()
    run(args.config,args.device,args.steps,args.model,args.resume)
