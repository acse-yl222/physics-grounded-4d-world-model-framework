"""Oriel House only: low red-brick annexe, evidence-limited street rhythm and saltbox roof."""
import math
ROOF=[[(793.847931487946, 25.25059709079139, 8.1), (792.0167771852575, 24.43868111167103, 5.8), (792.8538812190426, 23.15349803421037, 5.984)], [(793.847931487946, 25.25059709079139, 8.1), (792.8538812190426, 23.15349803421037, 5.984), (794.3406651906371, 23.91400669412817, 7.9045)], [(793.847931487946, 25.25059709079139, 8.1), (794.3406651906371, 23.91400669412817, 7.9045), (794.9508936961998, 22.721018357639245, 7.9045)], [(793.847931487946, 25.25059709079139, 8.1), (794.9508936961998, 22.721018357639245, 7.9045), (795.8403230676827, 20.98219616785775, 7.9045)], [(793.847931487946, 25.25059709079139, 8.1), (795.8403230676827, 20.98219616785775, 7.9045), (796.4505515732455, 19.789207831368827, 7.9045)], [(793.847931487946, 25.25059709079139, 8.1), (796.4505515732455, 19.789207831368827, 7.9045), (798.9693443088116, 15.238305455868883, 8.1)], [(798.9693443088116, 15.238305455868883, 8.1), (796.4505515732455, 19.789207831368827, 7.9045), (797.3399809447284, 18.050385641587333, 7.9045)], [(798.9693443088116, 15.238305455868883, 8.1), (797.3399809447284, 18.050385641587333, 7.9045), (797.9502094502911, 16.85739730509841, 7.9045)], [(798.9693443088116, 15.238305455868883, 8.1), (797.9502094502911, 16.85739730509841, 7.9045), (797.0156367754098, 14.6659793574363, 5.8)], [(797.0156367754098, 14.6659793574363, 5.8), (797.9502094502911, 16.85739730509841, 7.9045), (796.4634254786966, 16.09688864518061, 5.984)], [(797.0156367754098, 14.6659793574363, 5.8), (796.4634254786966, 16.09688864518061, 5.984), (795.8531969731339, 17.289876981669533, 5.984)], [(797.0156367754098, 14.6659793574363, 5.8), (795.8531969731339, 17.289876981669533, 5.984), (794.963767601651, 19.028699171451027, 5.984)], [(797.0156367754098, 14.6659793574363, 5.8), (794.963767601651, 19.028699171451027, 5.984), (792.0167771852575, 24.43868111167103, 5.8)], [(792.0167771852575, 24.43868111167103, 5.8), (794.963767601651, 19.028699171451027, 5.984), (794.3535390960882, 20.22168750793995, 5.984)], [(792.0167771852575, 24.43868111167103, 5.8), (794.3535390960882, 20.22168750793995, 5.984), (793.4641097246054, 21.960509697721445, 5.984)], [(792.0167771852575, 24.43868111167103, 5.8), (793.4641097246054, 21.960509697721445, 5.984), (792.8538812190426, 23.15349803421037, 5.984)], [(794.9508936961998, 22.721018357639245, 7.9045), (793.4641097246054, 21.960509697721445, 5.984), (794.3535390960882, 20.22168750793995, 5.984)], [(794.9508936961998, 22.721018357639245, 7.9045), (794.3535390960882, 20.22168750793995, 5.984), (795.8403230676827, 20.98219616785775, 7.9045)], [(796.4505515732455, 19.789207831368827, 7.9045), (794.963767601651, 19.028699171451027, 5.984), (795.8531969731339, 17.289876981669533, 5.984)], [(796.4505515732455, 19.789207831368827, 7.9045), (795.8531969731339, 17.289876981669533, 5.984), (797.3399809447284, 18.050385641587333, 7.9045)], [(799.4165706742788, 27.71967745758593, 5.302230285069646), (793.847931487946, 25.25059709079139, 8.1), (798.9693443088116, 15.238305455868883, 8.1)], [(799.4165706742788, 27.71967745758593, 5.302230285069646), (798.9693443088116, 15.238305455868883, 8.1), (802.4444703027839, 16.25632133986801, 6.463564730240025)]]
SOURCES=['mansions4986-denny-east-arm-2014','mansions4986-noswan-sw-2018','ea-lidar-composite-2022-tq27ne']
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[:2];L=math.dist(a,b);tx,ty=(b[0]-a[0])/L,(b[1]-a[1])/L;vx,vy=-ty,tx
 def p(s,v,z):return(a[0]+tx*s+vx*v,a[1]+ty*s+vy*v,base+z)
 def rh(v):return 5.8+1.15*min(v,2)-.46*max(0,v-2)
 brick=ctx.material('Oriel evidence red brick',(.36,.155,.095),.85);trim=ctx.material('Oriel pale painted sash',(.79,.79,.72),.59);slate=ctx.material('Oriel grey slate',(.12,.15,.17),.80);glass=ctx.material('Oriel grey glass',(.12,.18,.20),.20,0,.28);iron=ctx.material('Oriel painted dark metal',(.025,.029,.030),.43,.65);door=ctx.material('Oriel estimated dark timber entrance',(.12,.065,.033),.68);stone=ctx.material('Oriel threshold stone',(.47,.45,.40),.88)
 wall=ctx.mesh('complete original footprint and real street apertures');window=ctx.mesh('oval and sash frames');roof=ctx.mesh('asymmetric slate roof with clipped dormer holes');detail=ctx.mesh('brick dormers cornice and rainwater pipes');entry=ctx.mesh('estimated street entrance and finite threshold')
 def face(m,vs,mat):
  for i in range(1,len(vs)-1):
   A,B,C=vs[0],vs[i],vs[i+1];u=[B[k]-A[k] for k in range(3)];v=[C[k]-A[k] for k in range(3)]
   if sum((u[(k+1)%3]*v[(k+2)%3]-u[(k+2)%3]*v[(k+1)%3])**2 for k in range(3))>1e-12:m.face([A,B,C],mat)
 angle=math.atan2(ty,tx)
 def bx(m,s,v,z,w,d,h,mat):m.box(*p(s,v,z),w,d,h,mat,angle)
 for tr in ROOF:face(roof,[(x,y,base+z) for x,y,z in tr],slate)
 centers=[L*.20,L*.50,L*.80];es=centers[0]
 # Front wall is explicitly segmented around lower rectangular openings and upper elliptical apertures.
 cuts=sorted(set([0,L]+[s+d for s in centers for d in [-.62,.62]]))
 for s0,s1 in zip(cuts,cuts[1:]):
  sm=(s0+s1)/2;cc=next((c for c in centers if abs(sm-c)<.62),None)
  if cc is None:face(wall,[p(s0,0,0),p(s1,0,0),p(s1,0,5.8),p(s0,0,5.8)],brick);continue
  lo=.10 if cc==es else .55;hi=2.38
  face(wall,[p(s0,0,0),p(s1,0,0),p(s1,0,lo),p(s0,0,lo)],brick)
  face(wall,[p(s0,0,hi),p(s1,0,hi),p(s1,0,3.03),p(s0,0,3.03)],brick)
  # Ellipse cut uses a rectangle around the ellipse and radial boundary panels, no wall behind glass.
  for k in range(48):
   th0=math.tau*k/48;th1=math.tau*(k+1)/48
   def q(th,outer=False):
    co,si=math.cos(th),math.sin(th);fac=1/max(abs(co),abs(si)) if outer else 1
    return p(cc+.62*co*fac,0,4.22+1.19*si*fac)
   face(wall,[q(th0),q(th1),q(th1,True),q(th0,True)],brick)
   inner0=p(cc+.55*math.cos(th0),.14,4.22+1.10*math.sin(th0));inner1=p(cc+.55*math.cos(th1),.14,4.22+1.10*math.sin(th1))
   face(window,[q(th0),q(th1),inner1,inner0],trim)
   face(window,[p(cc,.18,4.22),inner0,inner1],glass)
  bx(window,cc,.10,4.22,.045,.055,2.16,trim);bx(window,cc,.10,4.22,1.08,.055,.045,trim)
  face(wall,[p(s0,0,5.41),p(s1,0,5.41),p(s1,0,5.8),p(s0,0,5.8)],brick)
  bx(entry if cc==es else window,cc,.40 if cc==es else .19,(lo+hi)/2,1.24,.075,hi-lo,door if cc==es else glass)
  for side in [-1,1]:
   bx(window,cc+side*.665,-.015,(lo+hi)/2,.09,.17,hi-lo+.14,trim)
   face(wall,[p(cc+side*.62,0,lo),p(cc+side*.62,.40 if cc==es else .19,lo),p(cc+side*.62,.40 if cc==es else .19,hi),p(cc+side*.62,0,hi)],brick)
  for zz in ([hi+.06] if cc==es else [lo-.04,hi+.06]):bx(window,cc,-.025,zz,1.42,.19,.11,trim)
  if cc!=es:
   bx(window,cc,.12,(lo+hi)/2,.04,.05,hi-lo,trim);bx(window,cc,.12,(lo+hi)/2,1.22,.05,.04,trim)
 # All remaining mapped boundaries remain closed; party walls get no speculative apertures.
 for aa,bb in zip(ring[1:],ring[2:]+ring[:1]):
  sa=(aa[0]-a[0])*tx+(aa[1]-a[1])*ty;va=(aa[0]-a[0])*vx+(aa[1]-a[1])*vy;sb=(bb[0]-a[0])*tx+(bb[1]-a[1])*ty;vb=(bb[0]-a[0])*vx+(bb[1]-a[1])*vy
  ts=[0,1]
  if abs(vb-va)>1e-8 and 0<(2-va)/(vb-va)<1:ts.append((2-va)/(vb-va))
  ts.sort()
  for t0,t1 in zip(ts,ts[1:]):
   s0,v0=sa+(sb-sa)*t0,va+(vb-va)*t0;s1,v1=sa+(sb-sa)*t1,va+(vb-va)*t1
   face(wall,[p(s0,v0,0),p(s1,v1,0),p(s1,v1,rh(v1)),p(s0,v0,rh(v0))],brick)
 for c in centers:
  # Brick dormer front with actual opening, flush flat cap and cheek closure to the clipped roof.
  for s0,s1 in [(c-.67,c-.43),(c+.43,c+.67)]:face(detail,[p(s0,.16,rh(.16)),p(s1,.16,rh(.16)),p(s1,.16,7.95),p(s0,.16,7.95)],brick)
  for z0,z1 in [(rh(.16),6.20),(7.65,7.95)]:face(detail,[p(c-.43,.16,z0),p(c+.43,.16,z0),p(c+.43,.16,z1),p(c-.43,.16,z1)],brick)
  bx(window,c,.24,6.925,.86,.07,1.45,glass)
  for side in [-1,1]:
   bx(window,c+side*.46,.14,6.925,.06,.10,1.55,trim)
   face(detail,[p(c+side*.67,.16,rh(.16)),p(c+side*.67,1.83,rh(1.83)),p(c+side*.67,1.83,7.95),p(c+side*.67,.16,7.95)],slate)
  for zz in [6.17,7.68]:bx(window,c,.14,zz,.98,.12,.07,trim)
  bx(window,c,.14,6.925,.04,.10,1.46,trim);bx(detail,c,.995,7.99,1.45,1.85,.08,slate)
  face(detail,[p(c-.67,1.83,rh(1.83)),p(c+.67,1.83,rh(1.83)),p(c+.67,1.83,7.95),p(c-.67,1.83,7.95)],slate)
 bx(detail,L/2,-.07,5.78,L,.24,.17,iron)
 for c in [.08,L-.08]:detail.beam(p(c,-.10,.10),p(c,-.10,5.8),.045,iron,10)
 # Estimated single-leaf joinery and hardware: licensed views do not resolve these.
 # All additions stay behind v=.25, beyond the unchanged clear approach throat.
 for ds in [-.52,.52]:
  bx(entry,es+ds,.350,1.24,.055,.025,2.08,door)
 for z in [.24,1.00,2.24]:
  bx(entry,es,.350,z,1.04,.025,.055,door)
 # Two inset-panel outlines, deliberately plain and explicitly estimated.
 for lo,hi in [(.34,.90),(1.10,2.14)]:
  for ds in [-.43,.43]:bx(entry,es+ds,.337,(lo+hi)/2,.018,.020,hi-lo,door)
  for z in [lo,hi]:bx(entry,es,.337,z,.878,.020,.018,door)
 # Small dark metal backplate and pull; no claimed historic hardware pattern.
 bx(entry,es+.45,.329,1.12,.052,.025,.20,iron)
 for z in [1.06,1.18]:entry.beam(p(es+.45,.315,z),p(es+.45,.280,z),.012,iron,8)
 entry.beam(p(es+.45,.280,1.06),p(es+.45,.280,1.18),.014,iron,10)
 # Two-leaf appearance is not asserted: one simple inferred door at street level.
 bx(entry,es,-.30,.05,1.65,.75,.10,stone)
 entrances=[{'name':'Estimated Oriel street entrance','threshold_xyz':p(es,0,.10),'outward_normal':[-vx,-vy,0],'clear_width_m':1.12,'door_leaf_xyz':p(es,.40,1.24),'door_leaf_depth_m':.44,'landing_depth_m':.75,'landing_z_m':.10,'supporting_surface':'finite low stone threshold; exact access location and height estimated','estimated':True}]
 objs=[m.done() for m in [wall,window,roof,detail,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'eaves_m':5.8,'ridge_m':8.1,'full_mapped_outline_preserved':True,'facade_confidence':'moderate material/roof family; low exact ID bay allocation'},'interfaces':{'entrances':entrances},'evidence_source_ids':SOURCES,'uncertainty':['Licensed low-wing photos span Oriel and adjacent 84; exact window-shape allocation to target ID is uncertain. Three oval upper windows and dormers are an explicit interpreted completion.','EA native1m roof reaches ~8.1m, but much of western original footprint samples terrain; footprint offset or included forecourt unresolved. Original footprint retained without movement.','Roof ridge axis, dormer count and entrance position/threshold dimensions estimated.','Rear/north/south adjoining boundaries are closed blank party walls, not extrapolated ornament. No Mansions or number84 geometry included.','Door panel outlines, joinery and metal pull are estimated editable geometry; available licensed photos do not resolve this exact entrance hardware.','Direct PBR colours and optical values visually estimated.']}
