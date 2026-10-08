exec(open('project/tower_hamlets/audit_cabot_west_strip001.py').read().split('zone=d')[0])
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union
O=R/'exports/cabot-west-roof-study-001';O.mkdir(exist_ok=True)
zone=d['zones'][2];poly=Polygon(zone['geometry'][0]['outer']);z=np.asarray(Z);ground=np.asarray(G);valid=~np.ma.getmaskarray(Z);mask=valid&np.array([poly.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape)
# Local axes: along original straight west chord; inward positive east.
ring=d['source_geometry']['geometry'][0]['outer'];a=np.array(ring[1]);b=np.array(ring[14]);t=(b-a)/np.linalg.norm(b-a);n=np.array([t[1],-t[0]]);u=(x-a[0])*t[0]+(y-a[1])*t[1];v=(x-a[0])*n[0]+(y-a[1])*n[1]
rows=[]
for idx in zip(*np.where(mask)):
 i,j=idx;rows.append({'x':float(x[idx]),'y':float(y[idx]),'u':float(u[idx]),'v':float(v[idx]),'dsm_odn':float(z[idx]),'dtm_odn':float(ground[idx])})
high=mask&(z>26)&(z<27.2);pts=np.c_[u[high],v[high]];print('high',len(pts),'range',pts.min(0),pts.max(0))
# Explicit bounded candidate: estimated ellipse cap constrained to existing west strip,
# compare a small boundary family, not high-cell islands/DSM holes.
results=[]
for uc in [23.,23.5,24.,24.5,25.,25.5,26.]:
 for ru in [5.0,5.5,6.0,6.5]:
  for front in [.5,1.,1.5,2.,2.5,3.]:
   pred=((u-uc)/ru)**2+((v-5)/(5-front))**2<=1
   sel=mask&pred
   if sel.sum()<5:continue
   h=float(np.median(z[high]));old=zone['roof_median_odn_m'];res=np.where(sel,h,old)-z
   # report all cells and stable independent high/low confusion, not optimizer-certified truth
   results.append({'center_u':uc,'radius_u':ru,'front_v':front,'raised_cells':int(sel.sum()),'high_recall':float(np.mean(pred[high])),'rmse_all':float(np.sqrt(np.mean(res[mask]**2))),'mae_all':float(np.mean(abs(res[mask]))),'new_low_under20':int(np.sum(sel&(z<20)))})
results.sort(key=lambda q:q['rmse_all']);best=results[0];uc,ru,front=best['center_u'],best['radius_u'],best['front_v'];theta=np.linspace(0,2*np.pi,129);uv=np.c_[uc+ru*np.cos(theta),5+(5-front)*np.sin(theta)];xy=a+uv[:,0,None]*t+uv[:,1,None]*n;candidate=poly.intersection(Polygon(xy)).simplify(.005,preserve_topology=True);h=float(np.median(z[high]));baseline=zone['roof_median_odn_m']
fig,axs=plt.subplots(1,2,figsize=(14,8));im=axs[0].scatter(x[mask],y[mask],c=z[mask],s=28,vmin=9,vmax=28);fig.colorbar(im,ax=axs[0],label='all DSM ODN m');axs[0].plot(*poly.exterior.xy,c='black');axs[0].plot(*candidate.exterior.xy,c='red',lw=2);axs[0].set_aspect('equal');axs[0].set_title('Red: estimated inner roof candidate; black: original west strip');axs[1].scatter(u[mask],v[mask],c=z[mask],s=30,vmin=9,vmax=28);cv=np.array(candidate.exterior.coords);du=(cv-a)@t;dv=(cv-a)@n;axs[1].plot(du,dv,c='red');axs[1].set(xlabel='along chord u m',ylabel='inward v m',title='Native-cell centers; no footprint deletion');fig.tight_layout();fig.savefig(O/'boundary-study.png',dpi=150)
report={'owner_id':d['building_id'],'source':'existing EA DSM/DTM 1m; flight date unknown','all_strip_cells':rows,'all_count':len(rows),'near_dtm_10cm':int(np.sum(mask&(abs(z-ground)<=.1))),'high_seed_count':int(high.sum()),'high_seed_odn_median':h,'baseline_odn':baseline,'baseline_all_rmse':float(np.sqrt(np.mean((z[mask]-baseline)**2))),'candidate_family':results,'selected_for_diagnostic_only':best,'candidate_outer_xy':list(candidate.exterior.coords)[:-1],'limitations':['Boundary estimated from raster support, not a mapped roof edge.','Full-grid RMSE includes DTM-equal cells, not interpreted as holes.','No facade correspondence or photographed parapet attribution achieved.','No geometry changed; ellipse family is a diagnostic, not measured shape.']};(O/'boundary-study.json').write_text(json.dumps(report,indent=2));print(best,'baseline',report['baseline_all_rmse'])
