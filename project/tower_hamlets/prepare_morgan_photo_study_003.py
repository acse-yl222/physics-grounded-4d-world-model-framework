from pathlib import Path
import json,math,numpy as np
from shapely.geometry import Polygon,Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';r=json.loads((R/'references/morgan_massing_study_002.json').read_text());rows=r['objects']; cam=json.loads((R/'references/morgan_photo_camera.json').read_text());C=np.array(cam['parameters_xyz_yaw_pitch_roll_logf'][:2]);zones=[]
for q in r['zones']:
 p=unary_union([Polygon(a['outer'],a.get('holes',[])) for a in q['support_xy']]);zones.append((q,p))
buckets={};intervals=[]
def box(owner,kind,a,t,n,s0,s1,z0,z1,d0,d1):
 if s1<=s0 or z1<=z0:return
 key=(owner,kind);ob=buckets.setdefault(key,dict(name='MorganPhoto_'+owner.split('-')[2]+'_'+kind,building_id=owner,kind=kind,vertices=[],roof_faces=[],wall_faces=[],bottom_faces=[]));v=ob['vertices'];i=len(v)
 for z in [z0,z1]:
  for s,d in [(s0,d0),(s1,d0),(s1,d1),(s0,d1)]:v.append([float(a[0]+t[0]*s+n[0]*d),float(a[1]+t[1]*s+n[1]*d),float(z)])
 ob['roof_faces'] += [[i+k for k in f] for f in [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]]
for q,p in zones:
 if not any(x in q['owner'] for x in ['39303788','31757561']):continue
 for pp in getattr(p,'geoms',[p]):
  acoords=list(orient(pp,sign=1).exterior.coords)
  for aa,bb in zip(acoords,acoords[1:]):
   a=np.array(aa);b=np.array(bb);L=np.linalg.norm(b-a);t=(b-a)/L;n=np.array([t[1],-t[0]]);mid=(a+b)/2
   if n@(C-mid)<=0 or n[0]>-.4 or L<1:continue
   adj=max([qq['scene_z_m'] for qq,ppp in zones if qq['name']!=q['name'] and ppp.buffer(.002).covers(Point(*(mid+n*.025)))]+[0])
   lo=max(40.,adj);hi=q['scene_z_m'];owner=q['owner']
   if hi-lo<.5:continue
   crown=q['name']=='north_high_body';step=3.7;nf=1 if crown else max(1,round((hi-lo)/step));h=(hi-lo)/nf;nb=max(1,round(L/(2.5 if crown else 1.75)));bay=L/nb
   intervals.append(dict(zone=q['name'],owner=owner,a=a.tolist(),b=b.tolist(),normal=n.tolist(),lo=lo,hi=hi,adjacent_height=adj,crown=crown,nominal_rows=nf,nominal_bays=nb))
   for j in range(nf):
    z=lo+j*h;band=.72 if not crown else .38
    box(owner,'bronze_panel',a,t,n,0,L,z,z+band,.005,.16)
    for k in range(nb):
     x=k*bay;w=.08 if not crown else .15
     box(owner,'dark_glass',a,t,n,x+w,x+bay-w,z+band+.05,z+h-.12,.01,.04)
     box(owner,'frame',a,t,n,x,x+w,z+band,z+h,.025,.21)
     box(owner,'frame',a,t,n,x+bay-w,x+bay,z+band,z+h,.025,.21)
     box(owner,'frame',a,t,n,x+w,x+bay-w,z+h-.12,z+h,.025,.19)
     if not crown:box(owner,'frame',a,t,n,x+w,x+bay-w,z+band+.38,z+band+.43,.025,.12)
   box(owner,'bronze_panel',a,t,n,0,L,hi-.16,hi,.01,.28)
rows.extend(buckets.values());r['objects']=rows;r['facade_intervals']=intervals;r['scope']='25 Cabot / Morgan standalone partial visible west-facing upper facade hypothesis. Existing002massing preserved exactly. Camera estimated from five manually picked landmarks in licensedOllie11491155;25Cabot maps to dark horizontally glazed office BEHIND curved western foreground (candidateparent4cf43bea;20Cabot assignmentrejected bydepth). Only exposed west-facing393/317 surfaces above40m receive facade.40m is conservativevisibility cutoff, not measuredarchitecturalbreak. Thin warmmetal bands and recessedglazing withframe/transom estimated fromphoto; top317 recessedcrown differentiated into tall dark bays. Otherowners/sides/lowerwalls remain unresolvedmassing;no inventedentry. No currentasbuiltclaim.';r['photo_camera']='references/morgan_photo_camera.json';r['limitations']+=['Camera lowfitresidual not independent validation; roofcenter picks andmixeddateheights approximate.','Visiblefacade proportions andmodulecadence estimated, not measured.','Frontcurvedbuilding belongs to closer westerncandidate, not established20Cabot; separate andunchanged.','Only selected upperwestfacades refined; bodymaterials below/sides remain diagnostic.'];(R/'references/morgan_photo_study_003.json').write_text(json.dumps(r,indent=2));print(len(rows),len(intervals))
