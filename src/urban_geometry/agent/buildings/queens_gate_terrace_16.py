"""QGT16 House only: EA-informed layered roof, explicitly estimated residential elevation."""
import math
ROOF=[[(394.73281296144705, -166.89312454406172, 23.2), (388.3979369158624, -167.88323533628136, 23.2), (387.90484173478427, -164.7214544658498, 23.2)], [(387.90484173478427, -164.7214544658498, 23.2), (394.2481860185146, -163.73002012855702, 23.2), (394.73281296144705, -166.89312454406172, 23.2)], [(394.2481860185146, -163.73002012855702, 23.2), (387.90484173478427, -164.7214544658498, 23.2), (387.16519896316726, -159.97878316020245, 23.2)], [(387.16519896316726, -159.97878316020245, 23.2), (393.5212456041161, -158.98536350529994, 23.2), (394.2481860185146, -163.73002012855702, 23.2)], [(393.5212456041161, -158.98536350529994, 23.2), (387.16519896316726, -159.97878316020245, 23.2), (386.7029222309066, -157.01461359417286, 23.2)], [(386.7029222309066, -157.01461359417286, 23.2), (393.06690784511693, -156.01995311576428, 23.2), (393.5212456041161, -158.98536350529994, 23.2)], [(393.06690784511693, -156.01995311576428, 23.2), (386.7029222309066, -157.01461359417286, 23.2), (386.086553254559, -153.06238750613338, 23.2)], [(386.086553254559, -153.06238750613338, 23.2), (392.46112416645144, -152.0660725963834, 23.2), (393.06690784511693, -156.01995311576428, 23.2)], [(385.07508521713316, -146.5767425140366, 10.5), (391.4460029443726, -145.4404929280281, 10.5), (392.46112416645144, -152.0660725963834, 10.5)], [(392.46112416645144, -152.0660725963834, 10.5), (386.086553254559, -153.06238750613338, 10.5), (385.07508521713316, -146.5767425140366, 10.5)]]
STEP=[[(386.0865532578414, -153.06238750562036), (392.4611241367058, -152.0660726010325)]]
def build(ctx,feature):
 assert feature['id']=='way-809617871'
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[3],ring[0];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 23.2
 plaster=ctx.material('QGT16 pale stucco',(.73,.71,.65),.86)
 trimat=ctx.material('QGT16 pale dressings',(.79,.77,.71),.72)
 slate=ctx.material('QGT16 dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('QGT16 blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('QGT16 painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('QGT16 estimated dark timber',(.09,.045,.027),.69)
 stone=ctx.material('QGT16 estimated threshold stone',(.52,.50,.45),.87)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA layered continuous roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei in [3]:
   count=3 if ei==3 else 1
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([1.15,6.1,11.15,16.2]):
     hi=lo+3.2;door=ei==3 and k==1 and row==0
     if hi>(10.5 if ei==2 else min(rh(*A),rh(*B)))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.08 if door else lo,3.4 if door else hi,door))
  xs=[0,ll]+[xx for op in apertures for xx in op[:2]]
  # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
  va=-(A[0]-a[0])*uy+(A[1]-a[1])*ux;vb=-(B[0]-a[0])*uy+(B[1]-a[1])*ux
  if abs(vb-va)>1e-8:
   for cut in [3.2,8,11,15.0]:
    t=(cut-va)/(vb-va)
    if 0<t<1:xs.append(t*ll)
  xs=sorted(set(xs))
  for l,r in zip(xs,xs[1:]):
   vm=va+(vb-va)*(l+r)/(2*ll)
   localrh=lambda pt:10.5 if vm>15.0 else rh(*pt)
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
    entrances.append({'name':'EstimatedQGT16 House street entrance','threshold_xyz':p(c,0,.08),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.74),'door_leaf_depth_m':.4,'estimated':True,'supporting_surface':'finite authored threshold .08m; precise step/entrance arrangement unverified'})
  if ei==3:
   for zz in [5.1,10.1,15.2,21.5,23.03]:bx(details,ll/2,.025,zz,ll,.20,.20,trimat)
 for A,B in STEP:
  wall.face([(A[0],A[1],base+10.5),(B[0],B[1],base+10.5),(B[0],B[1],base+rh(*B)),(A[0],A[1],base+rh(*A))],plaster)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'main_roof_m':23.2,'rear_roof_m':10.5,'roof_break_depth_m':15.0,'osm_levels':4,'modeled_window_rows':4,'complete_mapped_outline':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','va-praefcke-aerial-a-2011'],'uncertainty':['Original4vertex complete residential footprint, OSM4levels honored as four window rows.','EA62inset samples median21.520/p9523.184. Main23.2m; northrear6–16m mixed simplified10.5m at estimated15m setback. Roof pitch/floor heights uncertain.','No target licensed street photo. Three-bay stucco and one south entrance are estimates; precise material colours and hidden rear windows unresolved. Shared sides blank, rear windows omitted.']}
