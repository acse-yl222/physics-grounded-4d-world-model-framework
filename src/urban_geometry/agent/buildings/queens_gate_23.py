"""23 Queen Gate only: EA-informed layered roof, explicitly estimated residential elevation."""
import math
ROOF=[[(484.04703492391855, -117.53103865217417, 22.2), (485.4290178823285, -125.61732524167746, 22.2), (482.273469163389, -126.14889861582893, 28.799999999999997)], [(482.273469163389, -126.14889861582893, 28.799999999999997), (480.8914308339919, -118.06228803848754, 28.799999999999997), (484.04703492391855, -117.53103865217417, 22.2)], [(480.8914308339919, -118.06228803848754, 28.799999999999997), (482.273469163389, -126.14889861582893, 28.799999999999997), (474.581819160974, -127.44460871532311, 28.799999999999997)], [(474.581819160974, -127.44460871532311, 28.799999999999997), (473.1996458647957, -119.35720841762632, 28.799999999999997), (480.8914308339919, -118.06228803848754, 28.799999999999997)], [(469.1359790026909, -125.18755908776075, 26.804887206715215), (474.581819160974, -127.44460871532311, 28.799999999999997), (469.6580376853235, -128.27405277267098, 26.802743468669757)], [(469.1359790026909, -125.18755908776075, 26.804887206715215), (469.1239302030977, -125.18958575754714, 26.799999999999997), (468.26901447428526, -120.18728558374094, 26.799999999999997)], [(474.581819160974, -127.44460871532311, 28.799999999999997), (469.1359790026909, -125.18755908776075, 26.804887206715215), (473.1996458647957, -119.35720841762632, 28.799999999999997)], [(469.1359790026909, -125.18755908776075, 26.804887206715215), (468.26901447428526, -120.18728558374094, 26.799999999999997), (473.1996458647957, -119.35720841762632, 28.799999999999997)], [(461.6647163670277, -126.44426371902227, 14.0), (460.6482985659968, -121.35028567910194, 14.0), (466.20451519079506, -120.53484628722072, 14.0)], [(466.20451519079506, -120.53484628722072, 14.0), (468.26901447428526, -120.18728558374094, 14.0), (469.1239302030977, -125.18958575754714, 14.0)], [(469.1239302030977, -125.18958575754714, 14.0), (461.6647163670277, -126.44426371902227, 14.0), (466.20451519079506, -120.53484628722072, 14.0)]]
STEP=[[(469.1239301986773, -125.18958573168243), (468.26901447846654, -120.18728560820644)]]
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[-1],ring[0];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 22.2+6.6*max(0,min(1,v/3.2))-2.0*max(0,min(1,(v-11)/5))
 plaster=ctx.material('23 pale stucco',(.73,.71,.65),.86)
 trimat=ctx.material('23 pale dressings',(.79,.77,.71),.72)
 slate=ctx.material('23 dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('23 blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('23 painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('23 estimated dark timber',(.09,.045,.027),.69)
 stone=ctx.material('23 estimated threshold stone',(.52,.50,.45),.87)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA layered continuous roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei in [6,4]:
   count=3 if ei==6 else 1
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([1.05,5.45,9.85,14.25,18.65]):
     hi=lo+(2.8 if row<3 else 2.5);door=ei==6 and k==0 and row==0
     if hi>min(rh(*A),rh(*B))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.08 if door else lo,3.4 if door else hi,door))
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
   localrh=lambda pt:14.0 if vm>16.0 else rh(*pt)
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
    bx(entry,c,.31,.04,w+.25,.94,.08,stone)
    bx(details,c,.32,3.73,w+.58,.9,.24,trimat)
    # Plain rectangular portico pilasters sit outside the door approach width.
    for ss in [l-.24,r+.24]:bx(details,ss,.25,1.79,.20,.34,3.58,trimat)
    entrances.append({'name':'Estimated23 Queen Gate street entrance','threshold_xyz':p(c,0,.08),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.74),'door_leaf_depth_m':.4,'estimated':True,'supporting_surface':'finite authored threshold .08m; precise step/entrance arrangement unverified'})
  if ei==6:
   for zz in [4.65,9.05,13.45,17.85,21.85,22.13]:bx(details,ll/2,.025,zz,ll,.20,.20,trimat)
  if ei==6:
   # Listed facade balconies and crowning balustrade, simple estimated rail geometry.
   for zz in [5.18,9.58,18.38]:
    bx(details,ll/2,.24,zz,ll,.65,.15,trimat)
    bx(details,ll/2,.48,zz+.92,ll,.17,.13,trimat)
    for j in range(18):bx(details,(j+.5)*ll/18,.48,zz+.47,.075,.10,.80,trimat)
   for zz in [7.0,11.4]:
    for frac in [.04,.35,.65,.96]:
     bx(details,ll*frac,.08,zz,.16,.22,3.1,trimat)
     bx(details,ll*frac,.08,zz+1.5,.31,.28,.18,trimat)
 for A,B in STEP:
  wall.face([(A[0],A[1],base+14.0),(B[0],B[1],base+14.0),(B[0],B[1],base+rh(*B)),(A[0],A[1],base+rh(*A))],plaster)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'front_eaves_m':22.2,'main_roof_m':28.8,'rear_roof_m':26.8,'west_annexe_m':14.0,'full_mapped_outline':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','va-praefcke-aerial-a-2011','he-queensgate20-24-1266042-text'],'uncertainty':['EA83inset samples median27.884,p9528.811 supports28.8main and14m western annexe. Eaves and plane axes estimated.','HE OGL listing confirms stucco five-storey terrace, orders at first/second floors, balconies ;22alone has documented crowning balustrade, not copied to23. Simple pilasters and square rails stand in for carved capitals and balusters.','Exact threebay window count, dimensions, east entrance position/threshold, colours and rear windows estimated. No licensed target photograph acquired.','North22 and westterrace shared boundaries and south24 common wall blank. Only rear exposed inset edge has estimated windows. No footprints merged.','PD aerial viewed at regional scale only. Full-scene ground and doorway clearance remains coordinator review.']}
