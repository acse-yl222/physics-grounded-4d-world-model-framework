"""Protocolpackage surface027 recordedscalar fields, withoutdefault/view changes."""
import argparse,json,hashlib,shutil,zipfile,datetime
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def package(raw,out,terrain,geometry,config=None,physical_tests=None):
 out.mkdir(parents=True,exist_ok=False);shutil.copytree(raw,out/'raw');meta=json.loads((raw/'metadata.json').read_text());assert meta['complete'];values=np.load(raw/'values.npy',mmap_mode='r');lid=meta['kind'];sources=[Path(__file__),Path(__file__).with_name('canary_surface.py'),Path(__file__).with_name('canary_surface_prepare.py'),Path('src/urban_flow/physics/solar/model.py'),Path('src/urban_flow/physics/flood/model.py'),Path(config) if config else Path('project/tower_hamlets/configs/surface027.json')]
 with zipfile.ZipFile(out/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in sources:z.write(p,str(p))
 shutil.copytree(terrain,out/'terrain_inputs');(out/'geometry_inputs').mkdir()
 for name in ['height_m.npy','near_ground_building_mask.npy','building_footprint.npy','metadata.json']:
  p=geometry/name
  if p.exists():shutil.copy(p,out/'geometry_inputs'/name)
 shutil.copy(physical_tests or 'cache/tower_hamlets/surface027/physical_tests.json',out/'physical_tests.json');art=[]
 for p in out.rglob('*'):
  if p.is_file():art.append({'id':'source_snapshot'if p.name=='source_snapshot.zip'else str(p.relative_to(out)).replace('/','_').replace('.','_'),'asset':str(p.relative_to(out)),'sha256':sha(p),'media_type':'application/octet-stream'})
 layer={'id':lid,'kind':'scalar_field','format':'npy','asset':'raw/values.npy','sampling':'step','field':{'name':lid+' · controlled scenario','unit':meta['unit']},'encoding':{'coordinate_frame':'ENU','dtype':'<f4','shape':list(values.shape),'axes':'TYX','origin_m':[-2000,-2000,.2],'spacing_m':[4,4],'sample_location':'cell_center','byte_order':'little','compression':'none','mask_asset':'raw/invalid.npy','mask_dtype':'|u1','mask_semantics':'invalid_nonzero'},'display':{'widget':'scalar_field','capabilities':['opacity','pick','legend'],'range':[0,float(values.max())]}}
 layers=[layer]
 if lid=='sunlight':
  import copy
  shadow=copy.deepcopy(layer);shadow.update(id='shadow',asset='raw/shadow.npy',field={'name':'Geometry shadow · controlled clear sky','unit':'1'});shadow['display']['range']=[0,1];layers.append(shadow)
 project=json.loads(Path('project/tower_hamlets/project.json').read_text());m={'schema_version':'1.1.0','scene_id':'tower_hamlets','simulation':'urban_flow','run_id':out.name,'status':'complete','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'provenance':{'code_revision':'source_snapshot','dirty':True,'parameters':meta,'inputs':[{'id':'recorded_surface','sha256':sha(raw/'values.npy')}]},'spatial':project['spatial'],'time':{'unit':'s','samples':json.loads((raw/'times.json').read_text()),**({'epoch':meta['epoch']}if meta.get('epoch')else{})},'layers':layers,'artifacts':art};(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--terrain',type=Path,required=True);p.add_argument('--geometry',type=Path,required=True);p.add_argument('--config',type=Path);p.add_argument('--physical-tests',type=Path);a=p.parse_args();package(a.raw,a.output,a.terrain,a.geometry,a.config,a.physical_tests)
