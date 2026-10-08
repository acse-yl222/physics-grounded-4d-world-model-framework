exec(open('project/tower_hamlets/audit_state_street001.py').read().split('z=np.asarray')[0])
from shapely import constrained_delaunay_triangles,set_precision
z=np.asarray(Z);records=[];fig,axs=plt.subplots(1,2,figsize=(13,7))
for ax,index,lim in [(axs[0],4,(76,81)),(axs[1],5,(35,45))]:
 pp=polys[index];mask=~np.ma.getmaskarray(Z)&np.array([pp.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);im=ax.scatter(x[mask],y[mask],c=z[mask],vmin=lim[0],vmax=lim[1],s=12);fig.colorbar(im,ax=ax);ax.set_aspect('equal');ax.set_title(fs[index]['id'].split('-')[2]+' DSM ODN')
fig.savefig(R/'references/state_street_roof_detail001.png',dpi=150)
for index in [4,5]:
 pp=polys[index];mask=~np.ma.getmaskarray(Z)&np.array([pp.buffer(-2).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);hist,edges=np.histogram(z[mask],bins=np.arange(0,90,.2));ix=np.argsort(hist)[-8:];print(index,[(round(float(edges[i]),1),int(hist[i])) for i in ix])
from shapely.geometry import LineString
zones=[]
def entry(f,pp,h,label,bottom=0):
 gs=[]
 for poly in ([pp] if pp.geom_type=='Polygon' else pp.geoms):
  if poly.area<1e-8:continue
  poly=set_precision(poly,1e-6)
  gs.append({'outer':list(poly.exterior.coords)[:-1],'holes':[list(r.coords)[:-1] for r in poly.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(poly).geoms]})
 zones.append({'label':label,'owner_id':f['id'],'source_owner_ids':[f['id'],'overture-building-'+parent] if f['kind']=='part' else [f['id']],'height_m':h-4.28000021,'roof_median_odn_m':h,'min_height_m':bottom,'geometry':gs,'area_m2':pp.area,'stable_residual_p95_m':None})
for index,(f,pp) in enumerate(zip(fs,polys)):
 mask=~np.ma.getmaskarray(Z)&np.array([pp.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
 if index==0:continue
 if index in [1,2,3]:entry(f,pp,float(np.median(z[mask&(z>12.5)&(z<14)])),'east low mapped component',f.get('min_height_m',0));continue
 if index==4:
  edges=[LineString([a,b]) for a,b in zip(list(pp.exterior.coords)[:-1],list(pp.exterior.coords)[1:])];north=max(edges,key=lambda s:s.centroid.y);dist=np.array([north.distance(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);fit=mask&(z>70)&(z<81);best=min((float(np.mean(((dist[fit]>d)!=(z[fit]>78.7)))),float(d)) for d in np.arange(3,20,.2));low=pp.intersection(north.buffer(best[1],cap_style=3));high=pp.difference(low);entry(f,low,float(np.median(z[mask&(dist<best[1])&(z>73)&(z<76)])),'north roof zone estimated straight boundary');entry(f,high,float(np.median(z[mask&(dist>best[1])&(z>79)&(z<80)])),'main high roof zone');print('northboundary',best)
 if index==5:
  vertices=np.array(pp.exterior.coords);ee=np.diff(vertices,axis=0);u=ee[np.argmax(np.linalg.norm(ee,axis=1))];u/=np.linalg.norm(u);v=np.array([-u[1],u[0]]);c=np.array(pp.centroid.coords[0]);aa=(x-c[0])*u[0]+(y-c[1])*u[1];bb=(x-c[0])*v[0]+(y-c[1])*v[1];stable=mask&(z>42.4)&(z<43.4);al=np.percentile(aa[stable],[1,99]);bl=np.percentile(bb[stable],[1,99]);upper=Polygon([c+u*a+v*b for a,b in [(al[0]-.5,bl[0]-.5),(al[1]+.5,bl[0]-.5),(al[1]+.5,bl[1]+.5),(al[0]-.5,bl[1]+.5)]]).intersection(pp);entry(f,upper,float(np.median(z[stable])),'south wing raised roof spatial patch');entry(f,pp.difference(upper),float(np.median(z[mask&(z>36.5)&(z<37.5)])),'south wing lower roof')
parentlow=polys[0].intersection(north.buffer(best[1],cap_style=3));parenthigh=polys[0].difference(parentlow)
mainrows=[row for row in zones if '03ab7b24' in row['owner_id']]
entry(fs[0],parentlow,mainrows[0]['roof_median_odn_m'],'parent residual inherits adjacent north roof')
entry(fs[0],parenthigh,mainrows[1]['roof_median_odn_m'],'parent residual inherits adjacent high roof')
for row in zones:
 pp=unary_union([Polygon(t['outer'],t['holes']) for t in row['geometry']]);mm=~np.ma.getmaskarray(Z)&np.array([pp.buffer(-.5).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
 residual=z[mm]-row['roof_median_odn_m'];row['all_cell_residual']={'count':len(residual),'mae_m':float(np.mean(abs(residual))) if len(residual) else None,'p95_absolute_m':float(np.percentile(abs(residual),95)) if len(residual) else None}
report={'building_id':'overture-building-'+parent,'zones':zones,'sources':[f for f in fs],'north_boundary_fit':{'setback_m':best[1],'misclassification_fraction':best[0]},'method':'Footprints preserve disjoint source ownership. North boundary fitted spatially to roof modes with straight mapped alignment; southern raised patch fit to1st99th-percentile spatial high-return bounds. Surface heights stable conditional medians, not wholebuilding quantiles.','unverified':['No confirmed licensed image facade coverage; no window patterns inferred.','Roofzone straight edges estimated at1m resolution; minor rooftop returns not individual equipment.','Lowparts minheight retains floor-derived assumption; no unsupported columns added.','Parent0.550m2 residual inherits adjacent main roof to avoid spurious short needle.'],'identity_source':'https://www.adamson-associates.com/project/20-churchill-place-canary-wharf/'};(R/'references/state_street_authoring001.json').write_text(json.dumps(report,indent=2))
