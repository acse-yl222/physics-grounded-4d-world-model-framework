from pathlib import Path
exec(Path(__file__).with_name('leyland_review.py').read_text().split('rows=[]')[0])
pr=json.loads((R/'references/leyland_profiles.json').read_text());eu=np.array(pr['axis_u']);ev=np.array(pr['axis_v']);u=x*eu[0]+y*eu[1];v=x*ev[0]+y*ev[1];q=ps[0]
def box(a,b,c,d):return Polygon([eu*s+ev*t for s,t in [(a,b),(c,b),(c,d),(a,d)]])
# Rectangles delimit observed straight roof stretches; junctions excluded geometrically, never by height.
domains=[('south_end',box(457,-51,478,-40),v,u,-45.5),('south_crossbar',box(478,-38,488,-25),u,v,483),('west_spine',box(490,-25,509,-12),v,u,-18),('north_crossbar',box(509,-38,521,-25),u,v,514.5),('north_end',box(524,-52,541,-39),v,u,-45.5)]
rows=[];fig,ax=plt.subplots(2,5,figsize=(15,9),layout='constrained');m=mask(q)
for a,arr,title in zip(ax[0],[z,t,z-t],['DSM ODN','DTM ODN','DSM-DTM']):
 im=a.scatter(u[m],v[m],c=arr[m],s=16,marker='s');fig.colorbar(im,ax=a);a.set(aspect='equal',title=title)
uv=np.array(q.exterior.coords)@np.stack([eu,ev],axis=1)
for a in ax[0]:a.plot(uv[:,0],uv[:,1],'r-',lw=.7)
for k,(name,p,cross,along,ridge) in enumerate(domains):
 domain=q.buffer(-1.3).intersection(p);sel=mask(domain);r={'name':name,'area_m2':domain.area,'cells':int(sel.sum()),'dsm':stats(z[sel]),'dtm':stats(t[sel]),'DSM_minus_DTM':stats((z-t)[sel])}
 if sel.sum()>20:
  def fit(mm):return least_squares(lambda c:c[0]-c[1]*abs(cross[mm]-c[2])-z[mm],[23,.5,ridge],bounds=([10,0,ridge-2],[35,3,ridge+2]),loss='soft_l1',f_scale=.15).x
  cf=fit(sel);r['hip_or_gable_cross_section_coefficients_H_slope_ridge']=cf.tolist();r['in_sample']=metric(z[sel]-(cf[0]-cf[1]*abs(cross[sel]-cf[2])))
  r['holdout']=[]
  for fold in range(3):
   test=sel&(np.floor(along/3).astype(int)%3==fold);train=sel&~test
   cc=fit(train);r['holdout'].append({'coefficients':cc.tolist(),**metric(z[test]-(cc[0]-cc[1]*abs(cross[test]-cc[2])))})
  a=ax[1,k];a.scatter(cross[sel],z[sel],s=5,label=name);xx=np.linspace(cross[sel].min(),cross[sel].max(),50);a.plot(xx,cf[0]-cf[1]*abs(xx-cf[2]));a.legend(fontsize=7);a.set(xlabel='Cross-roof rotated coordinate',ylabel='ODN')
 rows.append(r)
fig.savefig(R/'references/leyland_domains.png',dpi=150)
(R/'references/leyland_domains.json').write_text(json.dumps({'domains':rows,'actual_capture_epoch':None,'datum_scene_offset_ODN':4.28000021,'selection':'Geometric straight roof stretches, 1.3m owner inset, no height filtering; bounded official EA extension used; original rasters preserved','geometry_authored':False},indent=2))
print(json.dumps(rows,indent=2))
