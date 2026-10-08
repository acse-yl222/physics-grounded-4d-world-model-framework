from pathlib import Path
import json,math,numpy as np
from shapely.geometry import Polygon,box
from shapely.ops import transform
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());fit=json.loads((R/'references/west_wintergarden_curve_fit.json').read_text());bid=fit['building_id'];f=next(q for q in g['buildings'] if q['id']==bid);th=math.radians(-10);co,si=math.cos(th),math.sin(th);uv=lambda x,y:(x*co+y*si,-x*si+y*co);xy=lambda u,v:(u*co-v*si,u*si+v*co);p=set_precision(transform(uv,Polygon(f['geometry'][0]['outer'])),.000001);c=fit['geometric_main_u_lt_minus27']['coefficients'];uc,vc=fit['center_uv'];datum=4.28000021
verts=[];faces=[];ids={}
def z(u,v):U=u-uc;V=v-vc;return c[0]+c[1]*U+c[2]*U*U+c[3]*V+c[4]*V*V-datum
def vi(u,v,h):
 x,y=xy(u,v);q=(round(x,6),round(y,6),round(h,6))
 if q not in ids:ids[q]=len(verts);verts.append(list(q))
 return ids[q]
# Clipped 2m discretization; these edges are tessellation, not physical framing.
for u in np.arange(math.floor(p.bounds[0]),p.bounds[2],2):
 for v in np.arange(math.floor(p.bounds[1]),p.bounds[3],2):
  part=set_precision(p.intersection(box(u,v,u+2,v+2)),.000001)
  if part.area<1e-8:continue
  for tri in constrained_delaunay_triangles(part).geoms:
   coords=list(tri.exterior.coords)[:-1];faces.append([vi(a,b,z(a,b)) for a,b in coords]);faces.append([vi(a,b,z(a,b)-.16) for a,b in reversed(coords)])
# Boundary uses vertexgrid intersections to close roofskin side faces exactly.
boundary=[]
for q in verts[::2]:pass
# Extract roof top boundary edges from face usage, after alltop/bottomfaces authored.
from collections import Counter
counts=Counter(tuple(sorted((a,b))) for face in faces[::2] for a,b in zip(face,face[1:]+face[:1]));lookup={tuple(v):i for i,v in enumerate(verts)}
for (i,j),n in counts.items():
 if n!=1:continue
 a=verts[i];b=verts[j];ii=lookup[(a[0],a[1],round(a[2]-.16,6))];jj=lookup[(b[0],b[1],round(b[2]-.16,6))];faces.append([i,j,jj,ii])
obj={'name':'WestWintergarden_estimated_curved_roof_skin','building_id':bid,'kind':'estimated','vertices':verts,'roof_faces':faces,'wall_faces':[],'bottom_faces':[]}
# Baseline roof plate comparison only, not replacementwalls.
baseline={'name':'WestWintergarden_original_roof24','building_id':bid,'kind':'estimated','vertices':[[*xy(u,v),h] for h in [23.84,24] for u,v in list(p.exterior.coords)[:-1]],'roof_faces':[],'wall_faces':[],'bottom_faces':[]};rr=list(p.exterior.coords)[:-1];N=len(rr);baseline['roof_faces']=[list(range(N-1,-1,-1)),list(range(N,2*N))]+[[i,(i+1)%N,(i+1)%N+N,i+N] for i in range(N)]
r={'building_id':bid,'objects':[obj],'baseline_mesh':baseline,'scope':'Roof-only doublycurved descriptive skin from618mainDSMreturns, nofacade/framegrid. Wholemappedoutline includesunverifiedeasternextrapolation. Do notreplacefullbuildingwithroof-onlystudy withoutseparateintegrationdesign.','curve_fit':fit,'skin_thickness_m':.16,'skin_thickness_basis':'artisticallyestimated','limitations':fit['limitations']+['Easternstriproofcurve extrapolated; mixedlowreturnmayreflecttransparentroofpenetration orrealheightstep.','Noentrances/walls/gridframing modeled; roof-onlyhypothesis.']};(R/'references/west_wintergarden_study.json').write_text(json.dumps(r,indent=2));print(len(verts),len(faces))
