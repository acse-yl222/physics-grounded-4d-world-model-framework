"""Export actual OpenFOAM terrain samples for the existing movie adapter.

This adapter does not certify the experiment or turn a short smoke run into a
production result. Missing sampled/terrain-covered points remain NaN.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from common.export import digest,write
from .scene_diagnostics import analyze


def sample_grid(samples, ground, h, height, origin_z=0.):
    samples=np.asarray(samples)
    if samples.ndim!=2 or samples.shape[1]!=6 or not np.isfinite(samples[:,:3]).all():
        raise ValueError('Expected cloud columns x,y,z,Ux,Uy,Uz')
    ny,nx=ground.shape
    fractional=samples[:,:2]/h-.5
    indices=np.rint(fractional).astype(int);i,j=indices.T
    if (np.any(i<0) or np.any(i>=nx) or np.any(j<0) or np.any(j>=ny)
        or not np.allclose(fractional,indices,rtol=0,atol=1e-5)):
        raise ValueError('Samples do not match recorded horizontal cell centres')
    if not np.allclose(samples[:,2],ground[j,i]+height-origin_z,rtol=0,atol=.01):
        raise ValueError('Samples do not match recorded terrain-following height')
    if len(set((j*nx+i).tolist()))!=len(i):raise ValueError('Duplicate sample positions')
    values=samples[:,3:]
    # OpenFOAM invalid/outside-domain sentinels must not become physical velocities.
    finite=np.isfinite(values).all(axis=1)&(np.abs(values)<1e20).all(axis=1)
    if np.any(np.abs(values[finite])>500):raise ValueError('Implausible wind velocity; inspect solver')
    out=np.full((ny,nx),np.nan,dtype=np.float32)
    out[j[finite],i[finite]]=values[finite,0]
    return out


def export(case):
    case=Path(case).resolve()
    history=analyze(case)
    if not history['numerical_smoke_checks_passed']:
        raise ValueError('Numerical checks failed; do not export this run as a movie')
    config=json.loads((case/'configuration.json').read_text())
    geometry=json.loads((case/'metadata.json').read_text())
    ground=np.load(case/'ground.npy');valid=np.load(case/'terrain_valid.npy')
    samples_root=case/'postProcessing/terrainSlice'
    directories=sorted((p for p in samples_root.iterdir() if p.is_dir()),key=lambda p:float(p.name))
    times=[];frames=[];rotor_speeds=[];inputs={}
    recorded_times=np.asarray(history['times'])
    for directory in directories:
        files=list(directory.glob('slice_U.*'))
        if len(files)!=1:raise ValueError(f'Expected exactly one sampled cloud: {directory}')
        t=float(directory.name)
        matches=np.flatnonzero(np.isclose(recorded_times,t,rtol=0,atol=1e-7))
        if len(matches)!=1:raise ValueError('No unique actual rotor diagnostic for sampled time')
        field=sample_grid(np.loadtxt(files[0]),ground,geometry['cell_m'],config['slice_agl_m'],geometry['origin_xyz_m'][2])
        field[~valid]=np.nan
        if not np.isfinite(field).any():raise ValueError('No valid wind samples')
        frames.append(field);times.append(t);rotor_speeds.append(history['disk_velocity_m_s'][int(matches[0])])
        inputs[str(files[0].relative_to(case))]=digest(files[0])
    if not times or not np.isclose(times[-1],config['target_seconds'],rtol=0,atol=1e-7):
        raise ValueError('Final requested sample is missing')
    out=case/'movie';out.mkdir(exist_ok=False)
    chunks=[]
    for index,offset in enumerate(range(0,len(frames),25)):
        name=f'u-{index}.bin';np.asarray(frames[offset:offset+25],dtype='<f2').tofile(out/name);chunks.append(name)
    ground.astype('<f4').tofile(out/'ground.bin')
    np.save(out/'terrain_valid.npy',valid)
    np.save(out/'sample_valid.npy',np.isfinite(np.asarray(frames)))
    geometry.update(times=times,display_shape=list(ground.shape),display_cell_m=geometry['cell_m'],
        display_first_center_offset_m=geometry['cell_m']/2,slice_agl_m=config['slice_agl_m'],
        solver='OpenFOAM pimpleFoam URANS kOmegaSST',simulation_cell_m=geometry['cell_m'],
        inlet_m_s=config['inlet_m_s'],wind_chunks=chunks,comparison_keys=[],default_model='mac_live',
        model_labels={'mac_live':'OPENFOAM URANS / TIME EVOLUTION'},
        model_details={'mac_live':f"{geometry['cell_m']:g} m uniform grid · 10 m/s inlet · Terrain included"},
        display_note='Numerical scenario under validation · Rotor motion is display-only · Missing terrain coverage masked',
        experimental_accuracy_validated=False)
    write(out/'metadata.json',geometry);write(out/'rotor-speeds.json',rotor_speeds)
    write(out/'export_provenance.json',{'source_case':case.name,'sample_hashes':inputs,
          'configuration_sha256':digest(case/'configuration.json'),'exporter_sha256':digest(Path(__file__)),
          'physical_time_samples':times,'publish_ready':False})
    print(out)
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('case',type=Path)
    export(parser.parse_args().case)
