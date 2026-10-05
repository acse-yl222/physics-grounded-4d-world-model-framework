"""Local Img2City display adapter step. See docs/framework/img2city-full-viewer.md. No Git operations."""
import argparse
from pathlib import Path
_parser=argparse.ArgumentParser()
_parser.add_argument('--root',type=Path,default=Path.cwd())
_args=_parser.parse_args()
_ROOT=_args.root.resolve()
from pathlib import Path
import json, numpy as np
r=(_ROOT/'project/south_ken/runs/img2city_original_page_20261005');p=r/'physics'
scene=json.loads((r/'scene.json').read_text())
if 'coordinate_adapter' in scene:raise ValueError('Already converted to the region frame; start from a fresh adapter bundle')
A=np.array([[.9971372878088512,.03850621238135248],[-.03860679068166115,.9997417959287375]])
t=np.array([-700.1750108416061,238.94679349918735]);S=np.diag([1,111320/110540]);
from visualization.adapters.img2city_legacy import campus_to_region_affine
M,shift=campus_to_region_affine()
old=scene['grid'];ox=old['x0'];oy=-old['z_south'];ow=old['cols'];oh=old['rows'];cell=4
corners=np.array([[ox,oy],[ox+ow*cell,oy],[ox,oy+oh*cell],[ox+ow*cell,oy+oh*cell]])@M.T+shift
lo=np.floor(corners.min(axis=0)/4)*4;hi=np.ceil(corners.max(axis=0)/4)*4
w,h=((hi-lo)/4).astype(int);xx,yy=np.meshgrid(lo[0]+(np.arange(w)+.5)*4,lo[1]+(np.arange(h)+.5)*4)
q=(np.stack([xx,yy],-1)-shift)@np.linalg.inv(M).T
ix=np.floor((q[...,0]-ox)/4).astype(int);iy=np.floor((q[...,1]-oy)/4).astype(int);inside=(ix>=0)&(ix<ow)&(iy>=0)&(iy<oh);ix=np.clip(ix,0,ow-1);iy=np.clip(iy,0,oh-1)
source_invalid=np.load(r/'data/invalid.npy');invalid=(~inside)|(source_invalid[iy,ix]!=0)
# NN preserves binary shading; the field is already spatially discretized at 4 m.
for file in list(p.glob('*.npy')):
 a=np.load(file)
 if a.shape[-2:]!=(oh,ow):continue
 out=a[...,iy,ix].copy();out[...,invalid]=0;np.save(file,out)
np.save(p/'invalid.npy',invalid.astype(np.uint8))
mat=np.eye(4);mat[0,0]=M[0,0];mat[0,2]=-M[0,1];mat[2,0]=-M[1,0];mat[2,2]=M[1,1];mat[0,3]=shift[0];mat[2,3]=-shift[1]
scene['model']['matrix']=mat.T.reshape(-1).tolist()
scene['grid'].update(cols=int(w),rows=int(h),x0=float(lo[0]),z_south=float(-lo[1]),size_note=f'{w*4} × {h*4} m')
scene['focus']['box']=[[float(lo[0]),float(-hi[1])],[float(hi[0]),float(-lo[1])]]
scene['replay_focus']={'min':scene['focus']['box'][0],'max':scene['focus']['box'][1]}
scene['surface_invalid']='invalid.npy'
scene['coordinate_adapter']={'source':'src/urban_geometry/core008/south_kensington_core008_merge.py','region_to_campus_A':A.tolist(),'region_to_campus_translation':t.tolist(),'north_scale':111320/110540,'method':'Inverse repository affine, with Img2City north scale conversion; nearest-neighbour scalar display resampling. Not solver recomputation.'}
(r/'scene.json').write_text(json.dumps(scene,indent=2)+'\n')
meta=json.loads((p/'manifest.json').read_text())
for v in meta['arrays'].values():v['shape'][-2:]=[int(h),int(w)]
(p/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
crop={'x':int((lo[0]+1636)/4),'y':int((lo[1]+1484)/4),'width':int(w),'height':int(h)}
(_ROOT/'project/south_ken/runs/img2city_original_page_20261005/reference_crop.json').write_text(json.dumps(crop));print('Viewer region grid',scene['grid'],'crop',crop,'matrix',mat.tolist())
