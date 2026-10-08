from pathlib import Path
exec(Path(__file__).with_name('leyland_review.py').read_text().split('rows=[]')[0])
from shapely import constrained_delaunay_triangles,set_precision
from shapely.geometry import LineString
from shapely.ops import split
pr=json.loads((R/'references/leyland_profiles.json').read_text());eu=np.array(pr['axis_u']);ev=np.array(pr['axis_v']);u=x*eu[0]+y*eu[1];v=x*ev[0]+y*ev[1]
uv=lambda x,y:(x*eu[0]+y*eu[1],x*ev[0]+y*ev[1]);xy=lambda u,v:(u*eu[0]+v*ev[0],u*eu[1]+v*ev[1]);p=transform(uv,ps[0]);fits=json.loads((R/'references/leyland_domains.json').read_text())['domains'];cs=[r['hip_or_gable_cross_section_coefficients_H_slope_ridge'] for r in fits]
# Ridge ends at observed intersecting ridges; outer hip starts estimated from end-strip DSM.
r0,r1,r2,r3,r4=[c[2] for c in cs]
def planes(endpoints):
 out=[]
 for i,(H,s,r) in enumerate(cs):
  if i in [0,2,4]:
   lo,hi=([endpoints[0],r1] if i==0 else ([r1,r3] if i==2 else [r3,endpoints[1]]));out.append(np.array([[H+s*r,0,-s],[H-s*r,0,s],[H-s*lo,s,0],[H+s*hi,-s,0]]))
  else:
   lo,hi=([r0,r2] if i==1 else [r4,r2]);out.append(np.array([[H+s*r,-s,0],[H-s*r,s,0],[H-s*lo,0,s],[H+s*hi,0,-s]]))
 return out
A=np.stack([np.ones(u.shape),u,v],axis=-1)
def predict(pl):return np.max(np.stack([np.min(A@pp.T,axis=-1) for pp in pl]),axis=0)
# Two outer hip starts, only terminal 8m domains, no height filtering.
m=mask(ps[0].buffer(-1.3))&((u<465)|(u>532))
opt=least_squares(lambda ends:(predict(planes(ends))-z)[m],[460.5,535],bounds=([456,532],[465,539]),loss='soft_l1',f_scale=.15)
pl=planes(opt.x);pred=predict(pl);metrics={}
for inset in [0,1,2,3]:
 mm=mask(ps[0].buffer(-inset));metrics[str(inset)]={'candidate':metric(z[mm]-pred[mm]),'old':metric(z[mm]-(fs[0]['height_m']+4.28000021))}
# Exact piecewise-planar roof envelope: max of five bounded hip tents, each a min of four planes.
def parts(g):return [g] if g.geom_type=='Polygon' else [p for p in getattr(g,'geoms',[]) if p.geom_type=='Polygon']
def cut(poly,c,positive):
 if np.linalg.norm(c[1:])<1e-12:return [poly] if (c[0]>=0)==positive else []
 mid=np.array(poly.centroid.coords[0]);normal=c[1:];a=mid-normal*(c[0]+normal@mid)/(normal@normal);d=np.array([-normal[1],normal[0]]);d=d/np.linalg.norm(d)*10000
 out=[]
 for pp in parts(split(poly,LineString([a-d,a+d]))):
  t=pp.representative_point();val=c[0]+c[1]*t.x+c[2]*t.y
  if (val>=-1e-8 if positive else val<=1e-8) and pp.area>1e-8:out.append(pp)
 return out
wingtiles=[]
for pp in pl:
 tiles=[]
 for i,c in enumerate(pp):
  polys=[p]
  for j,d in enumerate(pp):
   if i!=j:polys=[b for a in polys for b in cut(a,d-c,True)]
  tiles.extend((a,c) for a in polys)
 wingtiles.append(tiles)
tiles=wingtiles[0]
for wing in wingtiles[1:]:
 new=[]
 for a,c in tiles:
  for b,d in wing:
   for inter in parts(a.intersection(b)):
    if inter.area<1e-8:continue
    new.extend((t,c) for t in cut(inter,c-d,True));new.extend((t,d) for t in cut(inter,c-d,False))
 tiles=new
# Merge same plane pieces to avoid needless internal partitions.
groups={}
for a,c in tiles:groups.setdefault(tuple(c),[]).append(a)
tiles=[(part,np.array(c)) for c,polys in groups.items() for part in parts(unary_union(polys)) if part.area>1e-7]
objs=[];areas=[]
for k,(part,c) in enumerate(tiles):
 part=set_precision(part,1e-6);vs=[];ix={};roof=[];walls=[];bottom=[]
 def height(u,v):return float(c@[1,u,v]-4.28000021)
 def vi(u,v,h):
  a,b=xy(u,v);key=tuple(round(t,7) for t in [a,b,h])
  if key not in ix:ix[key]=len(vs);vs.append(list(key))
  return ix[key]
 for tri in constrained_delaunay_triangles(part).geoms:
  rr=list(tri.exterior.coords)[:-1];roof.append([vi(a,b,height(a,b)) for a,b in rr]);bottom.append([vi(a,b,0) for a,b in reversed(rr)])
 for ring in [part.exterior,*part.interiors]:
  for (a,b),(aa,bb) in zip(ring.coords,list(ring.coords)[1:]):walls.append([vi(a,b,0),vi(aa,bb,0),vi(aa,bb,height(aa,bb)),vi(a,b,height(a,b))])
 objs.append({'name':f'Leyland_roof_plane_{k:02d}','building_id':fs[0]['id'],'kind':'estimated','vertices':vs,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom});areas.append(part.area)
fig,ax=plt.subplots(1,3,figsize=(15,7),layout='constrained');mm=mask(ps[0])
for a,arr,title in zip(ax,[z,pred,z-pred],['DSM ODN: all owner cells','Estimated connected pitched roof ODN','DSM minus candidate: no filtering']):
 im=a.scatter(u[mm],v[mm],c=arr[mm],s=20,marker='s',vmin=(-16 if 'minus' in title else 6),vmax=(3 if 'minus' in title else 25));fig.colorbar(im,ax=a);a.set(aspect='equal',title=title)
fig.savefig(R/'references/leyland_fit.png',dpi=150)
r={'replacement_ids':[fs[0]['id']],'objects':objs,'scope':'Leyland House five connected pitched roof wings, estimated from licensed 1m DSM; original full footprint and open courtyard retained.','fit':fits,'terminal_hip_starts':opt.x.tolist(),'formula_metrics':metrics,'checks':[{'footprint_area_m2':p.area,'partition_area_m2':sum(areas),'difference_m2':sum(areas)-p.area}],'source_properties':fs[0]['source_properties'],'limitations':['1m raster cannot verify eave overhangs, dormers or chimneys; these are not authored.','Connecting hips/valleys are estimated continuous intersections of five evidenced roof tents.','Full domain includes mixed boundary and isolated low returns. Actual capture epoch unknown.','Common datum ODN minus4.28000021m; flatbase0 illustrative; localDTM notfoundation.','No facade photograph verification. Planar closed cells contain coincident internalwalls.'],'source_ids':['leyland_dsm_001','leyland_dtm_001','overture_buildings_20260923']}
(R/'references/leyland_study.json').write_text(json.dumps(r,indent=2));print(json.dumps({'objects':len(objs),'checks':r['checks'],'metrics':metrics,'hipstarts':opt.x.tolist()},indent=2))
