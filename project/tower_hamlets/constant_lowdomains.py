from pathlib import Path
exec(Path(__file__).with_name('constant_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
from scipy.ndimage import label
q=ps[0];domains={'north_strip':q.intersection(box(380,357.5,417,365)),'southeast_extension':q.intersection(box(418,320,430,332)),'northeast_patch':q.intersection(box(415,352,421,357))};rows={}
for name,p in domains.items():
 rows[name]={}
 for inset in [0,1,2,3,4]:
  mm=mask(p.intersection(q.buffer(-inset)));rows[name][str(inset)]={'DSM':stats(z[mm]),'DTM':stats(t[mm]),'DSM_minus_DTM':stats((z-t)[mm]),'within01m':int((abs(z-t)[mm]<.1).sum())}
# Thresholds are diagnostics only, not geometry boundaries or source validation.
components={};owner=mask(q)
for threshold in [5,10,15,18]:
 low=owner&(z<threshold);labs,count=label(low,np.ones((3,3)));rr=[]
 for k in range(1,count+1):
  sel=labs==k;coords=list(zip(x[sel],y[sel]));dist=min(q.boundary.distance(Point(a,b)) for a,b in coords);rr.append({'cells':int(sel.sum()),'boundary_min_distance_m':dist,'touches_exterior_within_1m':dist<1,'DSM':stats(z[sel]),'DTM':stats(t[sel])})
 components[str(threshold)]=sorted(rr,key=lambda a:-a['cells'])
fig,ax=plt.subplots(2,3,figsize=(15,9),layout='constrained');mm=mask(q)
for a,arr,title in zip(ax[0],[z,t,z-t],['DSM ODN','DTM ODN','DSM-DTM']):
 im=a.scatter(x[mm],y[mm],c=arr[mm],s=15,marker='s');fig.colorbar(im,ax=a);a.plot(*q.exterior.xy,'k-',lw=.7)
 for name,p in domains.items():a.plot(*p.exterior.xy,'r-',lw=.8)
 a.set(aspect='equal',title=title)
profiles=[]
for a,(name,axis,center,lo,hi) in zip(ax[1],[('Northstrip atx395','y',395,350,365),('SEextension aty328','x',328,407,426),('NEpatch aty354.5','x',354.5,407,422)]):
 along=y if axis=='y' else x;cross=x if axis=='y' else y;sel=mask(q.buffer(2))&(abs(cross-center)<.65)&(along>lo)&(along<hi);order=np.argsort(along[sel]);aa=along[sel][order];dd=z[sel][order];tt=t[sel][order];a.plot(aa,dd,'.-',label='DSM');a.plot(aa,tt,'.-',label='DTM');a.set(title=name,xlabel='ENU'+axis+'m',ylabel='ODNm');a.legend();profiles.append({'name':name,'coordinate':aa.tolist(),'DSM':dd.tolist(),'DTM':tt.tolist()})
fig.savefig(R/'references/constant_lowdomains.png',dpi=150);out={'domains':rows,'threshold_components':components,'profiles':profiles,'geometry_modified':False,'method':'Geometrically selected diagnostic domains; insetsclipwholeowner; no heightfilter in domainstatistics. Eight-connected raster components below several thresholds, proximitytoexterior separately reported; not roof segmentation.'};(R/'references/constant_lowdomains.json').write_text(json.dumps(out,indent=2));print({name:{i:(r['DSM']['cells'],r['DSM'].get('median'),r['DTM'].get('median'),r['within01m']) for i,r in vals.items()} for name,vals in rows.items()})
