"""Native supported car park upper surfaces; no inferred ramps or facades."""
from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon
S=Path(__file__).resolve().parent;ns={'__file__':str(S/'analyze_carpark_lidar.py')};exec(compile((S/'analyze_carpark_lidar.py').read_text().split('rep=')[0],str(S/'analyze_carpark_lidar.py'),'exec'),ns)
for k in ['ROOT','x','y','z','p','masks','ground','f']:globals()[k]=ns[k]
datum=float(np.median(ground[masks['0']]));support=masks['1']&(z>18)&(z<32);vertices=[];faces=[];lookup={};area=0
for i in range(z.shape[0]-1):
 for j in range(z.shape[1]-1):
  for tri in [[(i,j),(i,j+1),(i+1,j+1)],[(i,j),(i+1,j+1),(i+1,j)]]:
   if not all(support[q] for q in tri) or np.ptp([z[q] for q in tri])>1.25:continue
   xy=np.array([[x[q],y[q]] for q in tri]);poly=Polygon(xy)
   if not p.covers(poly):continue
   cross=float(np.linalg.det([xy[1]-xy[0],xy[2]-xy[0]]))
   if cross<0:tri.reverse()
   inds=[]
   for q in tri:
    if q not in lookup:lookup[q]=len(vertices);vertices.append([float(x[q]),float(y[q]),float(z[q]-datum)])
    inds.append(lookup[q])
   faces.append(inds);area+=abs(cross)/2
obj=ROOT/'references/carpark_native_roof.obj';obj.write_text('# Native upper surface observations; no inferred ramps/walls\n'+''.join('v '+' '.join(f'{a:.8f}' for a in q)+'\n' for q in vertices)+''.join('f '+' '.join(str(a+1) for a in q)+'\n' for q in faces));report={'building_id':f['id'],'obj':obj.name,'datum_odn_m':datum,'vertices':len(vertices),'triangles':len(faces),'projected_area_m2':area,'footprint_area_m2':p.area,'selection':'Native cells inside1m footprint inset;18<DSM<32ODN;triangle height spread<=1.25m; holes preserved','source_sha256':hashlib.sha256((ROOT/'references/ea_dsm_1m.tif').read_bytes()).hexdigest(),'baseline_height_m':f['height_m'],'selected_surface_odn_quantiles':np.percentile(z[support],[5,50,95]).tolist(),'limitations':['Historical1m DSM versus2026 footprint, unknown current condition.','No optical identification of parked cars, ramps, parapets or equipment.','Lower levels/façades absent. Native abrupt discontinuities retained as gaps.','Local medianDTM maps to flat scene, not surveyed foundation.']};(ROOT/'references/carpark_native_roof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
