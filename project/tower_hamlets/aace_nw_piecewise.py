from pathlib import Path
import json,numpy as np
exec(Path(__file__).with_name('aace_model_sensitivity.py').read_text().split('rows=[];')[0])
m=mask(transform(xy,nw).buffer(-1));lo=np.array(nw.bounds[:2]);hi=np.array(nw.bounds[2:]);center=(lo+hi)/2
# Stable geometric anchor is north-west wing eastern source edge; infer low band3mwest of it.
anchor=hi[0]-3;rows=[];predictions={}
for boundary in [anchor-1,anchor,anchor+1]:
 def pred(c):
  # Westroof: transversegable peak varying alongu; transition2m wide blendsallcells toeastlevel.
  west=c[0]-c[1]*abs(v-c[3])+c[2]*(u-center[0]);blend=np.clip((u-(boundary-2))/2,0,1);return west*(1-blend)+c[4]*blend
 def fit(mm):return least_squares(lambda c:(pred(c)-z)[mm],[11,.5,0,center[1],6],bounds=([5,0,-1,lo[1]+2,3],[18,2,1,hi[1]-2,10]),loss='soft_l1',f_scale=.2).x
 c=fit(m);checks={}
 for name,arr in [('u',u),('v',v)]:
  folds=np.floor(arr/3).astype(int)%3;errs=[];pars=[]
  for k in range(3):
   test=m&(folds==k);train=m&(folds!=k);cf=fit(train);errs.extend((z-pred(cf))[test]);pars.append(cf.tolist())
  checks[name]={'metrics':metric(np.array(errs)),'fold_parameters':pars}
 rows.append({'boundary_low_start_u':boundary,'transition_start_u':boundary-2,'parameters_west_ridge_slopev_slopeu_ridgev_eastlevel':c.tolist(),'fit':metric((z-pred(c))[m]),'holdout_all118_cells':checks});predictions[boundary]=pred(c).copy()
fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained');pd=predictions[anchor]
for ax,arr,title,lims in zip(axs,[z,pd,z-pd],['NW DSM','Anchored full-domain piecewise','All118 residual'],[(5,13),(5,13),(-2,2)]):
 im=ax.scatter(u[m],v[m],c=arr[m],s=25,vmin=lims[0],vmax=lims[1],cmap='coolwarm' if 'residual' in title else 'viridis');fig.colorbar(im,ax=ax);ax.plot(*nw.exterior.xy,'k-');ax.axvline(anchor,color='r',lw=.7);ax.axvline(anchor-2,color='r',lw=.7,ls='--');ax.set(aspect='equal',title=title)
fig.savefig(R/'references/aace_nw_piecewise.png',dpi=160);out={'mapped_wing_bounds_uv':[lo.tolist(),hi.tolist()],'anchor_basis':'Sourceeasternwingedgeu=-296.244; lowbandstart3mwest, transition2mwide. Bandwidthsartistinterpretationfromnativeprofiles, not mappedroofedges. Sensitivity±1m.','anchor_u':anchor,'models':rows,'sample_selection':'Full1m inset ofmappedNWwing118cells, noheightorresidualrejection. Robusttrainingonly.','photo_status':'ExistingestatePexelsviews centred onmainestate; no positivelyidentifiedviewofthissmallnorthwestoffice. No neighboringfacadetransfer ornewacquisition.','limitations':['Actualrastercapturevintageunknown. Per-buildingidentityaddressunresolved.','Blendmodel is continuousbutbilinearquadraticwithslopeu; notautomaticallyauthorablephysicalroofplanes.','Westroofpeakform notexternallyverified; boundarywidthconditional.']};(R/'references/aace_nw_piecewise.json').write_text(json.dumps(out,indent=2));print([(r['boundary_low_start_u'],r['parameters_west_ridge_slopev_slopeu_ridgev_eastlevel'],{k:x['metrics'] for k,x in r['holdout_all118_cells'].items()}) for r in rows])
