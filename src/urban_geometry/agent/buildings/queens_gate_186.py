"""186 Queen's Gate only; mapped footprint, licensed photo and EA roof evidence.
Unknown rear fenestration and fine ornament deliberately simplified.
"""
import math

def build(ctx,feature):
 stone=ctx.material('186 QG cream stucco',(.76,.73,.64),.83)
 trimat=ctx.material('186 QG pale carved trim',(.83,.80,.70),.78)
 roofmat=ctx.material('186 QG grey slate',(.16,.19,.20),.81)
 glass=ctx.material('186 QG recessed glass',(.065,.105,.12),.24,0,.18)
 wood=ctx.material('186 QG dark timber',(.12,.061,.028),.71)
 iron=ctx.material('186 QG dark railings',(.025,.029,.027),.48,.65)
 shell=ctx.mesh('mapped stucco and actual window apertures');roof=ctx.mesh('segmented main and rear roof');detail=ctx.mesh('major frames cornices balcony and portico')
 a=(508.12774789112154,-52.26565406285226);tx,ty=1.83834922756066,-9.82799136638642;ll=math.hypot(tx,ty);tx/=ll;ty/=ll;nx,ny=-ty,tx;angle=math.atan2(ty,tx);base=float(feature.get('base_m',0))
 def P(u,v,z):return(a[0]+u*tx+v*nx,a[1]+u*ty+v*ny,base+z)
 def UV(p):return((p[0]-a[0])*tx+(p[1]-a[1])*ty,(p[0]-a[0])*nx+(p[1]-a[1])*ny)
 def B(u,v,z,w,d,h,mat=trimat):
  x,y,zz=P(u,v,z);detail.box(x,y,zz,w,d,h,mat,angle)
 profile=[(-1,21.4),(0,21.4),(3.5,26.5),(9.,26.5),(12.,20.7),(24.,20.7),(30.,17.0),(40.,17.0)]
 def H(v):
  for (v0,z0),(v1,z1) in zip(profile,profile[1:]):
   if v0<=v<=v1:return z0+(z1-z0)*(v-v0)/(v1-v0)
  return 21.4
 def face(mesh,pts,mat):
  q=[]
  for p in pts:
   if not q or math.dist(q[-1],p)>1e-8:q.append(p)
  if len(q)>2 and math.dist(q[0],q[-1])<1e-8:q.pop()
  if len(q)>2:mesh.face(q,mat)
 def wall(aa,bb,ops,top=H,bottom=0):
  length=math.dist(aa,bb);du,dv=(bb[0]-aa[0])/length,(bb[1]-aa[1])/length
  def Q(s,z,dep=0):return P(aa[0]+du*s-dv*dep,aa[1]+dv*s+du*dep,z)
  def cap(s):return max(bottom,top(aa[1]+s*dv))
  xs={0.,length}
  if abs(dv)>1e-8:
   for v,z in profile:
    s=(v-aa[1])/dv
    if 0<s<length:xs.add(s)
   for (v0,z0),(v1,z1) in zip(profile,profile[1:]):
    if min(z0,z1)<bottom<max(z0,z1):
     v=v0+(bottom-z0)*(v1-v0)/(z1-z0);s=(v-aa[1])/dv
     if 0<s<length:xs.add(s)
  for c,r,bot,spr,arch,mat in ops:xs.update(c-r+2*r*j/(24 if arch else 1) for j in range((24 if arch else 1)+1))
  for lo,hi in zip(sorted(xs),sorted(xs)[1:]):
   if hi-lo<1e-8 or max(cap(lo),cap(hi))<=bottom+1e-8:continue
   op=next((o for o in ops if o[0]-o[1]<(lo+hi)/2<o[0]+o[1]),None)
   if op:
    c,r,bot,spr,arch,mat=op;zt=lambda s:spr+(math.sqrt(max(0,r*r-(s-c)**2)) if arch else 0);z0,z1=zt(lo),zt(hi);dep=.70 if mat==wood else .28
    if bot>bottom:face(shell,[Q(lo,bottom),Q(hi,bottom),Q(hi,bot),Q(lo,bot)],stone)
    face(shell,[Q(lo,z0),Q(hi,z1),Q(hi,cap(hi)),Q(lo,cap(lo))],stone)
    face(shell,[Q(lo,bot,dep),Q(hi,bot,dep),Q(hi,z1,dep),Q(lo,z0,dep)],mat)
    face(shell,[Q(lo,z0),Q(hi,z1),Q(hi,z1,dep),Q(lo,z0,dep)],trimat)
    if arch:detail.beam(Q(lo,z0,-.07),Q(hi,z1,-.07),.08,trimat,8)
   else:face(shell,[Q(lo,bottom),Q(hi,bottom),Q(hi,cap(hi)),Q(lo,cap(lo))],stone)
  for c,r,bot,spr,arch,mat in ops:
   dep=.70 if mat==wood else .28
   for s in(c-r,c+r):
    face(shell,[Q(s,bot),Q(s,spr),Q(s,spr,dep),Q(s,bot,dep)],trimat);detail.beam(Q(s,bot,-.06),Q(s,spr,-.06),.075,trimat,8)
   face(shell,[Q(c-r,bot),Q(c+r,bot),Q(c+r,bot,dep),Q(c-r,bot,dep)],trimat)
   if mat!=wood:detail.beam(Q(c-r,bot,-.07),Q(c+r,bot,-.07),.09,trimat,8)
   if not arch:detail.beam(Q(c-r,spr,-.07),Q(c+r,spr,-.07),.09,trimat,8)
   if mat==glass:
    detail.beam(Q(c,bot,.21),Q(c,spr,.21),.033,trimat,6);detail.beam(Q(c-r,(bot+spr)/2,.21),Q(c+r,(bot+spr)/2,.21),.033,trimat,6)
 # Per-floor wall bands allow multiple vertically aligned openings.
 bands=[(0,5.1,1.25,4.45,False),(5.1,10.,5.75,9.35,False),(10.,14.2,10.65,13.65,False),(14.2,18.,14.75,17.35,False),(18.,21.4,18.55,19.9,True)]
 ring=feature['geometry'][0]['outer'];uv=[UV(p) for p in ring]
 for i,(aa,bb) in enumerate(zip(uv,uv[1:]+uv[:1])):
  length=math.dist(aa,bb)
  if i not in(0,1,3,5):
   wall(aa,bb,[],top=H);continue
  for low,high,bot,spr,arch in bands:
   if i==0:centers=[1.7,5.,8.3]
   elif i==1:centers=[2.,11.5,15.3] if high<=18 else [2.,11.5,15.3]
   elif i in(3,5):centers=[length/2] if length>3.5 and high<=14.2 else []
   else:centers=[]
   ops=[]
   for c in centers:
    localv=aa[1]+(bb[1]-aa[1])*c/length
    if H(localv)<high-.01:continue
    isdoor=i==0 and low==0 and c==1.7
    ops.append((c,.8 if isdoor else .68,.9 if isdoor else bot,4.3 if isdoor else spr,False if isdoor else arch,wood if isdoor else glass))
   # Trim bands where the declining rear roof is lower than a storey.
   if min(H(aa[1]),H(bb[1]))<high:
    # No upper storey windows in uncertain rear, complete separately below.
    if i not in(0,1):continue
   wall(aa,bb,ops,top=lambda v,h=high:min(h,H(v)),bottom=low)
  # Complete above normal main cornice, or rear with simple estimated blank wall.
  if i in(0,1):
   if i==1:wall(aa,bb,[],bottom=21.4)
  else:
   wall(aa,bb,[],top=H,bottom=14.2 if i in(3,5) else 0)
 # Exact source bottom and roof: clip every mapped triangle at profile breaks.
 shell.surface(feature['geometry'],base,stone)
 def clip(points,cut,keep_above):
  out=[]
  for a,b in zip(points,points[1:]+points[:1]):
   ia=a[1]>=cut-1e-9 if keep_above else a[1]<=cut+1e-9;ib=b[1]>=cut-1e-9 if keep_above else b[1]<=cut+1e-9
   if ia:out.append(a)
   if ia!=ib:
    t=(cut-a[1])/(b[1]-a[1]);out.append((a[0]+t*(b[0]-a[0]),cut))
  return out
 for part in feature['geometry']:
  for tri in part['triangles']:
   for (v0,z0),(v1,z1) in zip(profile,profile[1:]):
    points=clip(clip([UV(p) for p in tri],v0,True),v1,False)
    if len(points)>=3:face(roof,[P(u,v,H(v)) for u,v in points],roofmat)
 # Main western cornices and shallow pilasters; split low bands at entrance.
 for z,h in[(.7,.22),(5.1,.3),(10.,.24),(14.2,.28),(18.,.55),(21.35,.35)]:
  if z<4.5:
   B(.35,-.13,z,.7,.26,h);B(6.45,-.13,z,7.1,.26,h)
  else:B(5.,-.15,z,10.,.4,h)
  B(10.05,5.7 if z>21 else 8.4,z,.32,11.4 if z>21 else 16.8,h)
 for u in(.2,3.3,6.7,9.8):B(u,-.08,12.,.14,.18,12.)
 for u in[.3+j*.43 for j in range(23)]:B(u,-.25,17.8,.19,.36,.42)
 # Three-window attic front, separate from roof plane rising behind.
 wall((.7,-.05),(9.3,-.05),[(1.25,.57,22.0,24.,False,glass),(4.3,.57,22.,24.,False,glass),(7.35,.57,22.,24.,False,glass)],top=lambda v:24.4,bottom=21.4)
 B(5.,-.07,24.4,8.8,.4,.26)
 for j in range(32):
  start=math.asin(.9/2.3);t0=start+(math.pi-2*start)*j/32;t1=start+(math.pi-2*start)*(j+1)/32
  face(detail,[P(5+2.3*math.cos(t0),-.09,24.4),P(5+2.3*math.cos(t1),-.09,24.4),P(5+2.3*math.cos(t1),-.09,23.5+2.3*math.sin(t1)),P(5+2.3*math.cos(t0),-.09,23.5+2.3*math.sin(t0))],stone)
  detail.beam(P(5+2.3*math.cos(t0),-.10,23.5+2.3*math.sin(t0)),P(5+2.3*math.cos(t1),-.10,23.5+2.3*math.sin(t1)),.12,trimat,8)
 # Side high chimney parapet follows visible front section; no hidden equipment.
 B(9.85,5.,26.45,.42,8.,1.0,stone);B(9.85,5.,27.,.6,8.3,.25)
 for v in(2.,3.5,5.,6.5,8.):
  x,y,z=P(9.85,v,27.1);detail.lathe(x,y,z,[(.13,0),(.13,.48)],roofmat,10)
 # Major first-floor triangular window pediments; sculpture simplified.
 for u in(5.,8.3):
  face(detail,[P(u-.9,-.15,9.55),P(u+.9,-.15,9.55),P(u,-.15,10.05)],trimat)
  B(u,-.15,9.52,1.9,.35,.12)
 for v in(2.,11.5,15.3):
  face(detail,[P(10.1,v-.9,9.55),P(10.1,v+.9,9.55),P(10.1,v,10.05)],trimat)
 # Portico at northern west bay; six finite estimated steps, first tread .15m.
 for u in(.45,2.95):
  B(u,-.85,.425,.60,.65,.95)
  x,y,z=P(u,-.85,.9);detail.lathe(x,y,z,[(.24,0),(.24,.2),(.17,.35),(.15,3.4),(.27,3.5),(.27,3.7)],trimat,16)
 B(1.7,-.65,4.72,3.35,1.7,.30)
 for j in range(6):
  v=-2.7+j*.32;top=.15*(j+1);B(1.7,v,(-.05+top)/2,1.9,.32,top+.05,trimat)
 B(1.7,-.47,.425,1.9,.94,.95,trimat)
 for u in(3.5,6.5,9.6):B(u,-.35,5.,.24,.7,.5)
 # Balcony rails, simplified geometric stone balusters above portico.
 for u in[.15+j*.24 for j in range(14)]:B(u,-1.35,5.25,.09,.12,.6)
 B(1.7,-1.35,5.6,3.4,.2,.16)
 threshold=P(1.7,0,.9)
 objects=[m.done() for m in(shell,roof,detail)]
 return {'created':[o.name for o in objects if o],'parameters':{'main_roof_m':26.5,'rear_roof_m':20.7,'chimney_pots_top_m':27.58,'height_basis':'EA native1m plus licensed2023 street image; detailed heights estimated'},'interfaces':{'entrances':[{'id':'west_186_door','threshold_xyz':list(threshold),'outward_normal':[-nx,-ny,0],'clear_width_m':1.6,'door_leaf_depth_m':.7,'stair_treads':6,'tread_m':.32,'riser_m':.15,'landing_depth_m':.76,'stairs_authoring_extent':[list(P(.75,-2.86,-.05)),list(P(2.65,-.16,.9))],'support_z':base-.05,'basis':'West door and stairs photo visible; exact risers dimensions estimated'}]},'evidence_source_ids':list(dict.fromkeys(feature.get('evidence_source_ids',[])+['gore-noswan-adjacent-2023','ea-lidar-composite-2022-tq27ne'])),'uncertainty':['Only way117010295, not187/188 or Gore; exact concave footprint retained.','Cream stucco, major sash and round-head windows, attic and portico photo-supported; detail dimensions estimated.','Northern partywall blank. Rear roof simplified from EA surfaces; unseen rear apertures not asserted.','Fine sculpture inscriptions and complete ironwork omitted. CC BY-SA4.0 photo-derived contribution.','Entrance level and stair dimensions need coordinator final paving/contact validation.']}
