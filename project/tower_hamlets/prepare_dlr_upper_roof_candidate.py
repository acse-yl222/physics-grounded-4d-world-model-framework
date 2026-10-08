from pathlib import Path
import json,sys,numpy as np
from scipy.optimize import least_squares
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';sys.path.insert(0,str(R))
from src.buildings.dlr_central_frame import frame_data,FEATURE_ID
r=json.loads((R/'references/dlr_upper_envelope.json').read_text());x=np.array(r['bin_centers_v_m']);curves=np.array(r['strip_group_q90_odn_m'],dtype=float);y=np.nanmedian(curves,axis=0);origin=float(np.mean(x));A=np.column_stack([np.ones(len(x)),x-origin,(x-origin)**2]);c=least_squares(lambda c:A@c-y,[44,0,-.03],loss='soft_l1',f_scale=.3).x
f=next(b for b in json.loads((R/'geometry.json').read_text())['buildings'] if b['id']==FEATURE_ID);roof,_,p=frame_data(f);verts,faces=roof;out=[]
for xx,yy,_ in verts:
 v=xx*p['axis_v'][0]+yy*p['axis_v'][1];dv=v-origin;out.append([xx,yy,float(c@[1,dv,dv*dv]-4.28000021)])
path=R/'references/dlr_upper_roof_candidate.obj'
with path.open('w') as f:
 f.write('# Exploratory upper-envelope completion; no verified height datum or surface identity\n')
 for v in out:f.write('v '+' '.join(map(str,v))+'\n')
 for face in faces:f.write('f '+' '.join(str(i+1) for i in face)+'\n')
report={'coefficients_odn_m':c.tolist(),'v_origin_m':origin,'datum_odn_m':4.28000021,'datum_status':'Shared illustrative datum; not surveyed canopy foundation','median_quantile_fit_rmse_m':float(np.sqrt(np.mean((A@c-y)**2))),'vertices':len(out),'faces':len(faces),'scope':'Open roof candidate using smooth upper-quantile profile across mapped footprint. Interpolates disputed strips; not independent validation. Do not move support bases or infer platform height from this model.','geometry_integrated':False};(R/'references/dlr_upper_roof_candidate.json').write_text(json.dumps(report,indent=2));print(report)
