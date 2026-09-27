"""17 Queen's Gate Terrace: parent/linked part remain separate inventory footprints."""
import math

def build(ctx,feature):
 fid=feature['id'];assert fid in ('way-213454223','way-809947759')
 main=fid=='way-809947759';base=float(feature.get('base_m',0))
 plaster=ctx.material('QGT17 estimated pale stucco',(.73,.71,.65),.86)
 trim=ctx.material('QGT17 estimated stone dressings',(.79,.77,.71),.72)
 slate=ctx.material('QGT17 estimated dark roof',(.12,.14,.15),.84)
 glass=ctx.material('QGT17 estimated glass',(.14,.20,.22),.2,0,.28)
 timber=ctx.material('QGT17 estimated timber door',(.09,.045,.027),.69)
 stone=ctx.material('QGT17 estimated threshold',(.52,.50,.45),.87)
 wall=ctx.mesh('mapped envelope with real apertures');roof=ctx.mesh('EA height roof');win=ctx.mesh('estimated sash frames');detail=ctx.mesh('estimated cornice');entry=ctx.mesh('front porch door and approach')
 entrances=[]
 for pi,part in enumerate(feature['geometry']):
  ring=part['outer'];height=24.9 if main else (4.0 if pi==0 else 10.5)
  roof.surface([part],base+height,slate);roof.surface([part],base,plaster)
  for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
   ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
   def p(s,d,z):return (A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
   def bx(m,s,d,z,w,dep,h,mat):m.box(*p(s,d,z),w,dep,h,mat,math.atan2(ty,tx))
   # Main front behind porch starts above its roof. All other shared edges blank.
   zmin=4.0 if main and ei==7 else (10.5 if main and ei in [1,2] else 0)
   if not main and ((pi==0 and ei==1) or (pi==1 and ei in [1,2,3])):continue
   aps=[]
   if main and ei in [6,7]:
    for k in range(2 if ei==6 else 1):
     c=ll*(k+.5)/(2 if ei==6 else 1)
     for row,lo in enumerate([1.0,5.25,9.55,13.85,18.15]):
      if lo<zmin:continue
      aps.append((c-.60,c+.60,lo,lo+2.65,False))
   elif main and ei==4:
    for lo in [11.3,15.5,19.7]:aps.append((ll/2-.52,ll/2+.52,lo,lo+2.1,False))
   elif not main and pi==0 and ei==3:
    aps=[(ll/2-.79,ll/2+.79,.45,3.25,True)]
   elif not main and pi==1 and ei==4:
    for k in range(2):
     for lo in [1.2,4.5,7.7]:
      c=ll*(k+.5)/2;aps.append((c-.55,c+.55,lo,lo+1.8,False))
   xs=sorted(set([0,ll]+[q for op in aps for q in op[:2]]))
   for l,r in zip(xs,xs[1:]):
    z=zmin
    for op in sorted([op for op in aps if op[0]<(l+r)/2<op[1]],key=lambda q:q[2]):
     if op[2]>z:wall.face([p(l,0,z),p(r,0,z),p(r,0,op[2]),p(l,0,op[2])],plaster)
     z=op[3]
    if height>z:wall.face([p(l,0,z),p(r,0,z),p(r,0,height),p(l,0,height)],plaster)
   for l,r,lo,hi,door in aps:
    c=(l+r)/2;w=r-l;d=.43 if door else .22
    bx(entry if door else win,c,-d,(lo+hi)/2,w,.06,hi-lo,timber if door else glass)
    for ss in [l,r]:wall.face([p(ss,0,lo),p(ss,-d,lo),p(ss,-d,hi),p(ss,0,hi)],trim)
    for zz in [lo,hi]:wall.face([p(l,0,zz),p(r,0,zz),p(r,-d,zz),p(l,-d,zz)],trim)
    for ss in [l-.055,r+.055]:bx(win,ss,.005,(lo+hi)/2,.11,.16,hi-lo+.14,trim)
    bx(win,c,.035,hi+.08,w+.26,.24,.16,trim)
    if not door:
     bx(win,c,.04,lo-.07,w+.28,.26,.14,trim);bx(win,c,-d+.05,(lo+hi)/2,.045,.05,hi-lo,trim);bx(win,c,-d+.05,(lo+hi)/2,w,.05,.05,trim)
    else:
     bx(entry,c,.31,.225,w+.25,.94,.45,stone)
     bx(entry,c,.93,.15,w+.25,.30,.30,stone);bx(entry,c,1.23,.075,w+.25,.30,.15,stone)
     for ss in [l-.24,r+.24]:bx(detail,ss,.10,1.75,.20,.25,3.5,trim)
     entrances.append({'name':'17 Terrace estimated porch entrance','threshold_xyz':p(c,0,.45),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.85),'door_leaf_depth_m':.4,'estimated':True,'supporting_surface':'authored landing .45m and three .15m rises'})
   if (main and ei in [6,7]) or (not main and pi==0 and ei==3):
    for z in ([4.65,8.95,13.25,17.55,22.8,24.25] if main else [3.83]):bx(detail,ll/2,.02,z,ll,.18,.18,trim)
 obs=[m.done() for m in [wall,roof,win,detail,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'main_roof_m':24.9,'rear_annexe_m':10.5,'porch_m':4.0,'full_inventory_footprint':True,'inventory_id':fid},'interfaces':{'entrances':entrances},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','va-praefcke-aerial-a-2011'],'uncertainty':['OSM explicitly links part809947759 with parent213454223; module branches preserve both original geometries.','EA native1m whole footprint72inset samples median23.644/p9524.929; main24.9 rear10.5; flat roof simplified, small pitch unverified.','No licensed target facade photograph. Three-bay five-level stucco, sash count, materials, porch4m, door and three steps are editable low-confidence estimates, not measured survey.','Party walls blank; rear exposed apertures estimated. No interior or fine sculptural detail.']}
