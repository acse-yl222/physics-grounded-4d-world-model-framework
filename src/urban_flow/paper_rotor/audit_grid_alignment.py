"""Measure rotor quadrature sensitivity to oblique axes and subcell translations.

An affine imposed velocity has known continuous weighted average at the hub;
this isolates geometry/sampling error from the flow solver and experiment.
"""
import argparse
import json
import math
from pathlib import Path
import torch
from common.export import write,digest
from .rotor import WeightedRotor


def audit():
    torch.set_num_threads(4)
    reports=[]
    for h in (.08,.04,.02):
        coordinates=(torch.arange(round(.8/h),dtype=torch.float64)+.5)*h-.4
        z,y,x=torch.meshgrid(coordinates,coordinates,coordinates,indexing='ij')
        xyz=torch.stack((x,y,z),-1)
        for direction in ([1.,0.,0.],[1.,1.,0.],[1.,1.,1.]):
            axis=torch.tensor(direction,dtype=torch.float64);axis/=torch.linalg.vector_norm(axis)
            for offset in (0.,.25,.49):
                hub=torch.tensor([offset*h]*3,dtype=torch.float64)
                # Continuous, symmetric support integrates the odd affine term to zero.
                relative=xyz-hub
                speed=10+relative@torch.tensor([2.,-1.,.5],dtype=torch.float64)
                velocity=speed[...,None]*axis
                rotor=WeightedRotor(.4647/2,.02,ct=.95,inner_radius=.09/2)
                row=dict(cell_m=h,axis=direction,hub_offset_cells=offset,exact_continuous_disc_speed_m_s=10.)
                try:
                    result=rotor(xyz,velocity,torch.full_like(speed,h**3),hub,axis)
                    actual=float(result['disc_speed'])
                    reaction=-result['acceleration'].sum((0,1,2))*h**3*rotor.rho
                    error=float(torch.linalg.vector_norm(reaction-result['body_force']))
                    if error>1e-10:raise AssertionError('Force normalization failed')
                    row.update(resolved=True,disc_speed_m_s=actual,speed_error_m_s=actual-10,
                               support_cells=int((result['weight']>0).sum()),force_balance_error_N=error)
                except ValueError as exception:
                    row.update(resolved=False,error=str(exception))
                reports.append(row)
    return dict(cases=reports,interpretation='Analytical affine-field quadrature audit, not experimental or flow-solver validation.',
                rotor_source_sha256=digest(Path(__file__).with_name('rotor.py')))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=audit();write(args.output,result)
    for h in (.08,.04,.02):
        rows=[r for r in result['cases'] if r['cell_m']==h]
        print(json.dumps({'cell_m':h,'unresolved_cases':sum(not r['resolved'] for r in rows),
                          'max_abs_disc_speed_error_m_s':max(abs(r['speed_error_m_s']) for r in rows if r['resolved'])}))
