"""Package recorded ENU wind slices without inventing times or resampling values.

Raw contract: velocity_samples.npy[T,3,H,Y,X], sample_invalid.npy[H,Y,X],
sample_times_s.json list, sample_heights.json list of actual cell-center heights.
Caller supplies the completed solver metadata/config and reproducible source files.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, zipfile
from datetime import datetime, timezone
import numpy as np
from common.storage import Storage
from common.contract import validate
from common.runs import promote, refresh_catalog
from common.catalog import view as check_view


def read(p): return json.loads(Path(p).read_text())
def write(p, value): Path(p).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def package(raw, config_path, metadata_path, scene, run_id, geometry_run, source_files, *, retain=False, input_artifacts=()):
    storage=Storage.load(); raw=Path(raw).resolve(); config_path=Path(config_path).resolve()
    config=read(config_path); meta=read(metadata_path)
    if not meta.get('complete'): raise ValueError('Solver result must be explicitly complete')
    times=read(raw/'sample_times_s.json'); heights=read(raw/'sample_heights.json')
    # Metadata may preserve requested heights alongside actual sampling centers.
    if isinstance(times,dict): times=times['times_s']
    if isinstance(heights,dict): heights=heights['actual_heights_m']
    values=np.load(raw/'velocity_samples.npy',mmap_mode='r'); mask=np.load(raw/'sample_invalid.npy',mmap_mode='r')
    if values.ndim!=5 or values.shape[1]!=3 or values.shape[0]!=len(times) or values.shape[2]!=len(heights): raise ValueError('Recorded field dimensions differ from times/heights')
    if mask.shape!=values.shape[2:] or not np.isin(mask,[0,1]).all(): raise ValueError('Invalid mask mismatch')
    if not np.isfinite(times).all() or any(b<=a for a,b in zip(times,times[1:])): raise ValueError('Times must be finite and strictly increasing')
    if not np.isfinite(values).all(): raise ValueError('Nonfinite solver velocity')
    origin=meta['origin_enu_m']; cell=float(meta['cell_m'])
    # A scene may be smaller than the computational padding. Select exact cells,
    # keeping full solver records in provenance rather than displaying fake context.
    display_bounds=config.get('scene_bounds_xy_m')
    if display_bounds:
        x0,y0,x1,y1=display_bounds
        indices=[(x0-origin[0])/cell,(y0-origin[1])/cell,(x1-origin[0])/cell,(y1-origin[1])/cell]
        if any(abs(v-round(v))>1e-8 for v in indices): raise ValueError('Display bounds must align with recorded cell edges')
        ix0,iy0,ix1,iy1=map(round,indices)
        if not (0<=ix0<ix1<=values.shape[-1] and 0<=iy0<iy1<=values.shape[-2]): raise ValueError('Display crop outside recorded domain')
        values=values[...,iy0:iy1,ix0:ix1];mask=mask[...,iy0:iy1,ix0:ix1]
        origin=[x0,y0,origin[2]]
    if not np.isfinite(heights).all() or any(abs((z-origin[2])/cell-.5-round((z-origin[2])/cell-.5))>1e-6 for z in heights): raise ValueError('Sample heights are not actual grid centers')
    project=read(storage.metadata(scene)/'project.json'); geometry=storage.run(scene,geometry_run)
    gm=read(geometry/'manifest.json'); assert gm['spatial']['origin']==project['spatial']['origin']
    out=storage.scratch(scene,'wind_protocol',run_id); out.mkdir(parents=True,exist_ok=False); (out/'data').mkdir(); (out/'provenance').mkdir()
    layers=[]
    for i,z in enumerate(heights):
        label=str(z).replace('.','_'); lid='wind_z'+label+'m'; asset=f'data/{lid}.npy'; invalid=f'data/{lid}_invalid.npy'
        np.save(out/asset,np.ascontiguousarray(values[:,:,i],dtype='<f4')); np.save(out/invalid,np.asarray(mask[i],dtype='u1'))
        speed=np.linalg.norm(values[:,:,i],axis=1)[:,~mask[i].astype(bool)]; speed_range=[0.0,float(speed.max())] if speed.size else [0.0,1.0]
        layers.append({'id':lid,'kind':'vector_field','format':'npy','asset':asset,'sampling':'step','field':{'name':f'Velocity at {z:g} m','unit':'m/s'},'encoding':{'coordinate_frame':'ENU','dtype':'<f4','shape':list(values[:,:,i].shape),'axes':'TCYX','origin_m':[origin[0],origin[1],z],'spacing_m':[cell,cell],'sample_location':'cell_center','byte_order':'little','compression':'none','mask_asset':invalid,'mask_dtype':'|u1','mask_semantics':'invalid_nonzero'},'display':{'widget':'vector_field','capabilities':['pick','legend','opacity'],'range':speed_range}})
    artifacts=[]
    for p in sorted(raw.iterdir()):
        if not p.is_file(): continue
        dst=out/'provenance'/p.name; shutil.copy2(p,dst)
        artifacts.append({'id':'raw_'+p.name.replace('.','_').replace('-','_'),'asset':str(dst.relative_to(out)),'sha256':sha(dst),'media_type':'application/octet-stream'})
    for index,p in enumerate(map(Path,input_artifacts)):
        dst=out/'provenance'/f'input_{index}_{p.name}'; shutil.copy2(p,dst)
        artifacts.append({'id':f'input_{index}','asset':str(dst.relative_to(out)),'sha256':sha(dst),'media_type':'application/octet-stream'})
    shutil.copy2(config_path,out/'provenance/config.json')
    artifacts.append({'id':'configuration','asset':'provenance/config.json','sha256':sha(config_path),'media_type':'application/json'})
    files=sorted({Path(__file__).resolve(),config_path,*[Path(p).resolve()for p in source_files]})
    with zipfile.ZipFile(out/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED)as archive:
        for p in files:
            try: name=str(p.relative_to(storage.root))
            except ValueError: name='external/'+p.name
            archive.write(p,name)
    artifacts.append({'id':'source_snapshot','asset':'source_snapshot.zip','sha256':sha(out/'source_snapshot.zip'),'media_type':'application/zip'})
    spatial=dict(project['spatial']); spatial['bounds_m']={'min':origin,'max':[origin[0]+values.shape[-1]*cell,origin[1]+values.shape[-2]*cell,origin[2]+meta['shape_zyx'][0]*cell]}
    limits=['Solid occupancy combines closed-component ray interiors, bounded six-axis enclosure recovery for diagnosed split surfaces, and owner-local triangle/cell surface intersection with enclosed-air fill; this is a conservative coarse representation, not a repaired source mesh.', 'Transient coarse-grid wind experiment; no RANS turbulence or steady-state validation.','Estimated building/roof geometry, flat unsurveyed terrain; not a measured local forecast.',f'{cell:g} m cells do not resolve window, entrance or small roof-unit flow.','Only recorded snapshots are exposed; step sampling does not invent intermediate flow states.']
    limits=meta.get('limitations',limits)
    manifest={'schema_version':'1.1.0','scene_id':scene,'simulation':'urban_flow','run_id':run_id,'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),'provenance':{'code_revision':'source-snapshot','dirty':True,'parameters':{'config':config,'solver_metadata':meta,'limitations':limits},'inputs':[{'id':'geometry_manifest','sha256':sha(geometry/'manifest.json')},{'id':'recorded_velocity','sha256':sha(raw/'velocity_samples.npy')},{'id':'configuration','sha256':sha(config_path)}]},'spatial':spatial,'time':{'unit':'s','samples':times},'layers':layers,'artifacts':artifacts}
    write(out/'manifest.json',manifest); validate(out/'manifest.json')
    if retain:
        view_path=storage.metadata(scene)/'views'/f'{run_id.lower()}.json'
        if view_path.exists():raise FileExistsError(view_path)
        promote(storage,out)
        view={'schema_version':'1.1.0','scene_id':scene,'title':'Canary Wharf · recorded coarse wind experiment','time_alignment':'relative','runs':[geometry_run,run_id],'layers':[{'run_id':geometry_run,'layer_id':'geometry','visible':True}]+[{'run_id':run_id,'layer_id':l['id'],'visible':i==1}for i,l in enumerate(layers)],'camera':{'position':[850,-1050,900],'target':[0,0,35]}}
        write(view_path,view); check_view(storage,scene,run_id.lower()); refresh_catalog(storage)
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--config',required=True);p.add_argument('--metadata',required=True);p.add_argument('--scene',required=True);p.add_argument('--run-id',required=True);p.add_argument('--geometry-run',required=True);p.add_argument('--source',action='append',default=[]);p.add_argument('--input-artifact',action='append',default=[]);p.add_argument('--retain',action='store_true');a=p.parse_args()
    print(package(a.raw,a.config,a.metadata,a.scene,a.run_id,a.geometry_run,a.source,retain=a.retain,input_artifacts=a.input_artifact))
if __name__=='__main__':main()
