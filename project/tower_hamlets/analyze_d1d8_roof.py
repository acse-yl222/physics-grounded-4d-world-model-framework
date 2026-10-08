from pathlib import Path
import json
exec(Path(__file__).with_name('review_d1d8_roof.py').read_text().split('rows=[]')[0])
from scipy.ndimage import label
m=mask(p);th=np.deg2rad(-5);u=x*np.cos(th)+y*np.sin(th);v=-x*np.sin(th)+y*np.cos(th)
low=m&(z<10);high=m&(z>30)&(z<34);lab,n=label(low);sizes=sorted([int((lab==i).sum()) for i in range(1,n+1)],reverse=True)
# Geometric west strip, chosen after visual inspection; no test residual rejection.
dom=mask(p.buffer(-2))&(x<-428);A=np.stack([np.ones(x.shape),x+437,y+405],axis=-1);c=fitplane(dom,A);checks={}
for name,arr in [('x',x),('y',y)]:
 folds=np.floor(arr/3).astype(int)%3;es=[]
 for k in range(3):
  train=dom&(folds!=k);test=dom&(folds==k)
  if train.sum()>10 and test.sum():es.extend((z-A@fitplane(train,A))[test])
 checks[name]=metric(np.array(es))
fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
for ax,a,title,lim in zip(axs,[z,t,z-t],['DSM ODN','DTM ODN','DSM minus DTM'],[(2,38),(2,6),(0,34)]):
 im=ax.scatter(x[m],y[m],c=a[m],s=20,marker='s',vmin=lim[0],vmax=lim[1]);fig.colorbar(im,ax=ax);ax.plot(*p.exterior.xy,'r-');ax.set(aspect='equal',title=title)
fig.savefig(R/'references/d1d8_roof_structure.png',dpi=150)
native=json.loads((R/'references/d1d8_native.json').read_text());verts=np.array(native['objects'][0]['vertices']);
r={'building_id':fs[0]['id'],'native_source_sha256':native['sha256'],'native_objects':[{'name':o['name'],'properties':o['properties']} for o in native['objects']],'native_bounds':[verts.min(0).tolist(),verts.max(0).tolist()],'low_return_cells':int(low.sum()),'low_return_stats':stats(z[low]),'low_dsm_minus_dtm':stats((z-t)[low]),'low_exact_dtm_within_1cm':int((abs(z-t)[low]<.01).sum()),'low_components_4connected_cells':sizes,'dominant_plateau_30to34_odn':stats(z[high]),'geometric_west_domain':{'selection':'2m inset and x<-428 selected after raster inspection; exploratory, no independent domain selection','cells':int(dom.sum()),'center_xy':[-437,-405],'plane_odn_coefficients':c.tolist(),'spatial_3m_strip_holdout_all_cells':checks},'decision':'Hold geometry replacement. Elevated plateau is clear but northeastern terrain-like region may be real open footprint region or missing/incorrect roof returns. Mapped polygon has no hole. Existing data do not determine full building envelope; whole footprint extrusion or invented courtyard would assert unsupported geometry.','datum':'ODN minus4.28000021 for scene; actual per-building raster capture vintage unresolved','geometry_changed':False,'photo_facade_identity':'No licensed photo correspondence established; no facade invented.'}
(R/'references/d1d8_roof_structure.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
