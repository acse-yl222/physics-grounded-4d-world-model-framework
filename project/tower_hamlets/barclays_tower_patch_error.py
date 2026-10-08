from pathlib import Path
exec(Path('project/tower_hamlets/barclays_tower_review.py').read_text().split('rows=[]')[0])
m=mask(p);X=x[m];Y=y[m];Z=z[m];native=json.loads((R/'references/barclays_tower_native.json').read_text());heights=[v[2] for o in native['objects'] for v in o['vertices']];assert abs(max(heights)-156)<.001
r=json.loads((R/'references/barclays_tower_study.json').read_text());ob=r['objects'][0];vv=np.array(ob['vertices']);top=np.full(len(X),-np.inf)
for face in ob['roof_faces']:
 if len(face)!=3:continue
 aa,bb,cc=vv[face];D=np.stack([bb[:2]-aa[:2],cc[:2]-aa[:2]],axis=1)
 if abs(np.linalg.det(D))<1e-10:continue
 bc=np.linalg.solve(D,np.stack([X-aa[0],Y-aa[1]]));inside=(bc[0]>=-1e-7)&(bc[1]>=-1e-7)&(bc.sum(axis=0)<=1+1e-7);zz=aa[2]+bc[0]*(bb[2]-aa[2])+bc[1]*(cc[2]-aa[2]);top[inside]=np.maximum(top[inside],zz[inside])
k=np.isfinite(top);hybrid=np.maximum(top,156);r={'whole_owner_same5056cells':{'baseline':metric(Z-156-4.28000021),'baseline_plus_roofskin_hypothesis':metric(Z-hybrid-4.28000021)},'roofskin_support':metric(Z[k]-top[k]-4.28000021),'method':'FrozenJSONroof triangles upperenvelope sampled at all native1m DSM cellcenters; unchanged native flat156m elsewhere. Compositehypothesis not exported or integrated.','low_returns':{'below30ODN_cells':int((Z<30).sum()),'DSM_DTM_equal_1cm':int((abs(Z-t[m])<.01).sum())},'limitations':['Wholeowner higherrors dominated unresolved perimeterlowreturns; no exclusion.','Roofskin does not resolve southern roof or buildingenvelope.','Boundaryselection exploratory, actual capturevintage unknown.']};(R/'references/barclays_tower_patch_error.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
