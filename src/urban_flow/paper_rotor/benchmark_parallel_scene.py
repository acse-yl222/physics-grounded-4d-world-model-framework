"""Branch an immutable 2 s checkpoint to benchmark higher parallelism without restarting a live run."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from common.export import write,digest
from common.provenance import snapshot_sources
from common.runtime import trial_root
from common.storage import Storage
from .openfoam_reference import IMAGE,header


def run(source,processes=16,end_s=6.):
    source=Path(source).resolve()
    saved=source/'completed_through_2s'
    config=json.loads((saved/'configuration.json').read_text())
    if config['target_seconds']!=2 or end_s<=2 or processes not in (8,16):
        raise ValueError('Expected saved 2 s branch and 8 or 16 processes')
    target=trial_root('windfarm','parallel_scene_benchmark');target.mkdir(parents=True,exist_ok=False)
    for name in ('0','constant','system','dynamicCode'):
        if (source/name).exists():shutil.copytree(source/name,target/name)
    inputs={}
    for rank in range(config['processes']):
        for name in ('constant','2'):
            src=source/f'processor{rank}'/name
            if not src.is_dir():raise ValueError(f'Missing source checkpoint {src}')
            shutil.copytree(src,target/f'processor{rank}'/name)
        for field in ('U','p','k','omega','nut','phi'):
            src=target/f'processor{rank}'/'2'/field
            if not src.is_file():raise ValueError(f'Incomplete checkpoint: {src}')
            inputs[str(src.relative_to(target))]=digest(src)
    for name in ('metadata.json','ground.npy','terrain_valid.npy','regularized_fluid_cells.npy',
                 'rotor_support_audit.json','mesh_mapping.json','fluidCells.input','transient_source_snapshot.tar.gz',
                 'transient_provenance.json','log.checkMesh'):
        shutil.copy2(source/name,target/name)
    shutil.copy2(saved/'log.pimpleFoam',target/'log.pimpleFoam')
    shutil.copytree(source/'postProcessing/terrainSlice/2',target/'postProcessing/terrainSlice/2')
    (target/'system/decomposeParDict').write_text(header('decomposeParDict')+f'numberOfSubdomains {processes};\nmethod scotch;\n')
    control=target/'system/controlDict';text=control.read_text()
    text=re.sub(r'endTime\s+[^;]+;',f'endTime {end_s};',text,count=1)
    # This bounded benchmark must end on and retain a restart checkpoint.
    text=text.replace('writeControl adjustableRunTime; writeInterval 20;',
                      'writeControl adjustableRunTime; writeInterval 2;')
    control.write_text(text)
    config.update(processes=processes,target_seconds=end_s,
                  benchmark_parent={'case':source.name,'checkpoint_s':2,'field_hashes':inputs},
                  benchmark_only=True)
    write(target/'configuration.json',config)
    revision=snapshot_sources(Storage.load().root,target/'benchmark_source_snapshot.tar.gz')
    write(target/'benchmark_provenance.json',{'code_revision':revision,'dirty':True,
          'source_snapshot_sha256':digest(target/'benchmark_source_snapshot.tar.gz')})
    print(target,flush=True)
    command=['docker','run','--rm','--name','farm-benchmark-'+target.name,
             '--user',f'{os.getuid()}:{os.getgid()}','--cpus',str(processes),'--memory','28g','--network','none',
             '-e','HOME=/tmp/foam-home','-e','OMP_NUM_THREADS=1','-v',f'{target}:/case','-w','/case',
             '--entrypoint','/bin/bash',IMAGE,'-lc',
             'mkdir -p /tmp/foam-home; source /usr/lib/openfoam/openfoam2312/etc/bashrc; '
             f'mpirun --oversubscribe -np {processes} redistributePar -parallel -overwrite -latestTime > log.redistributePar 2>&1 && '
             f'mpirun --oversubscribe -np {processes} pimpleFoam -parallel >> log.pimpleFoam 2>&1']
    started=time.monotonic();write(target/'status.json',{'state':'transient_running','command':command})
    result=subprocess.run(command,check=False)
    write(target/'status.json',{'state':'transient_finished' if result.returncode==0 else 'transient_failed',
          'returncode':result.returncode,'wall_seconds_including_redistribution':time.monotonic()-started,'validated':False})
    if result.returncode:raise RuntimeError(f'Parallel benchmark failed: {target}')
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path)
    parser.add_argument('--processes',type=int,default=16);args=parser.parse_args();run(args.source,args.processes)
