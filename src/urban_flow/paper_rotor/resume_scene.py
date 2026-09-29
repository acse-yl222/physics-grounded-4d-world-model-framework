"""Extend a successfully audited physical run from its actual parallel checkpoint."""
import argparse
import json
from pathlib import Path
import re
import shutil
import math
from common.export import write,digest
from .scene_diagnostics import analyze
from .scene_transient import execute


def prepare_resume(case,end_s):
    case=Path(case).resolve()
    report=analyze(case)
    if not report['numerical_smoke_checks_passed']:
        raise ValueError('Numerical checks failed; do not extend this run')
    config=json.loads((case/'configuration.json').read_text())
    previous=config['target_seconds']
    if not math.isfinite(end_s) or end_s<=previous:
        raise ValueError('Extension must advance physical end time')
    for rank in range(config['processes']):
        root=case/f'processor{rank}'
        times=[]
        for directory in root.iterdir():
            try:time=float(directory.name)
            except ValueError:continue
            if directory.is_dir():times.append((time,directory))
        if not times or not math.isclose(max(times)[0],previous,abs_tol=1e-7):
            raise ValueError(f'Rank {rank} lacks the requested final checkpoint')
        checkpoint=max(times)[1]
        for field in ('U','p','k','omega','nut','phi'):
            if not (checkpoint/field).is_file() or (checkpoint/field).stat().st_size==0:
                raise ValueError(f'Incomplete checkpoint: {checkpoint/field}')
    phase=case/f'completed_through_{previous:g}s'
    phase.mkdir(exist_ok=False)
    for name in ('configuration.json','physical_rotor_history.json','log.pimpleFoam','system/controlDict'):
        shutil.copy2(case/name,phase/Path(name).name)
    if (case/'movie').exists():
        shutil.move(str(case/'movie'),str(phase/'movie'))
    shutil.copy2(__file__,phase/'resume_scene.py')
    write(phase/'resume_provenance.json',{'restart_from_s':previous,'new_end_s':end_s,
          'resume_source_sha256':digest(Path(__file__))})
    control=case/'system/controlDict'
    text=control.read_text().replace('startFrom startTime;','startFrom latestTime;')
    text=re.sub(r'endTime\s+[^;]+;',f'endTime {end_s};',text,count=1)
    # Include the end time in the adjustable write schedule. Otherwise OpenFOAM
    # can stop half a timestep early and leave no checkpoint at the requested end.
    span=end_s-previous
    interval=span/math.ceil(span/20.)
    text=re.sub(r'(writeControl\s+adjustableRunTime;\s*writeInterval\s+)[^;]+;',
                lambda match:match[1]+f'{interval:.17g};',text,count=1)
    control.write_text(text)
    config['target_seconds']=end_s
    config.setdefault('continuation_segments',[]).append({'from_s':previous,'to_s':end_s,'record':phase.name})
    write(case/'configuration.json',config)
    write(case/'status.json',{'state':'transient_resume_prepared','restart_from_s':previous})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',type=Path);parser.add_argument('--seconds',type=float,required=True)
    args=parser.parse_args();prepare_resume(args.case,args.seconds);execute(args.case)
