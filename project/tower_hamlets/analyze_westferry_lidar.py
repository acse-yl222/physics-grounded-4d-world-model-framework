"""Bounded 7 Westferry Circus observed roof audit; does not alter assembly."""
import json,hashlib
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point
from shapely.ops import transform,unary_union
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
g=json.loads((ROOT/'geometry.json').read_text());f=next(f for f in g['buildings'] if f['id']=='overture-building-6019910a-84f8-40b5-b9b0-cf50cabf225c');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(ROOT/'references/ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(20)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True,boundless=True);dtm=dt.read(1,window=w,masked=True,boundless=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
z=np.asarray(dsm);ground=np.asarray(dtm);valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm)
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4]};m=masks['0'];inner=masks['3']
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist()} if len(v) else {'count':0}
rep={'building_id':f['id'],'geometry_modified':False,'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'footprint_area_m2':p.area,'ground_scalar_m_odn':float(np.median(ground[m])),'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[v]),'dtm_odn':stats(ground[v])} for k,v in masks.items()},'visual_review':{'inspected':False},'limitations':['Native 1m DSM, mixed 2017–2020 dates versus 2026 footprint.','ODN minus local median DTM maps to unsurveyed flat scene.','Façades, parapets, machinery and historical changes unresolved.']}
fig,axs=plt.subplots(2,2,figsize=(15,11),layout='constrained')
for ax,sel,title in [(axs[0,0],valid,'Context; target red; other outlines white'),(axs[0,1],m,'Exact footprint DSM (masked outside raster)')]:
 im=ax.scatter(x[sel],y[sel],c=z[sel],s=20,marker='s',vmin=0,vmax=55);fig.colorbar(im,ax=ax,label='DSM m ODN')
 for nf in g['buildings']:
  for q in nf['geometry']:
   poly=Polygon(q['outer'],q.get('holes',[]))
   if poly.intersects(p.buffer(20)):
    for ring in [poly.exterior,*poly.interiors]:
     px,py=ring.xy;ax.plot(px,py,c='red' if nf['id']==f['id'] else 'white',lw=1)
 ax.set(xlim=(x.min(),x.max()) if sel is valid else (p.bounds[0]-2,p.bounds[2]+2),ylim=(y.min(),y.max()) if sel is valid else (p.bounds[1]-2,p.bounds[3]+2),title=title,xlabel='Local E m',ylabel='Local N m');ax.set_aspect('equal')
for ax,c,label in [(axs[1,0],x,'East'),(axs[1,1],y,'North')]:
 ax.scatter(c[m],z[m],s=9,alpha=.3,label='Exact footprint');ax.scatter(c[inner],z[inner],s=10,alpha=.5,label='3m inward');ax.axhline(9+rep['ground_scalar_m_odn'],c='red',label='Baseline 9m + local ground');ax.set(xlabel=label+' local m',ylabel='DSM m ODN',title=label+' profile');ax.legend()
fig.suptitle('7 Westferry Circus — measured roof distribution and retained mapped footprint');fig.savefig(ROOT/'references/westferry_lidar_review.png',dpi=140)
(ROOT/'references/westferry_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps(rep,indent=2))
# Partial surface only. Thresholds separate the coherent roof returns from ground;
# small neighbour height differences avoid spanning terrace cliffs/dropouts.
mask=m&(z>=35)&(z<=55)
verts=[];faces=[];lookup={}
for r in range(z.shape[0]-1):
 for c in range(z.shape[1]-1):
  for ij in [[(r,c),(r,c+1),(r+1,c+1)],[(r,c),(r+1,c+1),(r+1,c)]]:
   if not all(mask[i,j] for i,j in ij):continue
   zz=[float(z[i,j]) for i,j in ij]
   if max(zz)-min(zz)>1.5:continue
   tri=Polygon([(float(x[i,j]),float(y[i,j])) for i,j in ij])
   if not p.covers(tri):continue
   inds=[]
   for i,j in ij:
    if (i,j) not in lookup:
     lookup[i,j]=len(verts);verts.append([float(x[i,j]),float(y[i,j]),float(z[i,j])-rep['ground_scalar_m_odn']])
    inds.append(lookup[i,j])
   v=np.array([verts[k] for k in inds])
   if np.cross(v[1]-v[0],v[2]-v[0])[2]<0:inds.reverse()
   faces.append(inds)
obj=ROOT/'references/westferry_observed_roof_candidate.obj'
with obj.open('w') as h:
 h.write('# Intentional open observed surface, no inferred walls; local ENU metres\n')
 for v in verts:h.write('v '+' '.join(f'{q:.8f}' for q in v)+'\n')
 for face in faces:h.write('f '+' '.join(str(k+1) for k in face)+'\n')
all_inside=all(p.covers(Polygon([(verts[k][0],verts[k][1]) for k in face])) for face in faces)
rep['visual_review']={'inspected':True,'image':'westferry_lidar_review.png','observations':['North roof is coherent lower plateau about 36.4 m ODN; central and southeast roof has upper plateau about 54.5 m ODN.','Southwest side contains multiple lower terraces around 44.6 and 48.7 m ODN.','Western part of mapped footprint extends outside the retained raster; its roof and wall ownership are not observed.','DTM is bimodal, approximately 4–5 m and 10.8 m ODN, which makes any single flat-scene ground convention uncertain.'],'recommendation':'Observed roof surface only; acquire missing western raster and independent roof plan evidence before closing full roof or extruding perimeter walls.'}
rep['raster_coverage']={'valid_center_cells':int(m.sum()),'footprint_area_m2':p.area,'approximate_missing_area_fraction':float(1-m.sum()/p.area),'note':'Cell count/area is a diagnostic approximate coverage, not exact area clipping.'}
rep['module_readiness']={'ready':False,'reason':'Incomplete western raster and unresolved terrace boundaries; do not close or stretch missing roof.'}
rep['interfaces']={'plan_ownership':'Exact source footprint union including all holes; no wall removal or changes to neighbours','vertical_datum':'EA ODN minus local valid-footprint median DTM 4.771223068237305 m; flat scene convention only','ground_surface_or_supports_created':False}
rep['candidate']={'obj':obj.name,'obj_sha256':hashlib.sha256(obj.read_bytes()).hexdigest(),'vertices':len(verts),'triangles':len(faces),'projected_area_m2':sum(Polygon([(verts[k][0],verts[k][1]) for k in face]).area for face in faces),'all_triangles_inside_source_footprint':all_inside,'intentional_open_surface':True,'selection_dsm_odn_m':[35,55],'maximum_triangle_vertical_range_m':1.5,'selection_scope':'Diagnostic coherent rooftop cells; thresholds are filtering parameters, not semantic architectural detection.','bounds_local_xyz_m':[np.min(verts,axis=0).tolist(),np.max(verts,axis=0).tolist()]}
rep['limitations']+=['Missing triangles are unknown surfaces, not verified physical roof openings.','No closed architectural module generated and no assembly inputs changed.']
assert all_inside and len(faces)>0
(ROOT/'references/westferry_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps({'candidate':rep['candidate'],'interfaces':rep['interfaces'],'module_readiness':rep['module_readiness']},indent=2))
