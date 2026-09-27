"""28 Queen Gate only: EA-informed layered roof, explicitly estimated residential elevation."""
import math
ROOF=[[(497.04503930255305, -190.05218432098627, 22.2), (498.3406936451793, -198.24201014917344, 22.2), (495.1787359751866, -198.73403593477602, 27.9)], [(495.1787359751866, -198.73403593477602, 27.9), (493.88454679856284, -190.55347141492905, 27.9), (497.04503930255305, -190.05218432098627, 22.2)], [(493.88454679856284, -190.55347141492905, 27.9), (495.1787359751866, -198.73403593477602, 27.9), (487.47146415457956, -199.93334878718238, 27.9)], [(487.47146415457956, -199.93334878718238, 27.9), (486.18084632008674, -191.77535870641464, 27.9), (493.88454679856284, -190.55347141492905, 27.9)], [(486.18084632008674, -191.77535870641464, 27.9), (487.47146415457956, -199.93334878718238, 27.9), (482.53090529521603, -200.70213907718642, 25.0)], [(482.53090529521603, -200.70213907718642, 25.0), (481.242576782602, -192.55861979070025, 25.0), (486.18084632008674, -191.77535870641464, 27.9)], [(473.11379384819884, -195.75151159614325, 12.0), (472.65403612249065, -193.92085196916014, 12.0), (481.242576782602, -192.55861979070025, 12.0)], [(473.9176749639446, -200.9204892963171, 12.0), (482.53090529521603, -200.70213907718642, 12.0), (474.08501500077546, -202.01638684421778, 12.0)], [(482.53090529521603, -200.70213907718642, 12.0), (473.11379384819884, -195.75151159614325, 12.0), (481.242576782602, -192.55861979070025, 12.0)], [(473.11379384819884, -195.75151159614325, 12.0), (482.53090529521603, -200.70213907718642, 12.0), (473.9176749639446, -200.9204892963171, 12.0)]]
STEP=[[(482.53090529125853, -200.70213905217142), (481.24257678322317, -192.55861979462682)]]
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[-1],ring[0];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 22.2+5.7*max(0,min(1,v/3.2))-2.9*max(0,min(1,(v-11)/5))
 plaster=ctx.material('28 pale stucco',(.73,.71,.65),.86)
 trimat=ctx.material('28 pale dressings',(.79,.77,.71),.72)
 slate=ctx.material('28 dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('28 blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('28 painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('28 estimated dark timber',(.09,.045,.027),.69)
 stone=ctx.material('28 estimated threshold stone',(.52,.50,.45),.87)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA layered continuous roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei in [5,2]:
   count=3 if ei==5 else 1
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([1.05,5.45,9.85,14.25,18.65]):
     hi=lo+(2.8 if row<3 else 2.5);door=ei==5 and k==1 and row==0
     if hi>(12.0 if ei==2 else min(rh(*A),rh(*B)))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.45 if door else lo,3.4 if door else hi,door))
  xs=[0,ll]+[xx for op in apertures for xx in op[:2]]
  # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
  va=-(A[0]-a[0])*uy+(A[1]-a[1])*ux;vb=-(B[0]-a[0])*uy+(B[1]-a[1])*ux
  if abs(vb-va)>1e-8:
   for cut in [3.2,11,16,16.0]:
    t=(cut-va)/(vb-va)
    if 0<t<1:xs.append(t*ll)
  xs=sorted(set(xs))
  for l,r in zip(xs,xs[1:]):
   vm=va+(vb-va)*(l+r)/(2*ll)
   localrh=lambda pt:12.0 if vm>16.0 else rh(*pt)
   aps=sorted([op for op in apertures if op[0]<(l+r)/2<op[1]],key=lambda x:x[2]);z=0
   for op in aps:
    if op[2]>z:wall.face([p(l,0,z),p(r,0,z),p(r,0,op[2]),p(l,0,op[2])],plaster)
    z=op[3]
   wall.face([p(l,0,z),p(r,0,z),p(r,0,localrh(p(r,0,0)[:2])),p(l,0,localrh(p(l,0,0)[:2]))],plaster)
  for l,r,lo,hi,door in apertures:
   c=(l+r)/2;w=r-l;d=.43 if door else .22
   bx(entry if door else windows,c,-d,(lo+hi)/2,w,.06,hi-lo,timber if door else glass)
   for ss in [l,r]:wall.face([p(ss,0,lo),p(ss,-d,lo),p(ss,-d,hi),p(ss,0,hi)],trimat)
   for zz in [lo,hi]:wall.face([p(l,0,zz),p(r,0,zz),p(r,-d,zz),p(l,-d,zz)],trimat)
   for ss in [l-.055,r+.055]:bx(windows,ss,.005,(lo+hi)/2,.11,.16,hi-lo+.14,trimat)
   bx(windows,c,.035,hi+.08,w+.26,.24,.16,trimat)
   if not door:
    bx(windows,c,.04,lo-.07,w+.28,.26,.14,trimat);bx(windows,c,-d+.05,(lo+hi)/2,.045,.05,hi-lo,trimat);bx(windows,c,-d+.05,(lo+hi)/2,w,.05,.05,trimat)
   else:
    bx(entry,c,.31,.225,w+.25,.94,.45,stone)
    bx(entry,c,.93,.15,w+.25,.30,.30,stone)
    bx(entry,c,1.23,.075,w+.25,.30,.15,stone)
    bx(details,c,.32,3.73,w+.58,.9,.24,trimat)
    # Plain rectangular portico pilasters sit outside the door approach width.
    for ss in [l-.28,r+.28]:
     details.beam(p(ss,.35,.18),p(ss,.35,3.55),.16,trimat,16)
     bx(details,ss,.35,.11,.46,.48,.22,trimat)
     bx(details,ss,.35,3.57,.46,.48,.24,trimat)
    entrances.append({'name':'Estimated28 Queen Gate street entrance','threshold_xyz':p(c,0,.45),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.925),'door_leaf_depth_m':.4,'estimated':True,'supporting_surface':'finite authored threshold .45m; precise step/entrance arrangement unverified'})
  if ei==5:
   # Photo-supported first-floor semicircular window heads: solid spandrels reduce the real opening.
   for k in range(3):
    c=ll*(k+.5)/3;rad=.67;spring=8.25-rad
    for j in range(16):
     t0=math.pi*j/16;t1=math.pi*(j+1)/16
     x0=c+rad*math.cos(t0);x1=c+rad*math.cos(t1);z0=spring+rad*math.sin(t0);z1=spring+rad*math.sin(t1)
     vs=[p(x0,0,8.25),p(x1,0,8.25)]
     if abs(z1-8.25)>1e-7:vs.append(p(x1,0,z1))
     if abs(z0-8.25)>1e-7:vs.append(p(x0,0,z0))
     wall.face(vs,plaster)
     details.beam(p(x0,.06,z0),p(x1,.06,z1),.085,trimat,8)
   bx(details,ll/2,.24,5.15,ll,.68,.18,trimat)
   bx(details,ll/2,.51,6.02,ll,.17,.14,trimat)
   for j in range(20):bx(details,(j+.5)*ll/20,.51,5.59,.085,.12,.76,trimat)
  if ei==5:
   for zz in [4.65,9.05,13.45,17.85,21.85,22.13]:bx(details,ll/2,.025,zz,ll,.20,.20,trimat)
 for A,B in STEP:
  wall.face([(A[0],A[1],base+12.0),(B[0],B[1],base+12.0),(B[0],B[1],base+rh(*B)),(A[0],A[1],base+rh(*A))],plaster)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'front_eaves_m':22.2,'main_roof_m':27.9,'rear_roof_m':25.,'west_annexe_m':12.,'full_mapped_outline':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','qg27-kenyh-adjacent-2014'],'uncertainty':['Photo actually viewed: number28 central entrance, pale stucco, paired round portico columns, steps, firstfloor arched windows and balcony. Capitals/balusters simplified and all dimensions estimated.','EA113inset median25.365,p9527.887 supports27.9main/25rear and12western low mass; plane axes and front eave22.2estimated.','Upper3rows and rear windows estimated because photo cropped upper facade/roof; no false exact facade survey claim. Basement omitted.','North27/south29-30 and shared rear edge segments blank; complete mapped footprint retained.','Entry threshold .45 and three rises estimated from visible steps; final fullscene ground and neighbouring clearance remain coordinator review.']}
