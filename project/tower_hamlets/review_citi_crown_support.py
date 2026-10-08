from pathlib import Path
import runpy,json
import numpy as np
r=Path(__file__).resolve().parent/'input/canary_wharf_20261007';a=runpy.run_path(str(Path(__file__).with_name('review_citi_roof.py')))
x,y,z,t,p,mask=[a[k] for k in ['x','y','z','t','p','mask']];f=json.loads((r/'references/citi_height_zones.json').read_text());o=f['origin_xy_m'];e=f['u_axis'];v=f['v_axis'];u=(x-o[0])*e[0]+(y-o[1])*e[1];w=(x-o[0])*v[0]+(y-o[1])*v[1];m=mask(p)
rows={}
for name,sel in [('west_interior',(u>3)&(u<18)&(w>5)&(w<55)),('west_shoulder',(u>23)&(u<26)&(w>5)&(w<55)),('east_shoulder',(u>72.5)&(u<74)&(w>5)&(w<55)),('top_interior',(u>30)&(u<69)&(w>5)&(w<55))]:
 s=m&sel;rows[name]={'cells':int(s.sum()),'dsm_quantiles':np.percentile(z[s],[0,10,50,90,100]).tolist(),'agl_quantiles':np.percentile((z-t)[s],[0,10,50,90,100]).tolist()}
s=m&(z>200);rows['height_conditioned_crown_support']={'threshold_odn_m':200,'u_quantiles':np.percentile(u[s],[0,1,5,95,99,100]).tolist(),'v_quantiles':np.percentile(w[s],[0,1,5,95,99,100]).tolist(),'warning':'Height-conditioned support only, not surveyed architectural breakline; interpolation and edge cells matter.'}
(r/'references/citi_crown_support.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
