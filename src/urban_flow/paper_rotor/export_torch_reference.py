"""Retain finite-time wind-tunnel diagnostics with replayable restart inputs."""
import argparse,json,shutil
from datetime import datetime,timezone
from pathlib import Path
from common.export import digest,write
from common.storage import Storage
from common.contract import validate
from common.runs import promote


def export(root,input_config,audit):
    root=Path(root).resolve();storage=Storage.load()
    cfg=json.loads((root/'configuration.json').read_text());status=json.loads((root/'status.json').read_text());prov=json.loads((root/'provenance.json').read_text())
    if status['state']!='diagnostic_finished':raise ValueError('Unfinished diagnostic')
    if digest(input_config)!=prov['input_sha256']:raise ValueError('Input configuration identity mismatch')
    shutil.copy2(input_config,root/'input_config.json');shutil.copy2(audit,root/'profile_comparison.json');shutil.copy2(__file__,root/'exporter_source.py')
    parent=cfg.get('resume_from')
    if parent:
        parent=Path(parent)
        if digest(parent/'checkpoint.pt')!=prov['parent_checkpoint_sha256']:raise ValueError('Parent checkpoint identity mismatch')
        target=root/'resume_parent';target.mkdir(exist_ok=True)
        for name in ['checkpoint.pt','configuration.json','provenance.json','source_snapshot.tar.gz']:shutil.copy2(parent/name,target/name)
    spatial=json.loads((storage.metadata('actuator_lab')/'project.json').read_text())['spatial'];spatial['bounds_m']={'min':[0,0,0],'max':cfg['domain_xyz_m']}
    for d in (1,3,5):
        raw=json.loads((root/f'data/wake_{d}d.json').read_text())
        write(root/f'protocol_data/wake_{d}d.json',{'positions':raw['positions'],'values':raw['values']})
    layers=[dict(id=f'wake_{d}d',kind='scalar_field',format='json',asset=f'protocol_data/wake_{d}d.json',sampling='static',field=dict(name='velocity_deficit',unit='1'),display=dict(widget='scalar_field',capabilities=['pick','legend'])) for d in (1,3,5)]
    replay=dict(command='PYTHONPATH=src python -m urban_flow.paper_rotor.run_torch_rans input_config.json --device cuda --model '+cfg['model']+' --steps '+str(cfg['steps_requested'])+(' --resume resume_parent' if parent else ''),source='Extract source_snapshot.tar.gz to a separate directory; execute there with artifact paths adjusted to this retained run.',physical_time_s=status['time_s'],scope='Completed finite-time calculation; neither experimental accuracy nor grid independence certified.')
    write(root/'replay.json',replay)
    artifacts=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.name=='manifest.json' or p.is_relative_to(root/'protocol_data'):continue
        aid='source_snapshot' if p==root/'source_snapshot.tar.gz' else 'artifact_'+str(len(artifacts))
        artifacts.append(dict(id=aid,asset=str(p.relative_to(root)),sha256=digest(p),media_type='application/octet-stream'))
    parameters=dict(cfg,physical_time_s=status['time_s'],steady_convergence_verified=False,experimental_accuracy_validated=False,resume_from='resume_parent' if parent else None)
    manifest=dict(schema_version='1.1.0',scene_id='actuator_lab',simulation='torch_rotor_reference',run_id=root.name,status='complete',created_at=datetime.now(timezone.utc).isoformat(),spatial=spatial,time=dict(unit='s',samples=[]),layers=layers,artifacts=artifacts,provenance=dict(code_revision=prov['code_revision'],dirty=True,parameters=parameters,inputs=[dict(id='input_configuration',sha256=digest(input_config))]))
    write(root/'manifest.json',manifest);validate(root/'manifest.json');result=promote(storage,root);print(result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('config',type=Path);p.add_argument('audit',type=Path);a=p.parse_args();export(a.run,a.config,a.audit)
