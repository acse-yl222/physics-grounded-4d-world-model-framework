"""True-grid SCALED inference with explicit interpreted (not calibrated) time.
Does not resample geometry or vector fields. Reuses existing model kernels.
"""
import argparse,hashlib,json,os,shutil,sys,time,zipfile,importlib.metadata
from pathlib import Path
import numpy as np

def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True,type=Path);ap.add_argument('--pilot-only',action='store_true');a=ap.parse_args();c=json.load(open(a.config));repo=Path(c['scaled_repository']);sys.path.insert(0,str(repo));sys.path.insert(0,str(Path(__file__).resolve().parents[2]));import torch
 from urban_flow.physics.wind import scaled_latent as k
 k.SCALED_REPO=repo
 out=Path(c['output']);out.mkdir(parents=True,exist_ok=True);source=Path(c['geometry']);gm=json.load(open(source.parent/'metadata.json'));solid=np.load(source).astype(bool);assert list(solid.shape)==c['shape_zyx'];assert gm.get('spacing_xyz_m',[gm.get('cell_m')]*3)==[4,4,4];origin=c['origin_enu_m'];assert list(gm.get('source_region_origin_xyz_m',gm.get('origin_xyz_m')))==origin
 original_hash=sha(source);solid[0]=True;np.save(out/'solid_inference.npy',solid);heights=c['sample_heights_m'];indices=[int(round((h-origin[2])/4-.5))for h in heights];assert all(abs(origin[2]+(i+.5)*4-h)<1e-8 and i>0 for i,h in zip(indices,heights));np.save(out/'sample_invalid.npy',solid[indices].astype('u1'));write(out/'sample_heights.json',heights);write(out/'sample_model_steps.json',c['decode_steps']);write(out/'sample_times_s.json',[step*c['interpreted_seconds_per_model_step']for step in c['decode_steps']]);shutil.copy2(a.config,out/'config.json');shutil.copy2(source.parent/'metadata.json',out/'geometry_metadata.json')
 weights={name:{'path':str(repo/'weight'/name),'sha256':sha(repo/'weight'/name)}for name in ['compression.pth','inference.pth']};write(out/'weights.json',weights)
 (out/'weights').mkdir(exist_ok=True)
 for name in weights:
  dst=out/name
  if not dst.exists():shutil.copy2(repo/'weight'/name,dst)
 with zipfile.ZipFile(out/'scaled_source_snapshot.zip','w',zipfile.ZIP_DEFLATED)as archive:
  for f in (repo/'scaled').rglob('*.py'):archive.write(f,'scaled/'+str(f.relative_to(repo/'scaled')))
  archive.write(repo/'LICENSE','SCALED-LICENSE');archive.write(__file__,'scaled_scene027.py');archive.write(k.__file__,'scaled_latent.py');archive.write(a.config,'config.json')
 torch.manual_seed(c['seed']);torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats();started=time.time();enc,net=k.load_models();log=[]
 def note(phase,seconds,**kw):
  row={'phase':phase,'seconds':seconds,'gpu_peak_allocated_gib':torch.cuda.max_memory_allocated()/1024**3,**kw};log.append(row);write(out/'timing.json',log);print(json.dumps(row),flush=True)
 t=time.time()
 if (out/'latent_initial.pt').exists()and(out/'geometry_identity.json').exists():
  assert json.load(open(out/'geometry_identity.json'))['source_sha256']==original_hash
  latent=torch.load(out/'latent_initial.pt',weights_only=True);geo=torch.load(out/'latent_geometry.pt',weights_only=True)
 else:
  l0,lbg=k.encode_domain(solid,enc);latent,geo=l0/10,lbg/10;torch.save(latent,out/'latent_initial.pt');torch.save(geo,out/'latent_geometry.pt');write(out/'geometry_identity.json',{'source_sha256':original_hash,'forced_ground_layer_index':0,'forced_ground_cell_center_m':-2})
 note('encode',time.time()-t)
 samples=np.lib.format.open_memmap(out/'velocity_samples.npy',mode='w+',dtype=np.float32,shape=(len(c['decode_steps']),3,len(indices),*solid.shape[1:]));metrics=[]
 for step in range(1,c['model_steps']+1):
  t=time.time();latent=k.latent_step(latent,geo,net);assert torch.isfinite(latent).all();note('latent_step',time.time()-t,step=step)
  if step==1 and a.pilot_only:
   write(out/'pilot.json',{'complete':True,'step_seconds':log[-1]['seconds'],'gpu_peak_gib':torch.cuda.max_memory_allocated()/1024**3,'estimated_100_step_seconds':log[-1]['seconds']*100});return
  if step in c['decode_steps']:
   t=time.time();uvw=k.decode_domain(latent,enc);uvw*=3.;uvw[0]*=-1.;uvw[:,solid]=0;assert np.isfinite(uvw).all();samples[c['decode_steps'].index(step)]=uvw[:,indices];samples.flush();fluid=~solid;speed=np.linalg.norm(uvw[:,indices],axis=0);valid=~solid[indices];metrics.append({'model_step':step,'valid_speed_mean_m_s':float(speed[valid].mean()),'valid_speed_max_m_s':float(speed[valid].max()),'invalid_zero_exact':bool(np.all(uvw[:,solid]==0))});note('decode',time.time()-t,step=step)
   if step==c['model_steps']:np.save(out/'velocity_final_enu.npy',uvw);torch.save(latent,out/'latent_final.pt')
   del uvw
 del samples
 meta={'complete':True,'solver':'SCALED pretrained geometry-conditioned latent surrogate','cell_m':4,'shape_zyx':list(solid.shape),'origin_enu_m':origin,'sample_model_steps':c['decode_steps'],'model_steps':c['model_steps'],'time_semantics':'Interpreted surrogate time,100s/modelstep; not calibrated physical time','interpreted_seconds_per_model_step':c['interpreted_seconds_per_model_step'],'sample_heights_m':heights,'ground_semantics':'Index0 cellcenter−2m forcedsolid below flatlocalz0; index1center2m firstvalidfluid awayfrombuildings. Verticaldomain shift explicitly changes modelgeometry alignment, notcalibration.','axes':'VelocityENU=(−raw_model_u,raw_model_v,raw_model_w) after ×3 scaling; negation applied once','source_geometry_sha256':original_hash,'inference_solid_sha256':sha(out/'solid_inference.npy'),'weights':weights,'metrics':metrics,'seconds_total':time.time()-started,'runtime_versions':{name:importlib.metadata.version(name)for name in ['torch','numpy','diffusers','accelerate']},'peak_gpu_gib':torch.cuda.max_memory_allocated()/1024**3,'limitations':c['limitations']};write(out/'metadata.json',meta)
 snapshot=out/'source_snapshot';snapshot.mkdir(exist_ok=True);shutil.copy2(__file__,snapshot/Path(__file__).name);shutil.copy2(Path(k.__file__),snapshot/'scaled_latent.py');print(json.dumps(meta),flush=True)
if __name__=='__main__':main()
