"""The Gore Hotel: evidence-limited moderate-detail envelope, explicit estimated facade."""
import math
ROOF=[[(502.988825081509, -0.36556545800385465, 28.6), (499.0428579066647, -1.0282228719443083, 23.8), (503.1308552393457, -22.160420082509518, 23.8)], [(502.988825081509, -0.36556545800385465, 28.6), (503.1308552393457, -22.160420082509518, 23.8), (507.0788327377151, -21.508154689339374, 28.6)], [(509.8942676374866, 0.7940850163919393, 28.6), (502.988825081509, -0.36556545800385465, 28.6), (507.0788327377151, -21.508154689339374, 28.6)], [(509.8942676374866, 0.7940850163919393, 28.6), (507.0788327377151, -21.508154689339374, 28.6), (513.9877933598617, -20.36669025129163, 28.6)], [(513.8402348123309, 1.4567424303323926, 25.400000000000002), (509.8942676374866, 0.7940850163919393, 28.6), (514.112179768621, -18.396594333462414, 28.202961620515342)], [(513.8402348123309, 1.4567424303323926, 25.400000000000002), (514.112179768621, -18.396594333462414, 28.202961620515342), (517.5687766219407, -17.817311444071677, 25.400000000000002)], [(514.2075862759957, -20.330377148464322, 28.421848697992985), (514.112179768621, -18.396594333462414, 28.202961620515342), (513.9877933598617, -20.36669025129163, 28.6)], [(513.9877933598617, -20.36669025129163, 28.6), (514.112179768621, -18.396594333462414, 28.202961620515342), (509.8942676374866, 0.7940850163919393, 28.6)], [(522.2779807262123, 2.8740082141011953, 25.400000000000002), (514.6204125924269, 1.5877598887309432, 25.400000000000002), (516.3383622682886, -4.035904133692383, 25.400000000000002)], [(522.2779807262123, 2.8740082141011953, 25.400000000000002), (516.3383622682886, -4.035904133692383, 25.400000000000002), (523.2434088403825, -2.8788824807852507, 25.400000000000002)], [(529.7071811569622, -5.057047649286687, 25.400000000000002), (516.8777530220104, -7.210805177688599, 25.400000000000002), (531.4576852355385, -15.489702106453475, 25.400000000000002)], [(531.4576852355385, -15.489702106453475, 25.400000000000002), (516.8777530220104, -7.210805177688599, 25.400000000000002), (517.5687766219407, -17.817311444071677, 25.400000000000002)], [(517.5687766219407, -17.817311444071677, 25.400000000000002), (516.8777530220104, -7.210805177688599, 25.400000000000002), (513.8402348123309, 1.4567424303323926, 25.400000000000002)], [(513.8402348123309, 1.4567424303323926, 25.400000000000002), (516.8777530220104, -7.210805177688599, 25.400000000000002), (516.3383622682886, -4.035904133692383, 25.400000000000002)], [(513.8402348123309, 1.4567424303323926, 25.400000000000002), (516.3383622682886, -4.035904133692383, 25.400000000000002), (514.6204125924269, 1.5877598887309432, 25.400000000000002)]]
SOURCES=['gore-noswan-adjacent-2023','ea-lidar-composite-2022-tq27ne']
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];origin=ring[0];tip=ring[1];length=math.dist(origin,tip);ux,uy=(tip[0]-origin[0])/length,(tip[1]-origin[1])/length;vx,vy=-uy,ux
 def eave(x,y):
  v=(x-origin[0])*vx+(y-origin[1])*vy
  return 23.8+4.8*max(0,min(1,v/4))-3.2*max(0,min(1,(v-11)/4))
 brick=ctx.material('Gore estimated red-brown brick',(.32,.13,.088),.86)
 stucco=ctx.material('Gore pale stucco and trim',(.78,.76,.68),.78)
 roofmat=ctx.material('Gore dark slate roof',(.105,.12,.135),.8)
 glass=ctx.material('Gore blue-grey glazing',(.115,.17,.19),.22,0,.28)
 iron=ctx.material('Gore black painted iron',(.022,.025,.025),.43,.70)
 timber=ctx.material('Gore dark timber door',(.09,.045,.023),.65)
 stone=ctx.material('Gore estimated stone approach',(.52,.49,.44),.86)
 wall=ctx.mesh('complete mapped envelope with recessed apertures');windows=ctx.mesh('sash glazing and pale surrounds');details=ctx.mesh('estimated stucco bands pilasters and portico');roof=ctx.mesh('EA informed closed roof with lower rear');entry=ctx.mesh('estimated hotel entrance and finite steps')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],roofmat)
 def face(m,vs,mat):
  for i in range(1,len(vs)-1):
   a,b,c=vs[0],vs[i],vs[i+1];u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
   if sum((u[(k+1)%3]*v[(k+2)%3]-u[(k+2)%3]*v[(k+1)%3])**2 for k in range(3))>1e-12:m.face([a,b,c],mat)
 entrances=[]
 for ei,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
  L=math.dist(a,b);tx,ty=(b[0]-a[0])/L,(b[1]-a[1])/L;nx,ny=ty,-tx;angle=math.atan2(ty,tx)
  def pos(s,d,z):return(a[0]+tx*s+nx*d,a[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,h,mat):m.box(*pos(s,d,z),w,dep,h,mat,angle)
  def quad(s0,s1,z0,z1,mat):face(wall,[pos(s0,0,z0),pos(s1,0,z0),pos(s1,0,z1),pos(s0,0,z1)],mat)
  n=max(1,int(L/3.6));pitch=L/n;openings=[]
  # Street front rhythm is estimated from partially obscured licensed context image.
  for j in range(n):
   s=(j+.5)*pitch;w=min(1.50,pitch*.50)
   for row,z in enumerate([1.0,5.2,9.4,13.6,17.8]):
    h=2.6 if row<4 else 2.25
    if z+h>eave(*pos(s,0,0)[:2])-.25:continue
    door=ei==0 and j==n//2 and row==0
    ww=2.05 if door else w;lo=.60 if door else z;hi=3.5 if door else z+h
    openings.append((s-ww/2,s+ww/2,lo,hi,door));d=-.40 if door else -.24
    bx(entry if door else windows,s,d,(lo+hi)/2,ww,.08,hi-lo,timber if door else glass)
    for side in [-1,1]:
     bx(windows,s+side*(ww/2+.06),.02,(lo+hi)/2,.12,.20,hi-lo+.18,stucco)
     face(wall,[pos(s+side*ww/2,0,lo),pos(s+side*ww/2,d,lo),pos(s+side*ww/2,d,hi),pos(s+side*ww/2,0,hi)],stucco if row==0 else brick)
    bx(windows,s,.06,hi+.1,ww+.26,.30,.18,stucco)
    bx(windows,s,d+.06,(lo+hi)/2,.05,.06,hi-lo,stucco if not door else timber)
    if not door:
     bx(windows,s,.08,lo-.08,ww+.30,.32,.15,stucco);bx(windows,s,d+.06,(lo+hi)/2,ww,.06,.05,stucco)
    if ei==0 and row in [1,2]:
     bx(details,s,.14,hi+.37,ww+.60,.42,.16,stucco)
     if row==1:
      face(details,[pos(s-ww*.65,.16,hi+.46),pos(s+ww*.65,.16,hi+.46),pos(s,.16,hi+1.03)],stucco)
    if door:
     es=s
     # Four low steps, measured geometry but estimated real dimensions/location.
     for k in range(4):
      hh=(k+1)*.15;dd=1.78-k*.32
      bx(entry,s,dd-.16,hh/2,2.65,.32,hh,stone)
     bx(entry,s,.36,.30,2.65,.92,.60,stone)
     for side in [-1,1]:
      bx(details,s+side*1.50,.27,2.45,.42,.60,3.65,stucco)
      bx(details,s+side*1.50,.27,4.28,.66,.80,.23,stucco)
      for dd,hh in [(1.7,.95),(.72,1.5),(.05,1.5)]:bx(entry,s+side*1.20,dd,hh-.40,.04,.04,.8,iron)
      entry.beam(pos(s+side*1.2,1.7,.95),pos(s+side*1.2,.72,1.5),.032,iron,n=8)
      entry.beam(pos(s+side*1.2,.72,1.5),pos(s+side*1.2,.05,1.5),.032,iron,n=8)
     bx(details,s,.30,4.49,3.7,1.0,.25,stucco)
     for side in [-1,1]:entrances.append({'name':'Estimated Queen Gate hotel entrance leaf '+str(side),'threshold_xyz':pos(s+side*.5125,0,.6),'outward_normal':[nx,ny,0],'door_leaf_xyz':pos(s+side*.5125,-.4,2.05),'clear_width_m':.93,'door_leaf_depth_m':.44,'stair_treads':4,'riser_m':.15,'tread_m':.32,'landing_depth_m':.92,'landing_z_m':.60,'supporting_surface':'finite estimated stair flight and landing; coordinator paving review pending','estimated':True})
  # Segment wall at every opening and at rear roof slope changes.
  cuts=[0,L]+[x for q in openings for x in q[:2]]
  va=(a[0]-origin[0])*vx+(a[1]-origin[1])*vy;dv=tx*vx+ty*vy
  if abs(dv)>1e-8:
   cuts +=[(z-va)/dv for z in [4,11,15] if 0<(z-va)/dv<L]
  cuts=sorted(set(cuts))
  for s0,s1 in zip(cuts,cuts[1:]):
   sm=(s0+s1)/2;holes=sorted([(q[2],q[3]) for q in openings if q[0]<sm<q[1]]);zz=0
   def panel(z0,z1):
    for aa,bb,mat in [(z0,min(z1,4.8),stucco),(max(z0,4.8),z1,brick)]:
     if bb>aa:quad(s0,s1,aa,bb,mat)
   for lo,hi in holes:
    if lo>zz:panel(zz,lo)
    zz=max(zz,hi)
   if zz<4.8:panel(zz,4.8);zz=4.8
   h0=eave(*pos(s0,0,0)[:2]);h1=eave(*pos(s1,0,0)[:2]);face(wall,[pos(s0,0,zz),pos(s1,0,zz),pos(s1,0,h1),pos(s0,0,h0)],brick)
  for z in [.40,4.45,8.6,12.8,17.05,22.5]:
   if z+.1>min(eave(*a),eave(*b)):continue
   spans=[(0,L)]
   if ei==0 and z<3.6:spans=[(0,es-1.35),(es+1.35,L)]
   for aa,bb in spans:
    if bb>aa:bx(details,(aa+bb)/2,.10,z,bb-aa,.30,.22,stucco)
  if ei==0:
   for j in range(n):
    s=(j+.5)*pitch;bx(roof,s,-.55,24.6,1.8,1.0,2.05,stucco);bx(windows,s,-.01,24.6,1.4,.08,1.60,glass);bx(windows,s,.04,24.6,.06,.06,1.62,stucco);bx(roof,s,-.55,25.68,2.0,1.22,.15,roofmat)
 # Small capped chimneys, approximate positions and height; no speculative plant.
 for x,y in [(506,-17),(504,-3),(521,-12)]:
  z=eave(x,y)-.3;roof.box(x,y,base+z,.8,1.4,2.5,brick);roof.box(x,y,base+z+1.30,1.0,1.6,.15,stucco)
 objs=[m.done() for m in [wall,windows,details,roof,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'street_eaves_m':23.8,'main_roof_m':28.6,'rear_roof_m':25.4,'mapped_outline_preserved':True,'evidence_level':'partial_photo_plus_native1m_lidar'},'interfaces':{'entrances':entrances},'evidence_source_ids':SOURCES,'uncertainty':['Photograph heavily obscures target at frame edge; facade and entrance are an explicitly estimated completion, not a fully source-reconstructed elevation.','Exact ridge topology, rear windows, dormer count, entry dimensions and four-step stair arrangement estimated.','No neighbour merged. PBR colours and optical parameters visually estimated.']}
