from pathlib import Path
import json,struct,hashlib
import numpy as np,rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union,transform
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/owner1f92-ground-evidence-001';O.mkdir(exist_ok=True)
g=json.load(open(R/'geometry.json'));owners=[f for f in g['buildings'] if any(k in f['id'] for k in ['1f9270f4','00851081'])];polys=[unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]) for f in owners];p=unary_union(polys);site=Polygon(next(f for f in g['buildings'] if f['kind']=='site')['geometry'][0]['outer']);fw=Transformer.from_crs(g['crs'],27700,always_xy=True);bk=Transformer.from_crs(27700,g['crs'],always_xy=True)
path=Path(__file__).resolve().parent/'runs/canary_wharf_appearance_owner1f92_001/region.glb';b=path.read_bytes();n=struct.unpack_from('<I',b,12)[0];gl=json.loads(b[20:20+n]);data=b[28+n:]
def acc(i):
 a=gl['accessors'][i];v=gl['bufferViews'][a['bufferView']];dt={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];sz={'SCALAR':1,'VEC3':3}[a['type']];return np.ndarray((a['count'],sz),dtype=dt,buffer=data,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dt).itemsize*sz),np.dtype(dt).itemsize)).copy()
support=[];bases=[]
for node in gl['nodes']:
 owner=node.get('extras',{}).get('building_id','')
 if owner!='site-support' and not any(k in owner for k in ['1f9270f4','00851081']):continue
 if 'mesh' not in node:continue
 assert not any(k in node for k in ['matrix','rotation','scale','translation'])
 for prim in gl['meshes'][node['mesh']]['primitives']:
  v=acc(prim['attributes']['POSITION']);z=v[:,1]
  if owner=='site-support':support.append({'name':node['name'],'z_min':float(z.min()),'z_max':float(z.max())})
  else:bases.append({'name':node['name'],'owner':owner,'minimum_scene_z':float(z.min())})
f=R/'references/ea_dtm_1m.tif'
with rasterio.open(f) as ds:
 bounds=transform(fw.transform,p.buffer(8)).bounds;w=from_bounds(*bounds,ds.transform).round_offsets().round_lengths();a=ds.read(1,window=w,boundless=True,masked=True);rr,cc=np.indices(a.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=bk.transform(np.array(xx).reshape(a.shape),np.array(yy).reshape(a.shape));z=np.asarray(a,float)-4.28000021;valid=~np.ma.getmaskarray(a);sourcebounds=list(ds.bounds)
 def sample(pts):
  vals=list(ds.sample([fw.transform(*v) for v in pts],masked=True));return [None if np.ma.is_masked(v[0]) else float(v[0]-4.28000021) for v in vals]
 points=[]
 for i,q in enumerate(polys):
  for d in np.arange(0,q.length,.5):
   v=q.exterior.interpolate(d);points.append({'owner':owners[i]['id'],'xy':[v.x,v.y],'inside_original_site':site.covers(v),'distance_to_site_m':v.distance(site)})
 for row,v in zip(points,sample([r['xy'] for r in points])):row['dtm_scene_z']=v;row['base0_minus_DTM']=None if v is None else -v
 profiles=[]
 for northing in [315,325,335,342]:
  pts=[(float(e),northing) for e in np.arange(-515,-455,.5)];profiles.append({'y':northing,'x':[v[0] for v in pts],'dtm_scene_z':sample(pts)})
def stats(v):
 v=np.array([x for x in v if x is not None]);return {'count':len(v),'min':float(v.min()),'median':float(np.median(v)),'max':float(v.max())} if len(v) else {'count':0}
rows=[]
for o,q in zip(owners,polys):
 mask=np.array([q.contains(Point(e,n)) for e,n in zip(x.flat,y.flat)]).reshape(x.shape);per=[r for r in points if r['owner']==o['id']];rows.append({'owner':o['id'],'footprint_area_m2':q.area,'footprint_outside_original_site_m2':q.difference(site).area,'DTM_grid_cells':int(mask.sum()),'missing_DTM_cells':int((mask&~valid).sum()),'DTM_scene_z':stats(z[mask&valid]),'perimeter_samples':len(per),'perimeter_missing_DTM':sum(r['dtm_scene_z'] is None for r in per),'perimeter_outside_site_samples':sum(not r['inside_original_site'] for r in per),'max_distance_to_original_site_m':max(r['distance_to_site_m'] for r in per),'perimeter_DTM_scene_z':stats([r['dtm_scene_z'] for r in per])})
fig,ax=plt.subplots(1,2,figsize=(13,6));im=ax[0].pcolormesh(x,y,np.ma.array(z,mask=~valid),shading='nearest',cmap='terrain');fig.colorbar(im,ax=ax[0],label='DTM scene z = ODN − 4.28000021 m')
for q in polys:ax[0].plot(*q.exterior.xy,'r-',lw=2)
ax[0].plot(*site.exterior.xy,'k--',label='Original illustrative site boundary');ax[0].set(xlim=(p.bounds[0]-8,p.bounds[2]+8),ylim=(p.bounds[1]-8,p.bounds[3]+8),xlabel='ENU east m',ylabel='ENU north m',title='Actual licensed DTM; red = full footprints');ax[0].set_aspect('equal');ax[0].legend(fontsize=7)
for r in profiles:ax[1].plot(r['x'],r['dtm_scene_z'],label=f"north {r['y']} m")
ax[1].axhline(0,color='r',label='Building base 0');ax[1].axhline(-.1,color='k',ls='--',label='Illustrative ground −0.1');ax[1].axvline(-499.9,color='grey',ls=':',label='Approximate site west edge');ax[1].set(xlabel='ENU east m',ylabel='Scene z m',title='Measured terrain profiles; no invented ramps');ax[1].legend(fontsize=8);fig.tight_layout();fig.savefig(O/'terrain-evidence.png',dpi=180)
report={'source_glb_sha256':hashlib.sha256(b).hexdigest(),'dtm_path':str(f),'dtm_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'DTM_source_CRS':'EPSG:27700','DTM_source_bounds':sourcebounds,'datum':'ODN minus4.28000021m; geometry.json CRS/ENU preserved','capture_epoch':'unknown','site_support_native_glb':support,'building_bases':bases,'owners':rows,'perimeter_samples':points,'profiles':profiles,'limitations':['DTM is 1m licensed EA evidence, not surveyed foundation.','Original site is illustrative horizontal support, not terrain.','No new data acquisition, no building modification, no terrain integration.']};(O/'evidence.json').write_text(json.dumps(report,indent=2));print(json.dumps({'owners':rows,'support':support,'base_levels':sorted(set(r['minimum_scene_z'] for r in bases))},indent=2))
