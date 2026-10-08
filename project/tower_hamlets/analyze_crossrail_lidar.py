"""Bounded Crossrail Place roof evidence; deliberately does not edit geometry."""
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon, Point
from shapely.ops import transform
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((ROOT/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id']=='overture-part-c9f4e448-eff2-39ad-ac25-e7f6cf708826')
p=Polygon(f['geometry'][0]['outer']);tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(35)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True);dtm=dt.read(1,window=w,masked=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm);z=np.asarray(dsm);ground=np.asarray(dtm);nh=z-ground
masks={str(erosion):valid&np.array([p.buffer(-erosion).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for erosion in [0,1,2,3,4]}
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist(),'mean_m':float(np.mean(v)),'std_m':float(np.std(v))}
# Axis along the longest original footprint edge, preserving mapped orientation.
v=np.array(p.exterior.coords);edges=np.diff(v,axis=0);u=edges[np.argmax(np.linalg.norm(edges,axis=1))];u=u/np.linalg.norm(u);vv=np.array([-u[1],u[0]]);cx,cy=p.centroid.coords[0];a=(x-cx)*u[0]+(y-cy)*u[1];b=(x-cx)*vv[0]+(y-cy)*vv[1]
rep={'building_id':f['id'],'name':f['name'],'geometry_modified':False,'source':'EA 1m DSM/DTM OGL, mixed 2017–2020; footprint release 2026-09-23','current_assumed_height_m':f['height_m'],'axis_local_xy':u.tolist(),'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[m]),'dtm_odn':stats(ground[m]),'cellwise_dsm_minus_dtm':stats(nh[m])} for k,m in masks.items()},'visual_review':{'inspected':False},'caveats':['Mixed 2017–2020 LiDAR versus 2026 footprint can reflect historical state.','DTM scalar is relative height convention, not surveyed foundation.','One metre DSM cannot resolve parapets or facade details.']}

rep['parent_context']=[{'id':q['id'],'height_m':q['height_m'],'height_basis':q['height_basis'],'geometry':q['geometry']} for q in g['buildings'] if q['id']=='overture-building-'+f['parent_id']]
rep['ground_scalar_m_odn']=float(np.median(ground[masks['0']]))
m=masks["0"];inner=masks["2"]
# Upper-envelope circle fit uses distributed longitudinal samples, not all vegetation returns.
bins=[]
for left in np.arange(-13,13,1.):
 sel=inner&(b>=left)&(b<left+1)
 if sel.sum()>40: bins.append([left+.5,float(np.percentile(z[sel],97)),int(sel.sum())])
bc=np.array(bins);B=bc[:,0];Z=bc[:,1]
# Circle: b²+z² = 2*b0*b + 2*z0*z + C.
coef=np.linalg.lstsq(np.column_stack([2*B,2*Z,np.ones(len(B))]),B*B+Z*Z,rcond=None)[0]
b0,z0,cc=coef;radius=float(np.sqrt(cc+b0*b0+z0*z0));pred=z0+np.sqrt(radius**2-(B-b0)**2)
rep['upper_envelope_circle_fit']={'method':'97th percentile DSM in 1m cross-axis bins within 2m inward footprint; algebraic circle fit; longitudinally distributed roof envelope, not vegetation surface','cross_axis_bins_b_z97_count':bins,'cross_axis_center_m':float(b0),'circle_center_z_odn_m':float(z0),'radius_m':radius,'apex_z_odn_m':float(z0+radius),'apex_scene_z_m':float(z0+radius-rep['ground_scalar_m_odn']),'bin_rmse_m':float(np.sqrt(np.mean((pred-Z)**2))),'model_scope':'Only upper roof envelope; not proof of continuous glazing across open garden.'}
rep['mapped_part_extent']={'area_m2':p.area,'centroid_local_xy':[cx,cy],'long_axis_range_m':[float(a[m].min()),float(a[m].max())],'cross_axis_range_m':[float(b[m].min()),float(b[m].max())],'description':'Mapped part spans approximately 276m by 29m central strip, most of longitudinal roof, excluding rounded ends and thin side residuals; not merely entrance canopy.'}
rep['parent_residual_stats']=[]
for pf in g['buildings']:
 if pf['id']=='overture-building-'+f['parent_id']:
  for geom in pf['geometry']:
   pp=Polygon(geom['outer'],geom.get('holes',[]));pm=valid&np.array([pp.contains(Point(xx,yy)) for xx,yy in zip(x.flat,y.flat)]).reshape(x.shape)
   rep['parent_residual_stats'].append({'area_m2':pp.area,'dsm_odn':stats(z[pm]) if pm.any() else None,'height_m':pf['height_m'],'height_basis':pf['height_basis']})
rep['visual_review']={'inspected':True,'image':'crossrail_lidar_review.png','observations':['A smooth upper arch envelope is repeated along the longitudinal span; broad geometry supports barrel-like upper envelope.','Two broad central longitudinal gaps expose lower returns around 18–20m ODN; vegetation-like irregular returns and lower terrace cannot be classified as roof.','Mapped part is central strip of most station length, with rounded ends and narrow side residuals belonging to parent.','A continuous full-span barrel surface would incorrectly cover garden openings; current 9m part and 28m parent are also inconsistent with observed envelope.'],'recommendation':'Coordinate parent and part in one roof reconstruction. Fit upper arch envelope but first establish garden opening boundaries from permissible plan evidence. Do not simply set entire part to 25.6m flat or create continuous barrel; explicit open roof regions required.'}
rep['caveats']+=['A circle fits the upper envelope but roof opening boundaries require licensed image or plan evidence.','Ground DTM varies across dock context; median 3.979m ODN is only flattened-scene convention.','Parent residual source-reported 28m height does not establish roof absolute datum.']
fig,axs=plt.subplots(2,2,figsize=(16,10),layout='constrained')
m=masks['0'];inner=masks['2']
ax=axs[0,0];im=ax.scatter(x,y,c=nh,s=7,marker='s',vmin=0,vmax=40,cmap='viridis');fig.colorbar(im,ax=ax,label='DSM − DTM (m)')
for nf in g['buildings']:
 for geom in nf['geometry']:
  poly=Polygon(geom['outer'])
  if poly.intersects(p.buffer(35)):
   px,py=poly.exterior.xy;ax.plot(px,py,color='red' if nf['id']==f['id'] else 'white',lw=2 if nf['id']==f['id'] else .6)
ax.set(xlim=(x.min(),x.max()),ylim=(y.min(),y.max()),title='Target red; context outlines white',xlabel='Local E (m)',ylabel='Local N (m)');ax.set_aspect('equal')
ax=axs[0,1];im=ax.scatter(a[m],b[m],c=z[m],marker='s',s=10,vmin=15,vmax=38);fig.colorbar(im,ax=ax,label='DSM m ODN');ax.set(title='Exact part cells in footprint-axis coordinates',xlabel='Long axis (m)',ylabel='Cross axis (m)');ax.set_aspect('equal')
rep['longitudinal_bins']=[]
for low in np.arange(np.floor(a[m].min()/10)*10,a[m].max(),10):
 mm=inner&(a>=low)&(a<low+10)
 if mm.any():rep['longitudinal_bins'].append({'range_m':[float(low),float(low+10)],'dsm_odn':stats(z[mm])})
for ax,c,label in [(axs[1,0],a,'Long axis'),(axs[1,1],b,'Cross axis')]:
 ax.scatter(c[m],z[m],s=5,alpha=.2,label='All exact-footprint DSM');ax.scatter(c[inner],z[inner],s=5,alpha=.4,label='Interior 2m DSM');ax.set(xlabel=label+' (m)',ylabel='DSM m ODN',title=label+' profile');ax.legend(fontsize=8)
axs[1,1].plot(B,pred,color='red',lw=2,label='Upper-envelope circle');axs[1,1].legend(fontsize=8)
fig.suptitle('Crossrail Place — exact mapped part versus EA 1m elevation evidence')
fig.savefig(ROOT/'references/crossrail_lidar_review.png',dpi=140)
(ROOT/'references/crossrail_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps({k:v for k,v in rep.items() if k not in ['parent_context','longitudinal_bins']},indent=2))
