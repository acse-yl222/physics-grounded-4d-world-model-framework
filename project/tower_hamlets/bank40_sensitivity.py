from pathlib import Path
exec(Path('project/tower_hamlets/bank40_review.py').read_text().split('rows=[]')[0])
a=np.deg2rad(-10);u=x*np.cos(a)+y*np.sin(a);v=-x*np.sin(a)+y*np.cos(a);m=mask(p);rows=[]
for shift in [-1,0,1]:
 pred=np.where(u>=31+shift,149.1800079345703,np.where(v>=-302,157.28000021,159.3590087890625));rows.append({'east_boundary_u':31+shift,'full_allpoint_error':metric(z[m]-pred[m])})
interface=[]
for f in g['buildings']:
 if f['id']==fs[0]['id']:continue
 q=poly(f);shared=p.boundary.intersection(q.boundary)
 if shared.length>.01:interface.append({'neighbor':f['id'],'name':f.get('name'),'shared':shared.__geo_interface__,'length_m':shared.length,'footprint_overlap_m2':p.intersection(q).area})
out={'east_boundary_sensitivity':rows,'shared_interfaces':interface,'limitations':['Allnativecells retained, candidateboundaries exploratory. Lower east plateau interpretable butnorthlowreturns remain unresolved.','NeighborWintergarden roofstudies held/independentlyauthored; noautomaticchanges. Candidatewall steps do not establish facadeappearance.']};(R/'references/bank40_interface_sensitivity.json').write_text(json.dumps(out,indent=2))
