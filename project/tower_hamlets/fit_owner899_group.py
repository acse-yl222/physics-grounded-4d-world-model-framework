from pathlib import Path
import json,numpy as np
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'review_owner899_roof.py')};exec((P/'review_owner899_roof.py').read_text().split('rows=[]')[0],ns)
g=ns['g'];R=ns['R'];x,y,z,t=ns['x'],ns['y'],ns['z'],ns['t'];ps=ns['ps'];mask=ns['mask']
# Dominant longest mapped edge establishes local horizontal axes; no image tracing.
coords=list(ps[0].exterior.coords);a,b=max(zip(coords,coords[1:]),key=lambda ab:np.linalg.norm(np.subtract(*ab)));u=np.subtract(b,a);u=u/np.linalg.norm(u)
if u[0]<0:u=-u
v=np.array([-u[1],u[0]]);origin=np.array(ps[0].centroid.coords[0]);U=(x-origin[0])*u[0]+(y-origin[1])*u[1];V=(x-origin[0])*v[0]+(y-origin[1])*v[1]
report={'origin':origin.tolist(),'u':u.tolist(),'v':v.tolist(),'overlap_area_m2':0.0,'shared_length_m':0.0,'parts':[]}
for i,p in enumerate(ps):
 m=mask(p.buffer(-2));xy=np.array(p.exterior.coords);uv=np.column_stack([(xy-origin)@u,(xy-origin)@v]);row={'id':ns['fs'][i]['id'],'uv_bounds':[uv.min(0).tolist(),uv.max(0).tolist()],'profiles':{}}
 for label,arr in [('u',U),('v',V)]:
  row['profiles'][label]=[{'range':[float(lo),float(lo+2)],'cells':int(mm.sum()),'p10_p50_p90':np.percentile(z[mm],[10,50,90]).tolist()} for lo in np.arange(np.floor(arr[m].min()),arr[m].max(),2) if (mm:=m&(arr>=lo)&(arr<lo+2)).sum()]
 report['parts'].append(row)
np.savez(R/'references/owner899_samples.npz',x=x,y=y,z=z,dtm=t,u=U,v=V,valid=ns['valid'])
(R/'references/owner899_spatial_profiles.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
