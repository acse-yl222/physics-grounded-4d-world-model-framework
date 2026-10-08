"""Independent geometric checks: real recess depths, shared-edge and owner boundary."""
import json
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,LineString,Point
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/westferry_house_facade_study_003.json').read_text());g=json.loads((R/'geometry.json').read_text());f=next(b for b in g['buildings'] if b['id']==r['building_id']);p=Polygon(f['geometry'][0]['outer']);ring=np.array(f['geometry'][0]['outer']);shared=LineString([ring[4],ring[5]]);body=r['objects'][0];tri=np.array(body['vertices'])[np.array(body['faces'])]
def first_hit(origin,direction):
 e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];h=np.cross(direction,e2);a=np.einsum('ij,ij->i',e1,h);valid=abs(a)>1e-9;inv=np.divide(1,a,out=np.zeros_like(a),where=valid);s=origin-tri[:,0];u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=inv*(q@direction);t=inv*np.einsum('ij,ij->i',e2,q);hit=valid&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(t>1e-6);assert hit.any();return float(t[hit].min())
recess=[]
for e in r['visible_edges']:
 a,b=np.array(e['endpoints_enu_m']);u=(b-a)/np.linalg.norm(b-a);n=np.array(e['inward_normal']);win=next(w for w in r['upper_windows'] if w['edge']==e['edge_index'] and w['bay']==1 and w['row']==3);s=sum(win['s_interval'])/2;z=sum(win['z_interval'])/2;origin=np.r_[a+u*s-n*.25,z];distance=first_hit(origin,np.r_[n,0]);depth=distance-.25;assert abs(depth-.64)<.0002;recess.append({'edge':e['edge_index'],'measured_mesh_recess_m':depth})
a,b=ring[4],ring[5];u=(b-a)/np.linalg.norm(b-a);n=np.array([-u[1],u[0]]);origin=np.r_[(a+b)/2-n*.25,25];hit=first_hit(origin,np.r_[n,0]);assert abs(hit-.25)<.0002
outside=[];mindistance=1e9
for ob in r['objects'][1:]:
 for xy in np.array(ob['vertices'])[:,:2]:
  pt=Point(xy);mindistance=min(mindistance,shared.distance(pt))
  if not p.buffer(1e-5).covers(pt):outside.append(ob['name'])
assert not outside and mindistance>.05
rep={'upper_recess_rays':recess,'shared_edge_4_body_face_preserved':True,'shared_edge_ray_expected_distance_m':.25,'shared_edge_ray_actual_distance_m':hit,'decorative_vertices_outside_owner_footprint':len(outside),'minimum_decoration_distance_to_shared_edge_m':mindistance,'roof_planes_preserved_area_check':r['checks'],'caution':'Tests verify authored geometry and scoped ownership, not factual window counts or ground level.'};(R/'references/westferry_house_facade_003_checks.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(rep,indent=2))
