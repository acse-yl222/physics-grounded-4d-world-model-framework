"""Audit a terminated OpenFOAM reference run without calling iterations seconds."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import tarfile

import numpy as np

from common.contract import validate
from common.export import digest, write
from common.storage import Storage


def load_history(log):
    rows = re.findall(r'^PAPER_ROTOR\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$', log, re.MULTILINE)
    if not rows:
        raise ValueError('No independent rotor diagnostics in solver log')
    data = np.asarray(rows, dtype=float)
    if not np.isfinite(data).all() or np.any(np.diff(data[:, 0]) <= 0):
        raise ValueError('Invalid or repeated SIMPLE iteration diagnostics')
    return data


def inspect_log(log, config):
    if not re.search(r'\nEnd\s*(?:Finalising parallel run\s*)?$', log):
        raise ValueError('Solver has not terminated successfully')
    history = load_history(log)
    residuals = {}
    for field, initial in re.findall(r'Solving for (\w+), Initial residual = ([\deE.+-]+)', log):
        residuals[field] = float(initial)
    required = ('p', 'Ux', 'Uy', 'Uz', 'k', 'omega' if config['turbulence_model']=='kOmegaSST' else 'epsilon')
    if any(name not in residuals for name in required) or not all(math.isfinite(x) for x in residuals.values()):
        raise ValueError('Missing or nonfinite solver residuals')
    continuity = re.findall(r'continuity errors : sum local = ([\deE.+-]+), global = ([\deE.+-]+)', log)
    if not continuity:
        raise ValueError('Missing continuity diagnostics')
    local, global_error = map(float, continuity[-1])
    if not math.isfinite(local) or not math.isfinite(global_error):
        raise ValueError('Nonfinite continuity diagnostics')
    window = history[-min(100,len(history)):]
    drift = float(np.ptp(window[:,2])/max(abs(window[:,2].mean()),1e-15))
    rho = config['rho_kg_m3']
    force_error = float(history[:,3].max()*rho)
    converged = all(residuals[name] < 1e-6 for name in required) and len(history)>=100 and drift<1e-3 and local<1e-6
    return dict(iterations=int(history[-1,0]), last_disc_speed_m_s=float(history[-1,1]),
                last_thrust_N=float(history[-1,2]), max_force_balance_error_N=force_error,
                final_initial_residuals=residuals, local_continuity_error=local, global_continuity_error=global_error,
                last_window_iterations=len(window), thrust_range_over_mean=drift,
                numerical_convergence_verified=bool(converged), experimental_accuracy_validated=False,
                time_semantics='steady SIMPLE iteration, not physical seconds'), history


def analyze(target):
    target=Path(target).resolve()
    status=json.loads((target/'status.json').read_text())
    if status['state']!='solver_finished':
        raise ValueError('Only a successful, terminated solver can be analyzed')
    config=json.loads((target/'configuration.json').read_text())
    summary, history=inspect_log((target/'log.simpleFoam').read_text(),config)
    sample_root=target/'postProcessing/profiles'
    samples=sorted((p for p in sample_root.iterdir() if p.is_dir()),key=lambda p:float(p.name))
    if not samples or float(samples[-1].name)!=summary['iterations']:
        raise ValueError('Final sampled profiles do not match the last solver iteration')
    (target/'data').mkdir(exist_ok=True)
    layers=[]
    for distance in (1,3,5):
        array=np.loadtxt(samples[-1]/f'wake{distance}D_k_nut_U.xy')
        if array.ndim!=2 or array.shape[1]!=6 or not np.isfinite(array).all():
            raise ValueError('Invalid reference sample columns: expected y,k,nut,Ux,Uy,Uz')
        hx,hy,hz=config['hub_xyz_m']; diameter=config['rotor_diameter_m']
        positions=[[hx+distance*diameter,float(y),hz] for y in array[:,0]]
        values=(1-array[:,3]/config['inlet_m_s']).tolist()
        name=f'wake_{distance}d'
        write(target/f'data/{name}.json',{'positions':positions,'values':values})
        layers.append(dict(id=name,kind='scalar_field',format='json',asset=f'data/{name}.json',sampling='static',
                           field={'name':'velocity_deficit','unit':'1'},
                           display={'widget':'scalar_field','capabilities':['pick','legend']}))
    write(target/'reference_summary.json',summary)
    shutil.copyfile(__file__, target/'analysis_reference.py')
    np.savetxt(target/'rotor_iterations.csv',history,delimiter=',',
               header='simple_iteration,disc_speed_m_s,thrust_N,force_over_density_balance_error',comments='')
    # Preserve all dictionaries needed to rebuild this case, independently of cache.
    with tarfile.open(target/'case_inputs.tar.gz','w:gz') as archive:
        for folder in ('0','system','constant'):
            for path in sorted((target/folder).rglob('*')):
                if path.is_file() and 'polyMesh' not in path.parts:
                    archive.add(path,arcname=str(path.relative_to(target)))
    storage=Storage.load()
    spatial=json.loads((storage.metadata('actuator_lab')/'project.json').read_text())['spatial']
    spatial['bounds_m']={'min':[0,0,0],'max':config['domain_xyz_m']}
    provenance=json.loads((target/'provenance.json').read_text())
    artifacts=[('source_snapshot','source_snapshot.tar.gz','application/gzip'),
               ('case_inputs','case_inputs.tar.gz','application/gzip'),
               ('configuration','configuration.json','application/json'),
               ('summary','reference_summary.json','application/json'),
               ('rotor_iterations','rotor_iterations.csv','text/csv'),
               ('solver_log','log.simpleFoam','text/plain'),('mesh_check','log.checkMesh','text/plain')]
    artifacts.append(('analysis_source','analysis_reference.py','text/x-python'))
    manifest=dict(schema_version='1.1.0',scene_id='actuator_lab',simulation='openfoam_rotor_reference',
                  run_id=target.name,status='complete',created_at=datetime.now(timezone.utc).isoformat(),spatial=spatial,
                  provenance={'code_revision':provenance['code_revision'],'dirty':True,
                              'parameters':config|{'numerical_convergence_verified':summary['numerical_convergence_verified'],
                                                   'experimental_accuracy_validated':False},
                              'inputs':[{'id':'reference_configuration','sha256':digest(target/'configuration.json')}]},
                  time={'unit':'s','samples':[]},layers=layers,
                  artifacts=[{'id':key,'asset':name,'sha256':digest(target/name),'media_type':mime} for key,name,mime in artifacts])
    write(target/'manifest.json',manifest)
    validate(target/'manifest.json')
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    analyze(args.run)
