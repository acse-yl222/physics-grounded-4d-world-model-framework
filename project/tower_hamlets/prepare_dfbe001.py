exec(open('project/tower_hamlets/audit_dfbe001.py').read().split('mask=')[0])
from shapely import constrained_delaunay_triangles,set_precision
z=np.asarray(Z);mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);fig,ax=plt.subplots(figsize=(8,9));im=ax.scatter(x[mask],y[mask],c=z[mask],vmin=20,vmax=36,s=14);fig.colorbar(im,ax=ax,label='ODN m');ax.set_aspect('equal');fig.savefig(R/'references/dfbe_roof_detail001.png',dpi=150);hist,edges=np.histogram(z[mask],bins=np.arange(0,90,.2));print([(float(edges[i]),int(hist[i])) for i in np.argsort(hist)[-8:]])
from shapely.geometry import LineString
edges=[LineString([a,b]) for a,b in zip(list(p.exterior.coords)[:-1],list(p.exterior.coords)[1:])];west=unary_union([e for e in edges if e.centroid.x<-230]);dw=np.array([west.distance(Point(a,b)) for a,b in zip(x[mask],y[mask])]);dp=np.array([p.boundary.distance(Point(a,b)) for a,b in zip(x[mask],y[mask])]);zz=z[mask];fit=((zz>26.3)&(zz<27))|((zz>31.4)&(zz<32.2));truth=zz>30;best=(1,None)
for edge in np.arange(1,5.1,.5):
 for wd in np.arange(5,13.1,.5):
  pred=(dp>edge)&(dw>wd);loss=float(np.mean(pred[fit]!=truth[fit]))
  if loss<best[0]:best=(loss,(float(edge),float(wd)))
edge,wd=best[1];high=p.buffer(-edge).difference(west.buffer(wd,cap_style=3));low=p.intersection(west.buffer(5,cap_style=3));mid=p.difference(high.union(low));zones=[]
for label,poly,band in [('main continuous roof',high,(31.6,32)),('lower perimeter roof estimate',mid,(26.4,26.9)),('western entrance envelope estimate',low,(15,19))]:
 mm=mask&np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);seed=mm&(z>band[0])&(z<band[1]);odn=float(np.median(z[seed]));gs=[]
 for q in ([poly] if poly.geom_type=='Polygon' else poly.geoms):
  if q.area<1e-6:continue
  q=set_precision(q,1e-6);gs.append({'outer':list(q.exterior.coords)[:-1],'holes':[list(r.coords)[:-1] for r in q.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(q).geoms]});xx,yy=q.exterior.xy;ax.plot(xx,yy,'k',lw=1)
 res=z[mm]-odn;zones.append({'label':label,'geometry':gs,'height_m':odn-4.28000021,'roof_median_odn_m':odn,'area_m2':poly.area,'stable_residual_p95_m':None,'all_cell_residual':{'count':int(mm.sum()),'mae_m':float(np.mean(abs(res))),'p95_absolute_m':float(np.percentile(abs(res),95))}})
fig.savefig(R/'references/dfbe_roof_detail001.png',dpi=150);neighbors=[]
for b in g['buildings']:
 if b['id']==f['id'] or b['id']=='site-support':continue
 bp=unary_union([Polygon(t['outer'],t.get('holes',[])) for t in b['geometry']]);gap=p.distance(bp)
 if gap<20:neighbors.append({'id':b['id'],'name':b.get('name'),'gap_m':gap,'overlap_m2':p.intersection(bp).area,'shared_boundary_m':p.boundary.intersection(bp.boundary).length})
D={'building_id':f['id'],'identity':'Cabot Place West / former Cabot Hall; mapped position west of DLR, east of Cabot Square, between North/South Colonnade; owner2021map inspected and council2006text supports context.','source_geometry':f,'zones':zones,'spatial_fit':{'perimeter_inset_m':edge,'west_main_inset_m':wd,'west_low_depth_m':5,'stable_seed_misclassification':best[0]},'neighbors':neighbors,'identity_primary_text':'https://towerhamlets.moderngov.co.uk/documents/g1597/Public%20reports%20pack%2008th-Mar-2006%2019.30%20Development%20Committee.pdf?T=10','source_height_basis':'OSM four floors multiplied by assumed3m=12m; not measured height.','unverified':['Composite DSM survey vintage unresolved; overlapping catalogue surveys2017/2018 and2020 do not assign pixel dates. Seeea_vintage_metadata_audit001.json.','Continuous roof massing only; no current photo facade verification or invented windows.','Main roof shallow central higher returns omitted; perimeter breaks and western entrance depth estimated.','Western low-envelope16–19ODN band uncertain; not a measured porch ceiling or exact entrance geometry.','Mappedfullfootprint retained, flat basez0 estimated. RoofmediansODN minus shared4.28000021m.','Shared eastern boundary with DLR-relatedmappedasset retained; no bridge or facade continuity inferred.']};(R/'references/dfbe_authoring001.json').write_text(json.dumps(D,indent=2));print(best,[(q['height_m'],q['all_cell_residual']) for q in zones],neighbors)
