from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon
S=Path(__file__).resolve().parent;ns={'__file__':str(S/'analyze_carpark_lidar.py')};exec(compile((S/'analyze_carpark_lidar.py').read_text().split('rep=')[0],str(S/'analyze_carpark_lidar.py'),'exec'),ns)
for k in ['ROOT','x','y','z','p','masks']:globals()[k]=ns[k]
r=json.loads((ROOT/'references/carpark_level_planes.json').read_text());out=[]
for plane in [r['planes'][0],r['planes'][2]]:
 lo,hi=plane['selection_odn_m'];cx,cy=plane['center_xy_m'];a,b,c=plane['coefficients_odn_m'];pred=a+b*(x-cx)+c*(y-cy);support=masks['3']&(z>lo)&(z<hi)&(abs(z-pred)<.15);verts=[];faces=[];lookup={};area=0
 for i in range(z.shape[0]-1):
  for j in range(z.shape[1]-1):
   for tri in [[(i,j),(i,j+1),(i+1,j+1)],[(i,j),(i+1,j+1),(i+1,j)]]:
    if not all(support[q] for q in tri):continue
    xy=np.array([[x[q],y[q]] for q in tri]);poly=Polygon(xy)
    if not p.covers(poly):continue
    cross=np.linalg.det([xy[1]-xy[0],xy[2]-xy[0]])
    if cross<0:tri.reverse()
    f=[]
    for q in tri:
     if q not in lookup:lookup[q]=len(verts);verts.append([float(x[q]),float(y[q]),float(pred[q]-4.28000021)])
     f.append(lookup[q])
    faces.append(f);area+=abs(cross)/2
 name='carpark_plane_'+plane['name']+'.obj';(ROOT/'references'/name).write_text(''.join('v '+' '.join(f'{a:.8f}' for a in q)+'\n' for q in verts)+''.join('f '+' '.join(str(a+1) for a in q)+'\n' for q in faces));out.append({'obj':name,'area_m2':area,'triangles':len(faces),'vertices':len(verts)})
(ROOT/'references/carpark_plane_candidates.json').write_text(json.dumps({'objects':out,'datum_odn_m':4.28000021,'support':'3m inset; original height band; all triangle vertices residual<0.15m; no gap closure','scope':'Conditional low/high upper surfaces only; middle band remains native observations'},indent=2)+'\n');print(out)
