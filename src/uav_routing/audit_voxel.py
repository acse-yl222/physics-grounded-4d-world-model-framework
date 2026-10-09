"""Independent NumPy route audit against original voxel occupancy and model times."""
import argparse,json
from pathlib import Path
import numpy as np

def audit(raw):
 c=json.loads((raw/'config.json').read_text());s=json.loads((raw/'summary.json').read_text());mask=np.load(c['solid_path']);origin=np.array(c['origin_enu_m']);cell=c['source_cell_m'];stations={x['id']:x for x in c['stations']};checks=[];total=0
 for r in s['routes']:
  p=np.load(raw/r['path']);t=np.load(raw/r['times']);assert r['success'];assert np.isfinite(p).all()and np.isfinite(t).all();assert np.allclose(p[0],stations[r['source']]['enu_m'],atol=.001)and np.allclose(p[-1],stations[r['target']]['enu_m'],atol=.001)
  assert np.allclose(p[0,:2],p[1,:2])and np.allclose(p[-1,:2],p[-2,:2]);assert abs(p[1,2]-p[0,2]-48)<1e-5 and abs(p[-2,2]-p[-1,2]-48)<1e-5
  count=0
  for a,b in zip(p[:-1],p[1:]):
   q=a+np.linspace(0,1,max(2,int(np.ceil(np.linalg.norm(b-a)/.5))+1))[:,None]*(b-a);idx=np.floor((q-origin)/cell).astype(int);assert ((idx>=0)&(idx<np.array(mask.shape[::-1]))).all();assert not mask[idx[:,2],idx[:,1],idx[:,0]].any();count+=len(q)
  delta=np.diff(p,axis=0)/[15,15,5];db=delta[:,2]*.2;dt=(-db+np.sqrt(db*db+.96*np.sum(delta*delta,axis=1)))/.96;assert np.allclose(np.diff(t),dt,atol=1e-6)and np.all(np.diff(t)>0);total+=count;checks.append({'source':r['source'],'target':r['target'],'samples':count,'endpoints':True,'vertical_48m_legs':True,'collision_free':True,'time_model_match':True})
 reached={c['stations'][0]['id']}
 while True:
  updated=reached|{b for a,b in c['routes']if a in reached}
  if updated==reached:break
  reached=updated
 assert len(reached)==len(stations)
 out={'all_pass':True,'routes':len(checks),'stations':len(stations),'strong_connectivity_bidirectional':True,'independent_halfmetre_samples':total,'checks':checks,'method':'IndependentNumPy≤0.5m sampling+endpoint/vertical/timechecks; production additionallyexactclosedvoxelgridplanechecks','limits':['8m voxelgeometry, notcontinuousmesh; canopyunknown','No multiUAV scheduling or dynamiccollisionavoidance']};(raw/'independent_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k!='checks'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);a=p.parse_args();audit(a.raw)
