"""Inspect Crossrail lower interface; does not mutate source geometry."""
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon
from shapely.ops import transform, unary_union
from shapely import contains_xy
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((ROOT/'geometry.json').read_text())
f=next(f for f in g['buildings'] if f['id']=='overture-part-c9f4e448-eff2-39ad-ac25-e7f6cf708826')
pf=next(q for q in g['buildings'] if q['id']=='overture-building-'+f['parent_id'])
p=unary_union([Polygon(s['outer'],s.get('holes',[])) for s in f['geometry']]); residual=unary_union([Polygon(s['outer'],s.get('holes',[])) for s in pf['geometry']]); union=p.union(residual)
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,union.buffer(10)).bounds,ds.transform).round_offsets().round_lengths(); dsm=ds.read(1,window=w,masked=True);dtm=dt.read(1,window=w,masked=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm);z=np.asarray(dsm);ground=np.asarray(dtm)
v=np.array(p.exterior.coords);edges=np.diff(v,axis=0);u=edges[np.argmax(np.linalg.norm(edges,axis=1))];u/=np.linalg.norm(u);vv=np.array([-u[1],u[0]]);cx,cy=p.centroid.coords[0];a=(x-cx)*u[0]+(y-cy)*u[1];b=(x-cx)*vv[0]+(y-cy)*vv[1]
pm=valid&contains_xy(p,x,y);rm=valid&contains_xy(residual,x,y);um=pm|rm
scalar=float(np.median(ground[pm]));bins=[]
for lo in np.arange(-150,150,10):
 m=um&(a>=lo)&(a<lo+10);low=m&(z<22)&(z>10)
 bins.append({'long_axis_range_m':[int(lo),int(lo+10)],'lower_return_count':int(low.sum()),'lower_dsm_odn_quantiles_10_25_50_75_90':np.percentile(z[low],[10,25,50,75,90]).tolist() if low.any() else []})
fig,axs=plt.subplots(3,1,figsize=(16,10),layout='constrained')
for ax,values,title,limits in [(axs[0],z,'DSM ODN: lower surfaces remain mixed with trees, roof and edge returns',(5,35)),(axs[1],ground,'DTM ODN: water/dock terrain is not station floor datum',(0,8))]:
 im=ax.scatter(a[um],b[um],c=values[um],s=14,marker='s',vmin=limits[0],vmax=limits[1]);fig.colorbar(im,ax=ax)
 for poly,color in [(p,'red'),(union,'black')]:
  q=np.array(poly.exterior.coords)-[cx,cy];ax.plot(q@u,q@vv,color=color,lw=1)
 ax.set_aspect('equal');ax.set(title=title,xlabel='Long axis m',ylabel='Cross axis m')
axs[2].scatter(a[pm],z[pm],s=3,alpha=.3,label='Mapped central part');axs[2].scatter(a[rm],z[rm],s=3,alpha=.3,label='Parent residual');axs[2].axhline(17.1,color='red',ls='--',label='SSL117.100 minus inferred Crossrail100m offset (site datum inferred)');axs[2].set(xlabel='Long axis m',ylabel='DSM ODN m',title='Observed levels do not establish SSL datum or lower building envelope');axs[2].legend()
fig.savefig(ROOT/'references/crossrail_lower_interface.png',dpi=140)
report={'geometry_modified':False,'part_id':f['id'],'parent_id':pf['id'],'footprint_areas_m2':{'part':p.area,'residual':residual.area,'union':union.area},'flattened_scene_datum_m_odn':scalar,'datum_status':'Median DTM under mapped part only; not station floor or surveyed foundation.','lower_return_definition':'DSM 10–22m ODN, within union; descriptive selection not classified deck.','long_axis_bins':bins,'source_level_evidence':{'park_ssl':117.100,'ground_ssl':111.250,'promenade_ssl':105.900,'ssl_to_odn_offset':'100m inferred at this site from primary Crossrail datum references supplied by coordinator; site article SSL datum itself not explicit','datum_reference':'https://learninglegacy.crossrail.co.uk/documents/multi-aquifer-pressure-relief-east-london-2/'},'interface_recommendation':{'can_replace_upper_roof':True,'can_assert_lower_body_envelope':False,'reason':'Parent and part are mapped roof envelopes; residual includes overhangs and rounded ends. Neither footprint nor DSM supplies a reliable vertical wall line.','safe_geometry_scope':'Keep observed roof and structural candidate independently editable. A provisional lower deck may be an explicitly estimated thin horizontal surface within central footprint only, not extruded parent union or inferred solid wall enclosure.','provisional_deck_elevation':{'z_odn_m':17.1,'z_scene_m':17.1-scalar,'basis':'SSL117.100 less inferred Crossrail100m datum offset; explicitly inferred site datum, not measured deck','consistency':'Exposed garden lower returns approximately17.8–18.1ODN are compatible with finishes and soil above this structural level; not independent proof.'},'parent_handling':'Do not retain 28m-high residual walls around lower curved roof. Hide/remove the misleading generic parent shell in candidate assembly and retain original mapping in provenance.','missing':['Georeferenced garden/deck plan','Verified SSL-to-ODN mapping or visible unambiguous deck control point','Actual lower facade/overhang footprint and height']},'visual_review':{'inspected':True,'image':'crossrail_lower_interface.png','observations':['Parent residual includes dock-edge bands around4–6ODN; roof-overhang footprint cannot define lower wall plane.','Central garden broad returns begin around18ODN; deck17.1ODN is plausible beneath soil/finishes but unobserved.','No complete lower-body vertical facade footprint is recoverable from this top surface raster.']}}
(ROOT/'references/crossrail_lower_interface.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'area':report['footprint_areas_m2'],'datum':scalar,'bins':bins},indent=2))
