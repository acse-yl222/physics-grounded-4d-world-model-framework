"""Offline exact-owner DSM patches for partial Crossrail assembly."""
from pathlib import Path
import json,math,hashlib
import numpy as np
import rasterio
from rasterio.windows import from_bounds,Window
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.ops import transform,unary_union
from shapely import contains_xy
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007'; refs=root/'references'
g=json.loads((root/'geometry.json').read_text());rep=json.loads((refs/'crossrail_lidar_review.json').read_text());part=next(f for f in g['buildings'] if f['id']==rep['building_id']);parent=next(f for f in g['buildings'] if f['id']=='overture-building-'+part['parent_id']);features=[part,parent];polys={f['id']:unary_union([Polygon(p['outer'],p.get('holes',[])) for p in f['geometry']]) for f in features};union=unary_union(list(polys.values()));tr=Transformer.from_crs(g['crs'],27700,always_xy=True);back=Transformer.from_crs(27700,g['crs'],always_xy=True)
with rasterio.open(refs/'ea_dsm_1m.tif') as ds:
 raw=from_bounds(*transform(tr.transform,union).bounds,ds.transform);c0,r0=math.floor(raw.col_off),math.floor(raw.row_off);w=Window(c0,r0,math.ceil(raw.col_off+raw.width)-c0,math.ceil(raw.row_off+raw.height)-r0);z=ds.read(1,window=w,masked=True);rr,cc=np.indices(z.shape);xx,yy=rasterio.transform.xy(ds.window_transform(w),rr,cc);x,y=back.transform(np.asarray(xx).reshape(z.shape),np.asarray(yy).reshape(z.shape))
u=np.array(rep['axis_local_xy']);v=np.array([-u[1],u[0]]);cx,cy=rep['mapped_part_extent']['centroid_local_xy'];cross=(x-cx)*v[0]+(y-cy)*v[1];fit=rep['upper_envelope_circle_fit'];disc=fit['radius_m']**2-(cross-fit['cross_axis_center_m'])**2;envelope=fit['circle_center_z_odn_m']+np.sqrt(np.maximum(0,disc));valid=~np.ma.getmaskarray(z)&(disc>0)&(np.abs(np.asarray(z)-envelope)<=1)
result={};allkeys=set()
for feature in features:
 poly=polys[feature['id']];supported=valid&contains_xy(poly,x,y);vertices=[];faces=[];lookup={}
 for i in range(z.shape[0]-1):
  for j in range(z.shape[1]-1):
   for pts in [((i,j),(i+1,j),(i+1,j+1)),((i,j),(i+1,j+1),(i,j+1))]:
    if not all(supported[a,b] for a,b in pts):continue
    triangle=Polygon([(x[a,b],y[a,b]) for a,b in pts])
    if not poly.covers(triangle):continue
    key=tuple(sorted(pts));assert key not in allkeys;allkeys.add(key);ids=[]
    for a,b in pts:
     if (a,b) not in lookup:lookup[a,b]=len(vertices);vertices.append([float(x[a,b]),float(y[a,b]),float(z[a,b]-rep['ground_scalar_m_odn'])])
     ids.append(lookup[a,b])
    a,b,c=[vertices[k] for k in ids]
    if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:ids.reverse()
    faces.append(ids)
 assert vertices and faces and all(math.isfinite(q) for p in vertices for q in p)
 result[feature['id']]={'vertices':vertices,'faces':faces,'plan_area_m2':poly.area,'supported_grid_cells':int(supported.sum()),'triangle_area_m2':sum(Polygon([vertices[k][:2] for k in f]).area for f in faces)}
report={'scope':'Partial assembly, not finished architecture; lower facades and supports absent','features':result,'part_id':part['id'],'parent_id':parent['id'],'deck':{'top_scene_z_m':17.1-rep['ground_scalar_m_odn'],'thickness_m_estimated':.30,'basis':'SSL117.100 minus inferred site Crossrail100m datum offset minus median terrain3.979098; deck outline central mapped roof footprint is provisional'},'checks':{'finite':True,'exact_owner_triangle_containment':True,'no_duplicate_roof_triangles_between_owners':True,'full_union_sampling_extent':True},'source_dsm_sha256':hashlib.sha256((refs/'ea_dsm_1m.tif').read_bytes()).hexdigest(),'limitations':['No filling unknown missing returns','Roof patches use measured1m DSM within1m fitted envelope; not verified cladding borders','Mapped roof outline does not establish lower facade plane','Deck datum, thickness and outline inferred; no invented columns or lower building enclosure']}
import sys
sys.path.insert(0,str(root/'src'))
from buildings.crossrail_partial_assembly import slab_mesh
sv,sf=slab_mesh(part,report['deck']['top_scene_z_m'],report['deck']['thickness_m_estimated'])
slab_area=sum(Polygon([sv[k][:2] for k in face]).area for face in sf if all(abs(sv[k][2]-report['deck']['top_scene_z_m'])<1e-8 for k in face))
assert abs(slab_area-polys[part['id']].area)<1e-6
report['checks'].update(deck_welded_closed_manifold=True,deck_exact_plan_area_m2=slab_area)
(refs/'crossrail_assembly_surfaces.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print(json.dumps({k:{'vertices':len(v['vertices']),'faces':len(v['faces'])} for k,v in result.items()}))
