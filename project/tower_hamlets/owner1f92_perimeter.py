from pathlib import Path
exec(Path(__file__).with_name('owner1f92_review.py').read_text().split('rows=[]')[0])
a=json.loads((R/'references/owner1f92_domains.json').read_text());c=np.array(a['center']);e=np.array(a['east_axis']);n=np.array(a['north_axis']);u=(x-c[0])*e[0]+(y-c[1])*e[1];v=(x-c[0])*n[0]+(y-c[1])*n[1];q=ps[0];full=mask(q)
# Geographic rectangular domains, no elevation threshold.
domains={'north_strip':full&(v>13.25)&(u<6.5)&(u>-10),'east_strip':full&(u>6.5)&(v>8)&(v<13.25),'north_inner_profile':full&(u>-8)&(u<4)&(v>10),'east_inner_profile':full&(v>8)&(v<12)}
rows={}
for name,m in domains.items():
 rows[name]={}
 for inset in [0,.5,1,1.5,2]:
  mm=m&mask(q.buffer(-inset));rows[name][str(inset)]={'dsm':stats(z[mm]),'dtm':stats(t[mm]),'near_dtm_10cm':int((abs(z[mm]-t[mm])<.1).sum())}
fig,ax=plt.subplots(1,3,figsize=(17,5),layout='constrained');im=ax[0].scatter(u[full],v[full],c=z[full],s=25,marker='s',vmin=10,vmax=21);fig.colorbar(im,ax=ax[0]);pr=(np.array(q.exterior.coords)-c)@np.stack([e,n],axis=1);ax[0].plot(pr[:,0],pr[:,1],'r-');ax[0].set(aspect='equal',title='Roof DSM ODN; full mapped owner')
for i,(name,coord) in enumerate([('north_inner_profile',v),('east_inner_profile',u)],1):
 m=domains[name];ax[i].scatter(coord[m],z[m],s=12,label='DSM');ax[i].scatter(coord[m],t[m],s=8,label='DTM');ax[i].set(title=name,xlabel='North-axis m' if i==1 else 'East-axis m',ylabel='ODN m');ax[i].legend()
fig.savefig(R/'references/owner1f92_perimeter.png',dpi=150);(R/'references/owner1f92_perimeter.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
