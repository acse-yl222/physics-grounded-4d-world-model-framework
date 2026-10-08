"""Evidence-constrained roof profile candidate; no unsupported gap closure."""
from pathlib import Path
import runpy,json,hashlib
import numpy as np
from shapely.geometry import Polygon
ns=runpy.run_path(str(Path(__file__).with_name('analyze_billingsgate_lidar.py')))
globals().update({k:ns[k] for k in ['ROOT','p','x','y','z','masks','across','pred','centers','rep']})
supported=masks['1']&(across>=centers[0])&(across<=centers[-1])&(z>pred+.5)
vertices=[];faces=[];lookup={};area=0
for row in range(z.shape[0]-1):
 for col in range(z.shape[1]-1):
  for ij in [[(row,col),(row,col+1),(row+1,col+1)],[(row,col),(row+1,col+1),(row+1,col)]]:
   if not all(supported[i,j] for i,j in ij):continue
   if np.ptp([z[i,j] for i,j in ij])>2.5:continue
   poly=Polygon([(x[i,j],y[i,j]) for i,j in ij])
   if not p.covers(poly):continue
   inds=[]
   for i,j in ij:
    if (i,j) not in lookup:
     lookup[i,j]=len(vertices);vertices.append([float(x[i,j]),float(y[i,j]),float(z[i,j]-rep['ground_scalar_m_odn'])])
    inds.append(lookup[i,j])
   vv=np.array([vertices[k] for k in inds])
   if np.cross(vv[1]-vv[0],vv[2]-vv[0])[2]<0:inds.reverse()
   faces.append(inds);area+=poly.area
out=ROOT/'references/billingsgate_raised_observations.obj'
with out.open('w') as f:
 f.write('# Raw elevated DSM observations; open gaps unknown; ENU metres\n')
 for v in vertices:f.write('v '+' '.join(f'{q:.8f}' for q in v)+'\n')
 for face in faces:f.write('f '+' '.join(str(k+1) for k in face)+'\n')
report={'building_id':rep['building_id'],'method':'Raw DSM triangles above fitted profile by0.5m,1m inward boundary, triangle height range at most2.5m; no wall inference','vertices':len(vertices),'triangles':len(faces),'projected_area_m2':area,'footprint_area_m2':p.area,'ground_offset_odn_m':rep['ground_scalar_m_odn'],'all_triangles_inside_outline':True,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'limitations':['Native raster elevated surface, not identified architectural components.','Gaps mean unsupported observations, not actual openings.','Only sufficiently contiguous elevated returns retained; steep edges and isolated returns excluded.','Local median DTM removes absolute ODN; scene terrain remains flat.']}
(ROOT/'references/billingsgate_raised_observations.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
