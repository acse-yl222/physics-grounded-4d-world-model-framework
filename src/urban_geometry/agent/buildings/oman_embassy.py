"""Embassy of the Sultanate of Oman,167 Queen Gate; licensed2013front,EA roof estimates."""
import math
ZONES=[{'outer': [[572.9531270298176, -328.67143033258617], [571.9252396915108, -322.7427966725081], [569.2463251486188, -323.2024172861129], [570.2400189883774, -328.96534734312445], [555.4929430857301, -331.5160095207393], [553.4553773914231, -319.76938378158957], [564.7782995162997, -317.8184301489964], [579.0763815045427, -315.34619744755804], [581.1423303394647, -327.2564528213441]], 'roof': [[[555.4929430857301, -331.5160095207393, 21.0], [553.4553773914231, -319.76938378158957, 21.0], [556.4118153018699, -319.2599858349014, 25.499999999999925]], [[556.4118153018699, -319.2599858349014, 25.499999999999925], [558.4490527463716, -331.00471920433654, 25.5], [555.4929430857301, -331.5160095207393, 21.0]], [[563.3101704262458, -318.0713906259623, 25.5], [565.3466419545352, -329.8117084660634, 25.5], [558.4490527463716, -331.00471920433654, 25.5]], [[558.4490527463716, -331.00471920433654, 25.5], [556.4118153018699, -319.2599858349014, 25.499999999999925], [563.3101704262458, -318.0713906259623, 25.5]], [[569.2463251486188, -323.2024172861129, 22.185409839246105], [569.2225931240652, -317.0499824648283, 21.500000000000018], [570.2596358138817, -323.0285638606738, 21.500000000000057]], [[569.2463251486188, -323.2024172861129, 22.185409839246105], [570.2400189883774, -328.96534734312445, 22.1893129175863], [565.3466419545352, -329.8117084660634, 25.5]], [[569.2463251486188, -323.2024172861129, 22.185409839246105], [563.3101704262458, -318.0713906259623, 25.5], [564.7782995162997, -317.8184301489964, 24.50682569056082]], [[569.2225931240652, -317.0499824648283, 21.500000000000018], [569.2463251486188, -323.2024172861129, 22.185409839246105], [564.7782995162997, -317.8184301489964, 24.50682569056082]], [[563.3101704262458, -318.0713906259623, 25.5], [569.2463251486188, -323.2024172861129, 22.185409839246105], [565.3466419545352, -329.8117084660634, 25.5]], [[571.9252396915108, -322.7427966725081, 21.5], [581.1423303394647, -327.2564528213441, 21.5], [572.9531270298176, -328.67143033258617, 21.5]], [[571.9252396915108, -322.7427966725081, 21.5], [570.2596358138817, -323.0285638606738, 21.500000000000057], [569.2225931240652, -317.0499824648283, 21.500000000000018]], [[581.1423303394647, -327.2564528213441, 21.5], [571.9252396915108, -322.7427966725081, 21.5], [579.0763815045427, -315.34619744755804, 21.5]], [[571.9252396915108, -322.7427966725081, 21.5], [569.2225931240652, -317.0499824648283, 21.500000000000018], [579.0763815045427, -315.34619744755804, 21.5]]]}, {'outer': [[596.8545321313431, -312.2722379202023], [598.9194492527749, -324.18482026737183], [581.1423303394647, -327.2564528213441], [579.0763815045427, -315.34619744755804]], 'roof': [[[596.8545321313431, -312.2722379202023, 6.2], [598.9194492527749, -324.18482026737183, 6.2], [581.1423303394647, -327.2564528213441, 6.2]], [[581.1423303394647, -327.2564528213441, 6.2], [579.0763815045427, -315.34619744755804, 6.2], [596.8545321313431, -312.2722379202023, 6.2]]]}]
def build(ctx,feature):
 base=float(feature.get('base_m',0));mapped=feature['geometry'][0]['outer'];a,b=mapped[3:5];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L;nx,ny=uy,-ux;angle=math.atan2(uy,ux)
 def P(u,d,z):return(a[0]+ux*u+nx*d,a[1]+uy*u+ny*d,base+z)
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 21+4.5*max(0,min(1,v/3))-4*max(0,min(1,(v-10)/6))
 stone=ctx.material('Oman pale limestone',(.65,.60,.49),.83);brick=ctx.material('Oman red brick',(.43,.17,.082),.86);trim=ctx.material('Oman pale sash frames',(.79,.76,.67),.70);slate=ctx.material('Oman estimated slate roof',(.12,.14,.15),.83);glass=ctx.material('Oman recessed glazing',(.12,.17,.18),.22,0,.22);wood=ctx.material('Oman warm timber door',(.30,.135,.050),.69);panel=ctx.material('Oman lighter timber panels',(.38,.19,.078),.70);iron=ctx.material('Oman dark painted metal',(.024,.024,.022),.46,.6)
 wall=ctx.mesh('complete embassy footprint real apertures');roof=ctx.mesh('main roof and low rear annex');details=ctx.mesh('frames masonry bands and stone bay');porch=ctx.mesh('open double arch two tier stone portico');entry=ctx.mesh('recessed wood door and estimated finite approach')
 def face(m,ps,mat):
  if m is wall and front and mat==brick:
   level=base+11
   if max(v[2] for v in ps)<=level+1e-8:mat=stone
   elif min(v[2] for v in ps)<level-1e-8:
    def clip(upper):
     out=[]
     for A,B in zip(ps,ps[1:]+ps[:1]):
      ia=A[2]>=level if upper else A[2]<=level;ib=B[2]>=level if upper else B[2]<=level
      if ia:out.append(A)
      if ia!=ib:
       t=(level-A[2])/(B[2]-A[2]);out.append(tuple(A[k]+t*(B[k]-A[k]) for k in range(3)))
     return out
    face(m,clip(False),stone);face(m,clip(True),brick);return
  q=[]
  for p in ps:
   if not q or math.dist(p,q[-1])>1e-7:q.append(p)
  for j in range(1,len(q)-1):
   v=[q[j][k]-q[0][k] for k in range(3)];w=[q[j+1][k]-q[0][k] for k in range(3)]
   if sum((v[(k+1)%3]*w[(k+2)%3]-v[(k+2)%3]*w[(k+1)%3])**2 for k in range(3))>1e-12:m.face([q[0],q[j],q[j+1]],mat)
 def BX(m,u,d,z,w,dep,h,mat):m.box(*P(u,d,z),w,dep,h,mat,angle)
 door_u=5.8;door_width=1.6
 for zi,z in enumerate(ZONES):
  ring=z['outer'];signed=sum(A[0]*B[1]-B[0]*A[1] for A,B in zip(ring,ring[1:]+ring[:1]));sg=1 if signed>0 else -1
  for tr in z['roof']:face(roof,[(x,y,base+zz) for x,y,zz in tr],slate)
  for A,B in zip(ring,ring[1:]+ring[:1]):
   ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;ox,oy=ty*sg,-tx*sg
   def p(s,d,h):return(A[0]+tx*s+ox*d,A[1]+ty*s+oy*d,base+h)
   def box(m,s,d,h,w,dep,hh,mat):m.box(*p(s,d,h),w,dep,hh,mat,math.atan2(ty,tx))
   def v(q):return -(q[0]-a[0])*uy+(q[1]-a[1])*ux
   def U(q):return (q[0]-a[0])*ux+(q[1]-a[1])*uy
   front=abs(v(A))<1e-5 and abs(v(B))<1e-5
   party=(not front and abs(U(A))<.2 and abs(U(B))<.2) or (not front and max(U(A),U(B))<.1)
   internal=abs(v(A)-26)<1e-5 and abs(v(B)-26)<1e-5
   def top(s):return 6.2 if zi else rh(*p(s,0,0)[:2])
   aps=[]
   if front:
    for u in [2.2,5.8,9.7]:
     for lo,hi in [(1.55,4.5),(7.2,10.5),(12.6,15.45),(17.3,20.1)]:
      isdoor=u==5.8 and lo<2
      su=(P(u,0,0)[0]-A[0])*tx+(P(u,0,0)[1]-A[1])*ty
      aps.append((su-(.8 if isdoor else .78),su+(.8 if isdoor else .78),1.2 if isdoor else lo,4.5 if isdoor else hi,isdoor))
   elif not party and not internal and ll>3:
    for j in range(max(1,int(ll/4))):
     c=ll*(j+.5)/max(1,int(ll/4))
     for lo,hi in [(1.3,3.7),(6.8,9.4),(11.7,14.3),(16.7,19.3)]:
      if hi<min(top(c-.6),top(c+.6))-.5:aps.append((c-.6,c+.6,lo,hi,False))
   cuts=[0,ll]+[x for ap in aps for x in ap[:2]]
   if zi==0 and abs(v(B)-v(A))>1e-8:
    for d in [3,10,16]:
     t=(d-v(A))/(v(B)-v(A))
     if 0<t<1:cuts.append(ll*t)
   cuts=sorted(set(cuts))
   for l,r in zip(cuts,cuts[1:]):
    if r-l<1e-6:continue
    zz=0
    for lo,hi in sorted((ap[2],ap[3]) for ap in aps if ap[0]<(l+r)/2<ap[1]):
     if lo>zz:face(wall,[p(l,0,zz),p(r,0,zz),p(r,0,lo),p(l,0,lo)],brick if not front or (U(p((l+r)/2,0,0))<8 and zz>=11) else stone)
     zz=hi
    face(wall,[p(l,0,zz),p(r,0,zz),p(r,0,top(r)),p(l,0,top(l))],brick if not front or U(p((l+r)/2,0,0))<8 else stone)
   for l,r,lo,hi,isdoor in aps:
    c=(l+r)/2;w=r-l;dep=.65 if isdoor else .28
    box(entry if isdoor else details,c,-dep,(lo+hi)/2,w,.08,hi-lo,wood if isdoor else glass)
    for ss in [l,r]:face(wall,[p(ss,0,lo),p(ss,-dep,lo),p(ss,-dep,hi),p(ss,0,hi)],stone)
    for zz in [lo,hi]:face(wall,[p(l,0,zz),p(r,0,zz),p(r,-dep,zz),p(l,-dep,zz)],stone)
    for ss in [l-.07,r+.07]:box(details,ss,.025,(lo+hi)/2,.14,.20,hi-lo+.18,trim)
    for zz in [lo-.08,hi+.08]:box(details,c,.07,zz,w+.3,.3,.16,stone)
    if not isdoor:
     box(details,c,-dep+.075,(lo+hi)/2,.055,.07,hi-lo,trim);box(details,c,-dep+.075,lo+(hi-lo)*.66,w,.07,.06,trim)
    else:
     for zz in [1.75,2.75,3.8]:
      for ss in [c-.35,c+.35]:box(entry,ss,-.57,zz,.55,.04,.55,panel)
     box(entry,c+.58,-.53,2.2,.055,.08,.25,iron)
 roof.surface(feature['geometry'],base,stone)
 # Open portico, both lower arches and upper loggia. No solid wall spans the passage.
 for u in [.55,4.0,7.45]:
  for off in ([-.13,.13] if u==4 else [0]):
   x,y,z=P(u+off,1.65,1.2)
   porch.lathe(x,y,z,[(.20,0),(.20,.18),(.145,.28),(.14,3.0),(.23,3.08),(.23,3.23)],stone,16)
 for center in [2.275,5.725]:
  for j in range(32):
   t0=j*math.pi/32;t1=(j+1)*math.pi/32
   for d in [1.38,1.92]:face(porch,[P(center+r*math.cos(t),d,4.35+r*math.sin(t)) for r,t in [(1.46,t0),(1.72,t0),(1.72,t1),(1.46,t1)]],stone)
   for rr in [1.46,1.72]:face(porch,[P(center+rr*math.cos(t),d,4.35+rr*math.sin(t)) for t,d in [(t0,1.38),(t1,1.38),(t1,1.92),(t0,1.92)]],stone)
 BX(porch,4.0,.85,6.275,7.8,2.05,.45,stone)
 for u in [.55,3.85,4.15,7.45]:
  x,y,z=P(u,1.65,6.5);porch.lathe(x,y,z,[(.22,0),(.22,.2),(.15,.32),(.14,4.42),(.24,4.48),(.24,4.65)],stone,16)
 BX(porch,4,.85,11.35,7.8,2.05,.4,stone)
 for h in [6.5,11.55]:
  BX(porch,4,1.77,h+.8,7.8,.16,.18,stone)
  for k in range(28):
   x,y,z=P(.2+7.6*k/27,1.77,h);porch.lathe(x,y,z,[(.065,0),(.045,.15),(.085,.32),(.045,.56),(.065,.67)],stone,8)
  for u in [.3,4,7.7]:BX(porch,u,1.77,h+.42,.34,.32,.84,stone)
 # Preserve approach beneath the right open arch: landing extends through the facade reveal.
 # Keep column footings outside the stair strip; shorten only the free approach.
 left=.05;lo=door_u-1.05;hi=door_u+1.05;right=7.95
 BX(entry,(left+lo)/2,.85,.575,lo-left,2.1,1.25,stone)
 BX(entry,(hi+right)/2,.85,.575,right-hi,2.1,1.25,stone)
 BX(entry,door_u,.675,.575,2.1,1.75,1.25,stone)
 for k in range(6):
  z=1.2-.2*k;d=1.70+.3*k
  BX(entry,door_u,d,(z-.05)/2,2.1,.30,z+.05,stone)
 for z in [6.1,11.5,16.2,20.85]:BX(details,L/2,.10,z,L-.06,.25,.20,brick if z>11 else stone)
 # Right window bay has broad pale stone horizontal divisions; relief limited to facade.
 for z in [5.25,10.9,15.95]:BX(details,9.7,.14,z,3.35,.40,.33,stone)
 objects=[m.done() for m in [wall,roof,details,porch,entry]]
 e={'name':'167 Oman embassy estimated main doorway','threshold_xyz':list(P(door_u,0,1.2)),'outward_normal':[nx,ny,0],'clear_width_m':1.45,'door_leaf_xyz':list(P(door_u,-.65,2.8)),'door_leaf_depth_m':.61,'stair_treads':6,'riser_m':.2,'tread_m':.3,'landing_depth_m':1.55,'approach_outward_extent_m':3.35,'supporting_surface':'finite estimated straight six-step approach bottom-.05. Actual photograph has a side/gated approach; exact hidden route not resolved.','estimated':True}
 return {'created':[x.name for x in objects if x],'parameters':{'front_eaves_m':21,'main_roof_m':25.5,'middle_roof_m':21.5,'rear_annex_m':6.2,'portico_upper_roof_m':11.55,'use':'Embassy of the Sultanate of Oman'},'interfaces':{'entrances':[e]},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','oman-sdrawkcab-front-2013'],'uncertainty':['Licensed target2013image shows twin round lower arches,open upper loggia,red brick upper facade and pale right bay. Exact heights and hidden roof are estimates.','Whole9corner mapped footprint and south notch preserved; rear low annex interpreted fromEA1m,roof break26m estimated.','169north party wall blank; no neighbouring building modified.','Actual side/gated stairs not resolved; straight finite approach explicitly estimated. No security gate,sign text,flag or crest modelled.','Fine Ionic capitals,carving and diamond glazing pattern simplified; hidden faces/window counts estimated. PBR factors are visual estimates,constant exportable values.']}
