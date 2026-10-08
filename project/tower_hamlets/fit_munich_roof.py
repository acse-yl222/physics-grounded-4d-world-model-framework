"""Bounded, conditional Munich roof profile; source rasters stay unchanged."""
from pathlib import Path
import json, hashlib
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon, Point
from shapely.ops import transform, unary_union
from pyproj import Transformer
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
ID='overture-building-118734b4-49b7-4a0b-80f8-4f7b33801433'
g=json.loads((ROOT/'geometry.json').read_text())
f=next(a for a in g['buildings'] if a['id']==ID)
p=unary_union([Polygon(a['outer'],a.get('holes',[])) for a in f['geometry']])
forward=Transformer.from_crs(g['crs'],27700,always_xy=True)
back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds:
    w=from_bounds(*transform(forward.transform,p.buffer(2)).bounds,ds.transform).round_offsets().round_lengths()
    dsm=ds.read(1,window=w,masked=True)
    rr,cc=np.indices(dsm.shape)
    xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc)
    x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
z=np.asarray(dsm,dtype=float)
valid=~np.ma.getmaskarray(dsm)
inside=valid & np.array([p.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
inner=valid & np.array([p.buffer(-2).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
sel=inner & (z>18) & (z<22)
theta=np.deg2rad(-10)
u=x*np.cos(theta)+y*np.sin(theta)
v=-x*np.sin(theta)+y*np.cos(theta)
knots=np.arange(np.floor(v[sel].min()),np.ceil(v[sel].max())+1)
uc=float(np.mean(u[sel]))
D=np.diff(np.eye(len(knots)),2,axis=0)
def basis(values):
    return np.array([np.interp(values,knots,q) for q in np.eye(len(knots))]).T
def fit(mask,tilt=False):
    B=basis(v[mask]); reg=D
    if tilt:
        B=np.column_stack([B,u[mask]-uc]);reg=np.column_stack([D,np.zeros(len(D))])
    initial=np.full(B.shape[1],20.)
    if tilt: initial[-1]=0
    return least_squares(lambda c:np.r_[B@c-z[mask],.15*reg@c],initial,loss='soft_l1',f_scale=.1).x
def predict(c,mask,tilt=False):
    return basis(v[mask])@c[:len(knots)]+(c[-1]*(u[mask]-uc) if tilt else 0)
def metrics(e):
    return {'cells':len(e),'rmse_m':float(np.sqrt(np.mean(e**2))),'median_abs_m':float(np.median(abs(e))),'p95_abs_m':float(np.percentile(abs(e),95)),'max_abs_m':float(np.max(abs(e)))}
fold_index=np.floor((u-u[sel].min())/2).astype(int)%3
validation={}
for tilt in [False,True]:
    folds=[]; pooled=[]
    for fold in range(3):
        test=sel&(fold_index==fold); train=sel&~test
        c=fit(train,tilt);err=z[test]-predict(c,test,tilt);pooled.extend(err)
        folds.append({'fold':fold,'train_cells':int(train.sum()),**metrics(err)})
    validation['profile_plus_longitudinal_tilt' if tilt else 'profile_only']={'folds':folds,'pooled':metrics(np.array(pooled))}
# Retain the simpler profile unless a modest longitudinal term has substantial held-out benefit.
plain=validation['profile_only']['pooled']['rmse_m']; tilted=validation['profile_plus_longitudinal_tilt']['pooled']['rmse_m']
use_tilt=bool(tilted < .9*plain)
c=fit(sel,use_tilt);pred=(basis(v.ravel())@c[:len(knots)]).reshape(v.shape)+(c[-1]*(u-uc) if use_tilt else 0)
ridge_indices=[i for i in range(1,len(knots)-1) if c[i]>c[i-1] and c[i]>c[i+1]]
report={'building_id':ID,'source_ids':['ea_lidar_dsm_1m','overture_buildings_20260923'],'source_hashes':{a:hashlib.sha256((ROOT/a).read_bytes()).hexdigest() for a in ['geometry.json','references/ea_dsm_1m.tif']},'coordinate_crs':g['crs'],'rotation_deg':-10,'u_formula':'x*cos(theta)+y*sin(theta)','v_formula':'-x*sin(theta)+y*cos(theta)','u_center_m':uc,'selection':'Valid native 1m cells, strictly inside footprint inward buffer 2m, 18 < DSM ODN < 22m. No residual-based test rejection.','footprint_cells':int(inside.sum()),'inset_cells':int(inner.sum()),'selected_cells':int(sel.sum()),'holdout':'Three folds, alternating 2m longitudinal strips relative to selected u minimum; each selected cell predicted exactly once out of fold.','validation':validation,'model_selection':'Longitudinal tilt retained only if pooled spatial holdout RMSE improves by at least 10%.','selected_model':'profile_plus_longitudinal_tilt' if use_tilt else 'profile_only','knots_v_m':knots.tolist(),'height_odn_m':c[:len(knots)].tolist(),'longitudinal_slope_m_per_m':float(c[-1]) if use_tilt else 0.,'datum_odn_m':4.28000020980835,'in_sample':metrics((z-pred)[sel]),'local_ridge_knots':[{'v_m':float(knots[i]),'height_odn_m':float(c[i])} for i in ridge_indices],'geometry_modified':False,'limitations':['Conditional interior fit only: low returns and footprint perimeter are unmodelled.','1m linear spline knots are estimated, not independently measured architectural breaklines.','Mixed 2017–2020 EA DSM versus 2026 mapped ownership footprint; current physical changes unknown.','Do not terminate roof or create walls at mapped owner boundaries.','No optical imagery, facade, roof equipment or material reconstruction in this fit.','Shared 4.28m ODN datum is retained from museum group, not this building terrain median.'],'visual_reviewed':False}
fig,axs=plt.subplots(1,3,figsize=(17,5),layout='constrained')
axs[0].scatter(v[inside],z[inside],s=8,c='0.7',label='Full owner footprint')
axs[0].scatter(v[sel],z[sel],s=10,c=u[sel],cmap='viridis',label='Selected interior')
axs[0].plot(knots,c[:len(knots)],color='red',lw=2,label='Profile at mean u')
axs[0].set(xlabel='Across row v (m)',ylabel='ODN elevation (m)',ylim=(17,22),title='Munich: observed repeated roof profile');axs[0].legend(fontsize=8)
im=axs[1].scatter(u[sel],v[sel],c=(z-pred)[sel],cmap='RdBu_r',vmin=-.5,vmax=.5,s=32,marker='s')
fig.colorbar(im,ax=axs[1],label='DSM minus model (m)');axs[1].set(xlabel='Along row u (m)',ylabel='Across row v (m)',aspect='equal',title='Final fit residuals')
axs[2].scatter(u[sel],v[sel],c=fold_index[sel],cmap='Set1',vmin=0,vmax=2,s=32,marker='s');axs[2].set(xlabel='Along row u (m)',ylabel='Across row v (m)',aspect='equal',title='Spatial holdout strips (3 folds)')
fig.savefig(ROOT/'references/munich_profile_fit.png',dpi=150)
# Export only triangles wholly supported by selected native cells near the fitted profile.
# Discarded western ridge departures remain in the original raw observation asset.
support=sel & (abs(z-pred)<=.30)
vertices=[]; faces=[]; index={}; area=0.
for row in range(z.shape[0]-1):
    for col in range(z.shape[1]-1):
        for tri in [[(row,col),(row,col+1),(row+1,col+1)],[(row,col),(row+1,col+1),(row+1,col)]]:
            if not all(support[a] for a in tri): continue
            xy=np.array([[x[a],y[a]] for a in tri])
            cross=float(np.linalg.det(np.array([xy[1]-xy[0],xy[2]-xy[0]])))
            if cross<0: tri.reverse()
            face=[]
            for a in tri:
                if a not in index:
                    index[a]=len(vertices)+1
                    vertices.append([float(x[a]),float(y[a]),float(pred[a]-report['datum_odn_m'])])
                face.append(index[a])
            faces.append(face); area+=abs(cross)/2
obj=ROOT/'references/munich_profile_roof.obj'
obj.write_text('# Partial conditional fitted surface, ENU metres; z = ODN - 4.28000020980835\n'+'\n'.join('v '+' '.join(f'{v:.9f}' for v in q) for q in vertices)+'\n'+'\n'.join('f '+' '.join(map(str,q)) for q in faces)+'\n')
report['candidate']={'obj':obj.name,'vertices':len(vertices),'triangles':len(faces),'projected_area_m2':area,'owner_footprint_area_m2':float(p.area),'owner_footprint_coverage_fraction':area/p.area,'support_cells':int(support.sum()),'support_rule':'All three native triangle vertices satisfy 2m inset, 18<ODN<22 and |observed-model|<=0.30m; no interpolation across rejected cells.','sha256':hashlib.sha256(obj.read_bytes()).hexdigest(),'acceptance':'Partial exploratory surface only. Full owner replacement rejected due to structured western-strip departures.'}
(ROOT/'references/munich_profile_fit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['selected_cells','selected_model','validation','local_ridge_knots']},indent=2))
