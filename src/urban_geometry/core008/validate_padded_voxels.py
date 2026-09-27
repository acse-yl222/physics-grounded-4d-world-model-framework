"""Validate the 1m/2m pair and produce matching padded-domain previews."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]/'output/core008/geometry'
reports=[]
for spacing in (1,2):
    folder=ROOT/f'south_kensington_core008_voxel_{spacing}m_domain4096'
    m=json.loads((folder/'metadata.json').read_text())
    s=np.load(folder/'solid.npy',mmap_mode='r',allow_pickle=False)
    h=np.load(folder/'height_m.npy',allow_pickle=False)
    assert s.shape==(128//spacing,4096//spacing,4096//spacing)
    assert s.dtype==np.bool_ and np.isfinite(h).all()
    assert m['origin_xyz_m']==[0,0,0] and m['upper_edge_xyz_m']==[4096,4096,128]
    count=0
    for k in range(len(s)):
        assert np.array_equal(s[k],np.ceil(h/spacing)>k)
        count+=int(s[k].sum())
    assert count==m['occupied_voxels'] and not s[-1].any()
    # Outer padding boundary is air; ensure all source bounds are inside horizontally.
    assert not (s[:,:,0].any() or s[:,:,-1].any() or s[:,0,:].any() or s[:,-1,:].any())
    b=np.array(m['source_bounds_in_domain_xyz_m'])
    assert np.all(b[0,:2]>0) and np.all(b[1,:2]<4096)
    with np.load(folder/'geometry.npz',allow_pickle=False) as z:
        for key in ('geometry','solid'):
            a=z[key]
            assert np.array_equal(a,s)
            del a
        assert np.array_equal(z['height_m'],h)
        assert np.array_equal(z['grid_origin'],m['origin_xyz_m'])
    # Max pooling for display preserves small occupied features.
    def reduced(a):
        factor=a.shape[0]//1024
        return a.reshape(1024,factor,1024,factor).max(axis=(1,3))
    hh=reduced(h)
    palette=np.array([[19,31,45],[37,116,148],[65,181,159],[229,207,99],[246,130,65]],float)
    value=np.clip(hh/96,0,1)*4
    low=np.minimum(value.astype(int),3); t=(value-low)[...,None]
    rgb=(palette[low]*(1-t)+palette[low+1]*t).astype(np.uint8)
    panels=[('Sampled roof height: dark = 0 m, orange = 96 m',rgb)]
    for altitude in (0,20,48):
        a=np.zeros((1024,1024,3),np.uint8);a[:]=[19,31,45]
        a[reduced(s[altitude//spacing])]=[92,215,183]
        panels.append((f'Solid cells: z = {altitude}-{altitude+spacing} m',a))
    preview=Image.new('RGB',(1480,1540),'#101b29');d=ImageDraw.Draw(preview)
    d.text((24,15),f'SOUTH KENSINGTON | {spacing} m voxels | Z,Y,X = {s.shape}',fill='white')
    d.text((24,37),'Domain: X,Y = 0-4096 m; Z = 0-128 m | North up | Original source extent outlined',fill='#c3d0db')
    for i,(title,a) in enumerate(panels):
        x=24+(i%2)*735;y=75+(i//2)*730
        d.text((x,y),title,fill='white')
        im=Image.fromarray(a[::-1]).resize((700,700),Image.Resampling.NEAREST)
        preview.paste(im,(x,y+22))
        d.rectangle((x+b[0,0]/4096*700,y+22+(1-b[1,1]/4096)*700,
                     x+b[1,0]/4096*700,y+22+(1-b[0,1]/4096)*700),outline='#8192a3')
    d.text((24,1520),'Outside source extent: padding, not surveyed free space. Column-solidified buildings; no wind inference.',fill='#c3d0db')
    preview.save(folder/'preview.png')
    reports.append({'spacing_m':spacing,'shape_zyx':list(s.shape),'occupied_voxels':count,
                    'solid_bytes':(folder/'solid.npy').stat().st_size,'checks_passed':True})
    print(reports[-1],flush=True)

p1=ROOT/'south_kensington_core008_voxel_1m_domain4096'
p2=ROOT/'south_kensington_core008_voxel_2m_domain4096'
a=np.load(p1/'solid.npy',mmap_mode='r');b=np.load(p2/'solid.npy',mmap_mode='r')
for z in range(64):
    pooled=a[z*2:z*2+2].reshape(2,2048,2,2048,2).max(axis=(0,2,4))
    assert np.array_equal(pooled,b[z]),f'Cross-resolution occupancy mismatch at layer {z}'
metadata=[json.loads((p/'metadata.json').read_text()) for p in (p1,p2)]
assert metadata[0]['source_region_origin_xyz_m']==metadata[1]['source_region_origin_xyz_m']
report={'datasets':reports,'coarse_equals_2x2x2_max_pool_of_fine':True,'same_coordinate_origin':True}
(ROOT/'south_kensington_padded_voxels_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Cross-resolution alignment and occupancy checks passed.',flush=True)
