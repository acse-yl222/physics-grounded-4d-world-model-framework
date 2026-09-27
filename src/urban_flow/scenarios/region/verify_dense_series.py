"""Check complete dense time series against its final float32 solver checkpoint."""
import json
from pathlib import Path
import numpy as np
import h5py
root=Path.cwd();folder=root/'visualizer/scenes/region/physics/ai4urban'
m=json.loads((folder/'manifest.json').read_text())
assert m['complete'] and m['completed_steps']==600
solid=np.load(root/'output/region/geometry/voxel_8m/solid.npy')
ground=np.load(root/'output/region/geometry/voxel_8m/ground_mesh_m_yx.npy')
y,x=np.indices(ground.shape)
with h5py.File(root/'output/region/physics/ai4urban_dense300/checkpoint.h5') as cp:
 assert cp.attrs['step']==600
 for f in m['fields']:
  assert f['steps']==list(range(0,601,10)) and f['times']==list(range(0,301,5))
  mask=np.load(folder.parent/f['mask']);valid=mask==0
  for name in f['files']:
   a=np.load(folder.parent/name)
   assert a.shape==(1,3,512,768)
   assert np.isfinite(a[0,:,valid]).all() and np.isnan(a[0,:,~valid]).all()
  z=np.clip(np.floor((ground+f['agl_m'])/8).astype(int),0,63)
  final=np.load(folder.parent/f['files'][-1])[0]
  for i,key in enumerate(['u','v','w']):
   expected=cp[key][:][z,y,x]*(-1 if i==0 else 1)
   np.testing.assert_array_equal(final[i][valid],expected[valid].astype(np.float16))
print(json.dumps({'passed':True,'frames_per_height':61,'heights_m':[40,80,120],'times_s':[0,300],'interval_s':5,'final_matches_float32_checkpoint_after_float16_export':True}))
