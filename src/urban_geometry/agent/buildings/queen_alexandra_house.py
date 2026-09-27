"""Queen Alexandra's House: mapped footprint, licensed street evidence, EA roof scale."""
import math
ROOF=[[(553.96743664, 50.29441758, 0.0), (555.3404978, 40.45962891, 0.0), (557.46923423, 43.2925423, 1.0)], [(553.96743664, 50.29441758, 0.0), (557.46923423, 43.2925423, 1.0), (556.78513828, 48.19249809, 1)], [(553.96743664, 50.29441758, 0.0), (556.78513828, 48.19249809, 1), (574.10098839, 53.34239506, 0.0)], [(556.78513828, 48.19249809, 1), (572.83290936, 50.62193754, 1.0), (574.10098839, 53.34239506, 0.0)], [(574.10098839, 53.34239506, 0.0), (572.83290936, 50.62193754, 1.0), (574.95108754, 53.46426046, 0.0)], [(574.95108754, 53.46426046, 0.0), (572.83290936, 50.62193754, 1.0), (576.00650704, 46.10029437, 0.0)], [(576.00650704, 46.10029437, 0.0), (581.25237718, 44.32161491, 1), (583.71109924, 47.19668614, 0.0)], [(583.71109924, 47.19668614, 0.0), (581.25237718, 44.32161491, 1), (586.65496398, 45.09042286, 1)], [(583.71109924, 47.19668614, 0.0), (586.65496398, 45.09042286, 1), (595.1395639, 48.82299865, 0.0)], [(595.1395639, 48.82299865, 0.0), (586.65496398, 45.09042286, 1), (601.92404613, 47.26326934, 1.0)], [(595.1395639, 48.82299865, 0.0), (601.92404613, 47.26326934, 1.0), (604.13005209, 50.10237814, 0.0)], [(604.13005209, 50.10237814, 0.0), (601.92404613, 47.26326934, 1.0), (605.23936361, 39.9011079, 0.0)], [(601.92404613, 47.26326934, 1.0), (602.50613751, 41.91033524, 1), (605.23936361, 39.9011079, 0.0)], [(594.28668009, 37.74159578, 0.0), (605.23936361, 39.9011079, 0.0), (602.50613751, 41.91033524, 1)], [(556.19214223, 9.61290245, 1), (558.18779644, 7.35420039, 0.0), (558.80513726, 9.72745925, 0.0)], [(551.46128985, 8.98968427, 1), (558.18779644, 7.35420039, 0.0), (556.19214223, 9.61290245, 1)], [(551.46128985, 8.98968427, 1), (549.3441236, 6.18918038, 0.0), (558.18779644, 7.35420039, 0.0)], [(550.27493869, 17.10478793, 1.0), (549.3441236, 6.18918038, 0.0), (551.46128985, 8.98968427, 1)], [(547.43731534, 19.23249096, 0.0), (549.3441236, 6.18918038, 0.0), (550.27493869, 17.10478793, 1.0)], [(547.43731534, 19.23249096, 0.0), (550.27493869, 17.10478793, 1.0), (558.11002085, 20.72414564, 0.0)], [(557.46923423, 43.2925423, 1.0), (555.3404978, 40.45962891, 0.0), (558.35882901, 40.89498311, 0.0)], [(557.46923423, 43.2925423, 1.0), (558.35882901, 40.89498311, 0.0), (571.56789682, 42.8002158, 0.0)], [(557.46923423, 43.2925423, 1.0), (571.56789682, 42.8002158, 0.0), (566.6055269, 44.61033124, 1)], [(566.6055269, 44.61033124, 1), (571.56789682, 42.8002158, 0.0), (572.73462443, 45.49437219, 1)], [(572.83290936, 50.62193754, 1.0), (573.54626069, 45.64467967, 1), (576.00650704, 46.10029437, 0.0)], [(573.54626069, 45.64467967, 1), (573.78261852, 43.99554292, 1), (576.00650704, 46.10029437, 0.0)], [(573.78261852, 43.99554292, 1), (574.251239, 43.32532723, 1), (576.00650704, 46.10029437, 0.0)], [(576.00650704, 46.10029437, 0.0), (574.251239, 43.32532723, 1), (576.68128481, 43.67113167, 1)], [(576.00650704, 46.10029437, 0.0), (576.68128481, 43.67113167, 1), (577.56136153, 43.79636982, 1)], [(576.00650704, 46.10029437, 0.0), (577.56136153, 43.79636982, 1), (581.25237718, 44.32161491, 1)], [(582.95824394, 35.79947367, 1), (584.33238832, 33.66088261, 0.0), (593.56393334, 40.1472241, 1)], [(584.33238832, 33.66088261, 0.0), (594.28668009, 37.74159578, 0.0), (593.56393334, 40.1472241, 1)], [(593.56393334, 40.1472241, 1), (594.28668009, 37.74159578, 0.0), (602.50613751, 41.91033524, 1)], [(582.1366212, 35.02915003, 1), (584.33238832, 33.66088261, 0.0), (582.95824394, 35.79947367, 1)], [(579.38020868, 32.44483778, 1), (584.33238832, 33.66088261, 0.0), (582.1366212, 35.02915003, 1)], [(562.65335414, 28.33743325, 0.0), (568.67492356, 29.81607477, 1), (578.44241751, 37.33115124, 1)], [(572.662987, 26.14701472, 1.0), (584.33238832, 33.66088261, 0.0), (579.38020868, 32.44483778, 1)], [(562.65335414, 28.33743325, 0.0), (562.00904057, 24.68736716, 1), (568.67492356, 29.81607477, 1)], [(559.86659436, 14.14958178, 1), (558.80513726, 9.72745925, 0.0), (572.662987, 26.14701472, 1.0)], [(572.662987, 26.14701472, 1.0), (558.80513726, 9.72745925, 0.0), (584.33238832, 33.66088261, 0.0)], [(556.56769643, 11.05665491, 1), (558.80513726, 9.72745925, 0.0), (559.86659436, 14.14958178, 1)], [(556.56769643, 11.05665491, 1), (556.19214223, 9.61290245, 1), (558.80513726, 9.72745925, 0.0)], [(550.27493869, 17.10478793, 1.0), (557.6981168, 18.14227729, 1.0), (558.11002085, 20.72414564, 0.0)], [(558.11002085, 20.72414564, 0.0), (557.6981168, 18.14227729, 1.0), (560.93351548, 18.59446793, 1)], [(560.29572204, 23.13757517, 1), (558.11002085, 20.72414564, 0.0), (560.93351548, 18.59446793, 1)], [(559.68615131, 27.47964743, 1.0), (558.11002085, 20.72414564, 0.0), (560.29572204, 23.13757517, 1)], [(556.87397855, 29.5286776, 0.0), (558.11002085, 20.72414564, 0.0), (559.68615131, 27.47964743, 1.0)], [(556.87397855, 29.5286776, 0.0), (559.68615131, 27.47964743, 1.0), (560.25537962, 27.57850562, 1.0)], [(556.87397855, 29.5286776, 0.0), (560.25537962, 27.57850562, 1.0), (562.23100252, 30.45903486, 0.0)], [(562.23100252, 30.45903486, 0.0), (560.25537962, 27.57850562, 1.0), (562.65335414, 28.33743325, 0.0)], [(571.56789682, 42.8002158, 0.0), (575.02489576, 37.85605511, 0.0), (574.251239, 43.32532723, 1)], [(571.56789682, 42.8002158, 0.0), (574.251239, 43.32532723, 1), (573.78261852, 43.99554292, 1)], [(572.73462443, 45.49437219, 1), (571.56789682, 42.8002158, 0.0), (573.78261852, 43.99554292, 1)], [(574.251239, 43.32532723, 1), (575.02489576, 37.85605511, 0.0), (578.44241751, 37.33115124, 1)], [(562.65335414, 28.33743325, 0.0), (578.44241751, 37.33115124, 1), (575.02489576, 37.85605511, 0.0)], [(560.25537962, 27.57850562, 1.0), (560.9874039, 23.9013234, 1), (562.65335414, 28.33743325, 0.0)], [(562.65335414, 28.33743325, 0.0), (560.9874039, 23.9013234, 1), (562.00904057, 24.68736716, 1)], [(556.78513828, 48.19249809, 1), (557.46923423, 43.2925423, 1.0), (572.73462443, 45.49437219, 1)], [(556.78513828, 48.19249809, 1), (572.73462443, 45.49437219, 1), (572.83290936, 50.62193754, 1.0)], [(572.83290936, 50.62193754, 1.0), (572.73462443, 45.49437219, 1), (573.78261852, 43.99554292, 1)], [(574.251239, 43.32532723, 1), (593.56393334, 40.1472241, 1), (584.41224411, 44.77127558, 1.0)], [(584.41224411, 44.77127558, 1.0), (593.56393334, 40.1472241, 1), (601.92404613, 47.26326934, 1.0)], [(593.56393334, 40.1472241, 1), (602.50613751, 41.91033524, 1), (601.92404613, 47.26326934, 1.0)], [(560.93351548, 18.59446793, 1), (557.33315754, 11.77432345, 1), (582.95824394, 35.79947367, 1)], [(560.93351548, 18.59446793, 1), (556.56769643, 11.05665491, 1), (557.33315754, 11.77432345, 1)], [(551.46128985, 8.98968427, 1), (556.19214223, 9.61290245, 1), (556.56769643, 11.05665491, 1)], [(550.27493869, 17.10478793, 1.0), (551.46128985, 8.98968427, 1), (556.56769643, 11.05665491, 1)], [(550.27493869, 17.10478793, 1.0), (556.56769643, 11.05665491, 1), (560.93351548, 18.59446793, 1)], [(560.25383934, 23.43591255, 1.0), (560.93351548, 18.59446793, 1), (560.9874039, 23.9013234, 1)], [(559.68615131, 27.47964743, 1.0), (560.25383934, 23.43591255, 1.0), (560.9874039, 23.9013234, 1)], [(574.251239, 43.32532723, 1), (578.44241751, 37.33115124, 1), (582.95824394, 35.79947367, 1)], [(574.251239, 43.32532723, 1), (582.95824394, 35.79947367, 1), (593.56393334, 40.1472241, 1)], [(560.9874039, 23.9013234, 1), (582.95824394, 35.79947367, 1), (578.44241751, 37.33115124, 1)], [(560.9874039, 23.9013234, 1), (560.93351548, 18.59446793, 1), (582.95824394, 35.79947367, 1)], [(559.68615131, 27.47964743, 1.0), (560.9874039, 23.9013234, 1), (560.25537962, 27.57850562, 1.0)]]
SOURCES=['queen-romain-entrance-2019','queen-romain-bremner-2019','queen-txllxt-street-2010','ea-lidar-composite-2022-tq27ne']
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer']
 brick=ctx.material('QAH warm red brick',(.31,.105,.078),.88)
 terra=ctx.material('QAH terracotta trim',(.38,.13,.080),.79)
 white=ctx.material('QAH pale painted sash',(.79,.79,.73),.58)
 slate=ctx.material('QAH grey slate',(.12,.14,.15),.81)
 glass=ctx.material('QAH inset glazing',(.14,.20,.21),.20,0,.32)
 iron=ctx.material('QAH iron handrails',(.025,.026,.028),.43,.72)
 timber=ctx.material('QAH timber entrance',(.13,.060,.026),.64)
 stone=ctx.material('QAH pale stone steps',(.59,.55,.45),.85)
 wall=ctx.mesh('mapped walls with real window and portico apertures');frames=ctx.mesh('white sash frames and projecting bay windows');trim=ctx.mesh('terracotta bands stepped gables and pilasters');roof=ctx.mesh('closed inset slate roofs');entry=ctx.mesh('deep arched entrance and stone steps')
 for tri in ROOF:roof.face([(x,y,base+19.0+4.6*d) for x,y,d in tri],slate)
 entrances=[]
 def cleanface(m,vs,mat):
  for j in range(1,len(vs)-1):
   a,b,c=vs[0],vs[j],vs[j+1];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
   if sum((u[(i+1)%3]*v[(i+2)%3]-u[(i+2)%3]*v[(i+1)%3])**2 for i in range(3))>1e-12:m.face([a,b,c],mat)
 for ei,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
  L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L;nx,ny=uy,-ux;angle=math.atan2(uy,ux)
  def pos(s,d,z):return(a[0]+ux*s+nx*d,a[1]+uy*s+ny*d,base+z)
  def bx(m,s,d,z,w,depth,h,mat):m.box(*pos(s,d,z),w,depth,h,mat,angle)
  def quad(m,s0,s1,z0,z1,d,mat):cleanface(m,[pos(s0,d,z0),pos(s1,d,z0),pos(s1,d,z1),pos(s0,d,z1)],mat)
  def pane(s0,d0,s1,d1,z0,z1):
   p0=pos(s0,d0,0);p1=pos(s1,d1,0);w=math.dist(p0,p1);aa=math.atan2(p1[1]-p0[1],p1[0]-p0[0]);cx=(p0[0]+p1[0])/2;cy=(p0[1]+p1[1])/2
   frames.box(cx,cy,base+(z0+z1)/2,w,.06,z1-z0,glass,aa)
   for zz in [z0,z1,z1-.55]:frames.box(cx+nx*.055,cy+ny*.055,base+zz,w,.07,.065,white,aa)
   for px,py in [p0[:2],p1[:2]]:frames.box(px+nx*.055,py+ny*.055,base+(z0+z1)/2,.065,.07,z1-z0,white,aa)
   # Upper small-pane rhythm, lower tall sash, as photographed.
   for frac in [1/3,2/3]:
    xx=p0[0]+(p1[0]-p0[0])*frac;yy=p0[1]+(p1[1]-p0[1])*frac
    frames.box(xx+nx*.06,yy+ny*.06,base+z1-.275,.033,.06,.55,white,aa)
  principal=ei in [1,3,4,5,6]
  bays=[L*(j+.5)/4 for j in range(4)] if ei==3 else ([L*.5] if ei in [1,5] else [])
  # Five levels including lower ground; side/rear rhythm is explicitly estimated.
  pitch=3.1 if principal else 3.5;n=max(1,int(L/pitch));centres=[(j+.5)*L/n for j in range(n)]
  openings=[]
  if bays:centres=[s for s in centres if min(abs(s-q) for q in bays)>2.1]+bays
  for s in centres:
   bay=any(abs(s-q)<.001 for q in bays)
   w=2.65 if bay else min(1.18,L/n*.45)
   if ei==4 and abs(s-L*.5)<3.0:continue
   for row,z in enumerate([.65,3.4,7.1,10.8,14.5]):
    h=1.55 if row==0 else 2.55
    # Avoid invented doors/openings inside the source-reported attached northern wall interval.
    neighbor=float(feature.get('facade_edges',[{}]*len(ring))[ei].get('wall_start_m',0))
    if z+h<neighbor:continue
    openings.append((s-w/2,s+w/2,z,z+h))
    if bay:
     # Three true glazed sides with substantial brick spandrels; the base footprint is unchanged.
     plan=[(s-w/2,0),(s-w*.32,.64),(s+w*.32,.64),(s+w/2,0)]
     for (ss,dd),(tt,ee) in zip(plan,plan[1:]):
      pane(ss,dd,tt,ee,z,z+h)
      lower_z=0 if row==0 else ([.65,3.4,7.1,10.8,14.5][row-1]+(1.55 if row==1 else 2.55)+.20)
      cleanface(wall,[pos(ss,dd,lower_z),pos(tt,ee,lower_z),pos(tt,ee,z),pos(ss,dd,z)],brick)
      cleanface(wall,[pos(ss,dd,z+h),pos(tt,ee,z+h),pos(tt,ee,z+h+.20),pos(ss,dd,z+h+.20)],terra)
      if row==4:cleanface(wall,[pos(ss,dd,z+h+.20),pos(tt,ee,z+h+.20),pos(tt,ee,19),pos(ss,dd,19)],brick)
     cleanface(trim,[pos(ss,dd,z-.08) for ss,dd in plan],terra)
    else:
     pane(s-w/2,-.20,s+w/2,-.20,z,z+h)
     for side in [-1,1]:cleanface(wall,[pos(s+side*w/2,0,z),pos(s+side*w/2,-.23,z),pos(s+side*w/2,-.23,z+h),pos(s+side*w/2,0,z+h)],brick)
    bx(trim,s,.03,z-.09,w+.22,.24,.14,terra)
    bx(trim,s,.01,z+h+.10,w+.22,.19,.13,terra)
  # Actual tall semicircular portico opening, connected to a recessed door and finite stair flight.
  if ei==4:
   es=L*.5;radius=1.85;spring=5.8;crown=spring+radius
   openings.append((es-radius,es+radius,0,crown))
   for k in range(24):
    t0=k*math.pi/24;t1=(k+1)*math.pi/24
    x0=es+radius*math.cos(t0);x1=es+radius*math.cos(t1);z0=spring+radius*math.sin(t0);z1=spring+radius*math.sin(t1)
    cleanface(wall,[pos(x0,0,z0),pos(x1,0,z1),pos(x1,0,crown),pos(x0,0,crown)],brick)
    cleanface(entry,[pos(x0,0,z0),pos(x1,0,z1),pos(x1,-1.7,z1),pos(x0,-1.7,z0)],terra)
    rr=radius+.26
    cleanface(trim,[pos(x0,.13,z0),pos(x1,.13,z1),pos(es+rr*math.cos(t1),.13,spring+rr*math.sin(t1)),pos(es+rr*math.cos(t0),.13,spring+rr*math.sin(t0))],terra)
   for side in [-1,1]:
    bx(trim,es+side*(radius+.32),.06,3.0,.63,.45,6,terra)
    cleanface(entry,[pos(es+side*radius,0,0),pos(es+side*radius,-1.8,0),pos(es+side*radius,-1.8,spring),pos(es+side*radius,0,spring)],terra)
   # Back wall around a narrower open doorway, no opaque slab crossing the actual leaves.
   for side in [-1,1]:bx(entry,es+side*1.38,-1.85,3.1,.94,.18,6.2,brick)
   bx(entry,es,-1.85,4.7,1.84,.18,3.0,brick)
   for side in [-1,1]:bx(entry,es+side*.45,-2.35,2.15,.86,.10,2.4,timber)
   bx(entry,es,-2.26,2.15,.05,.08,2.4,terra)
   # Six 0.15m risers, all treads below the 0.90m entrance landing.
   for k in range(6):
    h=(k+1)*.15;d=1.0-k*.32
    bx(entry,es,d-.16,h/2,3.30,.32,h,stone)
   bx(entry,es,-1.435,.45,3.3,1.03,.90,stone)
   for side in [-1,1]:
    for d,z in [(1.0,.90),(-.6,1.65),(-1.8,1.8)]:bx(entry,es+side*1.55,d,z-.4,.045,.045,.8,iron)
    entry.beam(pos(es+side*1.55,1.0,.9),pos(es+side*1.55,-.6,1.65),.035,iron,n=8)
    entry.beam(pos(es+side*1.55,-.6,1.65),pos(es+side*1.55,-1.8,1.8),.035,iron,n=8)
   for side in [-1,1]:entrances.append({'name':'Main arched portico leaf '+str(side),'threshold_xyz':pos(es+side*.45,-1.95,.9),'outward_normal':[nx,ny,0],'door_leaf_xyz':pos(es+side*.45,-2.35,2.15),'clear_width_m':.80,'door_leaf_depth_m':.45,'stair_treads':6,'riser_m':.15,'tread_m':.32,'landing_z_m':.9,'landing_depth_m':1.03,'supporting_surface':'finite stone stairs and landing; coordinator paving pending','estimated':True})
  cuts=sorted(set([0,L]+[v for q in openings for v in q[:2]]))
  for x0,x1 in zip(cuts,cuts[1:]):
   sm=(x0+x1)/2;holes=sorted([(q[2],q[3]) for q in openings if q[0]<sm<q[1]])
   zz=0
   for z0,z1 in holes:
    if z0>zz:quad(wall,x0,x1,zz,z0,0,brick)
    zz=max(zz,z1)
   if zz<19:quad(wall,x0,x1,zz,19,0,brick)
  for z in [2.65,6.55,10.25,13.95,18.6]:
   spans=[(0,L)]
   if ei==4 and z<7.7:spans=[(0,es-radius-.65),(es+radius+.65,L)]
   for x0,x1 in spans:
    if x1>x0:bx(trim,(x0+x1)/2,.08,z,x1-x0,.23,.17,terra)
  # Stepped gables are a defining silhouette; carving simplified.
  for s in bays:
   for w,z,h in [(4.0,19.4,1.0),(3.45,20.4,1.0),(2.9,21.4,1.0),(2.25,22.4,1.0),(1.6,23.4,1.0),(.9,24.6,1.4)]:
    bx(trim,s,-.08,z,w,.44,h,brick);bx(trim,s,.02,z+h/2,w+.15,.62,.12,terra)
   pane(s-.60,.20,s+.60,.20,19.9,21.45)
  # Low complexity downpipes on photographed principal wall.
  if ei==3:
   for s in [L*.24,L*.49,L*.74]:bx(trim,s,.16,9.3,.07,.10,18.4,iron)
 # Roof chimney masses: estimated positions, heights informed by native1m peaks.
 for x,y in [(554,15),(569,25),(583,39),(563,47)]:
  roof.box(x,y,23.7,.7,1.0,2.4,brick);roof.box(x,y,24.92,.90,1.2,.16,terra)
 objs=[m.done() for m in [wall,frames,trim,roof,entry]]
 return {'created':[ob.name for ob in objs if ob],'parameters':{'eaves_m':19,'roof_m':23.6,'gable_top_m':25.36,'mapped_outline_preserved':True},'interfaces':{'entrances':entrances},'evidence_source_ids':SOURCES,'uncertainty':['Moderate-detail exterior, not survey accuracy or Imperial Phase4 parity.','Entrance edge/offset and six-step dimensions estimated from photographs; all metrically unmeasured.','Rear fenestration inferred; sculpture panels omitted rather than invented.','Roof inset/ridges and exact gable count estimated from street images and1mLiDAR.']}
