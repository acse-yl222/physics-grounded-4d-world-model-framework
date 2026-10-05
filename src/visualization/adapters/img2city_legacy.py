"""Adapt retained CPU solar results to the existing feature-rich city viewer.

This exports display metadata, not new physical simulation results. Source run
identities are preserved; missing simulation modules remain explicitly unavailable.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tarfile
from zoneinfo import ZoneInfo
import numpy as np
from common.contract import validate
from urban_geometry.img2city_adapter import digest, write_json


def build(root, summer, winter, run_id='img2city_original_page_20261005'):
    root=Path(root).resolve(); summer=Path(summer).resolve(); winter=Path(winter).resolve()
    validate(summer/'manifest.json');validate(winter/'manifest.json')
    a=json.loads((summer/'manifest.json').read_text());b=json.loads((winter/'manifest.json').read_text())
    assert a['scene_id']==b['scene_id']=='south_ken'
    assert a['spatial']==b['spatial']
    out=root/'project/south_ken/runs'/run_id
    if out.exists(): raise FileExistsError(out)
    shutil.copytree(summer,out)
    physics=out/'physics';physics.mkdir()
    encoding=next(l['encoding'] for l in a['layers'] if l['id']=='irradiance')
    h,w=encoding['shape'][-2:];cell=encoding['spacing_m'][0];x0,y0=encoding['origin_m'][:2]
    height=np.load(summer/'data/height.npy');invalid=np.load(summer/'data/invalid.npy')
    np.save(physics/'height.npy',height)
    np.save(physics/'footprint.npy',((height>3)&(invalid==0)).astype(np.uint8))
    np.save(physics/'invalid.npy',invalid)
    metadata={'arrays':{},'adapter':'CPU solar results, unchanged values; no other solver outputs'}
    dates={}
    for src,manifest in [(summer,a),(winter,b)]:
        day=manifest['provenance']['parameters']['date_utc'];key=day.replace('-','')
        frames=json.loads((src/'data/frames.json').read_text())
        dates[key]={'label':day+' · Img2City CPU','ghi':f'ghi_{key}.npy','shadow':f'shadow_{key}.npy'}
        for source_file,field in [('irradiance.npy','ghi'),('shadow.npy','shadow')]:
            name=f'{field}_{key}.npy';shutil.copy2(src/'data'/source_file,physics/name)
            values=np.load(physics/name,mmap_mode='r')
            metadata['arrays'][name]={'shape':list(values.shape),'dtype':str(values.dtype),'time_local':[
                datetime.fromtimestamp(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()+f['seconds'],ZoneInfo('Europe/London')).strftime('%H:%M') for f in frames],
                'altitude_deg':[f['altitude_deg'] for f in frames],'azimuth_deg':[f['azimuth_deg'] for f in frames]}
    write_json(physics/'manifest.json',metadata)
    write_json(physics/'web/index.json',{'layers':{}})
    missing=[{'label':k,'reason':v} for k,v in [
      ('Wind / 流线','需要 CUDA、SCALED 权重；尚未针对 Img2City 重算'),
      ('Temperature / 等温线','需要新风场及热边界条件；尚未重算'),
      ('Day cycle / 昼夜温度','需要风场和热参数；尚未重算'),
      ('Pollution / 污染','需要风场和排放源；尚未重算'),
      ('Flooding / 积水','需要地形、降雨及排水输入；尚未重算'),
      ('Traffic / 信号灯','需要与模型对应的 SUMO 路网与交通需求'),
      ('UAVs / 无人机','需要针对当前建筑的航线与调度'),
      ('Birds / 鸟群','需要当前障碍物和栖息点输入')]]
    scene={'id':'south_ken','title':'Img2City · South Kensington · Original viewer',
      'description':'Img2City 地理模型 · 原版完整页面 · 本机重算日照',
      'integration_note':'当前模型：Img2City。日照为本机重算；其他模块未重算，未混入原场景数据。',
      'model':{'url':'data/model.glb','bytes':(out/'data/model.glb').stat().st_size},
      'grid':{'cell_m':cell,'cols':w,'rows':h,'x0':x0,'z_south':-y0,'size_note':f'{w*cell:g} × {h*cell:g} m'},
      'focus':{'box':[[x0,-y0-h*cell],[x0+w*cell,-y0]],'orbit_m':950,'label':'Img2City South Kensington'},
      'lite':{'footprint':'footprint.npy','roof':'height.npy','cell_m':cell},
      'masks':{},'surface_height':'height.npy',
      'timeline':{'step_s':1800,'steps':49},'phase_order':['solar'],
      'layers':{'solar':{'cell_m':cell,'shadow_cell_m':cell,'frames':49,'shadow_packed':False,'ghi_rate':2,'shadow_rate':2,'dates':dates,
         'label':'Sunlight · Img2City CPU 重算','ghi_label':'Irradiance · 4 m / 30 min','shadow_label':'Shadows · 4 m / 30 min'}},
      'unavailable_modules':missing,'limits':['4 m 顶表面近似；晴空假设；静态植被及玻璃按不透明处理。','日照时间使用伦敦本地时间；夏季 UTC+1。','Buildings / Ground / Trees、相机、自动轮播、日期切换和叠加模式沿用原版。']}
    write_json(out/'scene.json',scene)
    a['run_id']=run_id;a['simulation']='img2city_viewer_adapter';a['created_at']=datetime.now(timezone.utc).isoformat()
    a['provenance']['inputs'].extend([{'id':'summer_source_manifest','sha256':digest(summer/'manifest.json')},{'id':'winter_source_manifest','sha256':digest(winter/'manifest.json')}])
    a['provenance']['parameters']['adapter']='Existing legacy city viewer; solar only; unavailable modules explicit'
    snapshot=out/'viewer_source_snapshot.tar.gz'
    with tarfile.open(snapshot,'w:gz') as tar:
        for folder in ['src/visualization/legacy/viewer','src/visualization/adapters']:
            for p in sorted((root/folder).rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts:tar.add(p,arcname=str(p.relative_to(root)))
    a['artifacts'].extend({'id':'viewer_'+str(i),'asset':str(p.relative_to(out)),'sha256':digest(p),'media_type':'application/octet-stream'} for i,p in enumerate([out/'scene.json',snapshot,*sorted(physics.rglob('*.json')),*sorted(physics.glob('*.npy'))]))
    write_json(out/'manifest.json',a);validate(out/'manifest.json')
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('summer',type=Path);parser.add_argument('winter',type=Path);args=parser.parse_args()
    print(build(args.root,args.summer,args.winter))


def campus_to_region_affine():
    """Canonical Img2City ENU -> legacy core008 region XY, from its assembly code.

    The original core008 model was transformed out of the campus frame; the
    inherited project origin alone is insufficient to locate its replay arrays.
    """
    region_to_campus = np.array([[.9971372878088512,.03850621238135248],[-.03860679068166115,.9997417959287375]])
    translation = np.array([-700.1750108416061,238.94679349918735])
    inverse = np.linalg.inv(region_to_campus)
    return inverse @ np.diag([1.,111320./110540.]), -inverse @ translation
