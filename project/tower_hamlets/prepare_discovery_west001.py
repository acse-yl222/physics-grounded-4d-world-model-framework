exec(open('project/tower_hamlets/audit_discovery_west001.py').read().split('mask=')[0])
mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);z=np.asarray(Z)
fig,ax=plt.subplots(figsize=(11,7));im=ax.scatter(x[mask],y[mask],c=z[mask],vmin=50,vmax=64,s=28);fig.colorbar(im,ax=ax,label='DSM ODN m (low returns clipped in colour only)');c=np.array(p.exterior.coords);ax.plot(c[:,0],c[:,1],'k');
for i,(a,b) in enumerate(c[:-1]):ax.text(a,b,str(i))
ax.set_aspect('equal');fig.savefig(R/'references/discovery_west_roof_detail001.png',dpi=150)
print('coords',c.tolist());print('hist',np.histogram(z[mask],bins=np.arange(0,75,1)))
from shapely import constrained_delaunay_triangles,set_precision
A=c[5];u=(c[4]-A)/np.linalg.norm(c[4]-A);v=np.array([u[1],-u[0]])
uu=(x-A[0])*u[0]+(y-A[1])*u[1];vv=(x-A[0])*v[0]+(y-A[1])*v[1]
def rect(a,b,d,e):return p.intersection(Polygon([A+u*k+v*l for k,l in [(a,d),(b,d),(b,e),(a,e)]]))
# Two bounded upper patches; aligned to mapped north wall, estimated boundaries.
west=rect(11,21,8,17);east=rect(43,52,11,27);main=p.difference(west.union(east));zones=[]
for label,poly,band in [('main continuous roof',main,(58.6,59.1)),('western upper roof estimate',west,(60.5,62.5)),('eastern upper roof estimate',east,(60.5,64.5))]:
 mm=mask&np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);ss=mm&(z>band[0])&(z<band[1]);odn=float(np.median(z[ss]));geom=[]
 for q in ([poly] if poly.geom_type=='Polygon' else poly.geoms):
  q=set_precision(q,1e-6);geom.append({'outer':list(q.exterior.coords)[:-1],'holes':[list(t.coords)[:-1] for t in q.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(q).geoms]});a,b=q.exterior.xy;ax.plot(a,b,'r',lw=1)
 residual=z[mm]-odn;zones.append({'label':label,'geometry':geom,'height_m':odn-4.28000021,'roof_median_odn_m':odn,'area_m2':poly.area,'stable_residual_p95_m':float(np.percentile(abs(z[ss]-odn),95)),'all_cell_residual':{'count':int(mm.sum()),'mae_m':float(np.mean(abs(residual))),'p95_absolute_m':float(np.percentile(abs(residual),95))},'low_return_count_under20odn':int((mm&(z<20)).sum())})
fig.savefig(R/'references/discovery_west_roof_detail001.png',dpi=150);neighbors=[]
for feat in g['buildings']:
 if feat['id'] in [f['id'],'site-support']:continue
 bp=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in feat['geometry']]);gap=p.distance(bp)
 if gap<15:neighbors.append({'id':feat['id'],'name':feat.get('name'),'baseline_top_scene_m':feat.get('height_m'),'gap_m':gap,'overlap_m2':p.intersection(bp).area,'shared_boundary_m':p.boundary.intersection(bp.boundary).length})
D={'building_id':f['id'],'source_geometry':f,'zones':zones,'neighbors':neighbors,'identity':'Mapped OSM way352617205 Discovery Dock Apartments West; primary selling-agent Savills text confirms2SouthQuaySquare address. No imagery used from listing.','primary_text_url':'https://assets.savills.com/properties/GBCWRSCNS180258/CNS180258_CNS19002818.PDF','source_height_basis':'OSM14floors times assumed3m gives42m; not surveyed roof height. No mapped child parts.','spatial_fit':{'origin':A.tolist(),'u':u.tolist(),'v':v.tolist(),'estimated_upper_rectangles_uv_m':[[11,21,8,17],[43,52,11,27]]},'unverified':['EA composite actual local survey vintage unresolved; overlapping2017/18 and2020 catalogue footprints do not establishpixel dates.','Full mapped footprint preserved. Low westedge and southcentral returns filled continuously as an explicit envelope hypothesis; roof versus nonroof boundary unresolved there.','Two upper extents regularized from spatial returns, their boundaries and flatness estimated; no equipment identity or facade invented.','Scene roof elevations are original ODN minus4.28000021; base0 is existing scene assumption.','No licensed photo identified as confirming this facade; geometry remains descriptive roof massing only.','Neighbor interface report is mapped solid envelope contact; no independent current regional detailed-neighbor collision boolean.']};(R/'references/discovery_west_authoring001.json').write_text(json.dumps(D,indent=2));print('zones',[(q['height_m'],q['all_cell_residual']) for q in zones]);print(neighbors)
