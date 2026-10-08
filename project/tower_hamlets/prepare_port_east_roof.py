"""Evidence-constrained roof profile candidate; no unsupported gap closure."""
from pathlib import Path
import runpy,json,hashlib
import numpy as np
from shapely.geometry import Polygon
ns=runpy.run_path(str(Path(__file__).with_name('fit_port_east_roof.py')))
globals().update({k:ns[k] for k in ['ROOT','p','x','y','z','masks','pred']});across=ns['v'];centers=ns['knots'];rep={'ground_scalar_m_odn':4.28000021,'building_id':'overture-building-67710957-baa2-4b34-9bf4-81a97bc93397'}
supported=masks['2']&(across>=centers[0])&(across<=centers[-1])&(np.abs(z-pred)<=.3)
vertices=[];faces=[];lookup={};area=0
for row in range(z.shape[0]-1):
 for col in range(z.shape[1]-1):
  for ij in [[(row,col),(row,col+1),(row+1,col+1)],[(row,col),(row+1,col+1),(row+1,col)]]:
   if not all(supported[i,j] for i,j in ij):continue
   poly=Polygon([(x[i,j],y[i,j]) for i,j in ij])
   if not p.covers(poly):continue
   inds=[]
   for i,j in ij:
    if (i,j) not in lookup:
     lookup[i,j]=len(vertices);vertices.append([float(x[i,j]),float(y[i,j]),float(pred[i,j]-rep['ground_scalar_m_odn'])])
    inds.append(lookup[i,j])
   vv=np.array([vertices[k] for k in inds])
   if np.cross(vv[1]-vv[0],vv[2]-vv[0])[2]<0:inds.reverse()
   faces.append(inds);area+=poly.area
out=ROOT/'references/port_east_profile_roof.obj'
with out.open('w') as f:
 f.write('# Fitted roof profile at observed supported cells; open gaps unknown; ENU metres\n')
 for v in vertices:f.write('v '+' '.join(f'{q:.8f}' for q in v)+'\n')
 for face in faces:f.write('f '+' '.join(str(k+1) for k in face)+'\n')
report={'building_id':rep['building_id'],'method':'Cross-section interpolated fit, limited to native cells within0.3m observed residual and2m inward boundary; no walls or extrapolation','vertices':len(vertices),'triangles':len(faces),'projected_area_m2':area,'footprint_area_m2':p.area,'ground_offset_odn_m':rep['ground_scalar_m_odn'],'all_triangles_inside_outline':True,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'limitations':['Conditional fitted surface, not raw DSM or independently surveyed architecture.','Gaps mean unsupported observations, not actual openings.','Neighboring high returns and low boundary returns excluded.','Local median DTM removes absolute ODN; scene terrain remains flat.']}
(ROOT/'references/port_east_profile_roof.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
