"""Exact plane intersections over evidence-supported cells; no full enclosure."""
from pathlib import Path
import json,hashlib
import numpy as np
exec(Path(__file__).with_name('analyze_north_quay_east_fit.py').read_text().split('fig,axs=')[0])
report=json.loads((R/'references/north_quay_east_fit.json').read_text());records=[]
def clip(points,coef):
 out=[]
 for a,b in zip(points,points[1:]+points[:1]):
  da=np.dot(coef[:2],a)+coef[2];db=np.dot(coef[:2],b)+coef[2]
  if da<=1e-10:out.append(a)
  if (da<0)!=(db<0):out.append(a+(b-a)*da/(da-db))
 return out
for f,poly in zip(fs,polys):
 rec=next(q for q in report['features'] if q['id']==f['id']);b=rec['parameters_ridge_odn_ridge_u_slope_w_slope_e_south_at_v0_south_slope_north_at_v0_north_slope'];vc=rec['v_origin_m'];planes=np.array([[b[2],0,b[0]-b[2]*b[1]],[b[3],0,b[0]-b[3]*b[1]],[0,b[5],b[4]-b[5]*vc],[0,b[7],b[6]-b[7]*vc]])
 pred=np.min(np.array([a*u+bb*v+c for a,bb,c in planes]),axis=0);mask=valid&(z>21)&(z<26)&(abs(z-pred)<=.4)&np.array([poly.buffer(-2).contains(Point(q,t)) for q,t in zip(x.flat,y.flat)]).reshape(x.shape);verts=[];faces=[];lookup={};area=0;maxerror=0
 for row in range(z.shape[0]-1):
  for col in range(z.shape[1]-1):
   for ij in [[(row,col),(row,col+1),(row+1,col+1)],[(row,col),(row+1,col+1),(row+1,col)]]:
    if not all(mask[i,j] for i,j in ij):continue
    xytri=Polygon([(x[i,j],y[i,j]) for i,j in ij])
    if not poly.covers(xytri):continue
    for k,plane in enumerate(planes):
     points=[np.array([u[i,j],v[i,j]]) for i,j in ij]
     for j,other in enumerate(planes):
      if j!=k and points:points=clip(points,plane-other)
     if len(points)<3:continue
     for n in range(1,len(points)-1):
      pts=[points[0],points[n],points[n+1]];tri=Polygon(pts)
      if tri.area<1e-10:continue
      inds=[]
      for uu,vv in pts:
       xx=uu*np.cos(theta)-vv*np.sin(theta);yy=uu*np.sin(theta)+vv*np.cos(theta);zz=plane@[uu,vv,1]-report['datum_m_odn'];key=(round(xx,8),round(yy,8),round(zz,8))
       if key not in lookup:lookup[key]=len(verts);verts.append([float(xx),float(yy),float(zz)])
       inds.append(lookup[key]);maxerror=max(maxerror,abs(zz+report['datum_m_odn']-np.min(planes@[uu,vv,1])))
      vv=np.array([verts[k] for k in inds])
      if np.cross(vv[1]-vv[0],vv[2]-vv[0])[2]<0:inds.reverse()
      faces.append(inds);area+=tri.area
 assert maxerror<1e-7 and faces
 name='north_quay_hip_'+f['id'].split('-')[-1]+'.obj';path=R/'references'/name
 with path.open('w') as out:
  out.write('# Four-plane fitted partial roof; exact plane intersections; unknown gaps\n')
  for vert in verts:out.write('v '+' '.join(f'{q:.8f}' for q in vert)+'\n')
  for face in faces:out.write('f '+' '.join(str(k+1) for k in face)+'\n')
 records.append({'id':f['id'],'name':rec['name'],'obj':name,'vertices':len(verts),'triangles':len(faces),'projected_area_m2':area,'maximum_plane_intersection_error_m':maxerror,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(R/'references/north_quay_east_hip_candidate.json').write_text(json.dumps({'objects':records,'datum_m_odn':report['datum_m_odn'],'fit_sha256':hashlib.sha256((R/'references/north_quay_east_fit.json').read_bytes()).hexdigest(),'scope':'Four fitted planes with exact intersection lines, retained only within2m eroded footprints and observed residual<=0.4m. No perimeter/walls or unknown gap closure.'},indent=2)+'\n');print(records)
