from pathlib import Path
import json,hashlib,numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform,unary_union
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/impounding-evidence-001';O.mkdir(exist_ok=True);g=json.loads((R/'geometry.json').read_text());f=next(f for f in g['buildings'] if '0741fd47' in f['id']);p=Polygon(f['geometry'][0]['outer']);v=np.array(p.exterior.coords)[:-1];origin=v[0];eu=(v[1]-v[0]);eu/=np.linalg.norm(eu);ev=(v[3]-v[0]);ev/=np.linalg.norm(ev)
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(12)).bounds,ds.transform).round_offsets().round_lengths();Z=ds.read(1,window=w,masked=True,boundless=True);G=dt.read(1,window=w,masked=True,boundless=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape))
z=np.asarray(Z);ground=np.asarray(G);valid=~np.ma.getmaskarray(Z)&~np.ma.getmaskarray(G);m=valid&np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);core=valid&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);uv=np.stack([x-origin[0],y-origin[1]],axis=-1);u=uv@eu;t=uv@ev
# Asymmetric gable, cross-building ridge and optional along-axis grade; robust diagnostic only.
def pred(a,u,t):return a[0]-np.where(u<a[1],a[2],a[3])*abs(u-a[1])+a[4]*(t-14)
fit=least_squares(lambda a:pred(a,u[core],t[core])-z[core],[13,6.8,.3,.3,0],loss='soft_l1',f_scale=.3,bounds=([5,2,0,0,-.5],[30,12,2,2,.5]));a=fit.x
stats=lambda q:{'count':len(q),'percentiles_0_5_25_50_75_95_100':np.percentile(q,[0,5,25,50,75,95,100]).tolist()}
def resid(sel):
 r=z[sel]-pred(a,u[sel],t[sel]);return {'count':len(r),'within_0_5m':int((abs(r)<=.5).sum()),'within_1m':int((abs(r)<=1).sum()),'rmse_m':float(np.sqrt(np.mean(r*r))),'median_m':float(np.median(r))}
fig,axs=plt.subplots(2,2,figsize=(12,9),layout='constrained')
for ax,sel,title in [(axs[0,0],valid,'Context DSM'),(axs[0,1],m,'Exact footprint DSM')]:
 im=ax.scatter(x[sel],y[sel],c=z[sel],s=22,marker='s',vmin=5,vmax=18);fig.colorbar(im,ax=ax,label='ODN m');ax.plot(*np.vstack([v,v[0]]).T,'r');ax.set_aspect('equal');ax.set_title(title)
axs[1,0].scatter(u[m],z[m],s=8,c=t[m]);xx=np.linspace(0,np.linalg.norm(v[1]-v[0]),100);axs[1,0].plot(xx,pred(a,xx,np.full(len(xx),14)),'r');axs[1,0].set(xlabel='Across width m',ylabel='ODN m',title='All footprint cells; color along length')
axs[1,1].scatter(t[m],z[m]-pred(a,u[m],t[m]),s=10,c=u[m]);axs[1,1].axhline(0,c='red');axs[1,1].set(xlabel='Along length m',ylabel='Residual m',title='All-cell gable residual; color across width');fig.savefig(O/'dsm-spatial-review.png',dpi=150)
neighbors=[]
for nf in g['buildings']:
 if nf['id']==f['id']:continue
 q=unary_union([Polygon(h['outer'],h.get('holes',[])) for h in nf['geometry']]);d=p.distance(q)
 if d<15:neighbors.append({'id':nf['id'],'name':nf.get('name'),'gap_m':d,'overlap_m2':p.intersection(q).area,'shared_boundary_m':p.boundary.intersection(q.boundary).length})
d={'source_geometry':f,'area_m2':p.area,'dsm_odn':stats(z[m]),'dtm_odn':stats(ground[m]),'fit_parameters_ridge_odn_across_position_slopes_along_grade':a.tolist(),'all_cell_residual':resid(m),'inset_1m_residual':resid(core),'neighbors':neighbors,'datum':'Scene z = ODN - 4.28000021. No local DTM normalization.','raster_vintage':'Unresolved composite; catalogue overlap does not assign building capture date.','source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']}};(O/'audit.json').write_text(json.dumps(d,indent=2));np.savez(O/'roof-samples.npz',x=x[m],y=y[m],dsm_odn=z[m],dtm_odn=ground[m],u=u[m],along=t[m]);print(json.dumps({k:val for k,val in d.items() if k not in ['source_geometry','source_hashes']},indent=2))
