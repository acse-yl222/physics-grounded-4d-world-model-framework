exec(open('project/tower_hamlets/audit_credit999001.py').read().split('mask=')[0])
from shapely import constrained_delaunay_triangles,set_precision
z=np.asarray(Z);mask=~np.ma.getmaskarray(Z)&np.array([p.buffer(-1).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);fig,ax=plt.subplots(figsize=(8,9));im=ax.scatter(x[mask],y[mask],c=z[mask],vmin=45,vmax=58,s=14);fig.colorbar(im,ax=ax,label='ODN m');ax.set_aspect('equal');fig.savefig(R/'references/credit999_roof_detail002.png',dpi=150);hist,edges=np.histogram(z[mask],bins=np.arange(0,90,.2));print([(float(edges[i]),int(hist[i])) for i in np.argsort(hist)[-8:]])
from shapely.geometry import LineString
from shapely.ops import unary_union
south=LineString(list(p.exterior.coords)[:2]);sd=np.array([south.distance(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
fit=mask&(z>40)&(z<57);best=(1e9,None)
for depth in np.arange(11,18,.5):
 for inset in np.arange(1,6,.5):
  low=p.intersection(south.buffer(depth,cap_style=3));upper=p.buffer(-inset).difference(south.buffer(25,cap_style=3));mid=p.difference(low.union(upper));pred=np.full(z.shape,52.6);pred[sd<depth]=44.55;um=np.array([upper.contains(Point(a,b)) for a,b in zip(x[fit],y[fit])]);pv=pred[fit];pv[um]=55.8;loss=np.mean(np.minimum(abs(pv-z[fit]),8))
  if loss<best[0]:best=(float(loss),(float(depth),float(inset)))
depth,inset=best[1];low=p.intersection(south.buffer(depth,cap_style=3));upper=p.buffer(-inset).difference(south.buffer(25,cap_style=3));mid=p.difference(low.union(upper));zones=[]
for label,poly,band in [('main upper roof',upper,(55.5,56.1)),('lower perimeter and north connector roof',mid,(52.3,53)),('southern connector roof estimate',low,(44.3,44.8))]:
 mm=mask&np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);seed=mm&(z>band[0])&(z<band[1]);odn=float(np.median(z[seed]));gs=[]
 for q in ([poly] if poly.geom_type=='Polygon' else poly.geoms):
  if q.area<1e-5:continue
  q=set_precision(q,1e-6);gs.append({'outer':list(q.exterior.coords)[:-1],'holes':[list(r.coords)[:-1] for r in q.interiors],'triangles':[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(q).geoms]});xx,yy=q.exterior.xy;ax.plot(xx,yy,'k',lw=1)
 res=z[mm]-odn;zones.append({'label':label,'geometry':gs,'height_m':odn-4.28000021,'roof_median_odn_m':odn,'area_m2':poly.area,'stable_residual_p95_m':None,'all_cell_residual':{'count':int(mm.sum()),'mae_m':float(np.mean(abs(res))),'p95_absolute_m':float(np.percentile(abs(res),95))}})
fig.savefig(R/'references/credit999_roof_detail002.png',dpi=150)
neighbors=[]
for b in g['buildings']:
 if '3a202b7c' in b['id'] or ('Westferry' in str(b.get('name',''))):
  bp=unary_union([Polygon(t['outer'],t.get('holes',[])) for t in b['geometry']]);neighbors.append({'id':b['id'],'name':b.get('name'),'gap_m':p.distance(bp),'overlap_m2':p.intersection(bp).area,'shared_boundary_m':p.boundary.intersection(bp.boundary).length})
D={'building_id':f['id'],'source_geometry':f,'zones':zones,'identity':'17 Columbus Courtyard inferred mapped position and primary project relation','spatial_fit':{'south_connector_depth_m':depth,'main_setback_m':inset,'upper_south_cut_distance_m':25,'bounded_robust_fit_mae_m':best[0]},'neighbors':neighbors,'unverified':['Continuous three-plane roof approximation; setback and connector boundaries estimated from spatial DSM, not surveyed.','Southern connector has mixed low returns: 44.3–44.8m ODN occupied roof seed used; lower return cells retained in all-cell errors.','Fine rooftop plant and intermediate planes omitted; no borrowed facade.','Base scene z0 estimated; all roof medians use ODN minus shared4.28000021m.','Prior 999 footprint mismatch claim superseded after bounded-window coordinate correction; bad plot preserved.']};(R/'references/credit999_authoring002.json').write_text(json.dumps(D,indent=2));print(best,[(q['label'],q['height_m'],q['all_cell_residual']) for q in zones])
nd=json.loads((R/'references/credit3a_authoring001.json').read_text());np0=Polygon(nd['source_geometry']['geometry'][0]['outer']);shared=p.boundary.intersection(np0.boundary);interfaces=[]
for q in nd['zones']:
 qp=unary_union([Polygon(v['outer'],v['holes']) for v in q['geometry']]);length=shared.intersection(qp.buffer(1e-5)).length
 if length>1e-3:interfaces.append({'neighbor_zone':q['label'],'shared_length_m':length,'neighbor_scene_roof_m':q['height_m'],'target_scene_roof_m':zones[-1]['height_m'],'roof_step_m':q['height_m']-zones[-1]['height_m']})
D['interface_3a']=interfaces;D['unverified'].append('Shared 24.068m boundary with 20 Columbus has modeled roof steps; no inferred bridge, flashing or facade continuity. 7 Westferry separated by21.360m.');(R/'references/credit999_authoring002.json').write_text(json.dumps(D,indent=2))
