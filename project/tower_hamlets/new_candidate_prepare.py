from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,box
from shapely.ops import transform
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());bid='overture-building-dcdb752c-6b8b-43ae-84af-a23667921110';f=next(f for f in g['buildings'] if f['id']==bid);pr=json.loads((R/'references/new_candidate_profiles.json').read_text());e=np.array(pr['axis_u']);n=np.array(pr['axis_v']);uv=lambda xx,yy:(xx*e[0]+yy*e[1],xx*n[0]+yy*n[1]);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);p=transform(uv,Polygon(f['geometry'][0]['outer']));fits={x['name']:x for x in json.loads((R/'references/new_candidate_fit.json').read_text())['fits']};narrow=box(210,280.3,235.5,283.8);transition=box(198,280.3,210,283.8);wide=box(235.5,-1000,252,1000);domains={'base':p.difference(narrow.union(transition).union(wide)),'narrow_upper':p.intersection(narrow),'transition_upper':p.intersection(transition),'wide_upper':p.intersection(wide)};objs=[];areas=[]
for name,domain in domains.items():
 peak,slope,ridge=fits[name]['params_ridge_ODN_slope_ridge_v']
 for side,b in enumerate([box(-1000,-1000,1000,ridge),box(-1000,ridge,1000,1000)]):
  q=set_precision(domain.intersection(b),.000001)
  for k,part in enumerate(list(q.geoms) if hasattr(q,'geoms') else [q]):
   if part.area<1e-7:continue
   vs=[];ix={};roof=[];walls=[];bottom=[]
   def vi(u,v,z):
    xx,yy=xy(u,v);key=tuple(round(a,7) for a in (xx,yy,z))
    if key not in ix:ix[key]=len(vs);vs.append(list(key))
    return ix[key]
   def zz(u,v):return peak-slope*abs(v-ridge)-4.28000021
   for tri in constrained_delaunay_triangles(part).geoms:
    rr=list(tri.exterior.coords)[:-1];roof.append([vi(u,v,zz(u,v)) for u,v in rr]);bottom.append([vi(u,v,0) for u,v in reversed(rr)])
   for ring in [part.exterior,*part.interiors]:
    for (u,v),(uu,vv) in zip(ring.coords,list(ring.coords)[1:]):walls.append([vi(u,v,0),vi(uu,vv,0),vi(uu,vv,zz(uu,vv)),vi(u,v,zz(u,v))])
   objs.append({'name':f'NewCandidate_OMC_{name}_{side}_{k}','building_id':bid,'kind':'estimated','vertices':vs,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom});areas.append(part.area)
r={'replacement_ids':[bid],'objects':objs,'scope':'OMC research candidate: DSM-supported shallow main double pitch and broad raised band; narrow upper spine and transitional boundaries estimated, no facade reconstruction.','checks':[{'footprint_area_m2':p.area,'partition_area_m2':sum(areas),'difference_m2':sum(areas)-p.area}],'fit':fits,'limitations':['Not approved for regional replacement: narrowspine crossslope unstable under spatialholdout; exactstepboundaries estimated from1mDSM.','ScenezeroODN4.28000021; no capturedate assigned; flatbase0 illustrative.','No equipment identity,facade openings,textureoropticalverification.','Internal coincident sectorwalls intentional.','Mappedouterfootprint preserved; roofextrapolation toedge andlowreturns unresolved.']};(R/'references/new_candidate_study.json').write_text(json.dumps(r,indent=2))
