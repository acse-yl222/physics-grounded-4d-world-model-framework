from pathlib import Path
exec(Path(__file__).with_name('owner87aa_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
pr=json.loads((R/'references/owner87aa_profiles.json').read_text());e=np.array(pr['axis_u']);n=np.array(pr['axis_v']);u=x*e[0]+y*e[1];v=x*n[0]+y*n[1];xy=lambda a,b:(a*e[0]+b*n[0],a*e[1]+b*n[1]);q=ps[0];domains={'south_boundary_strip':q.intersection(transform(xy,box(-1000,-1000,-457,1000))),'interior_patch_1':q.intersection(transform(xy,box(-444,-372,-437,-366))),'interior_patch_2':q.intersection(transform(xy,box(-434,-372,-429,-366)))};out={}
for name,p in domains.items():
 row={}
 for inset in [0,1,2,3,4,5]:
  mm=mask(p.intersection(q.buffer(-inset)));row[str(inset)]={'DSM_ODN':stats(z[mm]),'DTM_ODN':stats(t[mm]),'DSM_minus_DTM':stats((z-t)[mm]),'within01m':int((abs(z[mm]-t[mm])<.1).sum()),'within001m':int((abs(z[mm]-t[mm])<.01).sum())}
 out[name]={'bounds_xy':list(p.bounds),'inset_sensitivity':row}
fig,axs=plt.subplots(2,3,figsize=(15,10),layout='constrained');m=mask(q.buffer(2))
for ax,a,title,lo,hi in zip(axs[0],[z,t,z-t],['DSM ODN','Co-located DTM ODN','DSM minus DTM'],[4,4,0],[36,8,30]):
 im=ax.scatter(u[m],v[m],c=a[m],s=14,marker='s',vmin=lo,vmax=hi);fig.colorbar(im,ax=ax)
 for name,p in domains.items():
  rr=np.array(p.exterior.coords);uu=rr@e;vv=rr@n;ax.plot(uu,vv,'r-',lw=.7)
 ax.set(aspect='equal',title=title,xlabel='Rotated u',ylabel='Rotated v')
profiles=[]
for ax,vc in zip(axs[1],[-380,-369,-358]):
 mm=m&(abs(v-vc)<.7);ix=np.argsort(u[mm]);ax.plot(u[mm][ix],z[mm][ix],'.-',label='DSM');ax.plot(u[mm][ix],t[mm][ix],'.-',label='DTM');ax.axvline(-457,color='gray',ls=':');ax.set(title='Across south boundary; v='+str(vc),xlabel='Rotated u',ylabel='ODN');ax.legend();profiles.append({'v_center':vc,'u':u[mm][ix].tolist(),'DSM':z[mm][ix].tolist(),'DTM':t[mm][ix].tolist()})
fig.savefig(R/'references/owner87aa_low_returns.png',dpi=150);r={'domains':out,'profiles':profiles,'selection':'Geometric strips/patches from inspected DSM. All validcellcenters within domains; no heightfilter. Inset clips originalownerboundary,notpatchboundary.','actual_capture_date':None,'geometry_modified':False};(R/'references/owner87aa_low_returns.json').write_text(json.dumps(r,indent=2));print(json.dumps(out,indent=2))
