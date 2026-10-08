"""Exact planar envelope of estimated d42 roof surfaces; closed footprint prisms."""
from pathlib import Path
exec(Path(__file__).with_name('d42_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import LineString
from shapely.ops import split
from shapely import constrained_delaunay_triangles, set_precision
O=R/'exports/ownerd42-massing-001';O.mkdir(exist_ok=True)
a=json.loads((R/'references/ownerd42_diagnostic.json').read_text());c=np.array(a['center']);e=np.array(a['east_axis']);n=np.array(a['north_axis']);q=ps[0];uvpoly=transform(lambda x,y:((np.asarray(x)-c[0])*e[0]+(np.asarray(y)-c[1])*e[1],(np.asarray(x)-c[0])*n[0]+(np.asarray(y)-c[1])*n[1]),q)
r=json.loads((R/'references/ownerd42_transition.json').read_text());p=r['parameters'];h=r['main_odn_m'];base=np.array([h,0.,0.])
def polys(g):return [g] if g.geom_type=='Polygon' else [pp for pp in g.geoms if pp.geom_type=='Polygon']
def env(A,B,op):
 out=[]
 for qa,pa in A:
  for qb,pb in B:
   common=qa.intersection(qb)
   if common.is_empty or common.area<1e-9:continue
   diff=pa-pb; norm=np.linalg.norm(diff[1:]); pieces=polys(common)
   if norm>1e-10:
    origin=-diff[0]*diff[1:]/norm**2;direction=np.array([-diff[2],diff[1]])/norm
    line=LineString([origin-1000*direction,origin+1000*direction]);pieces=[rr for qq in pieces for rr in polys(split(qq,line))]
   for qq in pieces:
    if qq.area<1e-9:continue
    pt=qq.representative_point();va=pa@[1,pt.x,pt.y];vb=pb@[1,pt.x,pt.y];choose=(va<=vb) if op=='min' else (va>=vb);out.append((qq,pa if choose else pb))
 # Merge subdivisions carrying the same analytical plane.
 groups={}
 for qq,pp in out:groups.setdefault(tuple(pp),[]).append(qq)
 return [(qq,np.array(pp)) for pp,parts in groups.items() for qq in polys(unary_union(parts)) if qq.area>1e-8]
def envelope(planes,op):
 out=[(uvpoly,np.array(planes[0]))]
 for plane in planes[1:]:out=env(out,[(uvpoly,np.array(plane))],op)
 return out
hip=envelope([[p[0]+p[3]*p[1],-p[3],0],[p[0]-p[3]*p[1],p[3],0],[p[0]+p[4]*p[2],0,-p[4]],[p[0]-p[4]*p[2],0,p[4]],[h-p[9]*p[5],p[9],0],[h+p[9]*p[6],-p[9],0],[h-p[9]*p[7],0,p[9]],[h+p[9]*p[8],0,-p[9]]],'min')
cap=envelope([[p[13]+p[15]*p[10],-p[15],0],[p[13]+p[15]*p[11],0,-p[15]],[p[13]-p[15]*p[12],0,p[15]],[p[13],0,0]],'max')
ledge=envelope([[h+p[15]*p[14],-p[15],0],[h+p[15]*p[11],0,-p[15]],[h-p[15]*p[12],0,p[15]],[h,0,0]],'max')
central=env(env(env(hip,cap,'min'),ledge,'min'),[(uvpoly,base)],'max')
sw=json.loads((R/'references/ownerd42_swfit.json').read_text())['parameters'];core=json.loads((R/'references/ownerd42_fit002.json').read_text())['regions']['southwest']['models']['plane']['parameters']
# Shallow roof core follows its stable inset fit; the outer transitions are estimated.
swplanes=envelope([core,[h-sw[7]*sw[3],sw[7],0],[h+sw[7]*sw[4],-sw[7],0],[h-sw[7]*sw[5],0,sw[7]],[h+sw[7]*sw[6],0,-sw[7]]],'min')
roof=env(central,swplanes,'max');objects=[]
for idx,(qq,pp) in enumerate(roof):
 qq=set_precision(qq, 0.000001).simplify(0.000002,preserve_topology=True)
 # Constrained triangulation preserves concavity and holes.
 tris=list(constrained_delaunay_triangles(qq).geoms); points={};vertices=[]
 def vi(uv):
  key=tuple(round(float(a),8) for a in uv)
  if key not in points:points[key]=len(points);xy=c+e*key[0]+n*key[1];vertices.append([float(xy[0]),float(xy[1]),float(pp@[1,*key]-4.28000021)])
  return points[key]
 top=[[vi(p) for p in list(t.exterior.coords)[:3]] for t in tris];rings=[[vi(p) for p in list(ring.coords)[:-1]] for ring in [qq.exterior,*qq.interiors]];count=len(vertices);vertices+=[[v[0],v[1],0.] for v in vertices.copy()];bottom=[[i+count for i in tri[::-1]] for tri in top];walls=[]
 for ring in rings:
  for i,j in zip(ring,ring[1:]+ring[:1]):walls.append([i,j,j+count,i+count])
 objects.append({'name':f'ownerd42_roof_domain_{idx:02d}','building_id':fs[0]['id'],'kind':'estimated','vertices':vertices,'roof_faces':top,'wall_faces':walls,'bottom_faces':bottom,'plane_odn':[float(v) for v in pp],'polygon_uv':{'outer':list(map(list,qq.exterior.coords)),'holes':[list(map(list,i.coords)) for i in qq.interiors]}})
u=(x-c[0])*e[0]+(y-c[1])*e[1];v=(x-c[0])*n[0]+(y-c[1])*n[1];full=mask(q);pred=np.full(z.shape,np.nan)
for qq,pp in roof:
 mm=full&np.array([qq.covers(Point(a,b)) for a,b in zip(u.flat,v.flat)]).reshape(u.shape);pred[mm]=pp[0]+pp[1]*u[mm]+pp[2]*v[mm]
assert np.isfinite(pred[full]).all();coverage=unary_union([qq for qq,pp in roof]);rows={}
for name,mm in [('all_valid',full),('inner2',mask(q.buffer(-2))),('edge2',full&~mask(q.buffer(-2))),('central',full&(u>-11)&(u<18)&(v>-15)&(v<14)),('SW',full&(u>-26)&(u<-12)&(v>-18)&(v<-3))]:rows[name]={'baseline15_scene':metric((z-19.28000021)[mm]),'candidate':metric((z-pred)[mm])}
report={'owner':fs[0]['id'],'scope':'EA DSM roof massing estimate: hip with eastern notch and SW shallow roof, main flat plane. Facades/entrances/materials unverified. Transition slopes and boundaries estimated, not resolved survey breaklines. Base0 unchanged; datum scene=ODN−4.28000021 m.','objects':objects,'source_baseline':json.loads((R/'references/ownerd42_native.json').read_text())['source'],'source_baseline_sha256':json.loads((R/'references/ownerd42_native.json').read_text())['source_sha256'],'coverage':{'footprint_area_m2':q.area,'missing_m2':uvpoly.difference(coverage).area,'outside_m2':coverage.difference(uvpoly).area,'sum_domain_area_m2':sum(qq.area for qq,pp in roof)},'metrics':rows,'central_fit':r,'SW_core_plane':core,'SW_transition_fit':sw,'source_hashes':{str(path.relative_to(R)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [R/'geometry.json',R/'references/ea_dsm_1m.tif',R/'references/ea_dtm_1m.tif']}}
(R/'references/ownerd42_study.json').write_text(json.dumps(report,indent=2));fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained')
for aa,values,title in zip(ax,[z,pred,z-pred],['Actual DSM ODN: all valid cells','Authored roof prediction','DSM minus candidate: full range']):
 im=aa.scatter(u[full],v[full],c=values[full],s=12,marker='s',cmap='coolwarm' if aa==ax[2] else 'viridis');fig.colorbar(im,ax=aa)
 for qq,pp in roof:rx,ry=qq.exterior.xy;aa.plot(rx,ry,'k-',lw=.4)
 aa.set(aspect='equal',title=title)
fig.savefig(O/'full_domain.png',dpi=150);print(json.dumps({'objects':len(objects),'coverage':report['coverage'],'metrics':rows},indent=2))
