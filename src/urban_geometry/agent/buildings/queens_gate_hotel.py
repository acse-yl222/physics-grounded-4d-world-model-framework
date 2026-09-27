"""Queen Gate Hotel Embassy only: EA-informed layered roof, explicitly estimated residential elevation."""
import math
ROOF=[[(500.7927701609442, -213.7139726933092, 22.2), (505.9564146986231, -246.34038591384888, 22.2), (502.797466411106, -246.85142965666844, 27.799999999999997)], [(502.797466411106, -246.85142965666844, 27.799999999999997), (497.62999688729093, -214.20084831662913, 27.799999999999997), (500.7927701609442, -213.7139726933092, 22.2)], [(497.62999688729093, -214.20084831662913, 27.799999999999997), (502.797466411106, -246.85142965666844, 27.799999999999997), (495.097529960283, -248.0970987797912, 27.799999999999997)], [(495.097529960283, -248.0970987797912, 27.799999999999997), (489.92073703276117, -215.38760764847157, 27.799999999999997), (497.62999688729093, -214.20084831662913, 27.799999999999997)], [(489.92073703276117, -215.38760764847157, 27.799999999999997), (495.097529960283, -248.0970987797912, 27.799999999999997), (490.1616732610375, -248.8956046279468, 25.499999999999996)], [(490.1616732610375, -248.8956046279468, 25.499999999999996), (484.9789037926779, -216.14835080990903, 25.499999999999996), (489.92073703276117, -215.38760764847157, 27.799999999999997)], [(484.9789037926779, -216.14835080990903, 25.499999999999996), (490.1616732610375, -248.8956046279468, 25.499999999999996), (488.3847648493091, -249.1830667332828, 25.499999999999996)], [(488.3847648493091, -249.1830667332828, 25.499999999999996), (483.19984382624796, -216.4222183480265, 25.499999999999996), (484.9789037926779, -216.14835080990903, 25.499999999999996)], [(486.64780482056085, -244.8577466486022, 10.0), (482.46816134254914, -245.50879009906203, 10.0), (481.9107823256636, -241.86691741459072, 10.0)], [(481.9107823256636, -241.86691741459072, 10.0), (478.4563775007846, -242.40092389844358, 10.0), (477.22398273809813, -234.40908352751282, 10.0)], [(483.19984382624796, -216.4222183480265, 10.0), (475.9569750932278, -226.24041993450373, 10.0), (474.64241537381895, -217.73954429943112, 10.0)], [(486.64780482056085, -244.8577466486022, 10.0), (488.3847648493091, -249.1830667332828, 10.0), (487.34228304668795, -249.35171583853662, 10.0)], [(486.64780482056085, -244.8577466486022, 10.0), (481.9107823256636, -241.86691741459072, 10.0), (477.22398273809813, -234.40908352751282, 10.0)], [(475.9569750932278, -226.24041993450373, 10.0), (483.19984382624796, -216.4222183480265, 10.0), (477.22398273809813, -234.40908352751282, 10.0)], [(488.3847648493091, -249.1830667332828, 10.0), (486.64780482056085, -244.8577466486022, 10.0), (483.19984382624796, -216.4222183480265, 10.0)], [(486.64780482056085, -244.8577466486022, 10.0), (477.22398273809813, -234.40908352751282, 10.0), (483.19984382624796, -216.4222183480265, 10.0)]]
STEP=[[(488.38476484395807, -249.18306669947236), (483.19984383285004, -216.42221838974143)]]
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[9],ring[0];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 22.2+5.6*max(0,min(1,v/3.2))-2.3*max(0,min(1,(v-11)/5))
 plaster=ctx.material('Hotel pale stucco',(.73,.71,.65),.86)
 trimat=ctx.material('Hotel pale dressings',(.79,.77,.71),.72)
 slate=ctx.material('Hotel dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('Hotel blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('Hotel painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('Hotel estimated dark timber',(.09,.045,.027),.69)
 stone=ctx.material('Hotel estimated threshold stone',(.52,.50,.45),.87)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA layered continuous roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei in [9]:
   count=12 if ei==9 else 1
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([1.05,5.45,9.85,14.25,18.65]):
     hi=lo+(2.8 if row<3 else 2.5);door=ei==9 and k==5 and row==0
     if hi>(10.0 if ei==2 else min(rh(*A),rh(*B)))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.45 if door else lo,3.4 if door else hi,door))
  xs=[0,ll]+[xx for op in apertures for xx in op[:2]]
  # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
  va=-(A[0]-a[0])*uy+(A[1]-a[1])*ux;vb=-(B[0]-a[0])*uy+(B[1]-a[1])*ux
  if abs(vb-va)>1e-8:
   for cut in [3.2,11,16,17.8]:
    t=(cut-va)/(vb-va)
    if 0<t<1:xs.append(t*ll)
  xs=sorted(set(xs))
  for l,r in zip(xs,xs[1:]):
   vm=va+(vb-va)*(l+r)/(2*ll)
   localrh=lambda pt:10.0 if vm>17.8 else rh(*pt)
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
    for ss in [l-.24,r+.24]:bx(details,ss,.25,1.79,.20,.34,3.58,trimat)
    entrances.append({'name':'EstimatedQueen Gate Hotel Embassy street entrance','threshold_xyz':p(c,0,.45),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.925),'door_leaf_depth_m':.4,'estimated':True,'supporting_surface':'finite authored threshold .45m; precise step/entrance arrangement unverified'})
  if ei==9:
   for zz in [4.65,9.05,13.45,17.85,21.85,22.13]:bx(details,ll/2,.025,zz,ll,.20,.20,trimat)
 for A,B in STEP:
  wall.face([(A[0],A[1],base+10.0),(B[0],B[1],base+10.0),(B[0],B[1],base+rh(*B)),(A[0],A[1],base+rh(*A))],plaster)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'front_eaves_m':22.2,'main_roof_m':27.8,'rear_roof_m':25.5,'west_annexe_m':10.,'full_mapped_outline':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','va-praefcke-aerial-a-2011'],'uncertainty':['Complete31-34 single mapped footprint; five levels from OSM.12-bay facade and single central entry are low-confidence editable estimates, no licensed target street photo obtained.','EA661inset median25.234,p9527.767 supports27.8main/25.5rear/10westernlowmass; eave22.2 and profilebreakaxes estimated from1m raster.','PD aerial actually inspected only at regional roof scale; no claim of exact window/capital evidence. Pale stucco/slate/glass material classes neighbourhood analogy, exact colours estimated.','NorthThai/south35/rearMews shared boundaries solid withoutwindows. Entirefootprint retained; no four-way split or neighbouringfootprint merge.','Single estimated threshold.45withthree.15risers; original exact entrance/steps unresolved. Fine sculpture, basement and atticdetails omitted. Fullscene ground/approach remains coordinator review.']}
