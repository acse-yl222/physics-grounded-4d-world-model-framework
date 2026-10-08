from pathlib import Path
exec(Path(__file__).with_name('hipped_residential_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
pair=ps[0].union(ps[1]);edge=np.array(fs[0]['geometry'][0]['outer'][1])-np.array(fs[0]['geometry'][0]['outer'][0]);e=edge/np.linalg.norm(edge);n=np.array([-e[1],e[0]]);uv=lambda xx,yy:(xx*e[0]+yy*e[1],xx*n[0]+yy*n[1]);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);pq=transform(uv,pair);u=x*e[0]+y*e[1];v=x*n[0]+y*n[1];cut=float(np.array(fs[0]['geometry'][0]['outer'][0])@n);rows=[];fig,axs=plt.subplots(2,3,figsize=(15,9),layout='constrained')
for shift in [-1,0,1]:
 domain=pq.intersection(box(-1000,cut+shift,1000,1000));b=domain.bounds;center=np.array([(b[0]+b[2])/2,(b[1]+b[3])/2]);half=np.array([(b[2]-b[0])/2,(b[3]-b[1])/2]);actual=transform(xy,domain);m=mask(actual.buffer(-1));
 def pred(c):return c[0]+np.minimum(c[1]*(half[0]-abs(u-center[0]-c[3])),c[2]*(half[1]-abs(v-center[1]-c[4])))
 def fit(mm):return least_squares(lambda c:pred(c)[mm]-z[mm],[7,.6,.6,0,0],bounds=([2,.1,.1,-1.5,-1.5],[12,2,2,1.5,1.5]),loss='soft_l1',f_scale=.15).x
 c=fit(m);foldsout=[]
 for axis,a in [('u',u),('v',v)]:
  folds=np.floor(a/2).astype(int)%3
  for k in range(3):
   tr=m&(folds!=k);te=m&(folds==k)
   if tr.sum()<10 or te.sum()==0:continue
   cc=fit(tr);foldsout.append({'axis':axis,'fold':k,'parameters':cc.tolist(),**metric((z-pred(cc))[te])})
 rows.append({'cut_shift_m':shift,'cut_v_m':cut+shift,'axis_u':e.tolist(),'axis_v':n.tolist(),'center_uv':center.tolist(),'half_uv':half.tolist(),'parameters_eave_odn_slope_u_slope_v_du_dv':c.tolist(),'fit':metric((z-pred(c))[m]),'holdout':foldsout,'main_outline_xy':list(actual.exterior.coords),'low_wings':{'area_m2':pair.difference(actual).area,'dsm':stats(z[mask(pair.difference(actual).buffer(-.5))]),'dtm':stats(t[mask(pair.difference(actual).buffer(-.5))])}})
 if shift==0:
  for ax,a,title in zip(axs[0],[z,pred(c),z-pred(c)],['DSM ODN','Main hip hypothesis','Residual all inset cells']):
   mm=mask(pair) if title=='DSM ODN' else mask(actual);
   if title!='DSM ODN':
    lowmask=mask(pair.difference(actual));ax.scatter(x[lowmask],y[lowmask],color='lightgray',s=24,marker='s');ax.text(pair.centroid.x,pair.bounds[1]+3,'LOW WINGS\nNOT FITTED',ha='center',fontsize=8)
   im=ax.scatter(x[mm],y[mm],c=a[mm],s=24,marker='s',cmap='coolwarm' if 'Residual' in title else 'viridis',vmin=-3 if 'Residual' in title else 2,vmax=3 if 'Residual' in title else 12);fig.colorbar(im,ax=ax)
   ax.plot(*pair.exterior.xy,'k-');ax.plot(*actual.exterior.xy,'r-');ax.set(aspect='equal',title=title)
  low=mask(pair.difference(actual).buffer(-.5));axs[1,0].scatter(u[low],z[low],s=12);axs[1,0].set(title='Low wings: all 0.5m inset cells',xlabel='Rotated u',ylabel='ODN');axs[1,1].scatter(v[low],z[low],s=12);axs[1,1].set(xlabel='Rotated v',ylabel='ODN');im=axs[1,2].scatter(x[low],y[low],c=(z-t)[low],s=35,marker='s',vmin=0,vmax=5);fig.colorbar(im,ax=axs[1,2],label='DSM minus DTM');axs[1,2].plot(*pair.exterior.xy,'k-');axs[1,2].set(aspect='equal',title='Low-wing surface-vs-terrain diagnostic')
fig.savefig(R/'references/hipped_residential_west_domain_masked.png',dpi=150)
report={'ids':[fs[i]['id'] for i in [0,1]],'domain_basis':'Main / low-wing split follows the northern edge of mapped courtyard, extended across both owners; ±1m sensitivity is a diagnostic, not alternate observed breaklines. Geometric insets only; no height filtering.','models':rows,'capture_date':None,'geometry_modified':False};print(json.dumps(report,indent=2))
