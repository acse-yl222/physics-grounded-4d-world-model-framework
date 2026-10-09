"""Versioned city display of independent recorded fields, copied without resampling."""
import argparse,json,shutil
from pathlib import Path
import numpy as np
from common.storage import Storage
from common.export import write,digest
from common.contract import validate
from common.recorded_city_view import retain


def prepare(storage,config_path,out):
    cfg=json.loads(Path(config_path).read_text());scene=cfg['scene_id'];out=Path(out)
    out.mkdir(parents=True,exist_ok=False);physics=out/'physics';(physics/'masks').mkdir(parents=True);(physics/'web').mkdir()
    base=storage.run(scene,cfg['base_run']);meta=json.loads((base/'scene.json').read_text())
    # Reuse exact geometry and activity assets; no solver runs or old fields copied.
    for name in ['models','uav','traffic']:shutil.copytree(base/name,out/name,copy_function=__import__('os').link)
    for name in ['lite_footprint.npy','lite_height.npy']:shutil.copy2(base/'physics/masks'/name,physics/'masks'/name)
    layers={};arrays={};masks={};inputs=[];limitations=[];domain=None
    for key,selection in cfg['fields'].items():
        folder=storage.run(scene,selection['run_id']);validate(folder/'manifest.json');m=json.loads((folder/'manifest.json').read_text())
        layer=next(l for l in m['layers'] if l['id']==selection['layer_id']);e=layer['encoding'];times=m['time']['samples']
        if layer['format']!='npy' or layer['sampling']!='step' or e['axes'] not in ['TYX','TCYX']:raise ValueError('Unsupported recorded field')
        if len(times)<2 or not np.allclose(np.diff(times),times[1]-times[0]):raise ValueError('Uniform recorded samples required')
        dx,dy=e['spacing_m'];x0,y0,z=e['origin_m'];ny,nx=e['shape'][-2:]
        extent=(x0,y0,nx*dx,ny*dy)
        if dx!=dy or (domain is not None and extent!=domain):raise ValueError('Field grids must have identical domain, no silent resampling')
        domain=extent;asset=f'{key}.npy';mask=f'masks/{key}_invalid.npy'
        shutil.copy2(folder/layer['asset'],physics/asset);shutil.copy2(folder/e['mask_asset'],physics/mask)
        if digest(physics/asset)!=digest(folder/layer['asset']):raise ValueError('Recorded values changed')
        invalid=np.load(physics/mask)
        if invalid.shape!=(ny,nx) or not np.isin(invalid,[0,1]).all():raise ValueError('Mask shape/values differ')
        lo,hi=selection.get('display_range',layer['display']['range']);label=selection['label']
        entry={'file':asset,'cell_m':dx,'frames':len(times),'t0_s':times[0],'step_s':times[1]-times[0],'own_clock':True,'overlay_frame':len(times)-1,'y':z,'rate':2,'label':label,'title':label,'range':[lo,hi],'legend':[f'{lo:g}',layer['field']['unit'],f'{hi:g}']}
        entry.update(selection.get('display_options',{}));layers[key]=entry;masks[key]=mask
        arrays[asset]={'shape':e['shape'],'time_s':times,'axes':e['axes'],'unit':layer['field']['unit']}
        if key=='solar':
            sun=json.loads((folder/selection['sun_positions_asset']).read_text())
            arrays[asset].update(time_local=[f"{int(r['local_bst_hour']):02d}:{round((r['local_bst_hour']%1)*60):02d}" for r in sun],altitude_deg=[r['altitude_deg'] for r in sun],azimuth_deg=[r['azimuth_deg'] for r in sun])
        inputs.append({'id':key+'_manifest','sha256':digest(folder/'manifest.json')})
        parameters=m['provenance'].get('parameters',{});limitations.extend(parameters.get('limitations',parameters.get('limits',[])))
    x0,y0,width,height=domain;wind=layers['wind'];solar=layers['solar'];shadow=layers.pop('shadow')
    solar.update(dates={cfg['solar_date']:{'label':cfg['solar_label'],'ghi':solar['file'],'shadow':shadow['file']}},shadow_cell_m=shadow['cell_m'],shadow_packed=False,ghi_rate=2,shadow_rate=2,ghi_label='Irradiance · 4 m',shadow_label='Shadows · 4 m')
    arrays[shadow['file']].update({k:arrays[solar['file']][k] for k in ['time_local','altitude_deg','azimuth_deg']})
    temp=layers['temp'];temp.update(iso={'from':20,'step':2,'n':13},iso_y=temp['y']+.2,heat_label=f"Heat map at {temp['y']:g} m")
    np.save(physics/'masks/wind_invalid_zyx.npy',np.load(physics/masks['wind'])[None])
    meta.update(title=cfg['title'],description=cfg['description'],grid={'cell_m':wind['cell_m'],'cols':round(width/wind['cell_m']),'rows':round(height/wind['cell_m']),'x0':x0,'z_south':-y0,'domain_origin_xy_m':[x0,y0],'origin_label':'Local ENU','size_note':'4000 × 4000 m'},timeline={'t0_s':wind['t0_s'],'step_s':wind['step_s'],'steps':wind['frames']},phase_order=['wind','temp','solar','poll','flood'],layers=layers,masks={'footprint':{str(int(temp['cell_m'])):masks['temp']},'solid_wind':{'file':'masks/wind_invalid_zyx.npy','layer':0},'layer_invalid':{k:masks[k] for k in ['solar','shadow','poll','flood']}},limits=list(dict.fromkeys(cfg['limits']+limitations)))
    write(physics/'web/index.json',{'layers':{}});write(physics/'manifest.json',{'arrays':arrays});write(out/'scene.json',meta)
    inputs.append({'id':'base_presentation','sha256':digest(base/'manifest.json')});write(out/'adapter_inputs.json',inputs);shutil.copy2(config_path,out/'adapter_config.json')
    return meta

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--retain-run');a=p.parse_args();s=Storage.load();prepare(s,a.config,a.output)
    if a.retain_run:print(retain(s,json.loads(Path(a.config).read_text())['scene_id'],a.output,a.retain_run))
