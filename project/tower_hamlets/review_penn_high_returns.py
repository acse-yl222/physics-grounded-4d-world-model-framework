"""Describe spatially coherent elevated returns without naming equipment."""
from pathlib import Path
import json,warnings
warnings.filterwarnings('ignore',category=DeprecationWarning)
import numpy as np,rasterio
from rasterio.windows import from_bounds,Window
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union,transform
from pyproj import Transformer
from scipy.ndimage import label
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());ID='overture-part-094b8f17-78c6-3dbd-bf2e-430c36321ab5';f=next(a for a in g['buildings'] if a['id']==ID);p=unary_union([Polygon(a['outer'],a.get('holes',[])) for a in f['geometry']]);fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 w=from_bounds(*transform(fw.transform,p.buffer(2)).bounds,ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height));d=ds.read(1,window=w,masked=True);rr,cc=np.indices(d.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=bk.transform(np.array(xx).reshape(d.shape),np.array(yy).reshape(d.shape))
z=np.asarray(d,float);sel=~np.ma.getmaskarray(d)&np.array([p.buffer(-2).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);prior=json.loads((R/'references/penn_roof_review.json').read_text())['parts'][0];cx,cy=prior['center_local_xy_m'];c=prior['plane_fits']['2']['coefficients'];pred=c[0]+c[1]*(x-cx)+c[2]*(y-cy);res=z-pred
report={'building_id':ID,'plane_source':'penn_roof_review.json parts[0] plane_fits[2]','selection':'All valid1m cells within2m footprint inset; positive residual thresholds are descriptive post-fit groups, not independent validation.','thresholds':{},'limitations':['Mixed2017–2020 EA1mDSM vs2026 mapped footprint.','8-neighbour connectivity can join diagonal cells; footprints below are native cell centers, not measured object edges.','Thresholded groups do not establish equipment identity, material, count of real objects or current existence.','Residual-based groups must not be used to claim independently validated roof accuracy.'],'geometry_modified':False,'visual_reviewed':False}
fig,axs=plt.subplots(1,3,figsize=(15,6),layout='constrained')
for ax,threshold in zip(axs,[.3,.4,.5]):
 m=sel&(res>threshold);labs,n=label(m,structure=np.ones((3,3),int));groups=[]
 for k in range(1,n+1):
  cells=labs==k;coords=np.column_stack([x[cells],y[cells],z[cells],res[cells]])
  groups.append({'label':k,'cells':int(cells.sum()),'centroid_xy_m':[float(x[cells].mean()),float(y[cells].mean())],'bounds_cell_centers_xy_m':[float(x[cells].min()),float(y[cells].min()),float(x[cells].max()),float(y[cells].max())],'odn_min_median_max_m':np.percentile(z[cells],[0,50,100]).tolist(),'residual_min_median_max_m':np.percentile(res[cells],[0,50,100]).tolist(),'cells_local_x_y_odn_residual':coords.tolist()})
 report['thresholds'][str(threshold)]={'selected_cells':int(m.sum()),'components':sorted(groups,key=lambda a:-a['cells'])}
 ax.scatter(x[sel],y[sel],c='lightgray',s=30,marker='s');im=ax.scatter(x[m],y[m],c=labs[m],cmap='tab20',s=42,marker='s');xxp,yyp=p.exterior.xy;ax.plot(xxp,yyp,c='black',lw=.8)
 for q in groups:ax.text(*q['centroid_xy_m'],str(q['label']),fontsize=8)
 ax.set(aspect='equal',xlabel='Local east (m)',ylabel='Local north (m)',title=f'Residual >{threshold}m: {int(m.sum())} cells')
fig.savefig(R/'references/penn_high_returns.png',dpi=150);(R/'references/penn_high_returns.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:[(a['cells'],a['centroid_xy_m'],a['residual_min_median_max_m']) for a in v['components']] for k,v in report['thresholds'].items()},indent=2))
