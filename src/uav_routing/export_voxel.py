"""Package actual voxel WavePDE routes with the established UAV preview adapter."""
import argparse,datetime,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main(raw,run,solver):
 run.mkdir(parents=True,exist_ok=False);summary=json.loads((raw/'summary.json').read_text());config=json.loads((raw/'config.json').read_text());assert summary['successes']==summary['total'];shutil.copytree(raw,run/'raw');preview=run/'uav_visualization';preview.mkdir();rows=[];records=[];positions=[];triangles=[];offset=0
 for r in summary['routes']:
  if not config.get('preview_all_routes',False) and 'S1' not in [r['source'],r['target']]:continue
  p=np.load(raw/r['path']);t=np.load(raw/r['times']);assert np.all(np.diff(t)>0)
  records.append(np.c_[p[:,0],p[:,2],-p[:,1],t].astype('<f4'));rows.append({'from_station':r['source'],'to_station':r['target'],'offset_records':offset,'count':len(p),'duration_s':float(t[-1])});offset+=len(p)
  for a,b in zip(p[:-1],p[1:]):
   d=b-a;n=np.cross(d,[0,0,1]);n=np.array([1,0,0])if np.linalg.norm(n)<1e-8 else n/np.linalg.norm(n);base=len(positions);positions.extend([list(a-n*.7),list(a+n*.7),list(b-n*.7),list(b+n*.7)]);triangles.extend([[base,base+1,base+2],[base+1,base+3,base+2]])
 np.concatenate(records).tofile(preview/'routes.f32');stations=[{'station_id':s['id'],'id':i+1,'label':s['id'],'role':'hub'if i==0 else'dropoff','name':'Model ground site '+s['id'],'x_m':s['enu_m'][0],'y_m':s['enu_m'][2],'z_m':-s['enu_m'][1]}for i,s in enumerate(config['stations'])]
 write(preview/'routes.json',{'schema_version':'wavepde-uav-preview-1','source_run':run.name,'coordinate_frame':'world-y-up','record':['east_m','up_m','south_m','elapsed_s'],'dtype':'<f4','binary':'routes.f32','sha256':sha(preview/'routes.f32'),'stations':stations,'routes':rows,'mode':'independent_random_routes','seed':config.get('seed',20261008),'uav_count':config.get('uav_count',60),'duration_s':600,'limitations':summary['limitations'],'ascent_m':48})
 write(run/'routes_mesh.json',{'positions':positions,'triangles':triangles});shutil.copy(config['solid_path'],run/'solid.npy')
 with zipfile.ZipFile(run/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in [Path(__file__),Path(__file__).with_name('voxel_routes.py'),Path(__file__).with_name('expand_sites.py'),Path(__file__).with_name('audit_voxel.py')]:z.write(p,'framework/'+str(p))
  for p in solver.rglob('*.py'):z.write(p,'wavepde/'+str(p.relative_to(solver)))
  z.write(raw/'config.json','config.json')
 project=json.loads(Path('project/tower_hamlets/project.json').read_text());art=[]
 for p in run.rglob('*'):
  if p.is_file():art.append({'id':'source_snapshot' if p.name=='source_snapshot.zip' else str(p.relative_to(run)).replace('/','_').replace('.','_'),'asset':str(p.relative_to(run)),'sha256':sha(p),'media_type':'application/octet-stream'})
 m={'schema_version':'1.1.0','scene_id':'tower_hamlets','simulation':'wavepde','run_id':run.name,'status':'complete','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'provenance':{'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'dirty':True,'parameters':config,'inputs':[{'id':'native8m_solid','sha256':sha(run/'solid.npy')}]},'spatial':project['spatial'],'time':{'unit':'s','samples':[]},'layers':[{'id':'delivery_routes','kind':'mesh','format':'json','asset':'routes_mesh.json','sampling':'static','display':{'widget':'mesh','capabilities':['opacity','pick']}}],'artifacts':art}
 write(run/'manifest.json',m)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--raw',type=Path,required=True);a.add_argument('--run',type=Path,required=True);a.add_argument('--solver',type=Path,required=True);x=a.parse_args();main(x.raw,x.run,x.solver)
