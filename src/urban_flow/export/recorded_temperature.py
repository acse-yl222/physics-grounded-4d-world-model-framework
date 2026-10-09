"""Retain recorded thermal fields with original solid masks and surface heights."""
from pathlib import Path
import argparse,json,shutil,zipfile,hashlib
from datetime import datetime,timezone
import numpy as np
from common.storage import Storage
from common.contract import validate
from common.runs import promote

def main():
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('--run-id',required=True);p.add_argument('--scene',default='tower_hamlets');p.add_argument('--retain',action='store_true');a=p.parse_args();st=Storage.load();raw=a.raw;read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=read(raw/'metadata.json');assert m['complete'];times=read(raw/'times_s.json');air=np.load(raw/'air_temperature.npy');invalid=np.load(raw/'air_invalid.npy');surface=np.load(raw/'surface_temperature.npy');height=np.load(raw/'inputs.npz')['height'];assert air.shape==(len(times),len(m['actual_heights_m']),*m['shape_yx']);assert invalid.shape==air.shape[1:];assert surface.shape==(len(times),*m['shape_yx']);assert np.isfinite(air).all()and np.isfinite(surface).all();assert all(y>x for x,y in zip(times,times[1:]));O=st.scratch(a.scene,'thermal_protocol',a.run_id);O.mkdir(parents=True,exist_ok=False);(O/'data').mkdir();(O/'provenance').mkdir();layers=[]
 for i,z in enumerate(m['actual_heights_m']):
  lid=f'air_temperature_{int(z)}m';asset=f'data/{lid}.npy';mask=f'data/{lid}_invalid.npy';np.save(O/asset,np.asarray(air[:,i],dtype='<f4'));np.save(O/mask,np.asarray(invalid[i],dtype='u1'));valid=air[:,i][:,~invalid[i].astype(bool)];layers.append({'id':lid,'kind':'scalar_field','format':'npy','asset':asset,'sampling':'step','field':{'name':f'Air temperature {z:g} m','unit':'degC'},'encoding':{'coordinate_frame':'ENU','dtype':'<f4','shape':list(air[:,i].shape),'axes':'TYX','origin_m':[*m['origin_xy_m'],z],'spacing_m':[m['cell_m']]*2,'sample_location':'cell_center','byte_order':'little','compression':'none','mask_asset':mask,'mask_dtype':'|u1','mask_semantics':'invalid_nonzero'},'display':{'widget':'scalar_field','capabilities':['pick','legend','opacity'],'range':[float(valid.min()),float(valid.max())]}})
 np.save(O/'data/surface.npy',np.asarray(surface,dtype='<f4'));np.save(O/'data/surface_height.npy',np.asarray(height,dtype='<f4'));layers.append({'id':'surface_temperature','kind':'scalar_field','format':'npy','asset':'data/surface.npy','sampling':'step','field':{'name':'Topographic surface temperature','unit':'degC'},'encoding':{'coordinate_frame':'ENU','dtype':'<f4','shape':list(surface.shape),'axes':'TYX','origin_m':[*m['origin_xy_m'],.3],'spacing_m':[m['cell_m']]*2,'sample_location':'cell_center','byte_order':'little','compression':'none','height_asset':'data/surface_height.npy','height_dtype':'<f4'},'display':{'widget':'scalar_field','capabilities':['pick','legend','opacity'],'range':[float(surface.min()),float(surface.max())]}})
 artifacts=[]
 for f in raw.iterdir():
  if f.is_file():
   target=O/'provenance'/f.name;shutil.copy2(f,target);artifacts.append({'id':f.name,'asset':str(target.relative_to(O)),'sha256':sha(target),'media_type':'application/octet-stream'})
 sources=[Path(x)for x in read(raw/'runtime_identity.json')['source_hashes']];sources+=[Path(__file__).resolve(),raw/'config.json']
 with zipfile.ZipFile(O/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED)as z:
  for f in sources:
   if not f.is_absolute():f=st.root/f
   z.write(f,str(f.relative_to(st.root)))
 artifacts.append({'id':'source_snapshot','asset':'source_snapshot.zip','sha256':sha(O/'source_snapshot.zip'),'media_type':'application/zip'});spatial=read(st.metadata(a.scene)/'project.json')['spatial'];spatial['bounds_m']=m['spatial']['bounds_m'];manifest={'schema_version':'1.1.0','scene_id':a.scene,'simulation':'urban_flow','run_id':a.run_id,'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),'provenance':{'code_revision':'source-snapshot','dirty':True,'parameters':{'config':read(raw/'config.json'),'metadata':m,'limits':m['limits'],'surface_display_offset_m':.3},'inputs':[{'id':f.name,'sha256':sha(f)}for f in [raw/'inputs.npz',raw/'air_temperature.npy',raw/'input_provenance.json']]},'spatial':spatial,'time':{'unit':'s','samples':times,'epoch':m['epoch_utc']},'layers':layers,'artifacts':artifacts};(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');validate(O/'manifest.json');print(promote(st,O)if a.retain else O)
if __name__=='__main__':main()
