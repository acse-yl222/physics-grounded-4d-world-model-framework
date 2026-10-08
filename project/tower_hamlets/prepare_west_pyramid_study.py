from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon
from shapely.ops import transform
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());fit=json.loads((R/'references/west_pyramids_fit.json').read_text());e=np.array(fit['axis_u']);n=np.array(fit['axis_v']);c=np.array(fit['center_uv']);h=np.array(fit['half_widths_uv']);datum=4.28000021;E=fit['eave_odn_m'];rise=fit['rise_m'];uv=lambda x,y:(x*e[0]+y*e[1],x*n[0]+y*n[1]);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);corners=[c+h*np.array(k) for k in [(-1,-1),(1,-1),(1,1),(-1,1)]]
def mesh(p,bid,name,flat=False):
 vs=[];faces=[];ix={}
 def vi(u,v,z):
  x,y=xy(u,v);k=tuple(round(a,7) for a in (x,y,z))
  if k not in ix:ix[k]=len(vs);vs.append(list(k))
  return ix[k]
 def zz(u,v):return 6 if flat else E+rise*(1-max(abs((u-c[0])/h[0]),abs((v-c[1])/h[1])))-datum
 for tri in constrained_delaunay_triangles(p).geoms:
  rr=list(tri.exterior.coords)[:-1];faces.append([vi(u,v,zz(u,v)) for u,v in rr]);faces.append([vi(u,v,0) for u,v in reversed(rr)])
 for (u,v),(uu,vv) in zip(p.exterior.coords,list(p.exterior.coords)[1:]):faces.append([vi(u,v,0),vi(uu,vv,0),vi(uu,vv,zz(uu,vv)),vi(u,v,zz(u,v))])
 return {'name':name,'building_id':bid,'kind':'estimated','vertices':vs,'roof_faces':faces,'wall_faces':[],'bottom_faces':[]}
objs=[];baselines=[];checks=[]
for i,bid in enumerate(fit['ids']):
 f=next(f for f in g['buildings'] if f['id']==bid);p=transform(uv,Polygon(f['geometry'][0]['outer']));baselines.append(mesh(p,bid,'WestPyramid_baseline_'+str(i),True));areas=0
 for j in range(4):
  # far triangles cover footprint, partition along apex-to-corner lines
  sector=Polygon([c,c+10*(corners[j]-c),c+10*(corners[(j+1)%4]-c)]);q=set_precision(p.intersection(sector),.000001)
  if q.area<1e-6:continue
  objs.append(mesh(q,bid,f'WestPyramid_{i}_slope_{j}'));areas+=q.area
 checks.append({'id':bid,'footprint_area_m2':p.area,'partition_area_m2':areas,'difference_m2':areas-p.area})
r={'objects':objs,'baseline_meshes':baselines,'baseline_mesh':baselines[0],'scope':'Two adjoining mapped houses share one DSM-supported descriptive pyramidal roof, independently editable owner/sector closed solids. No facade details.','fit':fit,'checks':checks,'replacement_ids':fit['ids'],'limitations':fit['limitations']+['Internal coincident walls remain between closed sector solids. Exact apex fixed at pair bounding-rectangle centre; estimate not measured node. Scene usesflat4.28000021ODN base.']};(R/'references/west_pyramid_study.json').write_text(json.dumps(r,indent=2))
