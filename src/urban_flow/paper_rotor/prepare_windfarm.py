"""Prepare uniform scene geometry and audit discrete rotor support before RANS migration."""
import argparse
import json
from pathlib import Path
import numpy as np
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runtime import source_path, trial_root
from common.storage import Storage



def regularize_fluid(solid):
    """Fill underresolved fluid slits lacking an internal neighbour in any axis.

    OpenFOAM's cell determinant is zero for these cells. Record every changed
    voxel; this is a stated geometry approximation, not measured terrain.
    """
    fluid=~solid.copy()
    removed=np.zeros_like(solid)
    while True:
        bad=np.zeros_like(solid)
        for axis in range(3):
            lo=np.roll(fluid,1,axis); hi=np.roll(fluid,-1,axis)
            edge=[slice(None)]*3; edge[axis]=0; lo[tuple(edge)]=False
            edge[axis]=-1; hi[tuple(edge)]=False
            bad |= fluid & ~(lo|hi)
        if not bad.any():break
        fluid[bad]=False; removed |= bad
    return ~fluid,removed


def prepare(source, configuration):
    source = Path(source)
    config = json.loads(Path(configuration).read_text())
    geometry = json.loads((source/'metadata.json').read_text())
    h = config['cell_m']; old_h = geometry['cell_m']
    factor = round(h/old_h)
    if factor < 1 or not np.isclose(h, factor*old_h):
        raise ValueError('Target uniform grid must be an integer coarsening')
    solid = np.load(source/'solid.npy', mmap_mode='r')
    ground = np.load(source/'ground.npy', mmap_mode='r')
    valid = np.load(source/'terrain_valid.npy', mmap_mode='r')
    if list(solid.shape) != geometry['shape_zyx'] or ground.shape != solid.shape[1:] or valid.shape != ground.shape:
        raise ValueError('Geometry arrays do not match metadata')
    if any(n % factor for n in solid.shape) or not np.isfinite(ground).all():
        raise ValueError('Invalid coarsening or terrain values')
    nz, ny, nx = (n//factor for n in solid.shape)
    origin = np.asarray(geometry['origin_xyz_m'],dtype=float)
    # Conservative union preserves thin towers/nacelles instead of deleting them.
    coarse = np.asarray(solid).reshape(nz,factor,ny,factor,nx,factor).any(axis=(1,3,5))
    coarse,regularized = regularize_fluid(coarse)
    ground_out = ground.reshape(ny,factor,nx,factor).mean(axis=(1,3))
    valid_out = valid.reshape(ny,factor,nx,factor).all(axis=(1,3))
    ids = [t['id'] for t in geometry['turbines']]
    if len(ids) != 23 or len(set(ids)) != 23:
        raise ValueError('Expected 23 uniquely identified scene turbines')
    audits=[]
    half = config['sigma_m']*config['cutoff_sigma']
    for turbine in geometry['turbines']:
        hub=np.asarray(turbine['hub_xyz_m']); radius=turbine['radius_m']
        axis=np.asarray(turbine['normal_xyz'],dtype=float)
        if not np.isfinite(axis).all() or np.linalg.norm(axis)==0:
            raise ValueError('Invalid rotor axis')
        axis/=np.linalg.norm(axis)
        extent=half*np.abs(axis)+radius*np.sqrt(np.maximum(0,1-axis**2))
        lower=np.floor((hub-extent-origin)/h).astype(int)
        upper=np.ceil((hub+extent-origin)/h).astype(int)
        if np.any(lower<0) or np.any(upper>np.array([nx,ny,nz])):
            raise ValueError(f'Clipped rotor support: {turbine["id"]}')
        x0,y0,z0=lower; x1,y1,z1=upper
        z,y,x=np.meshgrid(*[(np.arange(a,b)+.5)*h+o for a,b,o in
                            ((z0,z1,origin[2]),(y0,y1,origin[1]),(x0,x1,origin[0]))],indexing='ij')
        delta=np.stack((x,y,z),axis=-1)-hub
        axial=delta@axis; radial2=np.maximum(0,(delta*delta).sum(axis=-1)-axial**2)
        weight=np.exp(-.5*(axial/config['sigma_m'])**2)*((np.abs(axial)<=half)&(radial2<=radius**2))
        fluid=~coarse[z0:z1,y0:y1,x0:x1]
        total=weight.sum(); available=(weight*fluid).sum()
        if available<=0: raise ValueError('Unresolved rotor')
        audits.append(dict(id=turbine['id'],fluid_support_cells=int(((weight>0)&fluid).sum()),
                           excluded_weight_fraction=float(1-available/total),
                           weighted_fluid_volume_m3=float(available*h**3),
                           diameter_cells=2*radius/h,axial_support_cells=2*half/h))
    target=trial_root('windfarm','paper_rotor_geometry')
    target.mkdir(parents=True,exist_ok=False)
    for name,array in [('solid',coarse),('ground',ground_out),('terrain_valid',valid_out),('regularized_fluid_cells',regularized)]:
        np.save(target/(name+'.npy'),array)
    inputs={name:digest(source/name) for name in ('metadata.json','solid.npy','ground.npy','terrain_valid.npy')}
    config['geometry_input_sha256']=inputs
    config['geometry_regularization']={'filled_fluid_cells':int(regularized.sum()),'reason':'No internal fluid neighbour along at least one axis; iterate to fixed point.','mask':'regularized_fluid_cells.npy'}
    write(target/'configuration.json',config)
    for key in ('estimated_original_solver_peak_gib','rotor_support_solid_fraction','structure_fraction'):
        geometry.pop(key,None)
    geometry.update(cell_m=h,shape_zyx=[nz,ny,nx],cell_count=int(coarse.size),
                    solid_fraction=float(coarse.mean()),terrain_coverage_fraction=float(valid_out.mean()),
                    ground_range_m=[float(ground_out.min()),float(ground_out.max())],coarsened_from_cell_m=old_h,
                    coarsening='solid union plus explicitly recorded fluid-slit filling; mean sampled ground; valid only if all source columns valid')
    write(target/'metadata.json',geometry)
    write(target/'rotor_support_audit.json',{'rotors':audits,'solver_executed':False,
          'normalization':'Use weighted FLUID cell volume; apply equal and opposite total force.'})
    revision=snapshot_sources(Storage.load().root,target/'source_snapshot.tar.gz')
    write(target/'provenance.json',{'code_revision':revision,'source_snapshot_sha256':digest(target/'source_snapshot.tar.gz'),
                                  'input_hashes':inputs,'configuration_sha256':digest(Path(configuration))})
    print(target)
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=source_path('legacy_output','windfarm_neural/geometry_4m'))
    parser.add_argument('--config',type=Path,default=Storage.load().metadata('windfarm')/'configs/paper_rotor_10ms.json')
    args=parser.parse_args();prepare(args.source,args.config)
