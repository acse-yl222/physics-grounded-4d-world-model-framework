exec(open('project/tower_hamlets/audit_owner407001.py').read().split('mask=')[0])
mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);z=np.asarray(Z)
fig,ax=plt.subplots(figsize=(11,7));im=ax.scatter(x[mask],y[mask],c=z[mask],vmin=5,vmax=23,s=28);fig.colorbar(im,ax=ax,label='DSM ODN m (low returns clipped in colour only)');c=np.array(p.exterior.coords);ax.plot(c[:,0],c[:,1],'k');
for i,(a,b) in enumerate(c[:-1]):ax.text(a,b,str(i))
ax.set_aspect('equal');fig.savefig(R/'references/owner407_roof_detail001.png',dpi=150)
print('coords',c.tolist());print('hist',np.histogram(z[mask],bins=np.arange(0,75,1)))

from shapely import constrained_delaunay_triangles,set_precision
from shapely.geometry import box
lower=p.intersection(box(153.5,-1000,1000,359));main=p.difference(lower);zones=[]
for label,poly,band in [('courtyard main roof envelope',main,(18,21)),('southern lower annex envelope',lower,(8,12))]:
 mm=mask&np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);ss=mm&(z>band[0])&(z<band[1]);odn=float(np.median(z[ss]));geom=[]
 for q in ([poly] if poly.geom_type=='Polygon' else poly.geoms):
  q=set_precision(q,1e-6);geom.append({'outer':list(q.exterior.coords)[:-1],'holes':[list(t.coords)[:-1] for t in q.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(q).geoms]});aa,bb=q.exterior.xy;ax.plot(aa,bb,'r')
  for h in q.interiors:aa,bb=h.xy;ax.plot(aa,bb,'k')
 res=z[mm]-odn;zones.append({'label':label,'geometry':geom,'height_m':odn-4.28000021,'roof_median_odn_m':odn,'area_m2':poly.area,'stable_residual_p95_m':float(np.percentile(abs(z[ss]-odn),95)),'all_cell_residual':{'count':int(mm.sum()),'mae_m':float(np.mean(abs(res))),'p95_absolute_m':float(np.percentile(abs(res),95))}})
fig.savefig(R/'references/owner407_roof_detail001.png',dpi=150);neighbors=[]
for feat in g['buildings']:
 if feat['id'] in [f['id'],'site-support']:continue
 bp=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in feat['geometry']]);gap=p.distance(bp)
 if gap<5:neighbors.append({'id':feat['id'],'name':feat.get('name'),'baseline_top_scene_m':feat.get('height_m'),'gap_m':gap,'overlap_m2':p.intersection(bp).area,'shared_boundary_m':p.boundary.intersection(bp.boundary).length})
D={'building_id':f['id'],'source_geometry':f,'zones':zones,'neighbors':neighbors,'identity':'Mapped college building within New City College Poplar campus; precise named wing unresolved. OSM relation2643629. Do not identify as adjacent listed naval college without evidence.','primary_text_url':'https://www.london.gov.uk/decisions/add2284-potential-development-new-city-college-site','source_height_basis':'Two mapped floors times assumed3m gives6m, not surveyed height. No mapped parts.','unverified':['Actual EA composite local survey vintage unresolved; no proof of present roof after proposed campus redevelopment.','Exact mapped courtyard hole retained; initial diagnostic excluded holes by mistake, corrected before geometry authoring.','Main roof shows spatially varying18–21ODN returns. Flat envelope is a simplification, not verified roof pitches or exact parapet.','Southern annex divide y359m estimated from spatial drop; no invented facade or equipment.','Shared datumODNminus4.28000021; flat base0 retained as scene assumption.','Primary2018proposal is not proof of completed redevelopment; current building morphology unverified.']};(R/'references/owner407_authoring001.json').write_text(json.dumps(D,indent=2));print([(t['height_m'],t['all_cell_residual']) for t in zones]);print(neighbors)
