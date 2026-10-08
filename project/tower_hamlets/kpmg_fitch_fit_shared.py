from pathlib import Path
exec(Path('project/tower_hamlets/kpmg_fitch_common.py').read_text())
from shapely.geometry import box
ang=np.deg2rad(-10);co,si=np.cos(ang),np.sin(ang);u=x*co+y*si;v=-x*si+y*co;uv=lambda x,y:(np.asarray(x)*co+np.asarray(y)*si,-np.asarray(x)*si+np.asarray(y)*co);regions=[];out={'scope':'North shared-domain roofcontinuity diagnostic only, not completepairedreplacement','datum':'ODNminus4.28000021','sensitivity':[]}
for inset in [-.5,0,.5]:
 q=box(175-inset,43-inset,191+inset,54+inset);m=mask(p)&np.array([q.contains(Point(a,b)) for a,b in zip(u.flat,v.flat)]).reshape(u.shape);A=np.stack([np.ones(x.shape),u-183,v-48],axis=-1)
 def fit(k):return least_squares(lambda c:A[k]@c-z[k],[75.2,0,0],loss='soft_l1',f_scale=.2).x
 c=fit(m);hold={}
 for axis,arr in [('u',u),('v',v)]:
  folds=np.floor(arr/3).astype(int)%3;errs=[]
  for f in range(3):
   te=m&(folds==f);tr=m&~te;cf=fit(tr);errs.extend(z[te]-A[te]@cf)
  hold[axis]=metric(np.array(errs))
 out['sensitivity'].append({'boundary_expansion_m':inset,'cells':int(m.sum()),'plane_odn_c0_cu_cv':c.tolist(),'formula':'c0+cu*(u-183)+cv*(v-48)','holdout':hold,'all_errors':metric(z[m]-A[m]@c)})
 if inset==0:
  out['nominal_plane']=c.tolist();out['domain_uv']=q.__geo_interface__
  out['by_owner']=[{'id':f['id'],'stats':stats(z[m&mask(pp)]),'plane_error':metric(z[m&mask(pp)]-A[m&mask(pp)]@c)} for f,pp in zip(fs,ps)]
out['conclusion']='Bothowner samples have matched dominantlevels near75.2ODN. This does not establish a singleplane throughoutdomain: spatialholdoutRMSE1.34m and higherpatches remain. No supported owner-wide boundaryheightstep. Southernterrain-likecomponent remainsunresolved; do notinfergroundcourtyard orcontinuousroof. Fullpairedreplacementheld.';(R/'references/kpmg_fitch_shared_fit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
