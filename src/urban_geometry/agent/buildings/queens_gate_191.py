"""191 Queen Gate only: EA-informed layered roof, explicitly estimated residential elevation."""
import math
ROOF=[[(499.0428579066647, -1.0282228719443083, 22.2), (497.440847438178, 7.717668702825904, 22.2), (500.6179185206765, 8.133503767832675, 28.799999999999997)], [(500.6179185206765, 8.133503767832675, 28.799999999999997), (502.1990130270607, -0.49820082730856374, 28.799999999999997), (499.0428579066647, -1.0282228719443083, 22.2)], [(502.1990130270607, -0.49820082730856374, 28.799999999999997), (500.6179185206765, 8.133503767832675, 28.799999999999997), (508.3620292842665, 9.147101738786683, 28.799999999999997)], [(508.3620292842665, 9.147101738786683, 28.799999999999997), (509.89214113302586, 0.7937279064910601, 28.799999999999997), (502.1990130270607, -0.49820082730856374, 28.799999999999997)], [(514.5903287252805, 2.8955733722156767, 23.499999999999996), (509.89214113302586, 0.7937279064910601, 28.799999999999997), (508.3620292842665, 9.147101738786683, 28.799999999999997)], [(508.3620292842665, 9.147101738786683, 28.799999999999997), (513.3262028506704, 9.796844027859764, 23.499999999999996), (514.5903287252805, 2.8955733722156767, 23.499999999999996)], [(509.89214113302586, 0.7937279064910601, 28.799999999999997), (514.5903287252805, 2.8955733722156767, 23.499999999999996), (514.6204125924269, 1.5877598887309428, 23.71840667569084)], [(514.5587383698439, 4.268877295777202, 23.499999999999996), (514.5903287252805, 2.8955733722156767, 23.499999999999996), (513.3262028506704, 9.796844027859764, 23.499999999999996)], [(514.5587383698439, 4.268877295777202, 23.499999999999996), (519.283211130355, 10.576534774747461, 23.499999999999996), (520.3000470139685, 5.025299896850077, 23.499999999999996)], [(519.283211130355, 10.576534774747461, 23.499999999999996), (514.5587383698439, 4.268877295777202, 23.499999999999996), (513.3262028506704, 9.796844027859764, 23.499999999999996)], [(520.7158787267981, 10.764051329344511, 6.5), (524.9338606375968, 11.316404725424945, 6.5), (525.6703734586481, 5.7328452579677105, 6.5)], [(520.7158787267981, 10.764051329344511, 6.5), (520.3000470139685, 5.025299896850077, 6.5), (519.283211130355, 10.576534774747461, 6.5)], [(520.3000470139685, 5.025299896850077, 6.5), (520.7158787267981, 10.764051329344511, 6.5), (525.6703734586481, 5.7328452579677105, 6.5)]]
STEP=[[(519.2832112223567, 10.576534272479977), (520.3000469235021, 5.025300390735717)]]
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[:2];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 22.2+6.6*max(0,min(1,v/3.2))-5.3*max(0,min(1,(v-11)/5))
 plaster=ctx.material('191 red brick',(.44,.17,.10),.86)
 trimat=ctx.material('191 terracotta dressings',(.65,.39,.24),.72)
 slate=ctx.material('191 dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('191 blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('191 painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('191 estimated dark timber',(.09,.045,.027),.69)
 stone=ctx.material('191 estimated threshold stone',(.52,.50,.45),.87)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA layered continuous roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei in [0,2]:
   count=3 if ei==0 else 1
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([1.05,5.45,9.85,14.25,18.65]):
     hi=lo+(2.8 if row<3 else 2.5);door=ei==0 and k==0 and row==0
     if hi>min(rh(*A),rh(*B))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.08 if door else lo,3.4 if door else hi,door))
  xs=[0,ll]+[xx for op in apertures for xx in op[:2]]
  # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
  va=-(A[0]-a[0])*uy+(A[1]-a[1])*ux;vb=-(B[0]-a[0])*uy+(B[1]-a[1])*ux
  if abs(vb-va)>1e-8:
   for cut in [3.2,11,16,22]:
    t=(cut-va)/(vb-va)
    if 0<t<1:xs.append(t*ll)
  xs=sorted(set(xs))
  for l,r in zip(xs,xs[1:]):
   vm=va+(vb-va)*(l+r)/(2*ll)
   localrh=lambda pt:6.5 if vm>22 else rh(*pt)
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
    entrances.append({'name':'Estimated191 Queen Gate street entrance','threshold_xyz':p(c,0,.08),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.74),'door_leaf_depth_m':.4,'estimated':True,'supporting_surface':'finite authored threshold .08m; precise step/entrance arrangement unverified'})
  if ei==0:
   for zz in [4.65,9.05,13.45,17.85,21.85,22.13]:bx(details,ll/2,.025,zz,ll,.20,.20,trimat)
 for A,B in STEP:
  wall.face([(A[0],A[1],base+6.5),(B[0],B[1],base+6.5),(B[0],B[1],base+rh(*B)),(A[0],A[1],base+rh(*A))],plaster)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'front_eaves_m':22.2,'main_roof_m':28.8,'rear_roof_m':23.5,'east_tail_m':6.5,'full_mapped_outline':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','va-praefcke-aerial-a-2011','lpa-191-queensgate-catalogue-text'],'uncertainty':['EA103inset samples median25.733,p9528.794 supports28.8main,23.5rear and low6.5east tail. Axes/eaves estimated from1m raster.','LPA catalogue text identifies red brick, five storeys/mansard and terracotta porch. Photo was not licensed and was not downloaded/traced.','Three-bay frontage, exact aperture sizes, west entrance position/threshold, colours and rear windows are estimates. Canted bay, decorative balcony and tiny attic details omitted at reduced requested detail.','South Gore and north192 common walls and eastJay boundary remain blank; short exposed inset rear edge has estimated windows. No adjacent footprint merged.','PD aerial inspected only at regional scale. Full-scene ground and doorway clearance remains coordinator review.']}
