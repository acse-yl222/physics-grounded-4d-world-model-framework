"""Roof-aligned bounded museum diagnostic; no scene or footprint mutations."""
exec(open(__file__.replace('analyze_museum_roof_fit.py','analyze_museum_lidar.py')).read().split('rep=')[0])
from scipy.optimize import least_squares
from scipy.signal import find_peaks
child=next(q for q in g['buildings'] if '97b6bbeb' in q['id']);cp=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in child['geometry']]); parent_poly=p; p=unary_union([p,cp]); masks={str(e):valid&np.array([p.buffer(-e).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape) for e in [0,2]};m=masks['0']
origin=np.array(p.centroid.coords[0]); ring=np.array(p.minimum_rotated_rectangle.exterior.coords); edges=np.diff(ring,axis=0);axis=edges[np.argmax(np.linalg.norm(edges,axis=1))];axis=axis/np.linalg.norm(axis);axis=axis if axis[0]>0 else -axis;cross=np.array([-axis[1],axis[0]])
u=(x-origin[0])*axis[0]+(y-origin[1])*axis[1];v=(x-origin[0])*cross[0]+(y-origin[1])*cross[1]
sel=masks['2']&(z>16)&(z<23); train=sel&((np.floor(u/4).astype(int)%3)!=1); test=sel&~train
# Infer longitudinal step from training only by minimising within-group median absolute deviations.
us=np.arange(-15,10,.25); costs=[]
for split in us:
 costs.append(sum(np.sum(abs(z[train&(u<s)]-np.median(z[train&(u<s)])))+np.sum(abs(z[train&(u>=s)]-np.median(z[train&(u>=s)]))) for s in [split]))
split=float(us[np.argmin(costs)])
# Explicit profile spline at 1m spacing; this is diagnostic, not closed mesh or named architectural parts.
knots=np.arange(np.ceil(v[sel].min()),np.floor(v[sel].max())+1)
def basis(vv):
 return np.array([np.interp(vv,knots,np.eye(len(knots))[i]) for i in range(len(knots))]).T
B=basis(v[train]);side=(u[train]>=split).astype(float);A=np.column_stack([B,side]);D=np.diff(np.eye(len(knots)),2,axis=0)
def resid(c):return np.r_[A@c-z[train], .3*(D@c[:-1])]
fit=least_squares(resid,np.r_[np.full(len(knots),17.5),3.],loss='soft_l1',f_scale=.15,max_nfev=300)
c=fit.x;pred=basis(v[sel])@c[:-1]+(u[sel]>=split)*c[-1];res=z[sel]-pred
vv=np.linspace(knots[0],knots[-1],600);curve=np.interp(vv,knots,c[:-1]);peaks,_=find_peaks(curve,prominence=.4,distance=70);valleys,_=find_peaks(-curve,prominence=.4,distance=70)
testres=z[test]-(basis(v[test])@c[:-1]+(u[test]>=split)*c[-1])
def metrics(a):return {'n':len(a),'rmse_m':float(np.sqrt(np.mean(a*a))),'median_abs_m':float(np.median(abs(a))),'p95_abs_m':float(np.percentile(abs(a),95))}
child=next(q for q in g['buildings'] if '97b6bbeb' in q['id']);cp=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in child['geometry']])
report={'building_id':f['id'],'geometry_modified':False,'source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m','overture_buildings_20260923'],'source_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['geometry.json','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif']},'origin_local_m':origin.tolist(),'long_axis':axis.tolist(),'cross_axis':cross.tolist(),'ground_m_odn':float(np.median(ground[m])),'longitudinal_step_u_m':split,'east_raise_m':float(c[-1]),'cross_profile_knots_v_m':knots.tolist(),'west_profile_odn_m':c[:-1].tolist(),'ridge_candidates_v_m':vv[peaks].tolist(),'valley_candidates_v_m':vv[valleys].tolist(),'spatial_holdout':{'description':'Every third 4m longitudinal stripe held out. Fit selection erosion2m and DSM16–23m ODN, conditional on observed roof returns. Step trained on remaining stripes.','metrics':metrics(testres),'fit_all_selected':metrics(res)},'child_id':child['id'],'child_overlap_parent_m2':cp.intersection(parent_poly).area,'ownership':'Fit union of parent residual and child. Parent already excludes child; clip future patches per retained owner footprint.','child_area_m2':cp.area,'readiness':'Diagnostic spline only. Candidate surface may be generated within measured support; closed whole-building integration not ready.','limitations':['One metre DSM mixes historical dates; optical source image not available.','Uniform east offset is hypothesis; step position and roof extremes depend on selected samples.','Profile knots are numerical representation, not architectural breaklines.','Footprint ground returns and perimeter are excluded, not explained.','Parent already excludes child. Use common union ground for both to avoid artificial datum step.','Facades, roof materials, windows, chimneys, parapets and full ridge topology unresolved.'],'visual_review':{'inspected':False}}
fig,axs=plt.subplots(2,2,figsize=(14,10),layout='constrained');im=axs[0,0].scatter(u[m],v[m],c=z[m],s=12,vmin=16,vmax=22);fig.colorbar(im,ax=axs[0,0],label='DSM ODN m');axs[0,0].axvline(split,c='r');axs[0,0].set(title='Roof-aligned native returns, step red',xlabel='u longitudinal m',ylabel='v cross-roof m',aspect='equal')
for east,col in [(False,'tab:blue'),(True,'tab:orange')]:
 q=sel&((u>=split)==east);axs[0,1].scatter(v[q],z[q],s=5,alpha=.2,c=col);axs[0,1].plot(vv,curve+east*c[-1],c=col,lw=2)
axs[0,1].set(title='West/east conditional spline profiles',xlabel='v m',ylabel='ODN m');im=axs[1,0].scatter(u[sel],v[sel],c=res,s=12,vmin=-.5,vmax=.5,cmap='RdBu_r');fig.colorbar(im,ax=axs[1,0],label='Observed minus fit m');axs[1,0].set(title='Residuals expose departures from shared profile',aspect='equal');axs[1,1].scatter(v[test],testres,s=10);axs[1,1].axhline(0,c='k');axs[1,1].set(title='Held-out longitudinal stripes',xlabel='v m',ylabel='Residual m');fig.suptitle('Museum Docklands: multiple roof profiles; diagnostic, not integrated geometry');fig.savefig(ROOT/'references/museum_roof_fit.png',dpi=140)
(ROOT/'references/museum_roof_fit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
# Independent profiles retain identical selection, train/test stripes and step.
independent={};ind_pred=np.full(z.shape,np.nan)
for east,label in [(False,'west'),(True,'east')]:
 trmask=train&((u>=split)==east);temask=test&((u>=split)==east);own=sel&((u>=split)==east)
 bb=basis(v[trmask]);cc=least_squares(lambda a:np.r_[bb@a-z[trmask],.3*(D@a)],c[:-1]+east*c[-1],loss='soft_l1',f_scale=.15,max_nfev=300).x
 ind_pred[own]=basis(v[own])@cc;line=np.interp(vv,knots,cc);pp,_=find_peaks(line,prominence=.4,distance=70);ll,_=find_peaks(-line,prominence=.4,distance=70)
 independent[label]={'profile_odn_m':cc.tolist(),'training_cells':int(trmask.sum()),'heldout':metrics(z[temask]-ind_pred[temask]),'ridge_candidates_v_m':vv[pp].tolist(),'valley_candidates_v_m':vv[ll].tolist(),'training_v_range_m':[float(v[trmask].min()),float(v[trmask].max())]}
indres=z[sel]-ind_pred[sel];indtest=z[test]-ind_pred[test]
report['independent_profiles']={'profiles':independent,'heldout':metrics(indtest),'fit_all_selected':metrics(indres),'rmse_reduction_fraction':float(1-metrics(indtest)['rmse_m']/metrics(testres)['rmse_m']),'comparison_scope':'Same selected roof cells, step, knots, loss, smoothing and withheld longitudinal stripes as shared model. No external validation.'}
report['readiness']='Independent profiles diagnostic; consider candidate only over measured support and separately audit longitudinal transition, boundaries and local residual clusters. No closed building integration.'
fig2,aa=plt.subplots(2,2,figsize=(14,10),layout='constrained')
for east,col,label in [(False,'tab:blue','west'),(True,'tab:orange','east')]:
 q=sel&((u>=split)==east);a=aa[0,int(east)];a.scatter(v[q],z[q],s=6,alpha=.2,c=col);a.plot(vv,np.interp(vv,knots,independent[label]['profile_odn_m']),c=col,lw=2,label='Independent profile');a.plot(vv,curve+east*c[-1],c='gray',ls='--',label='Shared translated profile');a.set(title=label+' roof, same held-out stripes',xlabel='Cross-roof v m',ylabel='ODN m');a.legend()
im=aa[1,0].scatter(u[sel],v[sel],c=indres,s=14,vmin=-.5,vmax=.5,cmap='RdBu_r');fig2.colorbar(im,ax=aa[1,0],label='Observed minus independent fit m');aa[1,0].set(title='Independent profile residuals',aspect='equal',xlabel='u m',ylabel='v m');aa[1,1].scatter(v[test],indtest,s=10);aa[1,1].axhline(0,c='k');aa[1,1].set(title='Identical held-out cells',xlabel='v m',ylabel='Residual m');fig2.suptitle('Museum Docklands: independent west/east profiles, no geometry integration');fig2.savefig(ROOT/'references/museum_roof_fit_independent.png',dpi=140)
(ROOT/'references/museum_roof_fit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['independent_profiles'],indent=2))
