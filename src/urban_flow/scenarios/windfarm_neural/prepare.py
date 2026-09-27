from common.runtime import source_path, trial_root
"""Coarsen the 2 m all-turbine voxel geometry to 4 m for the pure-PyTorch solver.
Terrain is re-thresholded from the averaged ground height with the same rule as
windfarm_2m/prepare.py (cell bottom <= ground). Towers and nacelles are kept if any
2 m child is solid, so thin structures do not disappear at 4 m.
"""
import json,argparse
from pathlib import Path
import numpy as np

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--src',type=Path,default=source_path('legacy_output','region_crop_2m/geometry'));ap.add_argument('--out',type=Path,default=trial_root('windfarm','geometry_4m'))
 ap.add_argument('--nz',type=int,default=0,help='4 m layers; 0 keeps the 2 m domain height');ap.add_argument('--clearance',type=float,default=0,help='terrain-following slip ceiling this far above smoothed ground (m)');ap.add_argument('--smooth',type=float,default=500.);a=ap.parse_args()
 g=json.loads((a.src/'metadata.json').read_text());assert g['cell_m']==2
 solid2=np.load(a.src/'solid.npy');ground2=np.load(a.src/'ground.npy');valid2=np.load(a.src/'terrain_valid.npy')
 nz,ny,nx=solid2.shape;assert nz%2==ny%2==nx%2==0
 terrain2=(np.arange(nz,dtype=np.float32)*2)[:,None,None]<=ground2[None]
 struct2=solid2&~terrain2;del terrain2,solid2
 struct4=struct2.reshape(nz//2,2,ny//2,2,nx//2,2).any((1,3,5));del struct2
 ground4=ground2.reshape(ny//2,2,nx//2,2).mean((1,3)).astype(np.float32)
 terrain4=(np.arange(nz//2,dtype=np.float32)*4)[:,None,None]<=ground4[None]
 solid4=terrain4|struct4;assert not solid4[-1].any()
 if a.nz:
  assert a.nz>=solid4.shape[0];solid4=np.concatenate((solid4,np.zeros((a.nz-solid4.shape[0],)+solid4.shape[1:],bool)))
 ceiling=None
 if a.clearance:
  # Constant air depth over the large-scale terrain trend: no mass-driven speed-up or leak.
  from scipy.ndimage import gaussian_filter
  ceiling=(gaussian_filter(ground4.astype(np.float64),a.smooth/4,mode='nearest')+a.clearance).astype(np.float32)
  assert ceiling.max()<solid4.shape[0]*4-4,('Domain too low for the ceiling',float(ceiling.max()))
  solid4|=(np.arange(solid4.shape[0],dtype=np.float32)*4)[:,None,None]>=ceiling[None]
 valid4=valid2.reshape(ny//2,2,nx//2,2).mean((1,3))>=.5
 out=a.out;out.mkdir(parents=True,exist_ok=True)
 if ceiling is not None:np.save(out/'ceiling.npy',ceiling)
 ox,oy,oz=g['origin_xyz_m'];h=4.;blocked=[]
 np.save(out/'solid.npy',solid4);np.save(out/'ground.npy',ground4);np.save(out/'terrain_valid.npy',valid4)
 for t in g['turbines']:
  hx,hy,hz=t['hub_xyz_m'];r=t['radius_m']
  z,y,x=np.meshgrid(*[(np.arange(n)+.5)*h+o for n,o in zip(solid4.shape,(oz,oy,ox))],indexing='ij',sparse=True)
  i0=int((hx-16-ox)//h);i1=int((hx+16-ox)//h)+1
  disc=((y-hy)**2+(z-hz)**2<=r*r)&(np.abs(x[...,i0:i1]-hx)<=16)
  blocked.append(float((solid4[...,i0:i1]&disc).sum()/disc.sum()))
 cinfo=None
 if ceiling is not None:
  gaps=[float(ceiling[int((t['hub_xyz_m'][1]-oy)//h),int((t['hub_xyz_m'][0]-ox)//h)]-t['hub_xyz_m'][2]-t['radius_m']) for t in g['turbines']]
  cinfo=dict(clearance_m=a.clearance,smoothing_sigma_m=a.smooth,range_m=[float(ceiling.min()),float(ceiling.max())],min_gap_above_rotor_top_m=min(gaps))
 g.update(cell_m=h,shape_zyx=list(solid4.shape),size_xyz_m=[nx*2.,ny*2.,solid4.shape[0]*4.],ceiling=cinfo,cell_count=int(solid4.size),ground_range_m=[float(ground4.min()),float(ground4.max())],
  terrain_coverage_fraction=float(valid4.mean()),solid_fraction=float(solid4.mean()),structure_fraction=float(struct4.mean()),rotor_support_solid_fraction=blocked,
  coarsened_from='2 m geometry: ground height = mean of 2x2 columns, terrain re-thresholded; tower/nacelle cells solid if any 2 m child solid')
 g['assumptions']=g['assumptions']+['4 m cells coarsened from the 2 m voxels; no new geometric information.']
 (out/'metadata.json').write_text(json.dumps(g,indent=2))
 print(json.dumps({k:v for k,v in g.items() if k!='turbines'},indent=1))
if __name__=='__main__':main()
