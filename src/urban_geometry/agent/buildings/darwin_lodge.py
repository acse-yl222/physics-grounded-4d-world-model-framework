"""Darwin west Lodge, photo-derived simplified CC BY-SA4.0 contribution; not surveyed."""
import math

def build(ctx,feature):
 stone=ctx.material('Darwin Lodge warm brick stone',(.55,.43,.30),.86)
 pale=ctx.material('Darwin Lodge pale stone courses',(.73,.69,.59),.82)
 slate=ctx.material('Darwin Lodge slate roofs',(.18,.22,.21),.75)
 glass=ctx.material('Darwin Lodge dark recessed glazing',(.04,.065,.058),.26)
 wood=ctx.material('Darwin Lodge timber door',(.13,.065,.028),.73)
 shell=ctx.mesh('Darwin Lodge mapped shell and true recessed apertures');roof=ctx.mesh('Darwin Lodge pitched roofs and campanile');trim=ctx.mesh('Darwin Lodge major stone frames and rose tracery')
 raw_face=shell.face
 def clean_face(points,mat):
  out=[]
  for q in points:
   if not out or math.dist(out[-1],q)>1e-8:out.append(q)
  if len(out)>2 and math.dist(out[0],out[-1])<1e-8:out.pop()
  if len(out)>2:raw_face(out,mat)
 shell.face=clean_face
 a=(579.822025736561,-436.50352396722883);L=math.hypot(7.9683806387475,1.3539654240012);tx,ty=7.9683806387475/L,1.3539654240012/L;nx,ny=-ty,tx;ang=math.atan2(ty,tx);base=float(feature.get('base_m',0))
 def P(u,v,z):return(a[0]+tx*u+nx*v,a[1]+ty*u+ny*v,base+z)
 def UV(q):return((q[0]-a[0])*tx+(q[1]-a[1])*ty,(q[0]-a[0])*nx+(q[1]-a[1])*ny)
 def B(u,v,z,w,d,h,mat=stone):
  x,y,zz=P(u,v,z);trim.box(x,y,zz,w,d,h,mat,ang)
 def wall(q0,q1,h,ops=(),bottom=0):
  length=math.dist(q0,q1);du,dv=(q1[0]-q0[0])/length,(q1[1]-q0[1])/length
  def Q(s,z,dep=0):return P(q0[0]+du*s-dv*dep,q0[1]+dv*s+du*dep,z)
  def cap(x):return min(h,5+5*(1-abs(x-length/2)/(length/2))) if bottom==5 and h==7.2 and length>6 else h
  xs={0.,length}
  if bottom==5 and h==7.2 and length>6:xs.update((length*.22,length*.78))
  for c,r,bot,spr,mat in ops:xs.update(c-r+2*r*j/32 for j in range(33))
  xs=sorted(xs)
  for lo,hi in zip(xs,xs[1:]):
   op=next((o for o in ops if o[0]-o[1]<(lo+hi)/2<o[0]+o[1]),None)
   if not op:shell.face([Q(lo,bottom),Q(hi,bottom),Q(hi,cap(hi)),Q(lo,cap(lo))],stone);continue
   c,r,bot,spr,mat=op;z0=spr+math.sqrt(max(0,r*r-(lo-c)**2));z1=spr+math.sqrt(max(0,r*r-(hi-c)**2));dep=.6 if mat==wood else .32
   if bot>bottom:shell.face([Q(lo,bottom),Q(hi,bottom),Q(hi,bot),Q(lo,bot)],stone)
   shell.face([Q(lo,z0),Q(hi,z1),Q(hi,cap(hi)),Q(lo,cap(lo))],stone)
   if mat is not None:shell.face([Q(lo,bot,dep),Q(hi,bot,dep),Q(hi,z1,dep),Q(lo,z0,dep)],mat)
   shell.face([Q(lo,z0),Q(hi,z1),Q(hi,z1,dep),Q(lo,z0,dep)],pale)
   trim.beam(Q(lo,z0,-.06),Q(hi,z1,-.06),.09,pale,8)
  for c,r,bot,spr,mat in ops:
   dep=.6 if mat==wood else .32
   for side in(-1,1):
    x=c+side*r;shell.face([Q(x,bot),Q(x,spr),Q(x,spr,dep),Q(x,bot,dep)],pale);trim.beam(Q(x,bot,-.06),Q(x,spr,-.06),.09,pale,8)
 r=feature['geometry'][0]['outer'];uv=[UV(q) for q in r];entries=[]
 for i,(aa,bb) in enumerate(zip(uv,uv[1:]+uv[:1])):
  length=math.dist(aa,bb);ops=[]
  if i==3:ops=[(length/2,.9,.015,2.4,wood)]
  else:
   for j in range(2 if length<10 else 3):ops.append(((j+.5)*length/(2 if length<10 else 3),.48,1.3,3.2,glass))
  wall(aa,bb,5,ops)
  if i==3:
   du,dv=(bb[0]-aa[0])/length,(bb[1]-aa[1])/length;threshold=P((aa[0]+bb[0])/2,(aa[1]+bb[1])/2,.015);entries.append({'id':'north_gable_door','threshold_xyz':list(threshold),'outward_normal':[tx*dv-nx*du,ty*dv-ny*du,0],'clear_width_m':1.8,'door_leaf_depth_m':.6,'support_z':base+.015,'basis':'Gable arch visible in2023; ground partly occluded; exact door and threshold estimated'})
 shell.surface(feature['geometry'],base,stone)
 # Long steep gabled slate roof. Use exact four mapped corners at the eaves.
 sw,se,ne,nw=r[1],r[2],r[3],r[0];southmid=((sw[0]+se[0])/2,(sw[1]+se[1])/2);northmid=((nw[0]+ne[0])/2,(nw[1]+ne[1])/2)
 roof.face([(*sw,base+5),(*southmid,base+10),(*northmid,base+10),(*nw,base+5)],slate);roof.face([(*southmid,base+10),(*se,base+5),(*ne,base+5),(*northmid,base+10)],slate)
 # Gable end upper windows have genuine round apertures, solid triangle above.
 for aa,bb in [(UV(sw),UV(se)),(UV(ne),UV(nw))]:
  ll=math.dist(aa,bb);wall(aa,bb,7.2,[(ll/2-1,.38,5.2,6.5,glass),(ll/2+1,.38,5.2,6.5,glass)],bottom=5)
  # Remaining gable shoulders and crown; inner gable plane overlaps no opening.
  x0,y0=aa;x1,y1=bb;mx,my=(x0+x1)/2,(y0+y1)/2
  shell.face([P(x0+(x1-x0)*.22,y0+(y1-y0)*.22,7.2),P(x1-(x1-x0)*.22,y1-(y1-y0)*.22,7.2),P(mx,my,10)],stone)
 # Two major west-facing dormers, inset round windows and closed side cheeks.
 for v in(5.,10.):
  wall((0,v+1),(0,v-1),7.5,[(1,.5,5.2,6.7,glass)],bottom=5)
  shell.face([P(0,v-1,7.5),P(0,v+1,7.5),P(0,v,8.5)],stone)
  for vv in(v-1,v+1):shell.face([P(0,vv,5),P(2,vv,5),P(2,vv,7.5),P(0,vv,7.5)],stone)
  for vv in(v-1,v+1):roof.face([P(0,vv,7.5),P(0,v,8.5),P(2,v,8.5),P(2,vv,7.5)],slate)
 # Prominent chimney is photo-evidenced; fine carved bands and animal finials omitted.
 B(4,7.4,10.7,2.5,1.0,7.4,stone);B(4,7.4,14.45,2.7,1.2,.25,pale)
 for u in(3.,3.5,4.,4.5,5.):
  x,y,z=P(u,7.4,14.55);trim.lathe(x,y,z,[(.15,0),(.15,.35)],pale,12)
 objects=[m.done() for m in(shell,roof,trim)]
 return {'created':[o.name for o in objects],'parameters':{'eaves_m':5,'main_roof_ridge_m':10,'chimney_top_m':14.9,'height_basis':'EA1m roof area approximately8–10m; chimney and facade dimensions photo-estimated; tree contamination near south edge'},'interfaces':{'entrances':entries},'evidence_source_ids':list(dict.fromkeys(feature.get('evidence_source_ids',[])+['darwin-lodge-noswansofine-2023','ea-lidar-composite-2022-tq27ne'])),'uncertainty':['Mapped rectangular footprint retained; Darwin modern building untouched.','Roof cross articulation and fine sculpture simplified; rear windows and threshold inferred.','Contribution derived from CC BY-SA4.0 photo; preserve attribution.','Glass is opaque exterior proxy; no photographic texture or hidden equipment.']}
