"""QGT26to28 House only: EA-informed layered roof, explicitly estimated residential elevation."""
import math
ROOF=[[(361.7036384031756, -168.7814482717742, 22.8), (348.7976776206633, -174.01863595005125, 22.8), (348.28576852975254, -170.859767636391, 22.8)], [(348.7976776206633, -174.01863595005125, 22.8), (361.7036384031756, -168.7814482717742, 22.8), (362.1935369936982, -171.9437258336693, 22.8)], [(360.96879051739165, -164.0380319289315, 22.8), (348.28576852975254, -170.859767636391, 22.8), (347.51790489338634, -166.12146516590062, 22.8)], [(348.28576852975254, -170.859767636391, 22.8), (360.96879051739165, -164.0380319289315, 22.8), (361.7036384031756, -168.7814482717742, 22.8)], [(360.5095105887767, -161.07339671465485, 22.8), (347.51790489338634, -166.12146516590062, 22.8), (347.03799012065747, -163.16002612184414, 22.8)], [(347.51790489338634, -166.12146516590062, 22.8), (360.5095105887767, -161.07339671465485, 22.8), (360.96879051739165, -164.0380319289315, 22.8)], [(353.7652145450702, -159.36316272988915, 22.8), (347.03799012065747, -163.16002612184414, 22.8), (346.2381321661094, -158.22429438174998, 22.8)], [(346.2381321661094, -158.22429438174998, 22.8), (353.4156904031808, -157.1125487458561, 22.8), (353.7652145450702, -159.36316272988915, 22.8)], [(355.4234251283342, -159.10999320540577, 22.8), (355.0740956542908, -156.8556752048039, 22.8), (359.74404404108515, -156.1323380241937, 22.8)], [(347.03799012065747, -163.16002612184414, 22.8), (353.7652145450702, -159.36316272988915, 22.8), (360.5095105887767, -161.07339671465485, 22.8)], [(355.4234251283342, -159.10999320540577, 22.8), (359.74404404108515, -156.1323380241937, 22.8), (360.5095105887767, -161.07339671465485, 22.8)], [(360.5095105887767, -161.07339671465485, 22.8), (353.7652145450702, -159.36316272988915, 22.8), (355.4234251283342, -159.10999320540577, 22.8)], [(355.76007745822426, -151.79258928447962, 8.0), (354.7030393736204, -151.9557917546481, 8.0), (354.3143543273909, -149.44316292274743, 8.0)], [(355.76007745822426, -151.79258928447962, 8.0), (358.6045317512471, -148.77682768926024, 8.0), (359.74404404108515, -156.1323380241937, 8.0)], [(356.1297445440432, -154.17233295179904, 8.0), (355.0740956542908, -156.8556752048039, 8.0), (354.69274435867555, -154.39471169002354, 8.0)], [(358.6045317512471, -148.77682768926024, 8.0), (355.76007745822426, -151.79258928447962, 8.0), (354.3143543273909, -149.44316292274743, 8.0)], [(355.0740956542908, -156.8556752048039, 8.0), (356.1297445440432, -154.17233295179904, 8.0), (359.74404404108515, -156.1323380241937, 8.0)], [(356.1297445440432, -154.17233295179904, 8.0), (355.76007745822426, -151.79258928447962, 8.0), (359.74404404108515, -156.1323380241937, 8.0)], [(346.2381321661094, -158.22429438174998, 8.0), (351.70416840573307, -146.09192132763565, 8.0), (353.4156904031808, -157.1125487458561, 8.0)], [(351.70416840573307, -146.09192132763565, 8.0), (346.2381321661094, -158.22429438174998, 8.0), (344.4580065240152, -147.23956567700952, 8.0)]]
STEP=[[(346.23813223515896, -158.22429437105478), (353.41569039922643, -157.11254874646858)], [(355.07409565494953, -156.85567520470187), (359.7440440408184, -156.13233802423503)]]
def build(ctx,feature):
 assert feature['id']=='way-809617876'
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[11],ring[0];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 22.8
 plaster=ctx.material('QGT26to28 pale stucco',(.73,.71,.65),.86)
 trimat=ctx.material('QGT26to28 pale dressings',(.79,.77,.71),.72)
 slate=ctx.material('QGT26to28 dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('QGT26to28 blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('QGT26to28 painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('QGT26to28 estimated dark timber',(.09,.045,.027),.69)
 stone=ctx.material('QGT26to28 estimated threshold stone',(.52,.50,.45),.87)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA layered continuous roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei in [11]:
   count=6 if ei==11 else 1
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([1.05,5.45,9.85,14.25,18.65]):
     hi=lo+(2.8 if row<3 else 2.5);door=ei==11 and k==2 and row==0
     if hi>(8.0 if ei==2 else min(rh(*A),rh(*B)))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.08 if door else lo,3.4 if door else hi,door))
  xs=[0,ll]+[xx for op in apertures for xx in op[:2]]
  # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
  va=-(A[0]-a[0])*uy+(A[1]-a[1])*ux;vb=-(B[0]-a[0])*uy+(B[1]-a[1])*ux
  if abs(vb-va)>1e-8:
   for cut in [3.2,8,11,16.0]:
    t=(cut-va)/(vb-va)
    if 0<t<1:xs.append(t*ll)
  xs=sorted(set(xs))
  for l,r in zip(xs,xs[1:]):
   vm=va+(vb-va)*(l+r)/(2*ll)
   localrh=lambda pt:8.0 if vm>16.0 else rh(*pt)
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
    entrances.append({'name':'EstimatedQGT26to28 House street entrance','threshold_xyz':p(c,0,.08),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.74),'door_leaf_depth_m':.4,'estimated':True,'supporting_surface':'finite authored threshold .08m; precise step/entrance arrangement unverified'})
  if ei==11:
   for zz in [4.65,9.05,13.45,17.85,21.85,22.65]:bx(details,ll/2,.025,zz,ll,.20,.20,trimat)
 for A,B in STEP:
  wall.face([(A[0],A[1],base+8.0),(B[0],B[1],base+8.0),(B[0],B[1],base+rh(*B)),(A[0],A[1],base+rh(*A))],plaster)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'main_roof_m':22.8,'rear_roof_m':8.0,'roof_break_depth_m':16.0,'complete_mapped_outline':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','va-praefcke-aerial-a-2011'],'uncertainty':['26–28 is one mapped residential footprint, not two invented separate houses.','EA185inset samples median21.368/p9522.856. Main22.8m; rear mixed6–14m simplified to8m at estimated16m setback; edge height uncertain.','No target licensed street facade. Six-bay five-level stucco, sash pattern and single offset south door are explicit estimates; no second unseen entrance invented.','All exact material colours estimated, constant PBR exported. Shared sides blank; rear fenestration unresolved and omitted.']}
