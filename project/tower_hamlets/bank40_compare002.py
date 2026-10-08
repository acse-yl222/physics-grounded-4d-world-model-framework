from pathlib import Path
exec(Path('project/tower_hamlets/bank40_review.py').read_text().split('rows=[]')[0])
m=mask(p);X=x[m];Y=y[m];Z=z[m];ang=np.deg2rad(-10);U=X*np.cos(ang)+Y*np.sin(ang);V=-X*np.sin(ang)+Y*np.cos(ang);central=(U>=-3)&(U<=11)&(V>=-311)&(V<=-306);out={}
for suffix in ['', '002']:
 study=json.loads((R/f'references/bank40_study{suffix}.json').read_text());meshz=np.full(len(X),-np.inf)
 for ob in study['objects']:
  vv=np.array(ob['vertices'])
  for face in ob['roof_faces']:
   if len(face)!=3:continue
   aa,bb,cc=vv[face];D=np.stack([bb[:2]-aa[:2],cc[:2]-aa[:2]],axis=1)
   if abs(np.linalg.det(D))<1e-10:continue
   bc=np.linalg.solve(D,np.stack([X-aa[0],Y-aa[1]]));inside=(bc[0]>=-1e-7)&(bc[1]>=-1e-7)&(bc.sum(axis=0)<=1+1e-7);zz=aa[2]+bc[0]*(bb[2]-aa[2])+bc[1]*(cc[2]-aa[2]);meshz[inside]=np.maximum(meshz[inside],zz[inside])
 assert np.isfinite(meshz).all();err=Z-meshz-4.28000021;out[suffix or '001']={'whole_owner':metric(err),'central_same_domain':metric(err[central]),'method':'FrozenJSON triangle upper-envelope at every native valid cell, no residual exclusions.'}
out['baseline153']={'whole_owner':metric(Z-153-4.28000021),'central_same_domain':metric((Z-153-4.28000021)[central])};(R/'references/bank40_mesh_comparison002.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
