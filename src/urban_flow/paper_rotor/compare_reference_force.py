"""Evaluate the Torch rotor on the actual independent OpenFOAM final velocity field."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
import torch
from common.export import digest,write
from .rotor import WeightedRotor


def compare(case):
    case=Path(case)
    config=json.loads((case/'configuration.json').read_text())
    summary=json.loads((case/'reference_summary.json').read_text())
    if not summary['numerical_convergence_verified']:
        raise ValueError('Compare only numerically converged reference fields')
    field=case/str(summary['iterations'])/'U'
    text=field.read_text()
    if not re.search(r'format\s+ascii;',text):raise ValueError('Expected ASCII reference field')
    match=re.search(r'internalField\s+nonuniform List<vector>\s+(\d+)\s*\((.*?)\n\)\s*;',text,re.S)
    if not match:raise ValueError('Missing vector internal field')
    count=int(match[1]);velocity=np.fromstring(match[2].replace('(',' ').replace(')',' '),sep=' ')
    if velocity.size!=3*count or not np.isfinite(velocity).all():raise ValueError('Invalid velocity field')
    nx,ny,nz=config['grid_cells_xyz']
    spacing=config.get('actual_spacing_xyz_m',[config['cell_m']]*3)
    dx,dy,dz=spacing;volume=dx*dy*dz
    if nx*ny*nz!=count:raise ValueError('Reference field is not the declared complete uniform grid')
    z,y,x=np.meshgrid((np.arange(nz)+.5)*dz,(np.arange(ny)+.5)*dy,(np.arange(nx)+.5)*dx,indexing='ij')
    xyz=torch.as_tensor(np.stack((x,y,z),axis=-1).reshape(-1,3))
    module=WeightedRotor(config['rotor_diameter_m']/2,config['sigma_m'],ct=config['ct'],
                         inner_radius=config['inner_diameter_m']/2,cutoff=config['cutoff_sigma'],rho=config['rho_kg_m3'])
    result=module(xyz,torch.as_tensor(velocity.reshape(-1,3)),torch.full((count,),volume,dtype=torch.float64),
                  config['hub_xyz_m'],config.get('axis',[1,0,0]))
    thrust=float(result['thrust']);speed=float(result['disc_speed'])
    integral=-result['acceleration'].sum(0)*volume*config['rho_kg_m3']
    conservation=float(torch.linalg.vector_norm(integral-result['body_force']))
    report=dict(reference_run=case.name,field_sha256=digest(field),torch_disc_speed_m_s=speed,
                cpp_disc_speed_m_s=summary['last_disc_speed_m_s'],torch_thrust_N=thrust,
                cpp_thrust_N=summary['last_thrust_N'],torch_force_balance_error_N=conservation,
                interpretation='Same converged flow field; C++ source logged immediately before final velocity solve.',
                passed=bool(np.isclose(thrust,summary['last_thrust_N'],rtol=1e-5) and conservation<1e-9),
                experimental_accuracy_validated=False)
    if not report['passed']:raise ValueError(report)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('cases',nargs='+',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();torch.set_num_threads(4)
    if args.output.exists():raise FileExistsError(args.output)
    reports=[compare(case) for case in args.cases];write(args.output,reports);print(json.dumps(reports,indent=2))
