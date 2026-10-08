from pathlib import Path
exec(Path(__file__).with_name('owner87aa_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
from shapely import constrained_delaunay_triangles,set_precision
pr=json.loads((R/'references/owner87aa_profiles.json').read_text());e=np.array(pr['axis_u']);n=np.array(pr['axis_v']);uv=lambda xx,yy:(xx*e[0]+yy*e[1],xx*n[0]+yy*n[1]);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);p=transform(uv,ps[0]);u=x*e[0]+y*e[1];v=x*n[0]+y*n[1];ugrid=u.copy();vgrid=v.copy()
domains={name:p.intersection(box(lo,-1000,hi,1000)) for name,lo,hi in [('upper_roof',-1000,-444.3),('terrace_1',-444.3,-437),('terrace_2',-437,-429.4),('terrace_3',-429.4,1000)]};objs=[];rows=[];areas=[]
for name,domain in domains.items():
 mm=mask(transform(xy,domain).buffer(-.6));datum=4.28000021
 if False:height=25.32539176940918;record={'note':'Original flat native maintained including ambiguouscentral lowreturn patch; no invented courtyard.'}
 else:
  fit=lambda sel:float(least_squares(lambda c:np.full(sel.sum(),c[0])-z[sel],[np.median(z[sel])],loss='soft_l1',f_scale=.1).x[0]);odn=fit(mm);height=odn-datum;checks=[]
  for aname,arr in [('u',ugrid),('v',vgrid)]:
   fold=np.floor(arr/2).astype(int)%3
   for k in range(3):
    tr=mm&(fold!=k);te=mm&(fold==k)
    if tr.sum()>5 and te.sum():h=fit(tr);checks.append({'axis':aname,'fold':k,'ODN_m':h,**metric(z[te]-h)})
  record={'fit_ODN_m':odn,'scene_z_m':height,'all_geometric_inset_residual':metric(z[mm]-odn),'holdout':checks}
 rows.append({'name':name,'area_m2':domain.area,**record})
 for k,part in enumerate(list(domain.geoms) if hasattr(domain,'geoms') else [domain]):
  part=set_precision(part,.000001)
  if part.area<1e-7:continue
  vs=[];ix={};roof=[];walls=[];bottom=[]
  def vi(u,v,z):
   xx,yy=xy(u,v);key=tuple(round(a,7) for a in (xx,yy,z))
   if key not in ix:ix[key]=len(vs);vs.append(list(key))
   return ix[key]
  for tri in constrained_delaunay_triangles(part).geoms:
   rr=list(tri.exterior.coords)[:-1];roof.append([vi(u,v,height) for u,v in rr]);bottom.append([vi(u,v,0) for u,v in reversed(rr)])
  for ring in [part.exterior,*part.interiors]:
   for (u,v),(uu,vv) in zip(ring.coords,list(ring.coords)[1:]):walls.append([vi(u,v,0),vi(uu,vv,0),vi(uu,vv,height),vi(u,v,height)])
  objs.append({'name':f'Owner87aa_{name}_{k}','building_id':fs[0]['id'],'kind':'estimated','vertices':vs,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom});areas.append(part.area)
r={'replacement_ids':[fs[0]['id']],'objects':objs,'scope':'Owner87aa four spatially evidenced roof tiers; fullmappedfootprint, no inferred openings orfacade reconstruction.','fit':rows,'checks':[{'footprint_area_m2':p.area,'partition_area_m2':sum(areas),'difference_m2':sum(areas)-p.area}],'limitations':['Terraceboundariesestimated from1m spatialsteps; within-zone smalllowreturnareas notcarved.','Within-tier nearterrain returns remainunresolved; no inferred holes.','Original9munknownheightmass replaced byfour spatialtiers; upperroofsmallgradient simplifiedflat.','SharedODNoffset4.28000021m,flatbase0illustrative,actualcapturedateunknown.','No optical facade verification;internalpartitionwalls deliberatelycoincident.']};(R/'references/owner87aa_study.json').write_text(json.dumps(r,indent=2))
