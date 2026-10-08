from pathlib import Path
exec(Path(__file__).with_name('owner1f92_review.py').read_text().split('rows=[]')[0])
a=json.loads((R/'references/owner1f92_domains.json').read_text());c=np.array(a['center']);e=np.array(a['east_axis']);n=np.array(a['north_axis']);u=(x-c[0])*e[0]+(y-c[1])*e[1];v=(x-c[0])*n[0]+(y-c[1])*n[1];q=ps[0];full=mask(q);b1,b2=a['boundaries_v_m'];hs=a['heights_odn_m'];zone=np.digitize(v,[b1,b2]);zone[(zone==1)&(u<a['middle_west_boundary_u_m'])]=2
core=mask(q.buffer(-.5))&(((v>13.5)&(u>-9)&(u<4))|((u>7)&(v>8)&(v<12.5)));h=float(np.median(z[core]));hs=hs+[h];best=None;m=mask(q.buffer(-.5))
for bn in np.arange(12.5,14.1,.1):
 for be in np.arange(6,8.1,.1):
  zz=zone.copy();zz[(zone==2)&((v>bn)|((u>be)&(v>b2)))]=3;pp=np.choose(zz,hs);loss=float(np.minimum(abs(z[m]-pp[m]),1.5).sum())
  if best is None or loss<best[0]:best=(loss,float(bn),float(be),zz,pp)
_,bn,be,zone,pred=best
hold=[]
for k in range(3):
 f=np.floor((u-u[core].min())/3).astype(int)%3;train=core&(f!=k);test=core&(f==k);hh=float(np.median(z[train]));hold.append({'fold':k,'height_odn_m':hh,**metric(z[test]-hh)})
sensitivity=[]
for dn in [-.5,0,.5]:
 for de in [-.5,0,.5]:
  zz=np.digitize(v,[b1,b2]);zz[(zz==1)&(u<a['middle_west_boundary_u_m'])]=2;zz[(zz==2)&((v>bn+dn)|((u>be+de)&(v>b2)))]=3;pp=np.choose(zz,hs);sensitivity.append({'north_shift_m':dn,'east_shift_m':de,**metric(z[full]-pp[full])})
a.update({'heights_odn_m':hs,'fourth_north_boundary_v_m':bn,'fourth_east_boundary_u_m':be,'fourth_core':metric(z[core]-h),'fourth_holdout':hold,'full_valid':metric(z[full]-pred[full]),'inner2':metric(z[mask(q.buffer(-2))]-pred[mask(q.buffer(-2))]),'boundary_outer2':metric(z[full&~mask(q.buffer(-2))]-pred[full&~mask(q.buffer(-2))]),'fourth_full':metric(z[full&(zone==3)]-h),'fourth_boundary_sensitivity':sensitivity,'limitations':['Four stepped roof levels supported by geographically coherent DSM plateaux. Exact breaklines estimated from 1 m raster, not survey.','North/east narrow lower tier has explicit inset/DTM profile evidence; west edge remains unresolved mixed/low strip.','Base stays original illustrative z=0. No facade/entrance/equipment detail invented.','Full-domain includes every valid DSM cell; robust fits do not imply all observations agree.','Actual composite flight date unknown.']})
fig,ax=plt.subplots(1,2,figsize=(12,7),layout='constrained');pr=(np.array(q.exterior.coords)-c)@np.stack([e,n],axis=1)
for aa,values,title in [(ax[0],pred,'Four-level predicted roof ODN'),(ax[1],z-pred,'DSM minus candidate (m)')]:
 im=aa.scatter(u[full],v[full],c=values[full],s=20,marker='s',cmap='viridis' if aa==ax[0] else 'coolwarm',**({} if aa==ax[0] else {'vmin':-16,'vmax':16}));fig.colorbar(im,ax=aa);aa.plot(pr[:,0],pr[:,1],'r-');aa.set(aspect='equal',title=title)
fig.savefig(R/'references/owner1f92_fourth.png',dpi=150);(R/'references/owner1f92_fourth.json').write_text(json.dumps(a,indent=2));print(json.dumps({k:a[k] for k in ['heights_odn_m','fourth_north_boundary_v_m','fourth_east_boundary_u_m','fourth_core','full_valid','inner2','boundary_outer2']},indent=2))
