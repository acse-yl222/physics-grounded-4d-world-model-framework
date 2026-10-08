from pathlib import Path
import json,numpy as np,trimesh
from shapely.geometry import Polygon,Point
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());bid='overture-building-6019910a-84f8-40b5-b9b0-cf50cabf225c';f=next(q for q in g['buildings'] if q['id']==bid);roof=json.loads((R/'references/westferry_roof_fit.json').read_text());cur=json.loads((R/'references/seven_westferry_current_mesh.json').read_text())[0];shift=roof['ground_scalar_m_odn']-4.28000021;v=np.array(cur['vertices']);v[v[:,2]>0,2]+=shift;body=trimesh.Trimesh(v,cur['faces'],process=False);assert body.is_watertight
ring=np.array(f['geometry'][0]['outer']);partitions=[(Polygon(q['outer'],q.get('holes',[])),q['height_scene_m']+shift) for q in roof['partitions']];cut=[];meshes={'glass':[],'frame':[],'sill':[]};records=[]
def box(a,t,n,s0,s1,d0,d1,z0,z1):
 T=np.eye(4);T[:2,0]=t;T[:2,1]=n;T[:3,3]=[*list(a+t*(s0+s1)/2+n*(d0+d1)/2),(z0+z1)/2];return trimesh.creation.box([s1-s0,d1-d0,z1-z0],transform=T)
for ei in [3,4,5]:
 a=ring[ei];b=ring[ei+1];L=np.linalg.norm(b-a);t=(b-a)/L;n=np.array([-t[1],t[0]]);count=max(1,round((L-1.4)/3));step=(L-1.4)/count
 for j in range(count):
  mid=.7+(j+.5)*step;ww=min(1.68,step-.65);lo=mid-ww/2;hi=mid+ww/2;pt=Point(*(a+t*mid+n*.8));zt=max([h for p,h in partitions if p.buffer(.002).covers(pt)]+[0]);intervals=[]
  for row in range(8):
   z0=16.3+row*3.8;z1=z0+2.72
   if z1>zt-.7:continue
   cut.append(box(a,t,n,lo,hi,-.025,.62,z0,z1));meshes['glass'].append(box(a,t,n,lo+.06,hi-.06,.53,.57,z0+.06,z1-.06))
   for x0,x1,y0,y1 in [(lo,lo+.065,z0,z1),(hi-.065,hi,z0,z1),(lo,hi,z0,z0+.065),(lo,hi,z1-.065,z1),(mid-.025,mid+.025,z0+.065,z1-.065),(lo+.065,hi-.065,z0+.76,z0+.81)]:meshes['frame'].append(box(a,t,n,x0,x1,.38,.49,y0,y1))
   meshes['sill'].append(box(a,t,n,lo-.08,hi+.08,.03,.34,z0+.02,z0+.11));intervals.append([z0,z1])
  records.append({'edge':ei,'bay':j,'center_s':mid,'roof_height':zt,'window_intervals':intervals})
 # Broader recessed lowstorey bays, no doors/signage and no presumed publicground elevation.
 gc=max(1,round(L/6))
 for j in range(gc):
  stepg=(L-1.4)/gc;mid=.7+(j+.5)*stepg;lo=mid-(stepg-1.2)/2;hi=mid+(stepg-1.2)/2
  cut.append(box(a,t,n,lo,hi,-.025,1.75,7,15.45));meshes['glass'].append(box(a,t,n,lo+.08,hi-.08,1.49,1.53,7.1,15.3))
  for x0,x1,y0,y1 in [(lo,lo+.09,7.05,15.35),(hi-.09,hi,7.05,15.35),(lo,hi,10.9,11.0),(lo,hi,15.25,15.35)]:meshes['frame'].append(box(a,t,n,x0,x1,1.32,1.44,y0,y1))
 for zz in [15.6,15.82,27.55,27.77,34.6,34.8]:cut.append(box(a,t,n,.25,L-.25,-.025,.075,zz,zz+.065))
# Visible stepped upperfacade: tallattic apertures, onlyaboveadjacentroof andawayfrommappedouteredge.
attic_records=[]
for poly,zt in partitions:
 if zt<43:continue
 rr=np.array(poly.exterior.coords)
 for aa,bb in zip(rr[:-1],rr[1:]):
  L=np.linalg.norm(bb-aa)
  if L<6:continue
  t=(bb-aa)/L;n=np.array([-t[1],t[0]])*(1 if poly.exterior.is_ccw else -1);mid=(aa+bb)/2;out=-n
  if mid[1]>145 or out[0]>-.35 or out[1]>.3:continue
  zlow=max([h for pp,h in partitions if pp.buffer(.002).covers(Point(*(mid+out*.08)))]+[0])
  if zt-zlow<2 or zt-zlow>8:continue
  count=max(1,round((L-1.4)/3));step=(L-1.4)/count
  for j in range(count):
   mm=.7+(j+.5)*step;ww=min(1.55,step-.7);lo=mm-ww/2;hi=mm+ww/2;z0=zlow+.65;z1=zt-.6
   cut.append(box(aa,t,n,lo,hi,-.025,.5,z0,z1));meshes['glass'].append(box(aa,t,n,lo+.06,hi-.06,.42,.455,z0+.06,z1-.06))
   for x0,x1,y0,y1 in [(lo,lo+.065,z0,z1),(hi-.065,hi,z0,z1),(lo,hi,z0,z0+.065),(lo,hi,z1-.065,z1)]:meshes['frame'].append(box(aa,t,n,x0,x1,.29,.39,y0,y1))
   if zt>49:
    for zz in [z1-.9,z1-.65,z1-.4]:meshes['frame'].append(box(aa,t,n,lo+.065,hi-.065,.1,.25,zz,zz+.065))
   attic_records.append({'a':aa.tolist(),'b':bb.tolist(),'bay':j,'z':[z0,z1]})
newbody=trimesh.boolean.difference([body,*cut],engine='manifold');assert newbody.is_watertight and newbody.is_winding_consistent
objs=[]
def obj(name,kind,m):objs.append({'name':name,'kind':kind,'building_id':bid,'vertices':m.vertices.tolist(),'roof_faces':m.faces.tolist(),'wall_faces':[],'bottom_faces':[]})
obj('SevenWestferry_recessed_stone_body','stone',newbody)
for kind,ms in meshes.items():obj('SevenWestferry_'+kind,kind,trimesh.util.concatenate(ms))
levels=np.array(roof['levels_odn_m'])-4.28000021;tc=newbody.triangles_center;rm=(newbody.face_normals[:,2]>.999)&(np.abs(tc[:,2,None]-levels).min(axis=1)<1e-4);area=float(newbody.area_faces[rm].sum());p=Polygon(f['geometry'][0]['outer']);assert abs(area-p.area)<.005
r={'objects':objs,'building_id':bid,'scope':'7WestferryCircus boundedSW facadephoto study. Preserve currentregional authored7mergedroofregions from9treeleaves, normalize ODN datum to4.28000021m;roofboundaries remainestimated. Onlysourceedges3/4/5 get actualrecessedpunchedwindows,frames/mullions/lowtransoms andwidegroundbays;counts anddimensionsestimated fromcontinuousOllieforegroundfrontage. Northernwing/otherfacesplain;sharededge7 with26b untouched. Groundrecesses are notverifiedentrances;7m lowerpubliclevelillustrative. No sourcephototextures.','roof_levels_scene_m':levels.tolist(),'roof_shift_m':shift,'source_current_scene':'runs/canary_wharf_appearance_five_canada_support_001/region.blend','source_mesh_snapshot':'references/seven_westferry_current_mesh.json','roof_partition_count':len(roof['partitions']),'roof_fit_tree_leaf_count':roof['fit']['leaf_count'],'photo_source_id':'pexels_ollie_11491155','window_records':records,'upper_terrace_apertures':attic_records,'source_edges':[3,4,5],'untouched_shared_edge':[ring[7].tolist(),ring[8].tolist()],'checks':{'body_watertight':bool(newbody.is_watertight),'consistent_winding':bool(newbody.is_winding_consistent),'roof_area_m2':area,'source_footprint_area_m2':p.area,'roof_area_error_m2':area-p.area,'body_triangles':len(newbody.faces)},'limitations':['Photo camera approximate: adjacent26b calibrationperturbations yield119px corner uncertainty; do notclaimprecisebaycorrespondence.','PartialDSMcoverage andoriginalplateauselectionlimitroofinference; noheightextrapolationclaimedassurveyed.','Whole footprint retained includingnorthwingoutsideimage; unverifiedfacades stayplain.','Oldscene roofheights increased0.86186m solely datum normalization, not newphysicalheight evidence.','Source7mergedregions retain originalestimated geometricroofbreaks.']};(R/'references/seven_westferry_photo_study.json').write_text(json.dumps(r,indent=2));print(r['checks'])
