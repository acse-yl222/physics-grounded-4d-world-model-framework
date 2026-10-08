"""Package a completed legacy array export into self-contained protocol runs and one view."""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
from datetime import datetime, timezone
from .contract import validate, read_json
from .storage import identifier


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def copy_asset(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    try:os.link(source,destination)
    except OSError:shutil.copy2(source,destination)


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def package_export(storage,source,config,run_id,source_snapshot=None,code_revision=None):
    import numpy as np
    source=Path(source).resolve();identifier(run_id,run=True)
    scene=config['scene'];scene_meta=read_json(source/'scene.json');field_meta=read_json(source/'physics/manifest.json')
    bundle=source.parent/'protocol'
    if bundle.exists():raise FileExistsError(f'Protocol bundle already exists: {bundle}')
    grid=scene_meta['grid'];geo=config['georeference']
    registered=storage.metadata(scene)/'project.json'
    if registered.exists():spatial=read_json(registered)['spatial']
    else:
        if geo.get('latitude_deg') is None or geo.get('longitude_deg') is None:raise ValueError('Set the scene coordinate origin before exporting')
        spatial={'frame':'ENU','units':'m','origin':{'longitude':geo['longitude_deg'],'latitude':geo['latitude_deg'],'height_m':0,'vertical_datum':geo.get('terrain','Local engineering height')},'bounds_m':{'min':[grid['x0'],-grid['z_south'],0],'max':[grid['x0']+grid['cols']*grid['cell_m'],-grid['z_south']+grid['rows']*grid['cell_m'],config['domain']['wind_layers']*grid['cell_m']]}}
    from .provenance import snapshot_sources
    bundle.mkdir(parents=True)
    snapshot=bundle/'source_snapshot.tar.gz'
    export_snapshot=None
    if source_snapshot is not None:
        shutil.copy2(source_snapshot,snapshot)
        export_snapshot=bundle/'export_source_snapshot.tar.gz'
        snapshot_sources(storage.root,export_snapshot)
    else:
        code_revision=snapshot_sources(storage.root,snapshot)
    code_revision=code_revision or 'source-snapshot'
    snapshot_hash=digest(snapshot)
    provenance={'code_revision':code_revision,'dirty':True,'parameters':config,'inputs':[{'id':'scene_export','sha256':digest(source/'scene.json')},{'id':'field_metadata','sha256':digest(source/'physics/manifest.json')},{'id':'geometry_asset','sha256':digest(source/scene_meta['model']['url'])}]}
    base={'schema_version':'1.1.0','scene_id':scene,'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),'provenance':provenance,'spatial':spatial}
    runs=[];selection=[]
    def emit(simulation,layer,asset,times,epoch=None,invalid=None):
        rid=f'{run_id}_{simulation}';target=bundle/rid;asset_name='data/'+Path(asset).name
        copy_asset(asset,target/asset_name);layer={**layer,'asset':asset_name}
        copy_asset(snapshot,target/'provenance/source_snapshot.tar.gz')
        manifest={**base,'artifacts':[{'id':'source_snapshot','asset':'provenance/source_snapshot.tar.gz','sha256':snapshot_hash,'media_type':'application/gzip'}],'simulation':simulation,'run_id':rid,'time':{'unit':'s','samples':times},'layers':[layer]}
        if export_snapshot is not None:
            copy_asset(export_snapshot,target/'provenance/export_source_snapshot.tar.gz')
            manifest['artifacts'].append({'id':'export_source_snapshot','asset':'provenance/export_source_snapshot.tar.gz','sha256':digest(export_snapshot),'media_type':'application/gzip'})
        if invalid is not None:
            np.save(target/'data/invalid.npy',invalid.astype(np.uint8))
            layer['encoding'].update(mask_asset='data/invalid.npy',mask_dtype='|u1',mask_semantics='invalid_nonzero')
        if epoch is not None:manifest['time']['epoch']=epoch
        write(target/'manifest.json',manifest);validate(target/'manifest.json');runs.append(rid);selection.append({'run_id':rid,'layer_id':layer['id'],'visible':True})
    try:
        model=source/scene_meta['model']['url']
        emit('geometry',{'id':'geometry','kind':'mesh','format':'glb','sampling':'static','encoding':{'coordinate_frame':'glTF-y-up'},'display':{'widget':'mesh','capabilities':['pick','opacity']}},model,[])
        names={'wind':('velocity','m/s'),'temp':('temperature','degC'),'poll':('concentration','1'),'flood':('water_depth','m')}
        for key,(field,unit) in names.items():
            meta=scene_meta.get('layers',{}).get(key)
            if not meta or not meta.get('file'):continue
            path=source/'physics'/meta['file'];array=np.load(path,mmap_mode='r',allow_pickle=False)
            vector=key=='wind';dims=4 if vector else 3
            if array.ndim!=dims:raise ValueError(f'Unexpected {key} shape {array.shape}')
            metadata=field_meta.get('arrays',{}).get(meta['file'],{})
            times=metadata.get('time_s')
            if times is None:
                if 'step_s' not in meta:raise ValueError(f'{key} has no explicit time samples')
                times=[meta.get('t0_s',0)+i*meta['step_s'] for i in range(array.shape[0])]
            if len(times)!=array.shape[0]:raise ValueError(f'{key}: time/array length mismatch')
            cell=meta['cell_m'];kind='vector_field' if vector else 'scalar_field'
            layer={'id':key,'kind':kind,'format':'npy','sampling':'linear','field':{'name':field,'unit':metadata.get('units',unit)},'encoding':{'coordinate_frame':'ENU','dtype':array.dtype.str,'shape':list(array.shape),'axes':'TCYX' if vector else 'TYX','origin_m':[grid['x0'],-grid['z_south'],meta.get('y',0)],'spacing_m':[cell,cell],'sample_location':'cell_center','byte_order':'little','compression':'none'},'display':{'widget':kind,'capabilities':['pick','legend','opacity']}}
            if metadata.get('layer_m'):
                layer['encoding']['origin_m'][2]=sum(metadata['layer_m'])/2
            invalid=None
            mask=scene_meta.get('masks',{}).get('solid_wind')
            if key in ('wind','temp') and mask:
                invalid=np.load(source/'physics'/mask['file'],allow_pickle=False)[mask['layer']]
                if invalid.shape!=array.shape[-2:]:raise ValueError('Field and obstacle mask grids differ')
            if meta.get('range'):layer['display']['range']=meta['range']
            emit(key,layer,path,list(times),invalid=invalid)
        # Recorded solar irradiance is a scalar series with an explicit UTC clock.
        solar=scene_meta.get('layers',{}).get('solar',{})
        for date,meta in solar.get('dates',{}).items():
            if not meta.get('ghi'):continue
            path=source/'physics'/meta['ghi'];array=np.load(path,mmap_mode='r',allow_pickle=False);info=field_meta['arrays'][meta['ghi']]
            utc=info.get('time_utc');times=info.get('time_s')
            if times is None and utc:
                parsed=[datetime.fromisoformat(t.replace('Z','+00:00')) for t in utc];times=[(t-parsed[0]).total_seconds() for t in parsed]
            if times is None:raise ValueError('Solar export is missing its time axis')
            kind='scalar_field';cell=solar['cell_m']
            emit('solar_'+date.replace('-','_'),{'id':'irradiance','kind':kind,'format':'npy','sampling':'linear','field':{'name':'irradiance','unit':'W/m2'},'encoding':{'coordinate_frame':'ENU','dtype':array.dtype.str,'shape':list(array.shape),'axes':'TYX','origin_m':[grid['x0'],-grid['z_south'],.1],'spacing_m':[cell,cell],'sample_location':'cell_center','byte_order':'little','compression':'none'},'display':{'widget':kind,'capabilities':['pick','legend','opacity']}},path,times,utc[0] if utc else None)
        view={'schema_version':'1.1.0','scene_id':scene,'title':scene_meta['title'],'time_alignment':'relative','runs':runs,'layers':selection}
        project={'schema_version':'1.1.0','scene_id':scene,'title':scene_meta['title'],'spatial':spatial,'inputs':[],'default_view':'default'}
        write(bundle/'bundle.json',{'schema_version':'1.1.0','scene_id':scene,'view_id':'run_'+re.sub('[^a-z0-9_]', '_', run_id.lower()),'runs':runs,'view':view,'project':project})
        return bundle
    except Exception:
        if bundle.exists():shutil.rmtree(bundle)
        raise
