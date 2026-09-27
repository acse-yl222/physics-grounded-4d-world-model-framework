"""27 Queen Gate only: EA-informed layered roof, explicitly estimated residential elevation."""
import math
ROOF=[[(483.011545244546, -183.01801389237076, 26.199999999999964), (483.3775420213351, -181.11444192379713, 22.5), (484.63884901592974, -181.92320361640304, 22.5)], [(484.63884901592974, -181.92320361640304, 22.5), (484.29114284715615, -179.75418069399893, 22.5), (487.655289627146, -179.22364675160497, 22.5)], [(471.14044747897424, -184.4032434085384, 22.5), (474.14911104560633, -191.8612165767734, 26.199999999999974), (472.65403612249065, -193.92085196916014, 22.5)], [(486.72126986212567, -183.54161099057646, 26.2), (487.0527244954767, -185.6092553467615, 26.2), (483.011545244546, -183.01801389237076, 26.199999999999964)], [(479.02080206701066, -183.11962642055005, 22.5), (473.1997497339137, -185.8915303043546, 26.199999999999932), (471.14044747897424, -184.4032434085384, 22.5)], [(474.14911104560633, -191.8612165767734, 26.199999999999974), (471.14044747897424, -184.4032434085384, 22.5), (473.1997497339137, -185.8915303043546, 26.199999999999932)], [(483.3775420213351, -181.11444192379713, 22.5), (483.011545244546, -183.01801389237076, 26.199999999999964), (480.19725145655684, -181.7269645249471, 22.5)], [(484.63884901592974, -181.92320361640304, 22.5), (487.655289627146, -179.22364675160497, 22.5), (488.02159088035114, -181.51443583145738, 22.5)], [(494.98511684069456, -188.5564086137081, 26.2), (472.65403612249065, -193.92085196916014, 22.5), (474.14911104560633, -191.8612165767734, 26.199999999999974)], [(484.63884901592974, -181.92320361640304, 22.5), (486.72126986212567, -183.54161099057646, 26.2), (483.011545244546, -183.01801389237076, 26.199999999999964)], [(473.1997497339137, -185.8915303043546, 26.199999999999932), (479.02080206701066, -183.11962642055005, 22.5), (479.9666439730064, -184.78928289858345, 26.2)], [(486.72126986212567, -183.54161099057646, 26.2), (484.63884901592974, -181.92320361640304, 22.5), (488.02159088035114, -181.51443583145738, 22.5)], [(472.65403612249065, -193.92085196916014, 22.5), (494.98511684069456, -188.5564086137081, 26.2), (497.04503930255305, -190.05218432098627, 22.5)], [(479.9666439730064, -184.78928289858345, 26.2), (479.02080206701066, -183.11962642055005, 22.5), (481.16200415117703, -183.3742347150814, 26.199999999999996)], [(494.00696690734145, -182.39325749317666, 26.2), (488.02159088035114, -181.51443583145738, 22.5), (495.50287140347064, -180.3352549513802, 22.5)], [(495.50287140347064, -180.3352549513802, 22.5), (497.04503930255305, -190.05218432098627, 22.5), (494.98511684069456, -188.5564086137081, 26.2)], [(480.19725145655684, -181.7269645249471, 22.5), (481.16200415117703, -183.3742347150814, 26.199999999999996), (479.02080206701066, -183.11962642055005, 22.5)], [(495.50287140347064, -180.3352549513802, 22.5), (494.98511684069456, -188.5564086137081, 26.2), (494.00696690734145, -182.39325749317666, 26.2)], [(480.19725145655684, -181.7269645249471, 22.5), (483.011545244546, -183.01801389237076, 26.199999999999964), (481.16200415117703, -183.3742347150814, 26.199999999999996)], [(486.72126986212567, -183.54161099057646, 26.2), (488.02159088035114, -181.51443583145738, 22.5), (494.00696690734145, -182.39325749317666, 26.2)], [(479.9666439730064, -184.78928289858345, 26.2), (481.16200415117703, -183.3742347150814, 26.199999999999996), (483.011545244546, -183.01801389237076, 26.199999999999964)], [(487.0527244954767, -185.6092553467615, 26.2), (486.72126986212567, -183.54161099057646, 26.2), (494.00696690734145, -182.39325749317666, 26.2)], [(487.0527244954767, -185.6092553467615, 26.2), (494.98511684069456, -188.5564086137081, 26.2), (474.14911104560633, -191.8612165767734, 26.199999999999974)], [(474.14911104560633, -191.8612165767734, 26.199999999999974), (473.1997497339137, -185.8915303043546, 26.199999999999932), (479.9666439730064, -184.78928289858345, 26.2)], [(479.9666439730064, -184.78928289858345, 26.2), (483.011545244546, -183.01801389237076, 26.199999999999964), (487.0527244954767, -185.6092553467615, 26.2)], [(494.98511684069456, -188.5564086137081, 26.2), (487.0527244954767, -185.6092553467615, 26.2), (494.00696690734145, -182.39325749317666, 26.2)], [(474.14911104560633, -191.8612165767734, 26.199999999999974), (479.9666439730064, -184.78928289858345, 26.2), (487.0527244954767, -185.6092553467615, 26.2)]]
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[2:4];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):return 22.5
 plaster=ctx.material('27 estimated pale stucco',(.73,.71,.65),.86)
 trimat=ctx.material('27 estimated pale dressings',(.79,.77,.71),.72)
 slate=ctx.material('27 dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('27 blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('27 painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('27 estimated dark timber',(.025,.027,.026),.69)
 stone=ctx.material('27 estimated threshold stone',(.52,.50,.45),.87)
 panel=ctx.material('27 estimated lighter timber panels',(.065,.069,.065),.70)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA layered continuous roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei==2 or (ei>=3 and ll>2.5):
   count=3 if ei==2 else max(1,int(ll/3.3))
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([1.1,6.1,10.9,15.25,19.3]):
     hi=lo+(3.0 if row<2 else 2.4);door=ei==2 and k==0 and row==0
     if hi>min(rh(*A),rh(*B))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.30 if door else lo,4.3 if door else hi,door))
  xs=[0,ll]+[xx for op in apertures for xx in op[:2]]
  # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
  va=-(A[0]-a[0])*uy+(A[1]-a[1])*ux;vb=-(B[0]-a[0])*uy+(B[1]-a[1])*ux
  if abs(vb-va)>1e-8:
   for cut in [3.2,10,16]:
    t=(cut-va)/(vb-va)
    if 0<t<1:xs.append(t*ll)
  xs=sorted(set(xs))
  for l,r in zip(xs,xs[1:]):
   aps=sorted([op for op in apertures if op[0]<(l+r)/2<op[1]],key=lambda x:x[2]);z=0
   for op in aps:
    if op[2]>z:wall.face([p(l,0,z),p(r,0,z),p(r,0,op[2]),p(l,0,op[2])],plaster)
    z=op[3]
   wall.face([p(l,0,z),p(r,0,z),p(r,0,rh(*p(r,0,0)[:2])),p(l,0,rh(*p(l,0,0)[:2]))],plaster)
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
    bx(entry,c,.40,.125,w+.25,1.0,.35,stone)
    bx(entry,c,1.05,.05,w+.25,.30,.20,stone)
    for zz in [.95,2.1,3.4]:
     for ss in [c-.34,c+.34]:bx(entry,ss,-.365,zz,.52,.04,.54,panel)
    bx(entry,c+.51,-.33,1.25,.055,.08,.26,iron)
    bx(details,c,.10,4.58,w+.58,.35,.24,trimat)
    entrances.append({'name':'Estimated27 Queen Gate street entrance','threshold_xyz':p(c,0,.3),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.74),'door_leaf_depth_m':.4,'estimated':True,'stair_treads':2,'riser_m':.15,'tread_m':.3,'landing_depth_m':.9,'supporting_surface':'two estimated .15m risers; finite approach bottom-.05' })
  if ei==2:
   for z in [q*.38 for q in range(1,14)]:
    intervals=[(0,ll)]
    for l,r,lo,hi,door in apertures:
     if lo-.1<z<hi+.1:
      intervals=[seg for aa,bb in intervals for seg in [(aa,min(bb,l-.12)),(max(aa,r+.12),bb)] if seg[1]-seg[0]>.05]
    for l,r in intervals:bx(details,(l+r)/2,.005,z,r-l,.022,.023,stone)
   bx(details,ll/2,.44,5.45,ll-.3,.95,.16,trimat)
   bx(details,ll/2,.86,6.10,ll-.3,.11,.12,trimat)
   for k in range(24):bx(details,.3+(ll-.6)*k/23,.86,5.78,.07,.09,.55,trimat)
   for zz in [5.15,10.35,14.8,18.9,22.35]:bx(details,ll/2,.025,zz,ll,.20,.20,trimat)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'front_eaves_m':22.5,'main_roof_m':26.2,'full_mapped_outline':True,'facade_confidence':'partial:27numbereddoor visible in licensed2014adjacent photograph; roof/upperbaycounts estimated'},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','qg27-kenyh-adjacent-2014'],'uncertainty':['Exact11corner footprint and north projections retained; no adjacent28or26merged. West/southpartywalls blank.','EA154inset samples median25.5945,p9526.4365 support26.2mainroof; eaves22.5/pitches/breaklines estimated.','2014photo right margin explicitly numbered27shows darkdoor,rusticatedpale facade,lowstep and partialupperbalustrade.28columnedportalnotcopied.','Remaining frontupperlevels,northbay windows and hidden roof features estimated; no invented roof equipment.','Main wall openings are real recessed sash apertures; decorativefirstfloorarchhoods simplified,not survey. PBR constantvalues estimated.','Master ground and entry clearance remain coordinator validation.']}
