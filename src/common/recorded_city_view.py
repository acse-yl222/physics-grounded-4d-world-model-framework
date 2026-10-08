"""Adapt retained protocol fields to the existing city presentation without resampling.

The retained protocol runs remain the scientific source of truth. This adapter copies
exact NPY values/masks and records their provenance; it does not run physics.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import numpy as np
from common.storage import Storage
from common.contract import validate
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runs import promote


def prepare(storage, config_path, output):
    config=json.loads(Path(config_path).read_text());scene=config['scene_id'];output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    physics=output/'physics';(physics/'masks').mkdir(parents=True,exist_ok=True)
    (physics/'web').mkdir(exist_ok=True);write(physics/'web/index.json',{'layers':{}})
    layers={};arrays={};inputs=[];limits=[];grid=None
    for key,selection in config['fields'].items():
        folder=storage.run(scene,selection['run_id']);validate(folder/'manifest.json')
        manifest=json.loads((folder/'manifest.json').read_text())
        layer=next(l for l in manifest['layers'] if l['id']==selection['layer_id'])
        encoding=layer['encoding'];times=np.asarray(manifest['time']['samples'])
        if layer['format']!='npy' or layer['sampling']!='step' or len(times)<2 or not np.allclose(np.diff(times),times[1]-times[0]):
            raise ValueError('City adapter requires uniformly sampled recorded NPY step fields')
        if encoding['axes'] not in ('TYX','TCYX') or encoding['spacing_m'][0]!=encoding['spacing_m'][1]:raise ValueError('Unsupported grid')
        cell=encoding['spacing_m'][0];ny,nx=encoding['shape'][-2:];x0,y0,z=encoding['origin_m']
        domain=(x0,y0,nx*cell,ny*cell)
        if grid is None:grid=domain
        if domain!=grid:raise ValueError('Field domains differ; do not silently resample')
        asset=f'{key}.npy';shutil.copy2(folder/layer['asset'],physics/asset)
        mask=f'masks/{key}_invalid.npy';shutil.copy2(folder/encoding['mask_asset'],physics/mask)
        values=np.load(physics/asset,mmap_mode='r');invalid=np.load(physics/mask)
        if not np.isin(invalid,[0,1]).all():raise ValueError('Invalid mask')
        if not np.array_equal(values,np.load(folder/layer['asset'],mmap_mode='r')):raise ValueError('Copy altered recorded values')
        low,high=selection.get('display_range',layer['display']['range'])
        label=selection['label']
        entry={'file':asset,'cell_m':cell,'frames':len(times),'t0_s':float(times[0]),'step_s':float(times[1]-times[0]),'range':[low,high],'y':z,'rate':3,'label':label,'title':label,'legend':[f'{low:.1f}',layer['field']['unit'],f'{high:.1f}']}
        if key=='temp':entry.update(iso={'from':20,'step':2,'n':13},iso_y=z+.2,iso_label='Isotherms (2 °C; display interpolation)',heat_label=f'Heat map at {z:g} m')
        layers[key]=entry;arrays[asset]={'shape':list(values.shape),'time_s':times.tolist(),'axes':encoding['axes'],'unit':layer['field']['unit']}
        inputs.append({'id':key+'_manifest','sha256':digest(folder/'manifest.json')})
        inputs.append({'id':key+'_array','sha256':digest(folder/layer['asset'])})
        limits.append(f'{label}: {len(times)} recorded frames, {times[0]:g}–{times[-1]:g} s; step sampling.')
    x0,y0,width,height=grid
    wind=layers['wind'];temp=layers['temp'];step=wind['step_s']
    if wind['t0_s']!=temp['t0_s'] or wind['t0_s']+(wind['frames']-1)*step!=temp['t0_s']+(temp['frames']-1)*temp['step_s']:
        raise ValueError('This presentation requires matching recorded time endpoints')
    # Lite geometry is an explicitly labelled column proxy, separate from full GLB.
    outer=storage.run(scene,config['outer_run'])
    for source,target in [('solver_grid8m/building_footprint.npy','lite_footprint.npy'),('solver_grid8m/height_m.npy','lite_height.npy')]:
        shutil.copy2(outer/source,physics/'masks'/target)
    model=output/'models/canary_wharf_4km.glb'
    if not model.is_file():raise FileNotFoundError(model)
    metadata={'id':scene,'title':config['title'],'description':config['description'],
        'grid':{'cell_m':wind['cell_m'],'cols':round(width/wind['cell_m']),'rows':round(height/wind['cell_m']),'x0':x0,'z_south':-y0,'domain_origin_xy_m':[x0,y0],'origin_label':'Local ENU','size_note':'4000 × 4000 m'},
        'model':{'url':'models/canary_wharf_4km.glb','bytes':model.stat().st_size,'building_ids_are_architecture':True,'non_occluding_site_ground':True,'plate_color':'#404b52'},
        'lite':{'footprint':'masks/lite_footprint.npy','roof':'masks/lite_height.npy','cell_m':8},
        'masks':{'footprint':{str(int(temp['cell_m'])):'masks/temp_invalid.npy'},'solid_wind':{'file':'masks/wind_invalid_zyx.npy','layer':0}},
        'focus':{'box':[[-600,-600],[600,600]],'orbit_m':1400,'label':'Canary Wharf · detailed core'},
        'timeline':{'t0_s':wind['t0_s'],'step_s':step,'steps':wind['frames']},'phase_order':['wind','temp'],'layers':layers,
        'traffic':{'dir':'traffic/','label':'Vehicle traffic · recorded SUMO baseline'},
        'limits':config['limits']+limits}
    metadata['model'].update(config.get('model_options',{}))
    metadata['traffic'].update(config.get('traffic_options',{}))
    if config.get('uav'): metadata['uav']=config['uav']
    np.save(physics/'masks/wind_invalid_zyx.npy',np.load(physics/'masks/wind_invalid.npy')[None])
    write(physics/'manifest.json',{'arrays':arrays});write(output/'scene.json',metadata)
    for name,run_id in config.get('additional_source_runs',{}).items():
        inputs.append({'id':name+'_manifest','sha256':digest(storage.run(scene,run_id)/'manifest.json')})
    write(output/'adapter_inputs.json',inputs);shutil.copy2(config_path,output/'adapter_config.json')
    return metadata


def retain(storage,scene,output,run_id):
    output=Path(output);project=json.loads((storage.metadata(scene)/'project.json').read_text())
    revision=snapshot_sources(storage.root,output/'source_snapshot.tar.gz')
    artifacts=[]
    for path in sorted(output.rglob('*')):
        if not path.is_file() or path.name=='manifest.json' and path.parent==output:continue
        rel=path.relative_to(output).as_posix()
        if rel=='models/canary_wharf_4km.glb':continue
        artifacts.append({'id':'source_snapshot' if rel=='source_snapshot.tar.gz' else rel,'asset':rel,'sha256':digest(path),'media_type':'application/octet-stream'})
    inputs=json.loads((output/'adapter_inputs.json').read_text())
    inputs.append({'id':'merged_geometry','sha256':digest(output/'models/canary_wharf_4km.glb')})
    manifest={'schema_version':'1.1.0','scene_id':scene,'simulation':'city_presentation','run_id':run_id,'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),
        'spatial':project['spatial'],'time':{'unit':'s','samples':[]},'provenance':{'code_revision':revision,'dirty':True,'parameters':{'adapter':'recorded_city_view','scientific_sources':json.loads((output/'adapter_config.json').read_text())},'inputs':inputs},
        'layers':[{'id':'geometry','kind':'mesh','format':'glb','asset':'models/canary_wharf_4km.glb','sampling':'static','encoding':{'coordinate_frame':'glTF-y-up'},'display':{'widget':'mesh','capabilities':['pick','opacity']}}],'artifacts':artifacts}
    write(output/'manifest.json',manifest);validate(output/'manifest.json');return promote(storage,output)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--retain-run');a=p.parse_args();s=Storage.load()
    prepare(s,a.config,a.output)
    if a.retain_run:print(retain(s,json.loads(Path(a.config).read_text())['scene_id'],a.output,a.retain_run))
