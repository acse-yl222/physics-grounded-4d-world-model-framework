"""Former RCO: exact OSM footprint, four-level east front, estimated divided roof.
Authoring UTM only. Simplified sgraffito panels use exportable solid PBR colors.
"""
import math

def build(ctx,feature):
 stucco=ctx.material('Organists pale warm stucco',(.70,.68,.57),.80)
 trim=ctx.material('Organists cream panel borders',(.85,.80,.66),.72)
 dark=ctx.material('Organists dark painted timber',(.065,.045,.042),.62)
 red=ctx.material('Organists muted red sgraffito fields',(.29,.12,.10),.85)
 grey=ctx.material('Organists charcoal sgraffito fields',(.24,.23,.20),.84)
 brick=ctx.material('Organists estimated rear stock brick',(.34,.25,.16),.87)
 slate=ctx.material('Organists grey roof covering',(.12,.15,.16),.79)
 glass=ctx.material('Organists recessed glazing',(.065,.12,.15),.22,0,.15)
 iron=ctx.material('Organists painted metal railing',(.065,.057,.045),.5,.6)
 m=ctx.mesh('Exact footprint exterior real apertures');r=ctx.mesh('Divided pitched roof');d=ctx.mesh('East front cornices timber bays and simple panels')
 base=float(feature.get('base_m',0));poly=feature['geometry'][0]['outer'];a,b=poly[11],poly[0];L=math.dist(a,b);tx,ty=(b[0]-a[0])/L,(b[1]-a[1])/L;nx,ny=ty,-tx;ang=math.atan2(ty,tx);entrances=[];nopen=0
 def xyz(u,v,z):return (a[0]+tx*u-nx*v,a[1]+ty*u-ny*v,base+z)
 def uv(p):return ((p[0]-a[0])*tx+(p[1]-a[1])*ty,-(p[0]-a[0])*nx-(p[1]-a[1])*ny)
 def face(mesh,ps,mat):
  for k in range(1,len(ps)-1):
   aa,bb,cc=ps[0],ps[k],ps[k+1];v=[bb[j]-aa[j] for j in range(3)];w=[cc[j]-aa[j] for j in range(3)];cross=[v[(j+1)%3]*w[(j+2)%3]-v[(j+2)%3]*w[(j+1)%3] for j in range(3)]
   if sum(x*x for x in cross)>1e-12:mesh.face([aa,bb,cc],mat)
 def roofheight(v):
  if v<=10:return 19.0+.46*v
  if v<=17:return 23.6-(v-10)*3.6/7
  return 20.0-(v-17)*.17
 def clip(ps,cut,positive):
  out=[]
  for p,q in zip(ps,ps[1:]+ps[:1]):
   dp=(p[1]-cut)*(1 if positive else -1);dq=(q[1]-cut)*(1 if positive else -1)
   if dp>=-1e-9:out.append(p)
   if dp*dq<0 and abs(dp)>1e-9 and abs(dq)>1e-9:
    t=dp/(dp-dq);out.append(tuple(p[k]+t*(q[k]-p[k]) for k in range(2)))
  return out
 for tri in feature['geometry'][0]['triangles']:
  pp=[uv(p) for p in tri]
  for lo,hi in [(-100,10),(10,17),(17,100)]:
   q=clip(clip(pp,lo,True),hi,False);face(r,[xyz(u,v,roofheight(v)) for u,v in q],slate)
 for edge,(aa,bb) in enumerate(zip(poly,poly[1:]+poly[:1])):
  ll=math.dist(aa,bb);tt=((bb[0]-aa[0])/ll,(bb[1]-aa[1])/ll);nn=(tt[1],-tt[0]);theta=math.atan2(tt[1],tt[0]);front=edge==11;party=edge in (8,9,10)
  def p(u,z,dep=0):return (aa[0]+tt[0]*u-nn[0]*dep,aa[1]+tt[1]*u-nn[1]*dep,base+z)
  za,zb=roofheight(uv(aa)[1]),roofheight(uv(bb)[1]);walltop=min(za,zb)-.15
  cs=[ll*.20,ll*.5,ll*.80] if front else [(k+.5)*ll/max(1,int(ll/3.5)) for k in range(max(1,int(ll/3.5)))]
  holes=[]
  if not party and (front or edge in (2,4,6,7)):
   for c in cs:
    for lo,hi in ([(1.55,4.0),(6.35,8.5),(10.8,14.15),(16.3,18.3)] if front else [(1.5,3.5),(5.8,8.0),(10.4,12.7),(14.6,16.5)]):
     if hi>walltop-.35:continue
     door=front and abs(c-ll*.5)<.1 and lo<2
     w=2.25 if door else 3.1 if front else 1.45
     if ll<w+1:continue
     holes.append((c-w/2,c+w/2,.15 if door else lo,4.5 if door else hi,door))
  cuts=sorted(set([0,walltop]+[z for h in holes for z in h[2:4]]))
  for lo,hi in zip(cuts,cuts[1:]):
   intervals=sorted((h[0],h[1]) for h in holes if h[2]<=lo and h[3]>=hi);cursor=0
   for le,ri in intervals+[(ll,ll)]:
    if le>cursor:face(m,[p(cursor,lo),p(le,lo),p(le,hi),p(cursor,hi)],stucco if front or edge<5 else brick)
    cursor=max(cursor,ri)
  # Vertical roof closure follows each piecewise-linear roof interval exactly.
  values=[0,ll];va,vb=uv(aa)[1],uv(bb)[1]
  for v in (10,17):
   if (va-v)*(vb-v)<0:values.append(ll*(v-va)/(vb-va))
  values=sorted(values)
  for x,y in zip(values,values[1:]):
   hx=roofheight(va+(vb-va)*x/ll);hy=roofheight(va+(vb-va)*y/ll)
   face(r,[p(x,walltop),p(y,walltop),p(y,hy),p(x,hx)],stucco if front else brick)
  for le,ri,lo,hi,door in holes:
   nopen+=1;c=(le+ri)/2;dep=.70 if door else .33
   # Glass backing and wall reveals leave a true aperture in the opaque shell.
   face(m,[p(le,lo,dep+.13),p(ri,lo,dep+.13),p(ri,hi,dep+.13),p(le,hi,dep+.13)],glass)
   for u,v in [((le,lo),(ri,lo)),((ri,lo),(ri,hi)),((ri,hi),(le,hi)),((le,hi),(le,lo))]:face(m,[p(*u),p(*v),p(*v,dep),p(*u,dep)],trim)
   for x in (le,ri):d.box(*p(x,(lo+hi)/2,.05),.12,.23,hi-lo,dark,theta)
   for z in ((hi,) if door else (lo,hi)):d.box(*p(c,z,.03),ri-le+.12,.25,.12,dark,theta)
   if door:
    w=(ri-le-.08)/2
    for sign in (-1,1):
     cc=c+sign*(w/2+.02);d.box(*p(cc,(lo+3.7)/2,dep),w,.10,3.7-lo,dark,theta)
     for z in (.65,1.5,2.55,3.25):d.box(*p(cc,z,dep-.065),w-.16,.04,.45,dark,theta)
     d.beam(p(cc-sign*.34,1.05,dep-.12),p(cc-sign*.34,1.4,dep-.12),.024,iron,8)
     entrances.append({'threshold_xyz':list(p(cc,lo)),'outward_normal':[nn[0],nn[1],0],'door_leaf_xyz':list(p(cc,(lo+3.7)/2,dep)),'door_leaf_depth_m':dep-.05,'clear_width_m':w-.15,'stair_treads':1,'riser_m':.15,'tread_m':.45,'landing_depth_m':.5,'landing_z_m':.15,'ramp':'not evidenced','supporting_surface':'finite authored entrance sill; surrounding ground coordinator-owned','estimated':True})
    d.box(*p(c,3.8,.1),ri-le,.22,.15,dark,theta)
    d.box(*p(c,.075,-.2),ri-le+.25,.65,.15,trim,theta)
   else:
    for x in (le+(ri-le)/3,le+2*(ri-le)/3):d.box(*p(x,(lo+hi)/2,.17),.09,.13,hi-lo,dark,theta)
    d.box(*p(c,lo+.67*(hi-lo),.16),ri-le,.14,.10,dark,theta)
    if front and 10<lo<11:
     # Source-visible curved timber motif sits inside tall glazed opening.
     radius=.64;z=lo+1.85
     pts=[p(c+radius*math.cos(k*math.pi/20),z+radius*math.sin(k*math.pi/20),.12) for k in range(21)]
     for x,y in zip(pts,pts[1:]):d.beam(x,y,.07,dark,8)
    if front and lo>9:
     d.box(*p(c,lo-.20,-.15),ri-le+.40,.65,.26,dark,theta)
     for x in (le+.25,c,ri-.25):d.beam(p(x,lo-.25,-.25),p(x,lo-.75,.02),.075,dark,8)
  if front:
   # Photographed ornate facade expressed as panels rather than invented sculpture.
   for z,h in [(5.45,.5),(9.6,.45),(15.2,.6)]:
    d.box(*p(ll/2,z,-.08),ll,.22,h,dark,theta)
   for c in [ll*.055,ll*.355,ll*.645,ll*.945]:
    for lo,hi,mat in [(1.0,4.3,red),(6.1,8.8,red),(10.5,14.4,grey),(16,18.5,grey)]:
     width=.88;d.box(*p(c,(lo+hi)/2,-.055),width,.12,hi-lo,mat,theta)
     for x in (c-width/2,c+width/2):d.box(*p(x,(lo+hi)/2,-.13),.055,.06,hi-lo,trim,theta)
     for z in (lo,hi):d.box(*p(c,z,-.13),width,.06,.055,trim,theta)
   for c in cs:
    d.box(*p(c,4.95,-.075),4.3,.15,.66,red,theta)
    for z in (4.61,5.29):d.box(*p(c,z,-.17),4.4,.06,.065,trim,theta)
   # Central pilaster strips and shallow balcony define the main bay without
   # changing the authoritative ground footprint or covering the doorway throat.
   for c in (ll*.5-2.2,ll*.5+2.2):d.box(*p(c,9.6,-.20),.20,.40,18.4,trim,theta)
   d.box(*p(ll*.5,10.65,-.55),3.6,1.2,.18,dark,theta)
   for k in range(13):d.beam(p(ll*.5-1.7+k*3.4/12,10.78,-1.05),p(ll*.5-1.7+k*3.4/12,11.55,-1.05),.022,iron,8)
   d.beam(p(ll*.5-1.8,11.6,-1.05),p(ll*.5+1.8,11.6,-1.05),.035,iron,8)
   for z,w,depth,h in [(18.9,ll+.5,.85,.30),(19.15,ll+.65,1.05,.16)]:d.box(*p(ll/2,z,-.18),w,depth,h,dark,theta)
   for k in range(int(ll/.7)):
    c=(k+.5)*ll/int(ll/.7);d.box(*p(c,18.63,-.22),.13,.65,.40,dark,theta)
   for k in range(int(ll/.55)+1):d.beam(p(k*ll/int(ll/.55),19.28,-.18),p(k*ll/int(ll/.55),19.92,-.18),.025,iron,8)
   for z in (19.35,19.9):d.beam(p(0,z,-.18),p(ll,z,-.18),.035,iron,8)
 objs=[m.done(),r.done(),d.done()]
 return {'created':[x.name for x in objs if x],'parameters':{'main_facade':'east, original edge 11','levels':4,'front_cornice_m':19.23,'roof_ridge_m':23.6,'roof_eaves_front_m':19.0,'roof_height_breaks_depth_m':[0,10,17],'actual_apertures':nopen,'footprint':'complete original concave 12-vertex OSM ring; no neighbouring footprint annexed','detail_level':'reduced; source-visible main window divisions, cornices and colored panel hierarchy; figurative sgraffito simplified','height_basis':'EA2022 DSM-DTM p50 19.765m, p95 23.581m; roof form and floor dimensions estimated'},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','organists-hisgett-2010','organists-enchufla-2017','organists-he-east-facade','ea-lidar-composite-2022-tq27ne'],'uncertainty':['Roof break positions and rear windows are estimates within the observed EA height envelope, not surveyed roof plans.','Source facade has canted central projection; reduced model keeps mapped footprint and expresses central bay with shallow pilasters and balcony.','Sgraffito figurative scenes and fine carvings are simplified colored bordered panels, not reproductions.','No unobserved roof plant or chimneys; boundary neighbour-height compatibility and terrain remain coordinator checks.','Photos date 2010 and 2017, LiDAR is 2022 composite, footprint is 2026; not a single-date survey.']}
