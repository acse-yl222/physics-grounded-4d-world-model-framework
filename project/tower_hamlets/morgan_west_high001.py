from pathlib import Path
import json,numpy as np,hashlib
from shapely.geometry import Polygon,Point
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-west-high001';O.mkdir(exist_ok=True)
a=np.load(R/'exports/morgan-roof-visibility-audit-001/samples.npz');src=json.loads((R/'references/morgan_massing_study_002.json').read_text());q=next(q for q in src['zones'] if q['name']=='podium_west_high');poly=Polygon(q['support_xy'][0]['outer']);x,y,z=a['x'],a['y'],a['z_odn'];ang=np.deg2rad(-10);U=x*np.cos(ang)+y*np.sin(ang);V=-x*np.sin(ang)+y*np.cos(ang);m=a['valid']&np.array([poly.covers(Point(xx,yy)) for xx,yy in zip(x.flat,y.flat)]).reshape(x.shape);u,v,zz=U[m],V[m],z[m];d=np.array([poly.boundary.distance(Point(xx,yy)) for xx,yy in zip(x[m],y[m])]);np.savez(O/'samples.npz',x=x[m],y=y[m],u=u,v=v,z_odn=zz,boundary_distance=d)
context=a['valid']&(U>=u.min()-3)&(U<=u.max()+3)&(V>=v.min()-2)&(V<=v.max()+3)
fig,ax=plt.subplots(figsize=(9,16),layout='constrained');im=ax.scatter(U[context],V[context],c=z[context],s=150,marker='s',vmin=30,vmax=85);fig.colorbar(im,ax=ax)
for xx,yy,h in zip(U[context],V[context],z[context]):ax.text(xx,yy,f'{h:.1f}',ha='center',va='center',fontsize=6)
xy=np.array(poly.exterior.coords);uv=xy@np.array([[np.cos(ang),-np.sin(ang)],[np.sin(ang),np.cos(ang)]]);ax.plot(*uv.T,'k');ax.set(aspect='equal',xlabel='u m',ylabel='v m',title='West high native DSM ODN context');fig.savefig(O/'context.png',dpi=140)
print('u/v',u.min(),u.max(),v.min(),v.max());print('high',np.c_[u[zz>82],v[zz>82],zz[zz>82],d[zz>82]].tolist())
def stats(e):return {'n':len(e),'rmse_m':float(np.sqrt(np.mean(e**2))),'mae_m':float(np.mean(abs(e))),'p95_abs_m':float(np.percentile(abs(e),95)),'within1m':int((abs(e)<=1).sum())}
candidates=[]
for cu in np.arange(-336.5,-334.49,.25):
 for cv in np.arange(-124.5,-122.49,.25):candidates.append((float(cu),float(cv),(u<cu)&(v>cv)))
def fit(train):
 best=None
 for cu,cv,high in candidates:
  if (train&high).sum()<4:continue
  h=float(np.median(zz[train&high]));pred=np.where(high,h,78.14);loss=float(np.mean(abs(zz[train]-pred[train])))
  if best is None or loss<best[0]:best=(loss,cu,cv,h,pred)
 return best
_,cu,cv,h,pred=fit(np.ones(len(zz),bool));holds=[]
for axis,coord in [('u',u),('v',v)]:
 for width in [1.,2.,3.]:
  folds=np.floor((coord-coord.min())/width).astype(int)%3;rows=[];err=[]
  for f in range(3):
   train=folds!=f;test=~train;sol=fit(train)
   if sol is None:continue
   _,bu,bv,bh,pr=sol;e=zz[test]-pr[test];err.extend(e);rows.append({'fold':f,'breaks':[bu,bv],'height_odn':bh,'test':stats(e)})
  holds.append({'axis':axis,'width_m':width,'folds':rows,'all_test':stats(np.array(err))})
high=(u<cu)&(v>cv);fig,axs=plt.subplots(1,2,figsize=(12,7),layout='constrained')
for ax,coord,label in [(axs[0],u,'u'),(axs[1],v,'v')]:
 ax.scatter(coord,zz,c=np.where(high,1,0),s=15);ax.axhline(78.14,color='k');ax.axhline(h,color='r');ax.set(xlabel=label,ylabel='ODN m',title='All selected-zone cells; candidate high in yellow')
fig.savefig(O/'profiles.png',dpi=150)
result={'zone':q,'fit':{'u_break':cu,'v_break':cv,'high_odn':h,'high_cells':int(high.sum()),'high_stats':stats(zz[high]-h),'outside_high_stats':stats(zz[~high]-78.14),'full':stats(zz-pred),'baseline':stats(zz-78.14)},'nested_holdouts':holds,'source_hashes':{f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/morgan_massing_study_002.json','exports/morgan-roof-visibility-audit-001/samples.npz']},'datum':4.28000021,'capture_date':None};(O/'evaluation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result['fit'],indent=2));print([(r['axis'],r['width_m'],[(x['breaks'],x['height_odn']) for x in r['folds']]) for r in holds])
from shapely.ops import transform
from shapely.geometry import box
uvpoly=transform(lambda x,y:(np.asarray(x)*np.cos(ang)+np.asarray(y)*np.sin(ang),-np.asarray(x)*np.sin(ang)+np.asarray(y)*np.cos(ang)),poly)
capuv=uvpoly.intersection(box(-1000,cv,cu,1000));cap=transform(lambda u,v:(np.asarray(u)*np.cos(ang)-np.asarray(v)*np.sin(ang),np.asarray(u)*np.sin(ang)+np.asarray(v)*np.cos(ang)),capuv)
interfaces=[]
for zone in src['zones']:
 if zone['owner']==q['owner']:continue
 for rg in zone['support_xy']:
  pp=Polygon(rg['outer']);length=cap.boundary.intersection(pp.boundary.buffer(1e-5)).length
  if length>.001:interfaces.append({'zone':zone['name'],'owner':zone['owner'],'contact_m':length,'adjacent_odn':zone['odn_m'],'step_difference_m':h-zone['odn_m'],'xy_overlap_m2':cap.intersection(pp).area})
result['cap']={'outer_xy':list(cap.exterior.coords)[:-1],'area_m2':cap.area,'bottom_scene':78.14-4.28000021,'top_scene':h-4.28000021,'interfaces':interfaces,'scope':'Standalone additive closed roof tier; original four b317 meshes unchanged. Vertical step walls estimated from abrupt raster transition; hidden construction unknown.'};(O/'evaluation.json').write_text(json.dumps(result,indent=2));print(result['cap'])
sens=[]
for du in [-.5,0,.5]:
 for dv in [-.5,0,.5]:
  hh=(u<cu+du)&(v>cv+dv);pr=np.where(hh,h,78.14);sens.append({'du':du,'dv':dv,'selected_cells':int(hh.sum()),'selected_stats':stats(zz[hh]-h),'full_stats':stats(zz-pr)})
result['sensitivity_fixed_height']=sens;result['samples_xyz_odn']=np.c_[x[m],y[m],zz].tolist();(O/'evaluation.json').write_text(json.dumps(result,indent=2))
