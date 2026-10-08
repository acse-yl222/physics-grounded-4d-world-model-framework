from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,LineString
from shapely.ops import split
from shapely import constrained_delaunay_triangles,set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';d=json.loads((R/'references/aace_model_sensitivity.json').read_text());r=d['regions'][0];p=Polygon(r['support_uv']);lo,hi=np.array(r['bounds_uv']);center=np.array(r['center_uv']);follow=json.loads((R/'references/aace_model_family_followup.json').read_text());selected=follow['models'][0];E,H,du,run,run_north=selected['parameters'];cu=center[0]+du;datum=4.28000021;th=np.deg2rad(16);co,si=np.cos(th),np.sin(th);xy=lambda u,v:(u*co-v*si,u*si+v*co)
# Four normalized plane distances. Their lower envelope gives a longitudinal hip ridge.
planes=np.array([[-lo[0]/(cu-lo[0]),1/(cu-lo[0]),0],[hi[0]/(hi[0]-cu),-1/(hi[0]-cu),0],[-lo[1]/run,0,1/run],[hi[1]/run_north,0,-1/run_north]])
parts=[p]
for i in range(4):
 for j in range(i):
  a,b,c=planes[i]-planes[j];norm=np.hypot(b,c)
  if norm<1e-10:continue
  point=-a*np.array([b,c])/(norm*norm);direction=np.array([-c,b])/norm;line=LineString([point-2000*direction,point+2000*direction]);parts=[q for pp in parts for q in split(pp,line).geoms if q.area>1e-8]
# dissolve pieces using the same active plane to eliminate artificial cuts
from shapely.ops import unary_union
buckets={}
for pp in parts:
 u,v=pp.representative_point().coords[0];active=int(np.argmin(planes@np.array([1,u,v])));buckets.setdefault(active,[]).append(pp)
objs=[];bounds=[];bid='overture-building-aace8b76-3b8c-44f1-8ed8-ed8e2c326cfe'
for active,polys in buckets.items():
 pp=set_precision(unary_union(polys),.000001);vs=[];faces=[];idx={}
 def zz(u,v):return E+H*(planes[active]@np.array([1,u,v]))-datum
 def vi(u,v,z):
  x,y=xy(u,v);k=tuple(round(t,7) for t in (x,y,z))
  if k not in idx:idx[k]=len(vs);vs.append(list(k))
  return idx[k]
 for q in getattr(pp,'geoms',[pp]):
  for t in constrained_delaunay_triangles(q).geoms:
   rr=list(t.exterior.coords)[:-1];faces.append([vi(u,v,zz(u,v)) for u,v in rr]);faces.append([vi(u,v,zz(u,v)-.12) for u,v in reversed(rr)])
  for (u,v),(uu,vv) in zip(q.exterior.coords,list(q.exterior.coords)[1:]):faces.append([vi(u,v,zz(u,v)-.12),vi(uu,vv,zz(uu,vv)-.12),vi(uu,vv,zz(uu,vv)),vi(u,v,zz(u,v))])
 objs.append({'name':f'Aace_SouthRoof_plane_{active}','building_id':bid,'kind':'estimated','vertices':vs,'roof_faces':faces,'wall_faces':[],'bottom_faces':[]})
def height(u,v):return E+H*np.min(planes@np.array([1,u,v]))-datum
edge=[]
for i,((u,v),(uu,vv)) in enumerate(zip(p.exterior.coords,list(p.exterior.coords)[1:])):
 samples=[height(u+t*(uu-u),v+t*(vv-v)) for t in np.linspace(0,1,21)];edge.append({'edge_index':i,'uv_start':[u,v],'uv_end':[uu,vv],'top_scene_min_m':min(samples),'top_scene_max_m':max(samples)})
ridge_uv=[[cu,lo[1]+run],[cu,hi[1]-run_north]];ridge_xy=[list(xy(*a)) for a in ridge_uv];verts=np.array([v for o in objs for v in o['vertices']]);assert verts[:,2].min()>0
out={'building_id':bid,'objects':objs,'scope':'South wing roof-only longitudinal hip hypothesis; notfullownerreplacement. No walls/basebuildings/NWroof added.','replacement_ids':[],'roof_only':True,'source_sensitivity':'aace_model_sensitivity.json','hip_parameters':{'eave_odn_m':E,'rise_m':H,'ridge_odn_m':E+H,'south_hip_run_m':run,'north_hip_run_m':run_north,'ridge_uv':ridge_uv,'ridge_xy':ridge_xy,'ridge_length_m':hi[1]-lo[1]-run-run_north},'edge_heights':edge,'all_vertex_min_scene_z':float(verts[:,2].min()),'all_vertex_max_scene_z':float(verts[:,2].max()),'base_scene_z_m':0,'datum_offset_odn_m':datum,'support_uv':list(p.exterior.coords),'thickness_m':.12,'holdout':selected['holdout'],'model_family_comparison':follow,'gable_comparison':r['models']['gable'],'limitations':['Roofskin0.12m isartistestimate. No hardzclamp; all fittedvertices naturallyabovebase.','Allheldoutreturnsretained; localized18ODNhighreturns not equipment.','Asymmetrichip improves symmetric/ gableRMSE; open-northmodel nearlyequalperformance so exactnorthhipend unresolved. Notcalibratedroof.','Sourceoutline roofdomain revisedtomappedwing; exacteavelines andhipends estimated. Actualrastercapturevintageunknown.']};(R/'references/aace_south_roof_study.json').write_text(json.dumps(out,indent=2));print(out['hip_parameters']);print(edge);print(verts[:,2].min())
