"""Reproduce the 40-bird, 120-second CPU sample for the original-page adapter."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import numpy as np


def run(root):
    root=Path(root).resolve();bundle=root/'project/south_ken/runs/img2city_original_page_20261005'
    scene=json.loads((bundle/'scene.json').read_text());grid=scene['grid']
    height=np.load(bundle/'physics/height.npy');invalid=np.load(bundle/'physics/invalid.npy')
    out=bundle/'bird_compute';out.mkdir(exist_ok=True)
    if (out/'img2city_birds.npz').exists():raise FileExistsError('Retained bird sample already exists; use a fresh bundle')
    z=(np.arange(32)+.5)*4
    geometry=(z[:,None,None]<=np.maximum(height,4)[None,:,:])&(invalid[None,:,:]==0)
    np.savez_compressed(out/'geometry.npz',geometry=geometry,grid_spacing=4.,grid_spacing_z=4.,grid_origin=[grid['x0'],-grid['z_south'],0])
    meta={'source':'Img2City CPU top-surface raster transformed to original region frame','approximation':'solid columns, vegetation opaque; 4m grid; minimum 4m ground column; invalid cells no obstacles','world_box':{'x':[grid['x0'],grid['x0']+4*grid['cols']],'z':[-grid['z_south'],-grid['z_south']+4*grid['rows']],'ceiling_m':128},'bird_grid':{'shape_zyx':list(geometry.shape),'spacing_m':4}}
    (out/'geometry_META.json').write_text(json.dumps(meta,indent=2))
    scripts=root/'src/visualization/legacy/agents/demo_rev02/tools/birds'
    subprocess.run([sys.executable,str(scripts/'run_city_v3.py'),'--source',str(root/'src/urban_geometry/birds'),'--geometry',str(out/'geometry.npz'),'--road-layer',str(bundle/'replay/data/roads.json'),'--out',str(out/'img2city_birds.npz'),'--n-birds','40','--n-steps','2400','--dt','0.05','--spawn','937,-674,70','--save-every','5','--roost-near','937,674','--forage-near','937,674'],check=True,cwd=root)
    subprocess.run([sys.executable,str(scripts/'build_bird_replay_v2.py'),'--npz',str(out/'img2city_birds.npz'),'--evidence',str(out/'img2city_birds_EVIDENCE.json'),'--geometry-meta',str(out/'geometry_META.json'),'--out-dir',str(bundle/'replay/data/birds_southken')],check=True,cwd=root)
    path=bundle/'replay/data/birds_southken/bird_replay.json';data=json.loads(path.read_text())
    data['claim']='Project bird solver on Img2City solid-column geometry: 40 birds, 120 seconds, 4m obstacle voxels, no wind, seed 42. Assumed roost/forage sites, not ecological validation; no traffic or UAV coupling.'
    data['source_npz']['path']='bird_compute/img2city_birds.npz';path.write_text(json.dumps(data,indent=2))
    scene['bird_sample_loop']=True
    scene['integration_note']='Img2City 地理模型｜日照、40 只鸟群：本机计算｜风、温度、污染、积水、交通、UAV：原版参考演示，未按新建筑重算。'
    (bundle/'scene.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd());run(parser.parse_args().root)
