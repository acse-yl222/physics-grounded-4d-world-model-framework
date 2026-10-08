exec(open('project/tower_hamlets/audit_water15001.py').read().split('mask=')[0])
from shapely import constrained_delaunay_triangles,set_precision
z=np.asarray(Z);mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);fig,ax=plt.subplots(figsize=(8,9));im=ax.scatter(x[mask],y[mask],c=z[mask],vmin=65,vmax=75,s=14);fig.colorbar(im,ax=ax,label='ODN m');ax.set_aspect('equal');fig.savefig(R/'references/water15_roof_detail001.png',dpi=150);hist,edges=np.histogram(z[mask],bins=np.arange(0,90,.2));print([(float(edges[i]),int(hist[i])) for i in np.argsort(hist)[-8:]])
from shapely.geometry import LineString
edges=[LineString([a,b]) for a,b in zip(list(p.exterior.coords)[:-1],list(p.exterior.coords)[1:])];long=sorted(edges,key=lambda q:q.length,reverse=True)[:4];north=max(long,key=lambda q:q.centroid.y);west=min(long,key=lambda q:q.centroid.x);east=max(long,key=lambda q:q.centroid.x)
dist=[np.array([e.distance(Point(a,b)) for a,b in zip(x[mask],y[mask])]) for e in [north,west,east]];dn,dw,de=dist;zz=z[mask];fit=((zz>67.8)&(zz<69.0))|((zz>72.7)&(zz<74));truth=zz>72;best=(1,None)
for nd in np.arange(8,16,.5):
 for wd in np.arange(5,14,.5):
  for ed in np.arange(5,14,.5):
   pred=(dn<nd)&(dw>wd)&(de>ed);loss=float(np.mean(pred[fit]!=truth[fit]))
   if loss<best[0]:best=(loss,(float(nd),float(wd),float(ed)))
nd,wd,ed=best[1];high=p.intersection(north.buffer(nd,cap_style=3)).difference(west.buffer(wd,cap_style=3)).difference(east.buffer(ed,cap_style=3));low=p.difference(high);zones=[]
for label,poly,band in [('north upper roof envelope estimate',high,(72.7,74)),('main roof envelope estimate',low,(68,68.8))]:
 mm=mask&np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);seed=mm&(z>band[0])&(z<band[1]);odn=float(np.median(z[seed]));gs=[]
 for q in ([poly] if poly.geom_type=='Polygon' else poly.geoms):
  q=set_precision(q,1e-6);gs.append({'outer':list(q.exterior.coords)[:-1],'holes':[list(r.coords)[:-1] for r in q.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(q).geoms]});xx,yy=q.exterior.xy;ax.plot(xx,yy,'k',lw=1)
 res=z[mm]-odn;zones.append({'label':label,'geometry':gs,'height_m':odn-4.28000021,'roof_median_odn_m':odn,'area_m2':poly.area,'stable_residual_p95_m':None,'all_cell_residual':{'count':int(mm.sum()),'mae_m':float(np.mean(abs(res))),'p95_absolute_m':float(np.percentile(abs(res),95))}})
fig.savefig(R/'references/water15_roof_detail001.png',dpi=150);neighbors=[]
for b in g['buildings']:
 if b['id']==f['id'] or b['id']=='site-support':continue
 bp=unary_union([Polygon(t['outer'],t.get('holes',[])) for t in b['geometry']]);gap=p.distance(bp)
 if gap<35:neighbors.append({'id':b['id'],'name':b.get('name'),'gap_m':gap,'overlap_m2':p.intersection(bp).area,'shared_boundary_m':p.boundary.intersection(bp.boundary).length})
D={'building_id':f['id'],'identity':'15 Water Street; mapped name and location consistent with architect primary text','source_geometry':f,'zones':zones,'spatial_fit':{'north_depth_m':nd,'west_inset_m':wd,'east_inset_m':ed,'stable_seed_misclassification':best[0]},'neighbors':neighbors,'identity_primary_text':'https://www.alliesandmorrison.com/projects/15-water-street','epoch_primary_text':'https://group.canarywharf.com/wp-content/uploads/2021/04/canary-wharf-group-investment-holdings-plc-year-ended-31-december-2019.pdf','unverified':['Review-only DSM-era roof massing: mixed2017–2020 composite acquisition; exact local survey date unverified; owner2019report constructionQ42018 plannedcompletionQ22021; architect now completed. Present-day final roof agreement NOT established.','Two coherent height bands used for continuous estimated envelope; north upper rectangle boundaries estimated from spatial DSM.','Two isolated lower interior returns filled with main roof envelope, not asserted as physical roof holes; all cells retained in residual report.','No licensed view verified the target facade; inspected Ollie/Altaf images do not support reconstruction here. No invented windows or transferred facade.','Flat scene basez0 is estimated; roof medians ODN minus shared4.28000021m.','No present-day photo validation claim; candidate may improve baseline height but requires coordinator epoch review.']};(R/'references/water15_authoring001.json').write_text(json.dumps(D,indent=2));print(best,[(q['height_m'],q['all_cell_residual']) for q in zones],neighbors)
