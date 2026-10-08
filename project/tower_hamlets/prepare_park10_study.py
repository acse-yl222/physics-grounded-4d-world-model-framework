from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from shapely.geometry import Polygon,box
from shapely.ops import transform
from shapely import contains_xy,set_precision
# reuse pure prism mesh helper only; source files not mutated
s=Path(__file__).with_name('prepare_water8_study.py').read_text();exec(s.split('from shapely.geometry import box')[0].replace('overture-building-36beb80b-ced9-4f18-a461-04680502f52e','overture-part-dfcdb3b0-d651-355b-bed0-8d4948217eea'))
a=np.load('cache/tower_hamlets/park10_roof.npz');q=transform(uv,p);domains=[('south',q.intersection(box(350,-280,410,-245))),('middle',q.intersection(box(350,-245,410,-236))),('north',q.intersection(box(350,-236,410,-200)))];objs=[];regs=[]
for name,domain in domains:
 domain=set_precision(domain,.000001);m=a['valid']&contains_xy(domain.buffer(-2),a['u'],a['v']);u=a['u'][m];v=a['v'][m];z=a['z'][m];center=[float(np.mean(u)),float(np.mean(v))];A=np.stack([np.ones(len(z)),u-center[0],v-center[1]],axis=-1)
 def fit(mask):return least_squares(lambda c:A[mask]@c-z[mask],[np.median(z[mask]),0,0],loss='soft_l1',f_scale=.25).x
 c=fit(np.ones(len(z),bool));checks=[]
 for axis in [u,v]:
  folds=np.floor(axis/3).astype(int)%3;es=[]
  for k in range(3):
   if (folds==k).sum() and (folds!=k).sum()>5:es.extend(z[folds==k]-A[folds==k]@fit(folds!=k))
  checks.append({'rmse_m':float(np.sqrt(np.mean(np.square(es)))),'median_abs_m':float(np.median(np.abs(es))),'p90_abs_m':float(np.percentile(np.abs(es),90))})
 # Each region level is descriptive median; slopes are diagnosed, not used to invent kinked unstable planes.
 level=float(np.median(z)); constant_checks=[]
 for axis in [u,v]:
  folds=np.floor(axis/3).astype(int)%3;es=[]
  for k in range(3):
   if (folds==k).sum() and (folds!=k).sum():es.extend(z[folds==k]-np.median(z[folds!=k]))
  constant_checks.append({'rmse_m':float(np.sqrt(np.mean(np.square(es)))),'median_abs_m':float(np.median(np.abs(es))),'p90_abs_m':float(np.percentile(np.abs(es),90))})
 objs.append(make(domain,[level,0,0],'Park10_'+name));regs.append({'name':name,'support_uv':list(domain.exterior.coords),'cells':len(z),'roof_odn_m':level,'scene_z_m':level-datum,'plane_center_uv':center,'robust_plane_coefficients':c.tolist(),'diagnostic_plane_spatial3m_strip_holdout_all_test_cells':checks,'authored_constant_level_spatial3m_strip_holdout_all_test_cells':constant_checks})
r={'building_id':bid,'parent_id':f['parent_id'],'objects':objs,'baseline_mesh':make(q,[129+datum,0,0],'Park10_baseline129'),'scope':'Exploratory10ParkDrive tower roof envelope with three estimated spatial levels; source129m is43floors times assumed3m. Preserve sibling f8bf native39m. No facade or equipment modeled.','datum_odn_m':datum,'regions':regs,'checks':{'source_area_m2':p.area,'partition_area_m2':sum(d.area for _,d in domains),'symmetric_difference_m2':q.symmetric_difference(domains[0][1].union(domains[1][1]).union(domains[2][1])).area},'limitations':['Actual per-building raster capture vintage unknown;2020completion does not prove scan captures completed building.','Spatial boundaries v=-245/-236 chosen after plot review; exploratory interpretation, no measured architectural breakline. Roof steps simplify sloping/structured returns.','Separate adjoining closed meshes retain internal coincident walls. Northeast low returns unresolved.','Parent footprint and sibling are not replaced. Roof energy centre is textual fact, not an identified geometric component.'],'primary_sources':[{'url':'https://www.jra.co.uk/projects/10-park-drive-8-water-street','facts':'2020completion;43storey10ParkDrive;sharedenergycentre at top. No metricheight or exact roofgeometry.'}]};(R/'references/park10_study.json').write_text(json.dumps(r,indent=2));print(json.dumps(regs,indent=2))
