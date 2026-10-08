from pathlib import Path
exec(Path(__file__).with_name('abd75_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
pr=json.loads((R/'references/abd75_profiles.json').read_text());e=np.array(pr['axis_u']);n=np.array(pr['axis_v']);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);u=x*e[0]+y*e[1];v=x*n[0]+y*n[1];q=ps[0];domains={'central_roof':q.intersection(transform(xy,box(156,-62,231,-34))),'north_perimeter':q.intersection(transform(xy,box(156,-1000,231,-63))),'south_perimeter':q.intersection(transform(xy,box(156,-33,231,1000))),'east_curve':q.intersection(transform(xy,box(233,-57,1000,-36))),'external_unbuilt':q.buffer(3).difference(q).difference(unary_union([poly(f) for f in g['buildings'] if f.get('kind')!='site']))};rows={}
for name,p in domains.items():
 mm=mask(p);rows[name]={'cells':int(mm.sum()),'dsm_odn':stats(z[mm]),'dtm_odn':stats(t[mm]),'dsm_minus_dtm':stats((z-t)[mm]),'within_01m_DTM':int((abs(z[mm]-t[mm])<.1).sum()),'bounds_xy':list(p.bounds)}
 if name=='central_roof':
  center=np.array(p.centroid.coords[0]);A=np.stack([np.ones(x.shape),x-center[0],y-center[1]],axis=-1);fit=lambda m:least_squares(lambda c:A[m]@c-z[m],[35.7,0,0],loss='soft_l1',f_scale=.1).x;c=fit(mm);checks=[]
  for nameaxis,ar in [('u',u),('v',v)]:
   ff=np.floor(ar/5).astype(int)%3
   for k in range(3):
    tr=mm&(ff!=k);te=mm&(ff==k);cc=fit(tr);checks.append({'axis':nameaxis,'fold':k,'parameters':cc.tolist(),**metric(z[te]-A[te]@cc)})
  rows[name].update({'plane_center_xy':center.tolist(),'plane_interceptODN_dx_dy':c.tolist(),'residual':metric(z[mm]-A[mm]@c),'holdout':checks})
fig,axs=plt.subplots(1,3,figsize=(16,6),layout='constrained');mm=mask(q.buffer(3))
for ax,a,title,lo,hi in zip(axs,[t,z,z-t],['DTM ODN','DSM ODN','DSM minus DTM'],[10,10,0],[13,38,26]):
 im=ax.scatter(x[mm],y[mm],c=a[mm],s=5,marker='s',vmin=lo,vmax=hi);fig.colorbar(im,ax=ax);ax.plot(*q.exterior.xy,'r-');ax.set(aspect='equal',title=title)
fig.savefig(R/'references/abd75_domains.png',dpi=150);(R/'references/abd75_domains.json').write_text(json.dumps({'domains':rows,'selection':'Geometric domains based on actual spatial DSM transitions; notconfirmed architecturalboundaries. No elevationfilter.','datum_ODN_scene_offset':4.28000021,'capture_date':None,'geometry_modified':False},indent=2));print(json.dumps(rows,indent=2))
