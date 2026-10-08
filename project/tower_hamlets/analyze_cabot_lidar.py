"""Bounded Cabot dome evidence fit; leaves geometry unchanged."""
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon, Point
from shapely.ops import transform
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((root/'geometry.json').read_text()); f=next(f for f in g['buildings'] if f['id']=='overture-part-a3461c5d-098b-382d-b1d8-a6fbe5e6db1d')
p=Polygon(f['geometry'][0]['outer']); tr=Transformer.from_crs(g['crs'],27700,always_xy=True); back=Transformer.from_crs(27700,g['crs'],always_xy=True); pb=transform(tr.transform,p)
with rasterio.open(root/'references/ea_dsm_1m.tif') as ds, rasterio.open(root/'references/ea_dtm_1m.tif') as dt:
 b=pb.buffer(5).bounds;w=from_bounds(*b,ds.transform).round_offsets().round_lengths();a=ds.read(1,window=w,masked=True); terrain=dt.read(1,window=w,masked=True);t=ds.window_transform(w)
 rr,cc=np.indices(a.shape); xx,yy=rasterio.transform.xy(t,rr,cc);xx=np.array(xx).reshape(a.shape);yy=np.array(yy).reshape(a.shape);x,y=back.transform(xx,yy)
inside=np.array([p.contains(Point(i,j)) for i,j in zip(x.flat,y.flat)]).reshape(a.shape)
inner=np.array([p.buffer(-1.5).contains(Point(i,j)) for i,j in zip(x.flat,y.flat)]).reshape(a.shape)
valid=~np.ma.getmaskarray(a)&~np.ma.getmaskarray(terrain); mask=inner&valid
cx,cy=p.centroid.coords[0];radius=np.sqrt(p.area/np.pi);r=np.hypot(x-cx,y-cy);z=np.asarray(a); ground=float(np.median(np.asarray(terrain)[inside&valid]));q=r[mask]**2
# Fixed mapped centre and radius prevent arbitrary spatial overfitting. Robust radial parabola.
fit=least_squares(lambda v:v[0]-v[1]*q-z[mask],[30,.035],loss='soft_l1',f_scale=.6,bounds=([-100,0],[300,2]))
apex,k=fit.x; pred=apex-k*r*r;res=z-pred
flat=float(np.median(z[mask])); residual=res[mask]
# Also fit spherical cap z = centre_z + sqrt(R^2-r^2), R > footprint radius.
sph=least_squares(lambda v:v[0]+np.sqrt(v[1]**2-q)-z[mask],[15,16],loss='soft_l1',f_scale=.6,bounds=([-100,radius+0.01],[300,200]))
sz,sr=sph.x;spherical=sz+np.sqrt(np.maximum(0,sr*sr-r*r));sres=z-spherical
stats=lambda v:{'median_m':float(np.median(v)),'mae_m':float(np.mean(abs(v))),'rmse_m':float(np.sqrt(np.mean(v*v))),'p95_absolute_m':float(np.percentile(abs(v),95))}
rings=[]
for lo,hi in [(0,3),(3,6),(6,9),(9,12),(12,15)]:
 m=inside&valid&(r>=lo)&(r<hi)
 rings.append({'radius_range_m':[lo,hi],'count':int(m.sum()),'dsm_quantiles_odn_m':np.percentile(z[m],[10,50,90]).tolist()})
report={'building_id':f['id'],'geometry_modified':False,'source':'EA 1m DSM/DTM, OGL; mixed 2017–2020 survey','fit_domain':'Exact footprint eroded 1.5m; all valid cell centres; no outlier deletion, soft-L1 loss 0.6m','centre_local_m':[cx,cy],'equivalent_radius_m':radius,'samples_full':int((inside&valid).sum()),'samples_fit':int(mask.sum()),'ground_reference_m_odn':ground,'ground_percentiles_odn_m':np.percentile(np.asarray(terrain)[inside&valid],[5,50,95]).tolist(),'observed_dsm_percentiles_odn_m':np.percentile(z[inside&valid],[0,5,50,95,100]).tolist(),'paraboloid':{'apex_m_odn':float(apex),'k_per_m':float(k),'boundary_at_equivalent_radius_m_odn':float(apex-k*radius**2),'apex_above_local_dtm_m':float(apex-ground),'residual':stats(residual)},'spherical_cap':{'centre_z_odn_m':float(sz),'sphere_radius_m':float(sr),'apex_m_odn':float(sz+sr),'boundary_at_equivalent_radius_m_odn':float(sz+np.sqrt(sr*sr-radius*radius)),'residual':stats(sres[mask])},'flat_comparison':stats(z[mask]-flat),'radial_rings':rings,'caveats':['Roof boundary/eave is partly extrapolated beyond 1.5m eroded fit domain; do not regard as measured eave.','LiDAR DSM on glass can contain low returns or interpolation; residual plot must be inspected.','One metre gridded product cannot resolve structural glazing bars.','Height above median local DTM is a local relative convention, not surveyed foundation/platform height.','Source roof_height=27 tag is ambiguous and not used as a dimensional constraint.']}
# Shifted radial paraboloid: four parameters, bounded centre shift; spatial checkerboard holdout.
X=x[mask];Y=y[mask];Z=z[mask]
def shifted(v,X,Y): return v[0]-v[1]*((X-v[2])**2+(Y-v[3])**2)
def shifted_fit(sel): return least_squares(lambda v:shifted(v,X[sel],Y[sel])-Z[sel],[apex,k,cx,cy],loss='soft_l1',f_scale=.6,bounds=([-100,0,cx-3,cy-3],[300,2,cx+3,cy+3])).x
train=((np.floor(X/3)+np.floor(Y/3)).astype(int)%2)==0
sv=shifted_fit(np.ones(len(X),dtype=bool));tv=shifted_fit(train)
report['shifted_paraboloid']={'apex_m_odn':float(sv[0]),'k_per_m':float(sv[1]),'centre_local_m':sv[2:].tolist(),'apex_scene_z_m':float(sv[0]-ground),'residual':stats(Z-shifted(sv,X,Y)),'holdout_description':'Alternating 3m spatial blocks, all residuals retained','holdout_count':int((~train).sum()),'held_out_residual':stats(Z[~train]-shifted(tv,X[~train],Y[~train])),'full_fit_parameters':sv.tolist()}
report['visual_review']={'inspected':True,'observations':['DSM plan and radial profile strongly show coherent elevated dome surface with sparse very low dropouts, not a flat roof.','Centred radial model has east-west residual trend; shifted-centre robust fit supplied separately.','Outer ring plateaus near 31.8m ODN: likely surrounding roof or dome base, and spherical fit incorrectly extrapolates lower.'],'recommendation':'Use mapped outer footprint; approximate dome as shifted paraboloid clipped from below at 31.8m ODN, keeping base threshold estimated. Apex and broad curvature supported; do not invent glazing framing dimensions from this raster.'}
report['proposed_lower_surface_clip_m_odn']=31.8
report['proposed_lower_surface_clip_scene_z_m']=31.8-ground
fig,axs=plt.subplots(2,2,figsize=(13,10),layout='constrained');ex=[x.min(),x.max(),y.min(),y.max()]
for ax,data,title,lim in [(axs[0,0],np.where(inside,z,np.nan),'DSM inside exact footprint (m ODN)',None),(axs[0,1],np.where(mask,z-shifted(sv,x,y),np.nan),'Shifted paraboloid residual (m)',(-2,2))]:
 im=ax.scatter(x,y,c=data,s=24,marker='s',cmap='viridis' if lim is None else 'coolwarm',**({} if lim is None else {'vmin':lim[0],'vmax':lim[1]}));vx,vy=p.exterior.xy;ax.plot(vx,vy,'k-',lw=1);ax.set_aspect('equal');ax.set_title(title);fig.colorbar(im,ax=ax)
ax=axs[1,0];ax.scatter(r[inside&valid],z[inside&valid],s=8,alpha=.5,label='All footprint cells');line=np.linspace(0,radius,150);ax.plot(line,apex-k*line**2,label='Paraboloid');ax.plot(line,sz+np.sqrt(sr*sr-line**2),label='Spherical cap');ax.axvline(radius-1.5,color='grey',ls=':');ax.set(xlabel='Radius from mapped centroid (m)',ylabel='DSM elevation (m ODN)',title='Radial profile; dotted line approximates fit edge');ax.legend()
ax=axs[1,1];ax.hist(residual,bins=35,alpha=.6,label='Paraboloid');ax.hist(sres[mask],bins=35,alpha=.6,label='Spherical cap');ax.set(xlabel='Residual (m)',ylabel='Cell count',title=f'{mask.sum()} interior cells, robust fit; no residual trimming');ax.legend()
fig.suptitle('Cabot Place dome — measured gridded surface evidence, not survey-grade geometry');fig.savefig(root/'references/cabot_lidar_fit.png',dpi=150)
(root/'references/cabot_lidar_fit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
