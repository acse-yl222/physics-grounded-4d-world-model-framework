exec(open('project/tower_hamlets/audit_credit3a001.py').read().split('mask=')[0])
from shapely import constrained_delaunay_triangles,set_precision
z=np.asarray(Z);mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);fig,ax=plt.subplots(figsize=(8,9));im=ax.scatter(x[mask],y[mask],c=z[mask],vmin=45,vmax=58,s=14);fig.colorbar(im,ax=ax,label='ODN m');ax.set_aspect('equal');fig.savefig(R/'references/credit3a_roof_detail001.png',dpi=150);hist,edges=np.histogram(z[mask],bins=np.arange(0,90,.2));print([(float(edges[i]),int(hist[i])) for i in np.argsort(hist)[-8:]])
from shapely.geometry import LineString
from shapely.ops import unary_union
edges=[LineString([a,b]) for a,b in zip(list(p.exterior.coords)[:-1],list(p.exterior.coords)[1:])];long=[e for e in edges if e.length>20];west=unary_union([e for e in edges if e.length>5 and e.centroid.x<p.centroid.x and abs(e.coords[-1][0]-e.coords[0][0])<.5*abs(e.coords[-1][1]-e.coords[0][1])]);north=max(long,key=lambda q:q.centroid.y);south=min(long,key=lambda q:q.centroid.y)
dw=np.array([west.distance(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);dn=np.array([north.distance(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);dsouth=np.array([south.distance(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);fit=mask&(((z>49)&(z<51))|((z>55.2)&(z<56.5)));ww=dw[fit];nn=dn[fit];ss=dsouth[fit];truth=z[fit]>55;best=(1,None)
for base in range(3,10):
 for notch in range(11,23):
  for nd in range(5,18,2):
   for sd in range(7,23,2):
    pred=(ww>base)&(ss>3)&((ww>notch)|(nn<nd)|(ss<sd));loss=float(np.mean(pred!=truth))
    if loss<best[0]:best=(loss,[base,notch,nd,sd])
base,notch,nd,sd=best[1];notchpoly=west.buffer(notch,cap_style=3).difference(north.buffer(nd,cap_style=3)).difference(south.buffer(sd,cap_style=3));high=p.difference(west.buffer(base,cap_style=3)).difference(south.buffer(3,cap_style=3)).difference(notchpoly);low=p.difference(high);zones=[]
for label,poly,band in [('upper main roof',high,(55.2,56.5)),('western lower roof estimate',low,(49,51))]:
 h=float(np.median(z[mask&(z>band[0])&(z<band[1])]))-4.28000021;gs=[]
 for q in ([poly] if poly.geom_type=='Polygon' else poly.geoms):
  if q.area<1e-5:continue
  q=set_precision(q,1e-6);gs.append({'outer':list(q.exterior.coords)[:-1],'holes':[list(r.coords)[:-1] for r in q.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(q).geoms]})
 mm=mask&np.array([poly.buffer(-.5).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);res=z[mm]-(h+4.28000021);zones.append({'label':label,'geometry':gs,'height_m':h,'roof_median_odn_m':h+4.28000021,'area_m2':poly.area,'stable_residual_p95_m':None,'all_cell_residual':{'count':int(mm.sum()),'mae_m':float(np.mean(abs(res))),'p95_absolute_m':float(np.percentile(abs(res),95))}})
for q in [high,low]:
 for pp in ([q] if q.geom_type=='Polygon' else q.geoms):
  xx,yy=pp.exterior.xy;ax.plot(xx,yy,'k',lw=1)
fig.savefig(R/'references/credit3a_roof_detail001.png',dpi=150);D={'building_id':f['id'],'identity':'20 Columbus Courtyard inferred from mapped position and primary engineering project relation','source_geometry':f,'zones':zones,'spatial_fit':{'parameters_m':{'west_base':base,'west_notch':notch,'north_end_depth':nd,'south_end_depth':sd,'south_edge':3},'stable_seed_misclassification':best[0]},'unverified':['Two planes simplify spatial roof returns; western repeated smaller high returns not individually reconstructed.','Western/southern edge low returns do not justifyholes; lower roof completed there as explicit estimate.','Main facade occluded in licensedOllie view, no neighboringfacade borrowed.','CRS roundtrip andsourcefootprint verified; bounded raster windowexplicitlyclipped.'],'identity_primary_text':'https://www.sandybrown.com/project/'};(R/'references/credit3a_authoring001.json').write_text(json.dumps(D,indent=2));print(best,[(a['height_m'],a['area_m2']) for a in zones])
