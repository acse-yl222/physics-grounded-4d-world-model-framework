"""Sample stored SCALED wind at terrain-relative heights for the voxel viewer.
Run from the workstation UrbanWorldModel root. No new inference is performed.
"""
import json
from pathlib import Path
import numpy as np

root = Path.cwd()
geom = root / 'output/region/geometry/voxel_8m'
run = root / 'output/region/physics/scaled_latent'
out = root / 'visualizer/scenes/region/neural_wind'
out.mkdir(parents=True, exist_ok=True)
meta = json.loads((geom/'metadata.json').read_text())
ground = np.load(geom/'ground_mesh_m_yx.npy')
study = np.load(geom/'study_area_8m_yx.npy')
solid = np.load(run/'temperature/solid_32m_zyx.npy')
ox, oy, _ = meta['source_region_origin_xyz_m']
nz, ny, nx = solid.shape
y, x = np.meshgrid(np.arange(0,ny,2), np.arange(0,nx,2), indexing='ij')
x, y = x.ravel(), y.ravel()
gx, gy = x*4+2, y*4+2
height = ground[gy,gx]
levels = []
for agl in [40,80,120]:
    z = np.floor((height+agl)/32).astype(int)
    valid = study[gy,gx] & (z>=0) & (z<nz)
    valid &= ~solid[np.clip(z,0,nz-1),y,x]
    xx, yy, zz = x[valid],y[valid],z[valid]
    pos = np.column_stack((ox+(xx+.5)*32,(zz+.5)*32,-oy-(yy+.5)*32)).astype('<f4')
    vectors = np.empty((100,len(xx),3),dtype='<f4')
    for k in range(1,101):
        with np.load(run/f'wind/wind32m_{k:03d}.npz') as f:
            uvw=f['uvw'][:,zz,yy,xx].T
        vectors[k-1]=uvw[:,[0,2,1]]
        vectors[k-1,:,2]*=-1
    assert np.isfinite(vectors).all()
    pos.tofile(out/f'positions_{agl}.f32')
    vectors.tofile(out/f'vectors_{agl}.f32')
    speeds=np.linalg.norm(vectors,axis=-1)
    levels.append({'agl_m':agl,'count':len(xx),'positions':f'positions_{agl}.f32','vectors':f'vectors_{agl}.f32',
                   'actual_agl_range_m':[float(((zz+.5)*32-height[valid]).min()),float(((zz+.5)*32-height[valid]).max())],
                   'mean_speed_by_step':speeds.mean(axis=1).tolist(),'max_speed_by_step':speeds.max(axis=1).tolist()})
report={'source':'Existing 100-step SCALED neural surrogate run; no new inference.',
        'frames':100,'cell_m':32,'horizontal_sample_spacing_m':64,'step_seconds_uncalibrated':50,
        'axes':'Viewer X=local x, Y=up, Z=-local y; stored coarse u already converted by coarse_wind.',
        'levels':levels,'limits':['8 m geometry; 32 m block-mean wind sampled every 64 m for display.',
                                'Nearest vertical cell at requested terrain-relative height; solid cells omitted.',
                                'Static obstacles, uncalibrated atmospheric conditions; no validated turbine wake or power prediction.']}
(out/'manifest.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'frames':100,'counts':[(l['agl_m'],l['count']) for l in levels]}))
