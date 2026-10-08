from pathlib import Path
exec(Path('project/tower_hamlets/mcgraw_review_roof.py').read_text().split('rows=[]')[0])
from shapely.geometry import box,shape
ang=np.deg2rad(-10);u=x*np.cos(ang)+y*np.sin(ang);v=-x*np.sin(ang)+y*np.cos(ang);m=mask(p);r=json.loads((R/'references/mcgraw_structure.json').read_text());pred=np.full(z.shape,np.nan)
for reg in r['regions']:
 q=shape(reg['geometry_uv']);k=m&np.array([q.covers(Point(uu,vv)) for uu,vv in zip(u.flat,v.flat)]).reshape(u.shape);c=reg['plane_odn_c0_cu_cv'];pred[k]=c[0]+c[1]*(u[k]-180)+c[2]*(v[k]+130)
assert np.isfinite(pred[m]).all()
out={'whole_owner_same_cells':{'cells':int(m.sum()),'frozen_envelope':metric(z[m]-pred[m]),'previous_70_95_scene':metric(z[m]-(70.95+4.28000021))},'central_boundary_sensitivity':{}}
for shift in [-1,0,1]:
 k=m&(u>=169-shift)&(u<=193+shift)&(v>=-138-shift)&(v<=-124+shift);zz=z[k];level=float(np.median(zz));out['central_boundary_sensitivity'][str(shift)]={'cells':int(k.sum()),'dsm_odn':stats(zz),'dtm_odn':stats(t[k]),'agl':stats((z-t)[k]),'flat_median_level_odn':level,'flat_all_error':metric(zz-level),'envelope_all_error':metric(zz-pred[k]),'levels_71_to_81_histogram':np.histogram(zz,bins=np.arange(71,82))[0].tolist()}
# Each visible horizontal return strip; these are observational domains, not declared architecture.
out['central_geometric_strips']=[]
for lo,hi in [(-138,-136),(-136,-132),(-132,-130),(-130,-126),(-126,-124)]:
 k=m&(u>=169)&(u<=193)&(v>=lo)&(v<hi);out['central_geometric_strips'].append({'v_interval':[lo,hi],'dsm_odn':stats(z[k]),'dtm_odn':stats(t[k]),'flat_median_errors':metric(z[k]-np.median(z[k]))})
out['conclusion']='Central domain is internally heterogeneous: low narrow frame-like bands alternate with elevated surfaces. A single closed lowered roof plane would replace some supported high returns with low geometry. Retain three-zone envelope only as explicitly coarse control, not accurate central roof. No hole, equipment, or depressed plane asserted.'
out['datum']='Scene z = ODN - 4.28000021; actual raster capture vintage unresolved.'
(R/'references/mcgraw_central_review.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
study=json.loads((R/'references/mcgraw_study.json').read_text());X=x[m];Y=y[m];meshz=np.full(len(X),-np.inf)
for ob in study['objects']:
 vv=np.array(ob['vertices'])
 for face in ob['roof_faces']:
  if len(face)!=3:continue
  aa,bb,cc=vv[face];D=np.stack([bb[:2]-aa[:2],cc[:2]-aa[:2]],axis=1)
  if abs(np.linalg.det(D))<1e-10:continue
  bc=np.linalg.solve(D,np.stack([X-aa[0],Y-aa[1]]));inside=(bc[0]>=-1e-7)&(bc[1]>=-1e-7)&(bc.sum(axis=0)<=1+1e-7);zz=aa[2]+bc[0]*(bb[2]-aa[2])+bc[1]*(cc[2]-aa[2]);meshz[inside]=np.maximum(meshz[inside],zz[inside])
assert np.isfinite(meshz).all();out['whole_owner_same_cells']['frozen_mesh_triangle_sample']=metric(z[m]-(meshz+4.28000021));out['whole_owner_same_cells']['mesh_analytic_max_difference_m']=float(np.max(abs(meshz+4.28000021-pred[m])));(R/'references/mcgraw_central_review.json').write_text(json.dumps(out,indent=2))
