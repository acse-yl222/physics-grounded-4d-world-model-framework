from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,Point
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-west-south-roof-study-001';O.mkdir(exist_ok=True);a=np.load(R/'exports/morgan-roof-visibility-audit-001/samples.npz');src=json.loads((R/'references/morgan_massing_study_002.json').read_text());q=next(q for q in src['zones'] if q['name']=='podium_west_south');poly=Polygon(q['support_xy'][0]['outer']);x,y,z=a['x'],a['y'],a['z_odn'];m=a['valid']&np.array([poly.covers(Point(xx,yy)) for xx,yy in zip(x.flat,y.flat)]).reshape(x.shape);xx,yy,zz=x[m],y[m],z[m];ang=np.deg2rad(-10);u=xx*np.cos(ang)+yy*np.sin(ang);v=-xx*np.sin(ang)+yy*np.cos(ang)
fig,axs=plt.subplots(1,3,figsize=(17,7),layout='constrained');im=axs[0].scatter(u,v,c=zz,cmap='viridis',s=200,vmin=10,vmax=80,marker='s');fig.colorbar(im,ax=axs[0],label='ODN m')
for aa,bb,cc in zip(u,v,zz):axs[0].text(aa,bb,f'{cc:.1f}',fontsize=7,ha='center',va='center')
for ax,t,label in [(axs[1],u,'u'),(axs[2],v,'v')]:ax.scatter(t,zz,c='navy');ax.axhline(59.6635,c='red');ax.set(xlabel=label+'m',ylabel='ODN m',title='All111cells, existing red59.6635')
axs[0].set(aspect='equal',xlabel='u m',ylabel='v m',title='Unfiltered native cell values');fig.savefig(O/'unfiltered-cells.png',dpi=160);np.savez(O/'zone-samples.npz',x=xx,y=yy,z_odn=zz,u=u,v=v);print('boundsUV',u.min(),u.max(),v.min(),v.max())
def metrics(err):return {'cells':len(err),'rmse_m':float(np.sqrt(np.mean(err**2))),'mae_m':float(np.mean(abs(err))),'p95_abs_m':float(np.percentile(abs(err),95)),'within1m':int((abs(err)<=1).sum())}
def labels(cutu,cutv):return (u>=cutu).astype(int)+2*(v<cutv).astype(int)
cutu,cutv=-338.5,-150.6;lab=labels(cutu,cutv);pred=np.empty(len(zz));parts=[]
for k in range(4):
 m=lab==k;h=float(np.median(zz[m]));pred[m]=h;hold={}
 for axis,coord in [('u',u),('v',v)]:
  folds=np.floor((coord[m]-coord[m].min())/2).astype(int)%3;err=[];ff=[]
  for f in range(3):
   tr=folds!=f;te=folds==f
   if not tr.any() or not te.any():continue
   hh=float(np.median(zz[m][tr]));ee=zz[m][te]-hh;err.extend(ee);ff.append({'fold':f,'train_cells':int(tr.sum()),'test_cells':int(te.sum()),'median':hh,'metrics':metrics(ee)})
  hold[axis]={'folds':ff,'metrics':metrics(np.array(err))}
 parts.append({'label':k,'name':['northwest_high','northeast_mid','southwest_mid','southeast_low'][k],'cells':int(m.sum()),'median_odn_m':h,'scene_z_m':h-4.28000021,'all_cells_metrics':metrics(zz[m]-h),'holdout':hold})
sens=[]
for du in [-1,-.5,0,.5,1]:
 for dv in [-1,-.5,0,.5,1]:
  l=labels(cutu+du,cutv+dv);pr=np.empty(len(zz));med=[]
  for k in range(4):
   m=l==k;h=float(np.median(zz[m]));pr[m]=h;med.append(h)
  sens.append({'u_break':cutu+du,'v_break':cutv+dv,'levels_odn':med,'metrics':metrics(zz-pr)})
G=json.loads((R/'geometry.json').read_text())['buildings'];neighbors=[]
for b in G:
 if any(k in b['id'] for k in ['3ae95773','39303788','31757561','b317a51d']):
  pp=Polygon(b['geometry'][0]['outer']);neighbors.append({'id':b['id'],'distance_to_zone_m':poly.distance(pp),'zone_shared_boundary_m':poly.boundary.intersection(pp.boundary).length,'plan_overlap_with_zone_m2':poly.intersection(pp).area})
fig,axs=plt.subplots(1,2,figsize=(12,7),layout='constrained')
for ax,vals,title in [(axs[0],pred,'Four descriptive plateaus'),(axs[1],zz-pred,'All-cell residual, including boundaryreturns')]:
 im=ax.scatter(u,v,c=vals,s=150,marker='s',cmap='viridis' if ax==axs[0] else 'coolwarm');fig.colorbar(im,ax=ax);ax.axvline(cutu,c='black');ax.axhline(cutv,c='black');ax.set(aspect='equal',title=title,xlabel='u m',ylabel='v m')
fig.savefig(O/'candidate-support.png',dpi=160)
out={'source_zone':q,'datum_odn_m':4.28000021,'capture_vintage':'Unresolved','partition':'Mappedorientation -10degrees; u=-338.5,v=-150.6 estimated spatial breaklines after inspecting unfiltered111cells. No photo/camera input.','parts':parts,'baseline':metrics(zz-59.6635),'candidate_full_zone':metrics(zz-pred),'sensitivity':sens,'interfaces':neighbors,'limitations':['All111cells included; boundary lowreturns remainunresolved, fullplateau extends toexactzoneboundary asestimatedcompletion','Fourmedians do not prove architecturalsteps; verticalfaces atestimatedbreaks notmeasured','2mstripholdout conditionalonselectedboundaries; smallnorthwestdomain limited','No slope proposed: clusters form discreteplateaus and mixededge returns, not supportedcontinuousplane']};(O/'evidence.json').write_text(json.dumps(out,indent=2));print(json.dumps({'parts':parts,'baseline':out['baseline'],'candidate':out['candidate_full_zone'],'interfaces':neighbors},indent=2))
boundary_distance=np.array([poly.boundary.distance(Point(a,b)) for a,b in zip(xx,yy)]);out['boundary_distance_subsets']=[]
for inset in [0,.5,1,2]:
 m=boundary_distance>=inset;out['boundary_distance_subsets'].append({'inset_m':inset,'retained_cells':int(m.sum()),'excluded_cells_reported_separately':int((~m).sum()),'candidate_retained_metrics':metrics(zz[m]-pred[m]),'candidate_excluded_metrics':metrics(zz[~m]-pred[~m]) if (~m).any() else None})
for row in neighbors:
 bb=next(b for b in G if b['id']==row['id']);pp=Polygon(bb['geometry'][0]['outer']);row['boundary_contact_length_tolerance_1e_5m']=poly.boundary.intersection(pp.boundary.buffer(1e-5)).length
out['source_sha256']={n:__import__('hashlib').sha256((R/n).read_bytes()).hexdigest() for n in ['references/morgan_massing_study_002.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']};(O/'evidence.json').write_text(json.dumps(out,indent=2));print('boundary',out['boundary_distance_subsets']);print('interfaces',neighbors)
