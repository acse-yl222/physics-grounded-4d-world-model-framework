"""Physical-time URANS and terrain-following samples for the prepared windfarm."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import numpy as np
from common.export import digest, write
from common.provenance import snapshot_sources
from common.storage import Storage
from .openfoam_reference import IMAGE, header, vector


def configure(target, end_s=2.0):
    target=Path(target).resolve()
    state=json.loads((target/'status.json').read_text())
    if state['state']!='mesh_checked':
        raise ValueError('Only a checked, unstarted scene mesh can be configured')
    if not np.isfinite(end_s) or end_s<=0:
        raise ValueError('Positive physical duration required')
    config=json.loads((target/'configuration.json').read_text())
    source=(target/'constant/fvOptions').read_text()
    bodies=re.findall(r'codeAddSup\s*#\{(.*?)#\};',source,re.S)
    if len(bodies)!=23:raise ValueError('All 23 force sources are required')
    # Compile once; each rotor retains its own local integration and MPI reduction.
    bodies=[re.sub(r'const scalar thrustOverRho = ([^;]+);',
                   r'const scalar thrustOverRho = min(scalar(1), mesh().time().value()/5.0)*(\1);',b) for b in bodies]
    (target/'constant/fvOptions').write_text(header('fvOptions')+'''
windFarmRotors {
 type vectorCodedSource; active yes; selectionMode all; fields (U); name windFarmWeightedRotors;
 codeInclude #{
 #include "fvCFD.H"
 #};
 codeAddSup #{
'''+ '\n'.join('{'+b+'}' for b in bodies)+'''
 #};
 codeCorrect #{ #}; codeConstrain #{ #};
}
''')
    schemes=target/'system/fvSchemes'
    schemes.write_text(schemes.read_text().replace('default steadyState;','default Euler;'))
    (target/'system/fvSolution').write_text(header('fvSolution')+'''
solvers {
 p { solver GAMG; tolerance 1e-8; relTol 0.05; smoother GaussSeidel; }
 pFinal { $p; relTol 0; }
 "(U|k|omega|epsilon)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.05; }
 "(U|k|omega|epsilon)Final" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0; }
}
PIMPLE { momentumPredictor yes; nOuterCorrectors 2; nCorrectors 2; nNonOrthogonalCorrectors 0; }
relaxationFactors { equations { ".*" 1; } }
''')
    geometry=json.loads((target/'metadata.json').read_text())
    ground=np.load(target/'ground.npy')
    h=geometry['cell_m']; origin=np.asarray(geometry['origin_xyz_m']); height=80.
    # Coordinates are local to the OpenFOAM mesh. Preserve source coverage separately.
    points=target/'system/terrainSamplePoints'
    with points.open('w') as stream:
        for j in range(ground.shape[0]):
            for i in range(ground.shape[1]):
                stream.write(vector([(i+.5)*h,(j+.5)*h,float(ground[j,i])+height-origin[2]])+'\n')
    (target/'system/controlDict').write_text(header('controlDict')+f'''
application pimpleFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {end_s};
deltaT 0.1; adjustTimeStep yes; maxCo 0.5; maxDeltaT 0.2;
writeControl adjustableRunTime; writeInterval 2; purgeWrite 2;
writeFormat binary; writePrecision 12; writeCompression off;
timeFormat general; timePrecision 10; runTimeModifiable false;
functions {{
 terrainSlice {{ type sets; libs ("libsampling.so");
   writeControl runTime; writeInterval 2;
   interpolationScheme cellPoint; setFormat raw; fields (U);
   sets (slice {{ type cloud; axis xyz; points (
       #include "terrainSamplePoints"
   ); }});
 }}
}}
''')
    config.update(solver='pimpleFoam',time_semantics='physical seconds',target_seconds=end_s,
                  startup_ramp_s=5.,save_interval_s=2.,slice_agl_m=height,
                  reproduction_status='scene_URANS_under_validation',
                  checkpoint_retention='latest two full fields; all sampled output retained')
    write(target/'configuration.json',config)
    revision=snapshot_sources(Storage.load().root,target/'transient_source_snapshot.tar.gz')
    write(target/'transient_provenance.json',dict(code_revision=revision,dirty=True,
                                      source_snapshot_sha256=digest(target/'transient_source_snapshot.tar.gz')))
    write(target/'status.json',dict(state='transient_prepared',solver_executed=False))


def execute(target):
    target=Path(target).resolve()
    state=json.loads((target/'status.json').read_text())['state']
    if state not in ('transient_prepared','transient_resume_prepared'):
        raise ValueError('Scene must be prepared and not already running')
    processes=json.loads((target/'configuration.json').read_text())['processes']
    if not isinstance(processes,int) or not 1<=processes<=16:raise ValueError('Invalid process count')
    start_command=('decomposePar > log.decomposePar 2>&1 && ' if state=='transient_prepared' else '')
    redirect='>' if state=='transient_prepared' else '>>'
    command=['docker','run','--rm','--name','farm-flow-'+target.name,
             '--user',f'{os.getuid()}:{os.getgid()}','--cpus',str(processes),'--memory','28g','--network','none',
             '-e','HOME=/tmp/foam-home','-e','OMP_NUM_THREADS=1','-v',f'{target}:/case','-w','/case',
             '--entrypoint','/bin/bash',IMAGE,'-lc',
             'mkdir -p /tmp/foam-home; source /usr/lib/openfoam/openfoam2312/etc/bashrc; '
             +start_command+f'mpirun --oversubscribe -np {processes} pimpleFoam -parallel {redirect} log.pimpleFoam 2>&1']
    write(target/'status.json',dict(state='transient_running',command=command))
    result=subprocess.run(command,check=False)
    write(target/'status.json',dict(state='transient_finished' if result.returncode==0 else 'transient_failed',
                                   returncode=result.returncode,validated=False))
    if result.returncode:raise RuntimeError(f'Physical-time solver failed: {target}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',type=Path)
    parser.add_argument('--seconds',type=float,default=2.)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args();configure(args.case,args.seconds)
    if not args.prepare_only:execute(args.case)
