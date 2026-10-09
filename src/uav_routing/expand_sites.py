"""Expand existing model ground stations using native-volume/water/road clearance."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt

def main(base,roads,water,output):
 c=json.loads(base.read_text());solid=np.load(c['solid_path']);wet=np.load(water);cell=c['source_cell_m'];origin=np.array(c['origin_enu_m']);clear=distance_transform_edt(~(solid.any(0)|wet))*cell;valid=clear>=40;valid[:30]=False;valid[-30:]=False;valid[:,:30]=False;valid[:,-30:]=False;yy,xx=np.nonzero(valid);xy=origin[:2]+np.c_[xx+.5,yy+.5]*cell
 starts=[];ends=[];width=[]
 for lane in json.loads(roads.read_text())['lanes']:
  p=np.array(lane['world_xyz'])[:,[0,2]];p[:,1]*=-1
  for a,b in zip(p[:-1],p[1:]):starts.append(a);ends.append(b);width.append(lane['width_m']/2)
 a=np.array(starts);v=np.array(ends)-a;vv=(v*v).sum(1).clip(.001);w=np.array(width)
 nearest=np.min(np.linalg.norm(xy[:,None]-np.array([s['enu_m'][:2]for s in c['stations']])[None],axis=2),axis=1)
 while len(c['stations'])<20:
  k=int(nearest.argmax());d=xy[k]-a;t=np.clip((d*v).sum(1)/vv,0,1);roadclear=float((np.linalg.norm(d-t[:,None]*v,axis=1)-w).min())
  if roadclear<20:nearest[k]=-1;continue
  idx=len(c['stations'])+1;p=xy[k];c['stations'].append({'id':f'S{idx}','enu_m':[float(p[0]),float(p[1]),.15],'gate_enu_m':[float(p[0]),float(p[1]),48.15],'building_water_clearance_m':float(clear[yy[k],xx[k]]),'mapped_passenger_lane_clearance_m':roadclear,'status':'model-derived flat ground; canopy unknown; not surveyed'})
  nearest=np.minimum(nearest,np.linalg.norm(xy-p,axis=1));nearest[k]=-1
 # Preserve five original hub spokes, connect each new node to an earlier node,
 # then add shortest missing undirected edges to reach50pairs=100directions.
 xy=np.array([s['enu_m'][:2]for s in c['stations']]);edges={(0,i)for i in range(1,6)}
 for i in range(6,20):edges.add(tuple(sorted((i,int(np.linalg.norm(xy[:i]-xy[i],axis=1).argmin())))))
 pairs=sorted((float(np.linalg.norm(xy[i]-xy[j])),i,j)for i in range(20)for j in range(i+1,20))
 for _,i,j in pairs:
  if len(edges)>=50:break
  edges.add((i,j))
 c['routes']=[[f'S{i+1}',f'S{j+1}']for i,j in sorted(edges)for i,j in [(i,j),(j,i)]];c.update(preview_all_routes=True,uav_count=600,seed=20261009)
 c['selection']={'method':'Retain6 original; deterministic farthest-point candidates with40m native-building/water and20m mappedpassenger-lane setback; connected50undirected pairs','water_path':str(water),'roads_path':str(roads),'canopy':'unknown','ground':'estimated flat context, not surveyed landing facilities'}
 output.write_text(json.dumps(c,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--roads',type=Path,required=True);p.add_argument('--water',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.base,a.roads,a.water,a.output)
