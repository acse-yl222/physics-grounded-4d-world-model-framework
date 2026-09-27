"""25 Elvaston Mews only: EA-informed flat roof, explicitly estimated residential elevation."""
import math
ROOF=[[(466.4388788820943, -227.40899484138936, 7.6), (467.90637429533984, -221.069910178196, 9.85), (468.5070770443282, -224.63630249351073, 9.849999999999993)], [(467.90637429533984, -221.069910178196, 9.85), (466.4388788820943, -227.40899484138936, 7.6), (465.0059327806812, -218.90154590271413, 7.6)], [(473.09215255713286, -224.0733743541448, 9.85), (466.4388788820943, -227.40899484138936, 7.6), (468.5070770443282, -224.63630249351073, 9.849999999999993)], [(474.64241537381895, -217.73954429943115, 7.6), (467.90637429533984, -221.069910178196, 9.85), (465.0059327806812, -218.90154590271413, 7.6)], [(466.4388788820943, -227.40899484138936, 7.6), (473.09215255713286, -224.0733743541448, 9.85), (475.9569750932278, -226.24041993450373, 7.6)], [(467.90637429533984, -221.069910178196, 9.85), (474.64241537381895, -217.73954429943115, 7.6), (472.54127620536536, -220.5110170967781, 9.85)], [(474.64241537381895, -217.73954429943115, 7.6), (475.9569750932278, -226.24041993450373, 7.6), (473.09215255713286, -224.0733743541448, 9.85)], [(473.09215255713286, -224.0733743541448, 9.85), (472.54127620536536, -220.5110170967781, 9.85), (474.64241537381895, -217.73954429943115, 7.6)], [(468.5070770443282, -224.63630249351073, 9.849999999999993), (472.54127620536536, -220.5110170967781, 9.85), (473.09215255713286, -224.0733743541448, 9.85)], [(472.54127620536536, -220.5110170967781, 9.85), (468.5070770443282, -224.63630249351073, 9.849999999999993), (467.90637429533984, -221.069910178196, 9.85)]]
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[:2];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):return 7.6
 plaster=ctx.material('Elvaston25 estimated buff brick',(.48,.40,.29),.86)
 trimat=ctx.material('Elvaston25 estimated pale dressings',(.79,.77,.71),.72)
 slate=ctx.material('Elvaston25 dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('Elvaston25 blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('Elvaston25 painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('Elvaston25 estimated dark timber',(.025,.027,.026),.69)
 stone=ctx.material('Elvaston25 estimated threshold stone',(.52,.50,.45),.87)
 panel=ctx.material('Elvaston25 estimated lighter timber panels',(.065,.069,.065),.70)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA estimated shallow pitched roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei==0:
   count=3
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([.8,4.2]):
     hi=lo+2.05;door=ei==0 and k==0 and row==0
     if hi>min(rh(*A),rh(*B))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.15 if door else lo,2.7 if door else hi,door))
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
    bx(entry,c,.35,.05,w+.25,.9,.20,stone)
    for zz in [.6,1.35,2.1]:
     for ss in [c-.34,c+.34]:bx(entry,ss,-.365,zz,.52,.04,.54,panel)
    bx(entry,c+.51,-.33,1.25,.055,.08,.26,iron)
    bx(details,c,.10,2.9,w+.58,.35,.24,trimat)
    entrances.append({'name':'Estimated25 Elvaston Mews street entrance','threshold_xyz':p(c,0,.15),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.74),'door_leaf_depth_m':.4,'estimated':True,'stair_treads':1,'riser_m':.15,'tread_m':.3,'landing_depth_m':.8,'supporting_surface':'one estimated .15m riser; finite approach bottom-.05' })
  if ei==0:
   for zz in [3.6,7.02]:bx(details,ll/2,.025,zz,ll-.08,.20,.20,trimat)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'wall_height_m':7.6,'main_roof_m':9.85,'full_mapped_outline':True,'facade_confidence':'low: exact25not confirmed in licensedmewscontext'},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','elvaston-ignavy-entrance-2023'],'uncertainty':['Independent4corner25ElvastonMews house footprint and2OSMlevels; north/south/eastpartywalls blank;22not modified.','EA38insetpixels median9.368/p959.83255 support9.85m shallowraisedroof, eaves7.6 andhip/plateauformestimated. No equipment inferred.','Previously actuallyviewed2023CCBYSA2MrIgnavy mewsentrance photo usedonlyforlocalbuffbrick/paletrimcontext; target25notidentified. Windowcount,doorplacement,palette androofbreaks estimated.','Realwestwindow/doorapertures; hiddenpartyfaces no openings; finite.15m step.','Masterground/accesschecks remaincoordinator.']}
