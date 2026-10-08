"""4.096 km SCALED/physical-thermal agent transfer pilot, 4 m grid.

Fresh geometry-conditioned wind rollouts; no reuse of old winds after edits.
Not a calibrated urban-planning benchmark or a converged CFD calculation.
"""
import argparse
import copy
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tarfile
import time
from types import SimpleNamespace
import uuid

import numpy as np

from common.storage import Storage
from common.provenance import snapshot_sources
from .problem import write_json
from .rsi.provider import ClaudeCodeProvider

BASE = {'height_steps': [0]*16, 'cool_blocks': []}
SCHEMA = {'type':'object','additionalProperties':False,'required':['action','plan','reason'], 'properties':{
 'action':{'type':'string','enum':['evaluate','submit']},'reason':{'type':'string','maxLength':1800},
 'plan':{'type':'object','additionalProperties':False,'required':['height_steps','cool_blocks'],'properties':{
 'height_steps':{'type':'array','minItems':16,'maxItems':16,'items':{'type':'integer','enum':[-1,0,1]}},
 'cool_blocks':{'type':'array','maxItems':3,'uniqueItems':True,'items':{'type':'integer','minimum':0,'maximum':15}}}}}}

def read(p): return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(8<<20),b''):h.update(block)
 return h.hexdigest()
def key(p):return json.dumps(dict(height_steps=p['height_steps'],cool_blocks=sorted(p['cool_blocks'])),sort_keys=True)
def height(solid):
 a=solid.copy();a[0]=False
 return np.max(np.where(a,(np.arange(a.shape[0])+1)[:,None,None]*4,0),axis=0).astype('f4')
def block_map(shape):
 y,x=np.indices(shape);valid=(y>=400)&(y<656)&(x>=400)&(x<656)
 return np.where(valid,((y-400)//64)*4+(x-400)//64,-1)
def edited(original,plan,blocks):
 out=original.copy();roof=height(original)
 for i,step in enumerate(plan['height_steps']):
  if not step:continue
  mask=(blocks==i)&(roof>0);new=np.maximum(8,roof[mask]+4*step)
  out[:,mask]=(np.arange(out.shape[0])[:,None]+.5)*4<new[None]
 out[0]=True
 return out

def prepare(config):
 cfg=read(config);s=Storage.load();rid='large_domain_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
 root=s.scratch('south_ken','large_domain',rid);root.mkdir(parents=True)
 shutil.copy2(config,root/'config.json')
 legacy=Path(read(s.root/'sources.local.json')['legacy_output'])/'core008/physics/scaled_latent_1024'
 source=legacy/'wind/solid_4m_full_zyx.npy';shutil.copy2(source,root/'original_solid.npy')
 shutil.copy2(legacy/'geometry_mapping.json',root/'geometry_mapping.json')
 model=Path(cfg['scaled_repo']);(root/'models/weight').mkdir(parents=True)
 for name in ('compression.pth','inference.pth'):shutil.copy2(model/'weight'/name,root/'models/weight'/name)
 shutil.copytree(model/'scaled',root/'models/scaled',ignore=shutil.ignore_patterns('__pycache__'))
 revision=snapshot_sources(s.root,root/'source_snapshot.tar.gz')
 files=[p for p in (root/'models').rglob('*') if p.is_file()]+[root/'original_solid.npy',root/'config.json',root/'geometry_mapping.json']
 write_json(root/'identity.json',{'code_revision':revision,'files':{str(p.relative_to(root)):sha(p) for p in files},'source_solid_sha256':sha(source),'code':{str(p.relative_to(s.root)):sha(p) for folder in ('src/urban_planning','src/urban_flow/physics','src/common/pipeline') for p in (s.root/folder).rglob('*.py')}})
 write_json(root/'state.json',{'run_id':rid,'status':'prepared'})
 return root

def verify(root):
 identity=read(root/'identity.json');s=Storage.load()
 assert all(sha(root/p)==v for p,v in identity['files'].items()),'Frozen input modified'
 assert all(sha(s.root/p)==v for p,v in identity['code'].items()),'Code modified'

class Problem:
 def __init__(self,root):
  self.root=root;self.cfg=read(root/'config.json');self.solid=np.load(root/'original_solid.npy');assert self.solid.shape==(64,1024,1024)
  self.roof=height(self.solid);self.blocks=block_map(self.roof.shape)
  y,x=np.indices(self.roof.shape);xx=-2116+(x+.5)*4;yy=-2124+(y+.5)*4
  # Restrict scoring to preserved legacy coverage, inset 64 m; padding is not observed city.
  self.receptor=(self.roof==0)&(xx>=-1572)&(xx<1372)&(yy>=-1420)&(yy<1268)
  self.baseline=None;self.cache={}
 def validate(self,plan):
  import jsonschema
  jsonschema.validate(plan,SCHEMA['properties']['plan'])
  cost=sum(abs(v) for v in plan['height_steps'])+len(plan['cool_blocks'])
  if cost>5 or np.count_nonzero(plan['height_steps'])>2:return ['At most two height-edit blocks; total edit cost <=5']
  h=height(edited(self.solid,plan,self.blocks));m=self.blocks>=0;ratio=float(h[m].sum()/self.roof[m].sum())
  return [] if .95<=ratio<=1.05 else ['Local building-volume proxy outside 95-105%']
 def simulate(self,plan):
  import torch
  from urban_flow.physics.wind import scaled_latent as kernel
  from urban_flow.physics.solar.model import ShadowNet,clear_sky
  from common.pipeline.scene_temperature_physical import load_solver,fields_and_boundary
  from urban_flow.physics.diurnal_solver import solve_from_state
  k=key(plan)
  if k in self.cache:return self.cache[k]
  identity=hashlib.sha256(k.encode()).hexdigest()[:12];dest=self.root/'simulations'/identity;dest.mkdir(parents=True)
  started=time.perf_counter();solid=edited(self.solid,plan,self.blocks);roof=height(solid)
  kernel.SCALED_REPO=self.root/'models';torch.set_num_threads(4);torch.manual_seed(0)
  kernel.device=torch.device('cuda');torch.backends.cudnn.benchmark=True
  print('ENCODE',identity,flush=True);enc,net=kernel.load_models()
  lat0,latgeo=kernel.encode_domain(solid,enc);state=lat0/10;latgeo=latgeo/10;del lat0
  diagnostics=[]
  for step in range(self.cfg['wind_steps']):
   nxt=kernel.latent_step(state,latgeo,net)
   if not torch.isfinite(nxt).all():raise ValueError('Nonfinite wind latent')
   if step%20==0 or step==self.cfg['wind_steps']-1:
    diagnostics.append({'step':step+1,'relative_latent_change':float(torch.linalg.vector_norm(nxt-state)/torch.linalg.vector_norm(nxt).clamp_min(1e-8))})
    print('WIND',identity,step+1,flush=True)
   state=nxt
  uvw=kernel.decode_domain(state,enc)*3*(~solid)[None]
  # SCALED raw u is positive toward decreasing x; convert once to ENU.
  uvw[0]*=-1
  if not np.isfinite(uvw).all():raise ValueError('Nonfinite decoded wind')
  wind_seconds=time.perf_counter()-started
  del enc,net,state,latgeo,nxt;gc.collect();torch.cuda.empty_cache()
  # Wind backend forces a numerical ground plane at z-index 0. Remove this plane
  # for open-ground thermal exchange, keeping actual building columns occupied.
  thermal_solid=solid[:16].copy();thermal_solid[0]=roof>0
  wind=uvw[:,:16].copy()
  wind*=~thermal_solid[None]
  with torch.inference_mode():shadow=ShadowNet(roof,4,'cuda')(60,180).cpu().numpy()
  dni,diffuse=clear_sky(60,6);irradiance=(~shadow)*dni*math.sin(math.radians(60))+diffuse
  albedo=np.full(roof.shape,.2,dtype='f4');albedo[np.isin(self.blocks,plan['cool_blocks'])&(roof==0)]=.6
  model,_=load_solver();ambient=30.
  excess=model.solve_surface_temperature_excess_c((1-albedo)*irradiance,np.full(roof.shape,.95),np.zeros(roof.shape),np.full(roof.shape,.3),np.full(roof.shape,12.),5.670374419e-8*(ambient+273.15)**4,ambient,0.)
  fields,boundary=fields_and_boundary(thermal_solid,wind[None],ambient,0.,.005)
  boundary['ground_surface_temperature_excess_c']=excess;boundary['roof_surface_temperature_excess_3d']=fields['roof_mask_3d']*excess[None]
  thermal=model.Temperature3DScenarioConfig(temperature_solver_device='cuda',ambient_temp_c=ambient,inflow_temp_c=ambient,frame_duration_s=self.cfg['thermal_duration_s'],diffusion_coeff_m2_s=1.)
  print('THERMAL',identity,flush=True)
  temperature,fluid,check=solve_from_state(model,fields,boundary,SimpleNamespace(model_resolution_m=4,height_scale_m=4),thermal,np.full(thermal_solid.shape,ambient,dtype='f4'))
  if not np.isfinite(temperature).all():raise ValueError('Nonfinite temperature')
  air=temperature[2];speed=np.linalg.norm(uvw[:,2],axis=0);m=self.receptor
  blocks=[]
  for i in range(16):
   q=m&(self.blocks==i);blocks.append({'id':i,'open_cells':int(q.sum()),'mean_c':float(air[q].mean()),'p95_c':float(np.quantile(air[q],.95)),'mean_speed_m_s':float(speed[q].mean())})
  result={'simulation_id':identity,'plan':plan,'p95_excess_c':float(np.quantile(air[m],.95)-ambient),'local_p95_excess_c':float(np.quantile(air[m&(self.blocks>=0)],.95)-ambient),'outside_mean_c':float(air[m&(self.blocks<0)].mean()),'blocks':blocks,'wind_seconds':wind_seconds,'total_seconds':time.perf_counter()-started,'latent_diagnostics':diagnostics,'thermal_check':check}
  np.savez_compressed(dest/'fields.npz',roof_m=roof,albedo=albedo,air_c=air,speed_m_s=speed,wind_enu=uvw[:,2],receptor_mask=m,blocks=self.blocks,shadow=shadow)
  if self.baseline is None:result.update(score=0.,feasible=True,max_block_warming_c=0.,outside_warming_c=0.)
  else:
   increase=max(b['mean_c']-a['mean_c'] for a,b in zip(self.baseline['blocks'],blocks));outside=result['outside_mean_c']-self.baseline['outside_mean_c']
   result.update(score=1-result['local_p95_excess_c']/self.baseline['local_p95_excess_c'],max_block_warming_c=increase,outside_warming_c=outside,feasible=increase<=1 and outside<=.1)
  write_json(dest/'result.json',result);self.cache[k]=result
  del uvw,wind,temperature,fields,boundary;gc.collect();torch.cuda.empty_cache()
  return result

def run(root):
 root=Path(root);verify(root);state=read(root/'state.json');assert state['status']=='prepared';state['status']='running';write_json(root/'state.json',state)
 sys.path.insert(0,str(root.resolve()/'models'))
 try:
  p=Problem(root);base=p.simulate(BASE);p.baseline=base
  provider=ClaudeCodeProvider('claude-opus-5-5',timeout=240);history=[base];used=0;chosen=None
  for step in range(5):
   prompt={'operation':'act','task':'4.096km full-domain SCALED wind plus physical thermal pilot. Maximize local p95 excess-temperature reduction in 1.024km editable window, no block mean warming >1C and outside mean warming >0.1C. One prescribed weather only; no robustness claim.',
    'geometry':'4m cells; block IDs 0..15 = row*4+col, rows south to north, columns west to east, 256m per block. Editable ENU bounds [-516,-524,508,500]. height_steps +/-1 = +/-4m on existing building columns, minimum8m. cool_blocks open-ground albedo .2->.6. Footprints fixed. Max2 height blocks, max3 material blocks, total edits<=5; editable-window building volume95-105%.',
    'rules':'Return evaluate or submit JSON. Submit only previously evaluated feasible plan. For this integration pilot first candidate must include a nonzero height edit to exercise geometry-conditioned wind recomputation. Remaining candidates may use only material edits. Baseline submission allowed. No file tools.',
    'remaining_evaluations':2-used,'remaining_steps':5-step,'history':history}
   with (root/'events.jsonl').open('a') as f:f.write(json.dumps({'kind':'request','prompt':prompt})+'\n')
   response=provider.complete(prompt,SCHEMA,16384)
   with (root/'events.jsonl').open('a') as f:f.write(json.dumps({'kind':'response','response':response})+'\n')
   if response['status']!='completed':raise RuntimeError('Model transport failure: '+str(response.get('subtype')))
   if list(response.get('model_usage',{}))!=['claude-opus-5-5']:raise RuntimeError('Model mismatch')
   action=provider.parse(response)
   import jsonschema;jsonschema.validate(action,SCHEMA)
   if action['action']=='submit':
    result=p.cache.get(key(action['plan']))
    if result and result['feasible']:chosen=result;break
    history.append({'error':'Submit an evaluated feasible plan'});continue
   if used>=2:history.append({'error':'Budget exhausted; submit'});continue
   used+=1;errors=p.validate(action['plan'])
   if used==1 and not any(action['plan']['height_steps']):errors.append('First candidate requires a geometry edit')
   result={'errors':errors,'plan':action['plan']} if errors else p.simulate(action['plan'])
   history.append({'action':action,'result':result});write_json(root/'online_history.json',history)
  write_json(root/'report.json',{'run_id':state['run_id'],'scope':p.cfg['scope'],'baseline':base,'selected':chosen,'submitted':chosen is not None,'evaluations_used':used,'history':history,'limits':['Single weather, one agent episode, two-query cap; no baseline optimizer comparison or held-out test.','4.096km padded computational domain; building support approximately2.85x2.59km.','SCALED surrogate transfer not independently validated; latent change is not CFD convergence.','Thermal transient300s, lower64m, sample10m; fixed wind, no buoyancy feedback.','Ground-plane removal for thermal exchange explicitly differs from wind numerical boundary.']})
  verify(root);state['status']='complete';write_json(root/'state.json',state)
 except Exception as e:
  state.update(status='failed',error=str(e));write_json(root/'state.json',state);raise
 print('COMPLETE',root,flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run']);ap.add_argument('path');a=ap.parse_args();print(globals()[a.action](a.path))
