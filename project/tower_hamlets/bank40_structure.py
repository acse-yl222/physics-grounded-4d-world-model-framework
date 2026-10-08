from pathlib import Path
exec(Path('project/tower_hamlets/bank40_review.py').read_text().split('rows=[]')[0])
a=np.deg2rad(-10);u=x*np.cos(a)+y*np.sin(a);v=-x*np.sin(a)+y*np.cos(a);m=mask(p.buffer(-2));U=u[m];V=v[m];Z=z[m]
print('UV bounds',U.min(),U.max(),V.min(),V.max())
fig,ax=plt.subplots(figsize=(11,8));im=ax.scatter(U,V,c=Z,s=13,marker='s',vmin=148,vmax=164);fig.colorbar(im,ax=ax,label='DSM ODN m');ax.set_aspect('equal');ax.set_title('40 Bank Street all 2m inset cells; aligned roof evidence');fig.savefig(R/'references/bank40_aligned.png',dpi=160)
for axis,A in [('u',U),('v',V)]:
 print(axis)
 for lo in np.arange(np.floor(A.min()/2)*2,A.max(),2):
  k=(A>=lo)&(A<lo+2);print(round(lo,1),len(Z[k]),np.round(np.percentile(Z[k],[10,50,90]),2).tolist())
from shapely.geometry import box
from shapely.ops import transform as st
PU=st(lambda x,y:(np.asarray(x)*np.cos(a)+np.asarray(y)*np.sin(a),-np.asarray(x)*np.sin(a)+np.asarray(y)*np.cos(a)),p)
regions=[('east_lower',box(31,-340,45,-288)),('central_high',box(-3,-311,11,-306)),('north_mixed',box(-30,-302,31,-280)),('southwest_main',box(-30,-340,31,-302).difference(box(-3,-311,11,-306)))]
out={'owner':fs[0]['id'],'datum':'ODNminus4.28000021; rastercapturevintageunknown','regions':[]}
for name,q0 in regions:
 q=q0.intersection(PU);k=np.array([q.contains(Point(uu,vv)) for uu,vv in zip(U,V)]);level=np.median(Z[k]);hold={}
 for axis,arr in [('u',U),('v',V)]:
  folds=np.floor(arr/3).astype(int)%3;errs=[]
  for f in range(3):
   te=k&(folds==f);tr=k&~te;errs.extend(Z[te]-np.median(Z[tr]))
  hold[axis]=metric(np.array(errs))
 out['regions'].append({'name':name,'geometry_uv':q.__geo_interface__,'ODNstats':stats(Z[k]),'constant_odn':float(level),'holdout':hold})
(R/'references/bank40_structure.json').write_text(json.dumps(out,indent=2));print(json.dumps([{k:v for k,v in q.items() if k!='geometry_uv'} for q in out['regions']],indent=2))
