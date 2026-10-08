from pathlib import Path
import json,hashlib,numpy as np,rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union,transform
from pyproj import Transformer
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-roof-visibility-audit-001';O.mkdir(exist_ok=True);g=json.loads((R/'geometry.json').read_text());owner='overture-part-b317a51d-586a-3b78-9ee5-b685a2db94a0';b=next(b for b in g['buildings'] if b['id']==owner);p=Polygon(b['geometry'][0]['outer']);src=json.loads((R/'references/morgan_massing_study_002.json').read_text());zones=[(q,unary_union([Polygon(s['outer'],s.get('holes',[])) for s in q['support_xy']])) for q in src['zones'] if q['owner']==owner];fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds,rasterio.open(R/'references/ea_dtm_1m.tif') as dt:
 w=from_bounds(*transform(fw.transform,p.buffer(5)).bounds,ds.transform).round_offsets().round_lengths();Z=ds.read(1,window=w,masked=True,boundless=True);T=dt.read(1,window=w,masked=True,boundless=True);rr,cc=np.indices(Z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=bk.transform(np.array(xx).reshape(Z.shape),np.array(yy).reshape(Z.shape));grid={'crs':str(ds.crs),'window':[w.col_off,w.row_off,w.width,w.height],'transform':list(ds.window_transform(w)),'resolution':list(ds.res)}
z=np.asarray(Z);dtm=np.asarray(T);valid=~np.ma.getmaskarray(Z);points=[Point(xx,yy) for xx,yy in zip(x.flat,y.flat)]
def mask(poly):return np.array([poly.covers(q) for q in points]).reshape(x.shape)
inside=mask(p);sel=valid&inside;prediction=np.full(x.shape,np.nan)
for q,poly in zones:prediction[mask(poly)]=q['odn_m']
def stats(m,h=None):
 zz=z[m];d={'cells':int(m.sum()),'odn_quantiles_p0_p10_p25_p50_p75_p90_p100':np.percentile(zz,[0,10,25,50,75,90,100]).tolist() if len(zz) else []}
 if h is not None and len(zz):
  e=zz-h;d.update(rmse_m=float(np.sqrt(np.mean(e*e))),mae_m=float(np.mean(abs(e))),p95_abs_m=float(np.percentile(abs(e),95)),within_1m=int((abs(e)<=1).sum()),below_model_by_over_5m=int((e< -5).sum()),above_model_by_over_5m=int((e>5).sum()))
 return d
zone_reports=[]
for q,poly in zones:
 m=sel&mask(poly);zz=z[m];holds={}
 for axis,arr in [('x',x),('y',y)]:
  k=np.floor((arr[m]-arr[m].min())/4).astype(int)%3;errs=[];folds=[]
  for i in range(3):
   train=k!=i;test=k==i
   if not test.any() or not train.any():continue
   h=float(np.median(zz[train]));ee=zz[test]-h;errs.extend(ee);folds.append({'fold':i,'train_median_odn':h,'test_cells':int(test.sum()),'rmse_m':float(np.sqrt(np.mean(ee**2)))})
  holds[axis]={'folds':folds,'rmse_m':float(np.sqrt(np.mean(np.array(errs)**2)))}
 zone_reports.append({'name':q['name'],'existing_odn_m':q['odn_m'],'existing_scene_z_m':q['scene_z_m'],'area_m2':poly.area,'full_cells':stats(m,q['odn_m']),'two_m_inset':stats(m&mask(poly.buffer(-2)),q['odn_m']),'spatial_holdout_constant_median':holds})
edges=[];ring=b['geometry'][0]['outer']
for i in [3,5,7,8,9,10,11,13]:
 line=LineString([ring[i],ring[(i+1)%len(ring)]]);band=line.buffer(3,cap_style=2).intersection(p);m=sel&mask(band);edges.append({'edge':i,'a':ring[i],'b':ring[(i+1)%len(ring)],'inward_band_m':3,'stats_vs_curved_low_odn33_967':stats(m,33.967),'samples_xyz_odn':np.c_[x[m],y[m],z[m]].tolist()})
np.savez(O/'samples.npz',x=x,y=y,z_odn=z,dtm_odn=dtm,valid=valid,inside=inside,existing_prediction_odn=prediction)
fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained')
for ax,vals,title,limits in [(axs[0],z,'DSM all owner cells (ODN)',(20,85)),(axs[1],prediction,'Existing descriptive roof (ODN)',(20,85)),(axs[2],z-prediction,'DSM minus existing roof',( -30,30))]:
 im=ax.scatter(x[sel],y[sel],c=vals[sel],s=28,marker='s',cmap='viridis' if ax!=axs[2] else 'coolwarm',vmin=limits[0],vmax=limits[1]);fig.colorbar(im,ax=ax);ax.plot(*p.exterior.xy,'k');ax.set(aspect='equal',title=title,xlabel='East m',ylabel='North m')
 for q,poly in zones:
  for pp in getattr(poly,'geoms',[poly]):ax.plot(*pp.exterior.xy,color='black',lw=.8)
 for i in [5,7,8,13]:
  aa=np.array(ring[i]);bb=np.array(ring[(i+1)%len(ring)]);mid=(aa+bb)/2;ax.text(*mid,str(i),color='red',fontsize=11)
fig.savefig(O/'full-domain.png',dpi=150)
fig,axs=plt.subplots(2,1,figsize=(12,8),layout='constrained')
low=next(poly for q,poly in zones if q['name']=='podium_curved_low');m=sel&mask(low)
for ax,coord,label in [(axs[0],x,'East'),(axs[1],y,'North')]:
 ax.scatter(coord[m],z[m],s=9,c='navy',alpha=.55);ax.axhline(33.967,color='red',label='Existing low-zone33.967 ODN');ax.set(xlabel=label+' m',ylabel='DSM ODN m',title='Curved-low full domain: all returns retained');ax.legend()
fig.savefig(O/'low-zone-profiles.png',dpi=150)
out={'owner':owner,'datum_odn_m':4.28000021,'capture_vintage':'Unresolved composite raster; catalog dates do not assign per-building capture year','grid':grid,'raw_footprint_area_m2':p.area,'full_footprint_cells':int(inside.sum()),'valid_cells':int(sel.sum()),'predicted_cells':int((sel&np.isfinite(prediction)).sum()),'full_owner_existing_error':stats(sel,z[sel]-(z[sel]-prediction[sel])),'zones':zone_reports,'edge_bands':edges,'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/morgan_massing_study_002.json']},'method':'No segmentation refit. Existing four mapped-zone predictions audited against every valid nativeDSMcell. 4m3fold spatialstrip median tests descriptive plateau suitability; edges inward3m bands include boundary ambiguity. No excluded outliers.','scope':'Evidence only; no roof/camera/geometry changed.'};(O/'audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(zone_reports,indent=2))
