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
with rasterio.open(ROOT/'references/westferry_ea_dsm_1m.tif') as ds,rasterio.open(ROOT/'references/westferry_ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(tr.transform,p.buffer(20)).bounds,ds.transform).round_offsets().round_lengths();dsm=ds.read(1,window=w,masked=True,boundless=True);dtm=dt.read(1,window=w,masked=True,boundless=True);t=ds.window_transform(w);rr,cc=np.indices(dsm.shape);xx,yy=rasterio.transform.xy(t,rr,cc);x,y=back.transform(np.array(xx).reshape(dsm.shape),np.array(yy).reshape(dsm.shape))
z=np.asarray(dsm);ground=np.asarray(dtm);valid=~np.ma.getmaskarray(dsm)&~np.ma.getmaskarray(dtm)
masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,1,2,3,4]};m=masks['0'];inner=masks['3']
def stats(v):return {'count':len(v),'quantiles_0_5_10_25_50_75_90_95_100_m':np.percentile(v,[0,5,10,25,50,75,90,95,100]).tolist()} if len(v) else {'count':0}
rep={'building_id':f['id'],'geometry_modified':False,'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['geometry.json','references/westferry_ea_dsm_1m.tif','references/westferry_ea_dtm_1m.tif']},'footprint_area_m2':p.area,'ground_scalar_m_odn':float(np.median(ground[m])),'stats_by_inward_buffer_m':{k:{'dsm_odn':stats(z[v]),'dtm_odn':stats(ground[v])} for k,v in masks.items()},'visual_review':{'inspected':False},'limitations':['Native 1m DSM, mixed 2017–2020 dates versus 2026 footprint.','ODN minus local median DTM maps to unsurveyed flat scene.','Façades, parapets, machinery and historical changes unresolved.']}
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
fig.suptitle('7 Westferry Circus — measured roof distribution and retained mapped footprint');fig.savefig(ROOT/'references/westferry_complete_lidar_review.png',dpi=140)
(ROOT/'references/westferry_complete_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
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
obj=ROOT/'references/westferry_complete_observed_roof_candidate.obj'
with obj.open('w') as h:
 h.write('# Intentional open observed surface, no inferred walls; local ENU metres\n')
 for v in verts:h.write('v '+' '.join(f'{q:.8f}' for q in v)+'\n')
 for face in faces:h.write('f '+' '.join(str(k+1) for k in face)+'\n')
all_inside=all(p.covers(Polygon([(verts[k][0],verts[k][1]) for k in face])) for face in faces)
rep['visual_review']={'inspected':False}
rep['candidate']={'obj':obj.name,'vertices':len(verts),'triangles':len(faces),'all_inside':all_inside,'intentional_open_surface':True,'sha256':hashlib.sha256(obj.read_bytes()).hexdigest()}
rep['raster_validation']={}
for kind in ['dsm','dtm']:
 with rasterio.open(ROOT/f'references/westferry_ea_{kind}_1m.tif') as new,rasterio.open(ROOT/f'references/ea_{kind}_1m.tif') as old:
  bounds=(max(new.bounds.left,old.bounds.left),max(new.bounds.bottom,old.bounds.bottom),min(new.bounds.right,old.bounds.right),min(new.bounds.top,old.bounds.top))
  nv=new.read(1,window=from_bounds(*bounds,new.transform));ov=old.read(1,window=from_bounds(*bounds,old.transform))
  assert new.crs.to_epsg()==27700 and (new.width,new.height)==(67,102) and np.array_equal(nv,ov)
  rep['raster_validation'][kind]={'epsg':27700,'width':new.width,'height':new.height,'resolution_m':list(new.res),'overlap_cells':int(nv.size),'overlap_exact_equal':bool(np.array_equal(nv,ov)),'all_footprint_inside_raster':bool(Polygon([(new.bounds.left,new.bounds.bottom),(new.bounds.right,new.bounds.bottom),(new.bounds.right,new.bounds.top),(new.bounds.left,new.bounds.top)]).covers(transform(tr.transform,p)))}
(ROOT/'references/westferry_complete_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps(rep['raster_validation'],indent=2))
rep['visual_review']={'inspected':True,'image':'westferry_complete_lidar_review.png','observations':['Full footprint is now covered, including western corner.','North band has coherent 36.4 m ODN lower roof; central and southeast core approximately 54.5 m ODN.','Southwest slanted band contains coherent intermediate terraces around 44.6 and 48.7 m ODN.','Some roof returns extend across western mapped boundary; this boundary should remain an ownership seam, not automatically become an exposed facade.','Low edge returns and one-metre transitions do not establish exact terrace wall lines.'],'recommendation':'Roof tier partition is a reasonable next candidate, but should first fit straight breaklines from coherent samples and hold out cells for validation. Current deliverable remains observed surface; no unverified closed walls.'}
rep['coherent_roof_groups']=[]
for lo,hi in [(36,37),(44,45.5),(48,49.5),(54,55)]:
 sel=inner&(z>=lo)&(z<=hi)
 rep['coherent_roof_groups'].append({'selection_odn_m':[lo,hi],'stats':stats(z[sel]),'local_xy_bounds_m':[[float(x[sel].min()),float(y[sel].min())],[float(x[sel].max()),float(y[sel].max())]],'scene_z_median_m':float(np.median(z[sel])-rep['ground_scalar_m_odn'])})
rep['candidate']['projected_area_m2']=sum(Polygon([(verts[k][0],verts[k][1]) for k in face]).area for face in faces)
rep['candidate']['selection']={'dsm_odn_m':[35,55],'max_triangle_height_range_m':1.5,'missing_triangles':'Unknown surfaces, not real openings'}
rep['module_readiness']={'ready':False,'reason':'Full raster coverage verified, but fitted terrace partitions and boundary ownership remain unverified. No closed module or global edits.'}
rep['interfaces']={'plan':'Exact source footprint with holes preserved, no inferred neighbour walls','vertical':'ODN minus median full-footprint DTM; unsurveyed flattened scene convention, not absolute foundation height','ground_scalar_m_odn':rep['ground_scalar_m_odn'],'change_from_partial_data_ground_scalar_m':rep['ground_scalar_m_odn']-4.771223068237305}
(ROOT/'references/westferry_complete_lidar_review.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps({'ground':rep['ground_scalar_m_odn'],'candidate':rep['candidate'],'groups':rep['coherent_roof_groups']},indent=2))
