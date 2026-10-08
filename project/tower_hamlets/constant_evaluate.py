from pathlib import Path
exec(Path(__file__).with_name('constant_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
from shapely import intersects_xy
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/constant-massing-001';tri=json.loads((R/'references/constant_final_triangles.json').read_text());q=ps[0];m=mask(q);xx=x[m];yy=y[m];zz=z[m];top=np.full(len(xx),-np.inf);polys=[]
for row in tri:
 vv=np.array(row['vertices']);pp=Polygon(vv[:,:2])
 if pp.area<1e-9:continue
 # Include all nonvertical surface projections, pick the highest intersection.
 sel=intersects_xy(pp.buffer(1e-6),xx,yy)
 A=np.column_stack([vv[:,0],vv[:,1],np.ones(3)]);cf=np.linalg.solve(A,vv[:,2]);pred=cf[0]*xx+cf[1]*yy+cf[2];top[sel]=np.maximum(top[sel],pred[sel]);polys.append(pp)
covered=unary_union(polys);valid=np.isfinite(top);datum=4.28000021;baseline=fs[0]['height_m']+datum;err=zz[valid]-(top[valid]+datum);old=zz[valid]-baseline
inset=intersects_xy(q.buffer(-2),xx,yy);groups={}
for name,sel in [('all_valid_owner_cells',valid),('inner_2m_domain',valid&inset),('outer_2m_edge_band',valid&~inset),('changed_flat_roof',valid&(abs(top-fs[0]['height_m'])>.01))]:
 a=zz[sel]-(top[sel]+datum);b=zz[sel]-baseline;groups[name]={'final_mesh':metric(a),'old_flat_baseline':metric(b),'signed_mean_error_m':float(a.mean()),'within_05m':int((abs(a)<=.5).sum()),'within_1m':int((abs(a)<=1).sum())}
report={'method':'Read final frozen Blender asset world triangles; project every nonvertical triangle into XY; evaluate highest plane intersection at every valid DSM cell center inside mappedowner. No residual/height filtering. Baseline is oldscene12.52923489 pluscommonODN4.28000021.','asset_sha256':{n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in ['constant.blend','constant.glb']},'valid_owner_DSM_cells':len(xx),'missing_top_projections':int((~valid).sum()),'footprint_m2':q.area,'mesh_projected_union_m2':covered.area,'footprint_missing_area_m2':q.difference(covered).area,'mesh_outside_footprint_area_m2':covered.difference(q).area,'projection_holes_detail':[{'area_m2':Polygon(h).area,'bounds':list(Polygon(h).bounds)} for pp in ([covered] if covered.geom_type=='Polygon' else covered.geoms) for h in pp.interiors],'coverage_tolerance_01mm_missing_area_m2':q.difference(covered.buffer(.0001)).area,'mesh_projected_holes_count':len(covered.interiors) if covered.geom_type=='Polygon' else sum(len(p.interiors) for p in covered.geoms),'groups':groups,'capture_date':None,'limitations':['Geographic roof accuracy not established byfitimprovement; stepedges estimated fromsameDSM.','Individualplanesextrapolatedtountrainededges andgaps;allreported withoutrejection.','Nativefloatprecision creates tinyfootprintslivers; no designed roofholes.','No opticalfacadeverification orcurrentcapturedate.']};(O/'full_domain_evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
fig,axs=plt.subplots(1,3,figsize=(15,6),layout='constrained')
for ax,a,title,lo,hi in zip(axs,[zz,top+datum,zz-(top+datum)],['All valid owner DSM ODN','Final frozen mesh top ODN — full owner coverage','DSM minus final mesh (all cells)'],[6,6,-16],[25,25,3]):
 im=ax.scatter(xx,yy,c=a,s=12,marker='s',vmin=lo,vmax=hi,cmap='coolwarm' if 'minus' in title else 'viridis');fig.colorbar(im,ax=ax);ax.plot(*q.exterior.xy,'k-',lw=.7);ax.set(aspect='equal',title=title)
fig.savefig(O/'full_domain_evaluation.png',dpi=150);print(json.dumps(report,indent=2))
