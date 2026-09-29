"""Construct the 23-rotor OpenFOAM scene on a uniform voxel subset mesh.

Coordinates in OpenFOAM are source world coordinates minus the recorded origin.
This stage builds and checks the real scene mesh; it does not fabricate animation.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import numpy as np
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runtime import trial_root
from common.storage import Storage
from .openfoam_reference import IMAGE, build_case, header, rotor_source


def prepare(geometry_root, iterations=1000, processes=4):
    geometry_root=Path(geometry_root)
    geometry=json.loads((geometry_root/'metadata.json').read_text())
    config=json.loads((geometry_root/'configuration.json').read_text())
    origin=np.asarray(geometry['origin_xyz_m'])
    turbines=geometry['turbines']
    if len(turbines)!=23 or len({t['id'] for t in turbines})!=23:
        raise ValueError('Expected all 23 source turbines')
    first=turbines[0]
    config.update(domain_xyz_m=geometry['size_xyz_m'],
                  hub_xyz_m=(np.asarray(first['hub_xyz_m'])-origin).tolist(),
                  rotor_diameter_m=first['diameter_m'],inner_diameter_m=0.,
                  rotor_thickness_m=2*config['sigma_m']*config['cutoff_sigma'],
                  world_origin_xyz_m=origin.tolist(),
                  coordinates='OpenFOAM local = source world - world_origin_xyz_m')
    target=trial_root('windfarm','openfoam_reference')
    build_case(target,config,config['turbulence_model'],iterations,processes)
    sources=[]
    for i,turbine in enumerate(turbines):
        rotor=config|dict(hub_xyz_m=(np.asarray(turbine['hub_xyz_m'])-origin).tolist(),
                          rotor_diameter_m=turbine['diameter_m'],axis=turbine['normal_xyz'])
        source=rotor_source(rotor).split('paperRotor',1)[1]
        source=f'rotor{i}'+source.replace('name paperWeightedRotor;',f'name weightedRotor{i};')
        source=source.replace('PAPER_ROTOR ',f'FARM_ROTOR {i} ')
        sources.append(source)
    (target/'constant/fvOptions').write_text(header('fvOptions')+'\n'.join(sources))
    # Single-rotor reference profiles are not scene samples.
    control=target/'system/controlDict'
    control.write_text(control.read_text().split('functions {',1)[0]+'functions {}\n')
    solid=np.load(geometry_root/'solid.npy',mmap_mode='r')
    if list(solid.shape)!=geometry['shape_zyx']:
        raise ValueError('Voxel shape mismatch')
    labels=np.flatnonzero(~solid.reshape(-1))
    # blockMesh single hex labels are x-fastest, matching C-order [z,y,x].
    # A small real OpenFOAM test verifies this convention separately.
    with (target/'fluidCells.input').open('w') as stream:
        stream.write(header('fluidCells','cellSet')+f'{len(labels)}\n(\n')
        np.savetxt(stream,labels,fmt='%d')
        stream.write(')\n')
    for name in ('metadata.json','rotor_support_audit.json','terrain_valid.npy','ground.npy','regularized_fluid_cells.npy'):
        shutil.copy2(geometry_root/name,target/name)
    write(target/'mesh_mapping.json',dict(shape_zyx=list(solid.shape),cell_m=config['cell_m'],
          world_origin_xyz_m=origin.tolist(),expected_fluid_cells=int(len(labels)),
          label_order='x-fastest C-order [z,y,x] before subsetMesh',
          input_hashes={name:digest(geometry_root/name) for name in
                        ('metadata.json','configuration.json','solid.npy','ground.npy','terrain_valid.npy')}))
    revision=snapshot_sources(Storage.load().root,target/'source_snapshot.tar.gz')
    write(target/'provenance.json',dict(code_revision=revision,dirty=True,
                                      source_snapshot_sha256=digest(target/'source_snapshot.tar.gz')))
    return target


def mesh(target):
    target=Path(target).resolve()
    command=['docker','run','--rm','--name','farm-mesh-'+target.name,
             '--user',f'{os.getuid()}:{os.getgid()}','--cpus','4','--memory','24g',
             '--network','none','-e','HOME=/tmp/foam-home','-v',f'{target}:/case','-w','/case',
             '--entrypoint','/bin/bash',IMAGE,'-lc',
             'mkdir -p /tmp/foam-home; source /usr/lib/openfoam/openfoam2312/etc/bashrc; '
             'blockMesh > log.blockMesh 2>&1 && mkdir -p constant/polyMesh/sets && '
             'cp fluidCells.input constant/polyMesh/sets/fluidCells && '
             'subsetMesh -overwrite -patch bottom fluidCells > log.subsetMesh 2>&1 && '
             'checkMesh -allTopology -allGeometry > log.checkMesh 2>&1']
    write(target/'status.json',dict(state='meshing',command=command,solver_executed=False))
    result=subprocess.run(command,check=False)
    good=result.returncode==0 and 'Mesh OK.' in (target/'log.checkMesh').read_text()
    write(target/'status.json',dict(state='mesh_checked' if good else 'mesh_failed',
                                   returncode=result.returncode,solver_executed=False))
    if not good: raise RuntimeError(f'Mesh construction failed: {target}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geometry',type=Path)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    root=prepare(args.geometry);print(root,flush=True)
    if not args.prepare_only:mesh(root)
