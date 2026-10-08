from pathlib import Path
import json,numpy as np
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'review_upper_bank_group_roof.py')};exec((P/'review_upper_bank_group_roof.py').read_text().split('rows=[]')[0],ns)
g=ns['g'];R=ns['R'];x,y,z,t=ns['x'],ns['y'],ns['z'],ns['t'];ps=ns['ps'];mask=ns['mask']
# Dominant longest mapped edge establishes local horizontal axes; no image tracing.
coords=list(ps[0].exterior.coords);a,b=max(zip(coords,coords[1:]),key=lambda ab:np.linalg.norm(np.subtract(*ab)));u=np.subtract(b,a);u=u/np.linalg.norm(u)
if u[0]<0:u=-u
v=np.array([-u[1],u[0]]);origin=np.array(ps[0].centroid.coords[0]);U=(x-origin[0])*u[0]+(y-origin[1])*u[1];V=(x-origin[0])*v[0]+(y-origin[1])*v[1]
report={'origin':origin.tolist(),'u':u.tolist(),'v':v.tolist(),'overlap_area_m2':ps[0].intersection(ps[1]).area,'shared_length_m':ps[0].boundary.intersection(ps[1].boundary).length,'parts':[]}
for i,p in enumerate(ps):
 m=mask(p.buffer(-2));xy=np.array(p.exterior.coords);uv=np.column_stack([(xy-origin)@u,(xy-origin)@v]);row={'id':ns['fs'][i]['id'],'uv_bounds':[uv.min(0).tolist(),uv.max(0).tolist()],'profiles':{}}
 for label,arr in [('u',U),('v',V)]:
  row['profiles'][label]=[{'range':[float(lo),float(lo+2)],'cells':int(mm.sum()),'p10_p50_p90':np.percentile(z[mm],[10,50,90]).tolist()} for lo in np.arange(np.floor(arr[m].min()),arr[m].max(),2) if (mm:=m&(arr>=lo)&(arr<lo+2)).sum()]
 report['parts'].append(row)
np.savez(R/'references/upper_bank_samples.npz',x=x,y=y,z=z,dtm=t,u=U,v=V,valid=ns['valid'])
(R/'references/upper_bank_spatial_profiles.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
from shapely.geometry import shape
from shapely.ops import transform,unary_union
from pyproj import Transformer
raw=json.loads((R/'references/buildings.geojson').read_text());f=next(f for f in raw['features'] if 'cc72c0ea' in str(f.get('id')))
tr=Transformer.from_crs(4326,g['crs'],always_xy=True);parent=transform(tr.transform,shape(f['geometry']));report['raw_parent']={'id':f.get('id'),'properties':f['properties'],'area_m2':parent.area,'child_union_symdiff_m2':parent.symmetric_difference(unary_union(ps)).area,'children_outside_parent_m2':unary_union(ps).difference(parent).area}
import matplotlib.pyplot as plt
fig,axs=plt.subplots(1,2,figsize=(12,7),layout='constrained')
for i,p in enumerate(ps):
 m=mask(p);im=axs[i].scatter(U[m],V[m],c=z[m],s=8,marker='s',vmin=[145,38][i],vmax=[160,49][i],cmap='viridis');fig.colorbar(im,ax=axs[i],label='ODN m (clamped colour range)');xy=np.array(p.exterior.coords);uv=np.column_stack([(xy-origin)@u,(xy-origin)@v]);axs[i].plot(*uv.T,c='r');axs[i].set(aspect='equal',title=['Tower part: low returns shown at colour floor','Lower part: low returns shown at colour floor'][i],xlabel='Mapped-edge u metres',ylabel='Mapped-edge v metres')
fig.savefig(R/'references/upper_bank_roof_zones_diagnostic.png',dpi=160)
(R/'references/upper_bank_spatial_profiles.json').write_text(json.dumps(report,indent=2)+'\n');print(report['raw_parent'])
