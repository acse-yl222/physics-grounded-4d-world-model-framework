"""197 independent house, mapped porch kept low; inspected2023front and EA roof interpretation."""
import math
MAIN=[[489.507156593143, 56.137839771807194], [504.19049711176194, 58.329609266482294], [503.5695357545046, 62.35874855518341], [512.4743628908182, 63.73761442210525], [513.1130679097259, 59.608946373686194], [519.1613378110342, 60.45456324145198], [517.901655337424, 68.61236847564578], [488.29944415867794, 64.03041686862707], [488.8148337297607, 60.57621786557138]]
PORCH=[[488.29944415867794, 64.03041686862707], [486.4478694855934, 63.747474977746606], [486.98407555778977, 60.29407836031169], [488.8148337297607, 60.57621786557138]]
ROOF=[[[491.4389251141995, 64.51635860191504, 26.19999999999996], [488.8148337297607, 60.57621786557138, 21.0], [488.29944415867794, 64.03041686862707, 21.03759567412876]], [[488.8148337297607, 60.57621786557138, 21.0], [491.4389251141995, 64.51635860191504, 26.19999999999996], [492.67215962426786, 56.61027702716999, 26.19999999999997]], [[488.8148337297607, 60.57621786557138, 21.0], [492.67215962426786, 56.61027702716999, 26.19999999999997], [489.507156593143, 56.137839771807194, 21.0]], [[492.67215962426786, 56.61027702716999, 26.19999999999997], [491.4389251141995, 64.51635860191504, 26.19999999999996], [498.158907193995, 65.55650497826963, 26.199999999999996]], [[498.158907193995, 65.55650497826963, 26.199999999999996], [499.3977910654082, 57.61420619481595, 26.2], [492.67215962426786, 56.61027702716999, 26.19999999999997]], [[503.5695357545046, 62.35874855518341, 23.20723184082837], [504.19049711176194, 58.329609266482294, 23.21181752272235], [499.3977910654082, 57.61420619481595, 26.2]], [[503.5695357545046, 62.35874855518341, 23.20723184082837], [498.158907193995, 65.55650497826963, 26.199999999999996], [504.08830314675566, 66.47428119270015, 22.500000000000018]], [[504.08830314675566, 66.47428119270015, 22.500000000000018], [504.7028922053471, 62.534242868683286, 22.500000000000007], [503.5695357545046, 62.35874855518341, 23.20723184082837]], [[498.158907193995, 65.55650497826963, 26.199999999999996], [503.5695357545046, 62.35874855518341, 23.20723184082837], [499.3977910654082, 57.61420619481595, 26.2]], [[504.7028922053471, 62.534242868683286, 22.500000000000007], [504.08830314675566, 66.47428119270015, 22.500000000000018], [509.02946644072296, 67.23909470472557, 22.5]], [[509.02946644072296, 67.23909470472557, 22.5], [509.6440098441372, 63.29934906920563, 22.49999999999997], [504.7028922053471, 62.534242868683286, 22.500000000000007]], [[512.4743628908182, 63.73761442210525, 15.339795432966996], [509.6440098441372, 63.29934906920563, 22.49999999999997], [509.02946644072296, 67.23909470472557, 22.5]], [[512.4743628908182, 63.73761442210525, 15.339795432966996], [514.2433794149507, 59.76697676754164, 12.5], [513.1130679097259, 59.608946373686194, 15.352905773566006]], [[512.4743628908182, 63.73761442210525, 15.339795432966996], [509.02946644072296, 67.23909470472557, 22.5], [512.9823970758968, 67.85094551434591, 12.500000000000018]], [[514.2433794149507, 59.76697676754164, 12.5], [512.4743628908182, 63.73761442210525, 15.339795432966996], [512.9823970758968, 67.85094551434591, 12.500000000000018]], [[517.901655337424, 68.61236847564578, 12.5], [519.1613378110342, 60.45456324145198, 12.5], [514.2433794149507, 59.76697676754164, 12.5]], [[514.2433794149507, 59.76697676754164, 12.5], [512.9823970758968, 67.85094551434591, 12.500000000000018], [517.901655337424, 68.61236847564578, 12.5]]]
def build(ctx,feature):
 base=float(feature.get('base_m',0));a=PORCH[-1];b=MAIN[0];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 21.+5.2*max(0,min(1,v/3.2))-3.7*max(0,min(1,(v-10)/6))-10.*max(0,min(1,(v-21)/4))
 stone=ctx.material('197 pale painted stucco',(.76,.74,.67),.82)
 trimat=ctx.material('197 pale stone details',(.82,.80,.74),.73)
 slate=ctx.material('197 estimated slate roof',(.115,.135,.15),.82)
 glass=ctx.material('197 recessed glass',(.11,.17,.19),.21,0,.28)
 iron=ctx.material('197 black painted iron',(.024,.028,.027),.46,.65)
 wood=ctx.material('197 dark painted timber',(.035,.048,.040),.68)
 panel=ctx.material('197 timber panel relief',(.075,.092,.072),.68)
 wall=ctx.mesh('mapped house body with real openings');roof=ctx.mesh('EA stepped roof and low mapped porch');detail=ctx.mesh('sashes cornices and simplified balustrades');entry=ctx.mesh('recessed panel door finite steps and columns')
 def face(m,ps,mat):
  q=[]
  for v in ps:
   if not q or math.dist(v,q[-1])>1e-7:q.append(v)
  for j in range(1,len(q)-1):
   v,w=[q[j][k]-q[0][k] for k in range(3)],[q[j+1][k]-q[0][k] for k in range(3)]
   if sum((v[(k+1)%3]*w[(k+2)%3]-v[(k+2)%3]*w[(k+1)%3])**2 for k in range(3))>1e-12:m.face([q[0],q[j],q[j+1]],mat)
 for tr in ROOF:face(roof,[(x,y,base+z) for x,y,z in tr],slate)
 face(roof,[(x,y,base+5.0) for x,y in PORCH],slate)
 roof.surface(feature['geometry'],base,stone)
 entries=[]
 for part,ring in enumerate([MAIN,PORCH]):
  signed=sum(A[0]*B[1]-B[0]*A[1] for A,B in zip(ring,ring[1:]+ring[:1]));sg=1 if signed>0 else -1
  for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
   if part==1 and ei==3:continue # interior shared porch back already belongs to main wall
   ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty*sg,-tx*sg;ang=math.atan2(ty,tx)
   def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
   def box(m,s,d,z,w,dep,h,mat):m.box(*p(s,d,z),w,dep,h,mat,ang)
   def top(s):return 5.0 if part else rh(*p(s,0,0)[:2])
   front=part==0 and ei in [7,8];doorfront=part==1 and ei==1
   aps=[]
   if front or (part==0 and ei in [1,2,3,5]):
    count=(1 if ei==7 else 2) if front else max(1,int(ll/3.1))
    for j in range(count):
     c=ll*(j+.5)/count
     for lo,hi in [(1.25,4.25),(5.75,9.0),(10.7,13.6),(15.2,17.7),(18.7,20.2)]:
      if front and ei==7 and lo<5:continue
      if hi>min(top(c-.65),top(c+.65))-.25:continue
      aps.append((c-.65,c+.65,lo,hi,False))
   if doorfront:aps.append((ll/2-.85,ll/2+.85,.3,4.25,True))
   cuts=[0,ll]+[x for ap in aps for x in ap[:2]]
   if not part:
    va=-(A[0]-a[0])*uy+(A[1]-a[1])*ux;vb=-(B[0]-a[0])*uy+(B[1]-a[1])*ux
    if abs(vb-va)>1e-8:
     for v in [3.2,10,16,21,25]:
      t=(v-va)/(vb-va)
      if 0<t<1:cuts.append(t*ll)
   cuts=sorted(set(cuts))
   for l,r in zip(cuts,cuts[1:]):
    if r-l<1e-6:continue
    zz=0
    for lo,hi in sorted((ap[2],ap[3]) for ap in aps if ap[0]<(l+r)/2<ap[1]):
     if lo>zz:face(wall,[p(l,0,zz),p(r,0,zz),p(r,0,lo),p(l,0,lo)],stone)
     zz=hi
    face(wall,[p(l,0,zz),p(r,0,zz),p(r,0,top(r)),p(l,0,top(l))],stone)
   for l,r,lo,hi,isdoor in aps:
    c=(l+r)/2;w=r-l;depth=.55 if isdoor else .24
    box(entry if isdoor else detail,c,-depth,(lo+hi)/2,w,.08,hi-lo,wood if isdoor else glass)
    for ss in [l,r]:face(wall,[p(ss,0,lo),p(ss,-depth,lo),p(ss,-depth,hi),p(ss,0,hi)],trimat)
    for z in [lo,hi]:face(wall,[p(l,0,z),p(r,0,z),p(r,-depth,z),p(l,-depth,z)],trimat)
    for ss in [l-.06,r+.06]:box(detail,ss,.015,(lo+hi)/2,.12,.18,hi-lo+.18,trimat)
    box(detail,c,.04,hi+.1,w+.30,.27,.20,trimat)
    if not isdoor:
     box(detail,c,.065,lo-.09,w+.32,.30,.18,trimat)
     box(detail,c,-depth+.07,(lo+hi)/2,.05,.06,hi-lo,trimat)
     box(detail,c,-depth+.07,(lo+hi)/2,w,.06,.055,trimat)
     if front and lo>5 and lo<14:
      box(detail,c,.12,hi+.35,w+.50,.35,.18,trimat)
    else:
     for z in [.85,1.85,3.05]:
      for ss in [c-.37,c+.37]:box(entry,ss,-.48,z,.57,.045,.68,panel)
     box(entry,c+.60,-.43,1.45,.06,.08,.28,iron)
     # Two low estimated risers and a continuous landing; bases reach-.05.
     for d,wid,zt in [(.45,.9,.3),(1.05,.3,.15)]:box(entry,c,d,(zt-.05)/2,2.35,wid,zt+.05,trimat)
     for ss in [l-.31,r+.31]:
      x,y,z=p(ss,.22,-.05)
      entry.lathe(x,y,z,[(.19,0),(.19,.22),(.14,.32),(.13,4.32),(.22,4.38),(.22,4.54)],trimat,16)
     box(detail,c,.18,4.63,2.6,.64,.28,trimat)
     entries.append({'name':'197 mapped west porch entrance','threshold_xyz':list(p(c,0,.3)),'outward_normal':[nx,ny,0],'clear_width_m':1.5,'door_leaf_xyz':list(p(c,-.55,2.2)),'door_leaf_depth_m':.51,'stair_treads':2,'riser_m':.15,'tread_m':.3,'landing_depth_m':.9,'estimated':True,'supporting_surface':'finite two-step approach bottom-.05; final paving review pending'})
   if front:
    for z in [4.8,9.9,14.45,18.3,20.85]:box(detail,ll/2,.05,z,ll-.04,.24,.23,trimat)
    # Upper two window-level balcony projections; mapped ground porch remains low.
    for c in ([ll/2] if ei==7 else [ll/4,ll*3/4]):
     for z in [5.25,10.25]:
      box(detail,c,.36,z,2.25,.8,.14,trimat)
      box(detail,c,.70,z+.75,2.25,.10,.12,trimat)
      for j in range(10):
       x,y,zz=p(c-1.02+2.04*j/9,.70,z+.08)
       detail.lathe(x,y,zz,[(.06,0),(.045,.12),(.075,.24),(.045,.50),(.06,.61)],trimat,8)
   if part==1 and ei in [0,1,2]:
    box(detail,ll/2,.03,5.08,ll,.18,.16,trimat);box(detail,ll/2,.03,5.80,ll,.12,.14,trimat)
    for j in range(max(3,int(ll/.24))):
     s=(j+.5)*ll/max(3,int(ll/.24));x,y,z=p(s,.03,5.16)
     detail.lathe(x,y,z,[(.06,0),(.04,.12),(.07,.25),(.04,.45),(.06,.56)],trimat,8)
 obs=[m.done() for m in [wall,roof,detail,entry]]
 return {'created':[x.name for x in obs if x],'parameters':{'front_eaves_m':21,'main_roof_m':26.2,'middle_roof_m':22.5,'rear_roof_m':12.5,'porch_roof_m':5,'mapped_outline_preserved':True},'interfaces':{'entrances':entries},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','stevens-noswan-queensgate-2023','va-praefcke-aerial-a-2011'],'uncertainty':['197 is the first pale house beside red-brick196 in the inspected197–200photo; remaining terrace is not modelled here.','Window dimensions,upper obscured row,roof planes and levels are estimates informed by EA1m; no measured survey.','Mapped protrusion interpreted as low columned porch. Upper floor returns behind it; rear notch preserved.','Back windows estimated,196andStevensparty walls blank. Fine Ionic carving,basement excavation and ironwork curls omitted.','PBR numerical values estimated; constant factors retained in export. Full-scene ground and cross-building checks await coordinator.']}
