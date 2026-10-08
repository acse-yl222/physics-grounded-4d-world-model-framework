from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,shape
from shapely.ops import transform,unary_union
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/fff_boundary-evidence-002';fit=json.load(open(O/'fff_boundary-fit.json'));audit=json.load(open(O/'fff_boundary-audit.json'));e=np.array(fit['axis_u']);n=np.array(fit['axis_v']);lo=np.array(fit['uv_lo']);hi=np.array(fit['uv_hi']);par=fit['free_parameters_eave_rise_du_dv'];c=np.array(fit['center_uv'])+par[2:];E,rise=par[:2];datum=4.28000021;uv=lambda x,y:(x*e[0]+y*e[1],x*n[0]+y*n[1]);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);corners=[np.array(v) for v in [(lo[0],lo[1]),(hi[0],lo[1]),(hi[0],hi[1]),(lo[0],hi[1])]]
def height(u,v):return E+rise*min((u-lo[0])/(c[0]-lo[0]),(hi[0]-u)/(hi[0]-c[0]),(v-lo[1])/(c[1]-lo[1]),(hi[1]-v)/(hi[1]-c[1]))-datum
objs=[];checks=[];parts=[]
for i,key in enumerate(['fff95900','02ed5509']):
 f=next(f for f in audit['nearby_raw_owners'] if f['id'].startswith(key));p=transform(uv,shape(f['geometry_local']));pieces=[]
 for j in range(4):
  sector=Polygon([c,c+10*(corners[j]-c),c+10*(corners[(j+1)%4]-c)]);q=set_precision(p.intersection(sector),1e-7)
  if q.area<1e-6:continue
  pieces.append(q);verts=[];faces=[];idx={}
  def vi(u,v,z):
   xx,yy=xy(u,v);k=tuple(round(a,7) for a in (xx,yy,z))
   if k not in idx:idx[k]=len(verts);verts.append(list(k))
   return idx[k]
  for tri in constrained_delaunay_triangles(q).geoms:
   rr=list(tri.exterior.coords)[:-1];faces.append([vi(u,v,height(u,v)) for u,v in rr]);faces.append([vi(u,v,0) for u,v in reversed(rr)])
  for a,b in zip(q.exterior.coords,list(q.exterior.coords)[1:]):faces.append([vi(*a,0),vi(*b,0),vi(*b,height(*b)),vi(*a,height(*a))])
  objs.append({'name':f'fff_boundary_{"target" if i==0 else "outside_context"}_sector{j}','building_id':'overture-building-'+f['id'],'context_only':i==1,'vertices':verts,'faces':faces})
 checks.append({'owner':f['id'],'area_m2':p.area,'partition_area_m2':sum(q.area for q in pieces),'symdiff_m2':unary_union(pieces).symmetric_difference(p).area});parts.append(f)
shared=shape(parts[0]['geometry_local']).boundary.intersection(shape(parts[1]['geometry_local']).boundary);edge=list(shared.coords);samples=[]
for t in np.linspace(0,1,21):
 q=(1-t)*np.array(edge[0])+t*np.array(edge[-1]);uu,vv=uv(*q);samples.append([*q,height(uu,vv)])
D={'objects':objs,'replace_ids':['overture-building-'+parts[0]['id']],'context_owner_ids':['overture-building-'+parts[1]['id']],'baseline_scene_base_m':0,'base_scope':'Inherited unsurveyed scene base0 retained; DTM not used to determine floor.','roof_scene_eave_reference_m':E-datum,'roof_scene_apex_m':E+rise-datum,'fit':fit,'checks':checks,'shared_owner_interface':{'length_m':shared.length,'sampled_xyz':samples,'role':'Internal owner split, not exterior wall. Coincident sector/body closure caps retained for editable solids; do not interpret exposed target-only cut as actual facade.','same_analytic_surface_on_both_sides':True},'scope':'Full joint pyramidal hypothesis partitioned to actual mapped owners; originalfff replacement only; westowner contextual, excluded from439inventory.','uncertainty':['Edges have substantial mixed/low returns; common eave is robust model estimate, not exact measured roof boundary.','No optical roof verification;1m DSM and unknown capture vintage.','Apexlocation varies underinset/spatialfold; boundedfreefit selected after1.5m-boundcheck,final2.5m bound not active.','Slight nonrectangular outer polygon preserved with projectedbbox roofhypothesis, minor eave variationpossible.','No entrances/windows/material identity reconstructed.','Target alone shows internal cut closure; pairedcontext necessary for full roofvisualization.']};(R/'references/fff_boundary-authoring001.json').write_text(json.dumps(D,indent=2));print(checks);print(D['roof_scene_eave_reference_m'],D['roof_scene_apex_m'])
