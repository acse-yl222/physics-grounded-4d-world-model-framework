from pathlib import Path
exec(Path(__file__).with_name('hipped_residential_review.py').read_text().split('rows=[]')[0])
results=[];fig,axs=plt.subplots(3,3,figsize=(15,13),layout='constrained')
for row,indices in enumerate([[0,1],[4],[2,3]]):
 q=unary_union([ps[i] for i in indices]);rect=np.array(q.minimum_rotated_rectangle.exterior.coords)[:4];ed=np.roll(rect,-1,axis=0)-rect; e=ed[np.argmax(np.linalg.norm(ed,axis=1))];e/=np.linalg.norm(e);n=np.array([-e[1],e[0]]);uv=rect@np.stack([e,n],axis=1);center=uv.mean(axis=0);half=np.ptp(uv,axis=0)/2;u=x*e[0]+y*e[1];v=x*n[0]+y*n[1]
 def predict(c):
  return c[0]+np.minimum(c[1]*(half[0]-abs(u-center[0]-c[3])),c[2]*(half[1]-abs(v-center[1]-c[4])))
 def fit(mm):return least_squares(lambda c:predict(c)[mm]-z[mm],[6,.7,.7,0,0],bounds=([2,.1,.1,-1.5,-1.5],[12,2,2,1.5,1.5]),loss='soft_l1',f_scale=.15).x
 m=mask(q.buffer(-1));c=fit(m);pr=predict(c);checks=[]
 for axis,arr in [('u',u),('v',v)]:
  folds=np.floor(arr/2).astype(int)%3
  for k in range(3):
   train=m&(folds!=k);test=m&(folds==k)
   if train.sum()<10 or test.sum()==0:continue
   cc=fit(train);checks.append({'axis':axis,'fold':k,'parameters':cc.tolist(),**metric((z-predict(cc))[test])})
 result={'ids':[fs[i]['id'] for i in indices],'axis_u':e.tolist(),'axis_v':n.tolist(),'center_uv':center.tolist(),'half_uv':half.tolist(),'parameters_eave_odn_slope_u_slope_v_du_dv':c.tolist(),'formula':'ODN=eave+min(slope_u*(half_u-abs(u-center_u-du)),slope_v*(half_v-abs(v-center_v-dv)))','fit_all_1m_inset_cells':metric((z-pr)[m]),'holdout_2m_strips':checks,'near_ground_cells_1m_inset':int((m&(abs(z-t)<.1)).sum()),'all_footprint_metric':metric((z-pr)[mask(q)])}
 results.append(result)
 for ax,arr,title in zip(axs[row],[z,pr,z-pr],['DSM ODN','Hip hypothesis ODN','Residual all inset cells']):
  im=ax.scatter(x[m],y[m],c=arr[m],s=24,marker='s',cmap='coolwarm' if 'Residual' in title else 'viridis',vmin=-3 if 'Residual' in title else 3,vmax=3 if 'Residual' in title else 11);fig.colorbar(im,ax=ax)
  for i in indices:ax.plot(*ps[i].exterior.xy,'k-')
  ax.set(aspect='equal',title=title+' / '+','.join(str(i+1) for i in indices))
fig.savefig(R/'references/hipped_residential_fit.png',dpi=140)
(R/'references/hipped_residential_fit.json').write_text(json.dumps({'groups':results,'selection':'All valid DSM cells within 1m geometric inset of group union; no height or residual rejection. Robust loss does downweight large residuals. Group bounding rectangle is a hypothesis, not measured roof breakline.','datum_odn_to_scene_subtract_m':4.28000021,'capture_date':None},indent=2))
print(json.dumps(results,indent=2))
