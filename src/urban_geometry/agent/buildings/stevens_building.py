"""Stevens: historic west and modern Jay Mews envelope; roof division is estimated from native EA data."""
import math
ZONES=[{'h': 23.8, 'outer': [(488.29944415867794, 64.03041686862707), (487.3814754491905, 68.19286017958075), (486.04520203650463, 68.06340176891536), (485.66551768872887, 71.4226189814508), (486.90292640042026, 71.59280534554273), (486.30336611380335, 76.86987221986055), (484.557946311892, 76.35719160549343), (483.74206810293254, 81.83748127147555), (485.2365728584118, 81.82828642055392), (484.37223819841165, 89.46686560288072), (492.094539422309, 90.33244839683175), (503.0, 91.55583139185916), (503.0, 66.3058291699073)], 'triangles': [[(484.37223819841165, 89.46686560288072), (485.2365728584118, 81.82828642055392), (492.094539422309, 90.33244839683175)], [(503.0, 91.55583139185916), (492.094539422309, 90.33244839683175), (486.30336611380335, 76.86987221986055)], [(503.0, 91.55583139185916), (486.30336611380335, 76.86987221986055), (503.0, 66.3058291699073)], [(503.0, 66.3058291699073), (486.30336611380335, 76.86987221986055), (486.90292640042026, 71.59280534554273)], [(503.0, 66.3058291699073), (486.90292640042026, 71.59280534554273), (487.3814754491905, 68.19286017958075)], [(503.0, 66.3058291699073), (487.3814754491905, 68.19286017958075), (488.29944415867794, 64.03041686862707)], [(486.04520203650463, 68.06340176891536), (487.3814754491905, 68.19286017958075), (486.90292640042026, 71.59280534554273)], [(486.04520203650463, 68.06340176891536), (486.90292640042026, 71.59280534554273), (485.66551768872887, 71.4226189814508)], [(484.557946311892, 76.35719160549343), (486.30336611380335, 76.86987221986055), (485.2365728584118, 81.82828642055392)], [(484.557946311892, 76.35719160549343), (485.2365728584118, 81.82828642055392), (483.74206810293254, 81.83748127147555)], [(485.2365728584118, 81.82828642055392), (486.30336611380335, 76.86987221986055), (492.094539422309, 90.33244839683175)]]}, {'h': 10.5, 'outer': [(507.82278644654434, 92.09685530234128), (510.0, 92.31867891612153), (510.0, 67.38931786794616), (503.0, 66.3058291699073), (503.0, 91.55583139185916)], 'triangles': [[(503.0, 91.55583139185916), (503.0, 66.3058291699073), (510.0, 67.38931786794616)], [(503.0, 91.55583139185916), (510.0, 67.38931786794616), (507.82278644654434, 92.09685530234128)], [(507.82278644654434, 92.09685530234128), (510.0, 67.38931786794616), (510.0, 92.31867891612153)]]}, {'h': 17.5, 'outer': [(513.0976041256217, 92.63427576702088), (523.7637794023613, 95.37271785084158), (526.9150724563515, 83.93626538757235), (529.497309614555, 71.39779239054769), (519.7342845284147, 69.2063669860363), (517.901655337424, 68.61236847564578), (510.0, 67.38931786794616), (510.0, 92.31867891612153)], 'triangles': [[(510.0, 92.31867891612153), (510.0, 67.38931786794616), (517.901655337424, 68.61236847564578)], [(510.0, 92.31867891612153), (517.901655337424, 68.61236847564578), (513.0976041256217, 92.63427576702088)], [(523.7637794023613, 95.37271785084158), (513.0976041256217, 92.63427576702088), (526.9150724563515, 83.93626538757235)], [(526.9150724563515, 83.93626538757235), (513.0976041256217, 92.63427576702088), (519.7342845284147, 69.2063669860363)], [(526.9150724563515, 83.93626538757235), (519.7342845284147, 69.2063669860363), (529.497309614555, 71.39779239054769)], [(517.901655337424, 68.61236847564578), (519.7342845284147, 69.2063669860363), (513.0976041256217, 92.63427576702088)]]}]
SOURCES=['stevens-noswan-queensgate-2023','stevens-shadowssettle-jay-entrance-2020','stevens-accessable-entry-text','ea-lidar-composite-2022-tq27ne']
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer']
 cream=ctx.material('Stevens pale historic stucco',(.77,.75,.67),.78)
 panel=ctx.material('Stevens modern cream panels',(.73,.72,.66),.63)
 dark=ctx.material('Stevens dark blue glazed brick',(.025,.035,.057),.31)
 roofmat=ctx.material('Stevens estimated grey membrane roof',(.18,.20,.21),.83)
 glass=ctx.material('Stevens blue-grey glass',(.11,.16,.18),.20,0,.32)
 metal=ctx.material('Stevens black coated window metal',(.018,.022,.026),.38,.65)
 stone=ctx.material('Stevens grey stone ramp',(.31,.32,.31),.88)
 wall=ctx.mesh('mapped exterior walls and true recessed openings');win=ctx.mesh('window glazing frames and reveals');trim=ctx.mesh('historic balconies cornices and modern bands');roof=ctx.mesh('three closed EA roof height zones');entry=ctx.mesh('Jay Mews curved vestibule column and ramp')
 def face(m,vs,mat):
  for i in range(1,len(vs)-1):
   a,b,c=vs[0],vs[i],vs[i+1];u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
   if sum((u[(k+1)%3]*v[(k+2)%3]-u[(k+2)%3]*v[(k+1)%3])**2 for k in range(3))>1e-12:m.face([a,b,c],mat)
 def height(x):return 23.8 if x<503 else (10.5 if x<510 else 17.5)
 for zone in ZONES:
  roof.surface([zone],base+zone['h'],roofmat)
  for a,b in zip(zone['outer'],zone['outer'][1:]+zone['outer'][:1]):
   if abs(a[0]-b[0])<1e-6 and (abs(a[0]-503)<1e-6 or abs(a[0]-510)<1e-6) and zone['h']>10.5:
    face(wall,[(a[0],a[1],base+10.5),(b[0],b[1],base+10.5),(b[0],b[1],base+zone['h']),(a[0],a[1],base+zone['h'])],panel)
 entrances=[]
 for ei,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
  L=math.dist(a,b);tx,ty=(b[0]-a[0])/L,(b[1]-a[1])/L;nx,ny=ty,-tx;angle=math.atan2(ty,tx)
  def pos(s,d,z):return(a[0]+tx*s+nx*d,a[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,h,mat):m.box(*pos(s,d,z),w,dep,h,mat,angle)
  cuts=[0,L]
  if abs(tx)>1e-8:cuts += [(x-a[0])/tx for x in [503,510] if 0<(x-a[0])/tx<L]
  cuts=sorted(cuts)
  for s0,s1 in zip(cuts,cuts[1:]):
   mid=(s0+s1)/2;x=pos(mid,0,0)[0];H=height(x);historic=x<503;street=historic and nx<-.5;mat=cream if historic else panel;holes=[]
   # Small outline jogs are retained solid; no invented squeezed windows.
   n=int((s1-s0)/3.15)
   for j in range(n):
    s=s0+(j+.5)*(s1-s0)/n;ww=min(1.6,(s1-s0)/n*.55) if historic else (s1-s0)/n*.78
    for row,z in enumerate(([1.3,5.4,9.9,14.2,18.2] if historic else [1.0,4.8,8.7,12.6])):
     hh=2.9 if historic and row<3 else 2.45
     if z+hh>H-.45:continue
     if ei==17 and row==0:continue
     holes.append((s-ww/2,s+ww/2,z,z+hh))
     bx(win,s,-.20,z+hh/2,ww,.07,hh,glass)
     for d in [-1,1]:
      bx(win,s+d*(ww/2+.05),.015,z+hh/2,.10,.17,hh+.16,cream if historic else metal)
      face(win,[pos(s+d*ww/2,0,z),pos(s+d*ww/2,-.20,z),pos(s+d*ww/2,-.20,z+hh),pos(s+d*ww/2,0,z+hh)],mat)
     for zz in [z-.07,z+hh+.07]:bx(win,s,.025,zz,ww+.20,.20,.14,cream if historic else metal)
     bx(win,s,-.13,z+hh*.5,ww,.05,.045,metal)
     if not historic:bx(win,s,-.13,z+hh/2,.045,.05,hh,metal)
     if street and row in [1,2]:
      bx(trim,s,.14,z+hh+.3,ww+.5,.38,.18,cream)
      if row==1:
       bx(trim,s,.43,z-.22,ww+.7,1.05,.22,cream)
       bx(trim,s,.90,z+.44,ww+.7,.13,.15,cream)
       for side in [-1,1]:
        entry.beam(pos(s+side*(ww/2+.25),.73,.35),pos(s+side*(ww/2+.25),.73,z-.35),.14,cream,16)
        bx(trim,s+side*(ww/2+.25),.73,z-.34,.43,.43,.19,cream)
       for k in range(9):bx(trim,s-(ww+.55)/2+k*(ww+.55)/8,.90,z+.09,.07,.07,.60,cream)
   if ei==17:
    es=L*.51;holes.append((es-2.35,es+2.35,0,3.55))
    # Curved side glazing meets paired flat doors; no generic door pasted on solid wall.
    for side in [-1,1]:
     bx(entry,es+side*.385,-.60,1.61,.74,.08,3.06,glass)
     bx(entry,es+side*.76,-.53,1.61,.065,.10,3.10,metal)
     for zz in [.11,1.0,2.03,3.11]:bx(entry,es+side*.385,-.53,zz,.74,.08,.055,metal)
     pts=[(es+side*(.79+1.49*k/8),-.60-.44*math.sin(k/8*math.pi/2)) for k in range(9)]
     for (ss,dd),(st,dt) in zip(pts,pts[1:]):
      face(entry,[pos(ss,dd,.08),pos(st,dt,.08),pos(st,dt,3.14),pos(ss,dd,3.14)],glass)
     for ss,dd in pts[::2]:entry.beam(pos(ss,dd,.08),pos(ss,dd,3.14),.025,metal,8)
     for zz in [.12,1.0,2.03,3.14]:
      for (ss,dd),(st,dt) in zip(pts,pts[1:]):entry.beam(pos(ss,dd,zz),pos(st,dt,zz),.025,metal,8)
     entrances.append({'name':'Jay Mews main entrance leaf '+str(side),'threshold_xyz':pos(es+side*.385,0,.08),'outward_normal':[nx,ny,0],'door_leaf_xyz':pos(es+side*.385,-.60,1.61),'clear_width_m':.68,'door_leaf_depth_m':.49,'door_leaf_depth_basis':'frontmost closed leaf horizontal frame; source normal distance','door_glass_front_depth_m':.56,'door_glass_back_depth_m':.64,'door_horizontal_frame_front_depth_m':.49,'door_horizontal_frame_back_depth_m':.57,'ramp_run_m':1.8,'ramp_rise_m':.08,'supporting_surface':'finite shallow ramp; exact slope estimated; AccessAble reports 1.48m overall double opening','estimated':True})
    for side in [-1,1]:
     face(entry,[pos(es+side*2.35,0,0),pos(es+side*2.28,-1.04,.08),pos(es+side*2.28,-1.04,3.14),pos(es+side*2.35,0,3.55)],panel)
    bx(entry,es,-.53,1.61,.05,.10,3.12,metal)
    # White cylindrical column seen beside the portal, outside either leaf approach.
    entry.beam(pos(es+1.65,.19,0),pos(es+1.65,.19,3.54),.22,panel,24)
    bx(entry,es,-.12,3.40,4.70,.86,.29,panel)
    vs=[pos(es-2.40,1.8,0),pos(es+2.40,1.8,0),pos(es+2.40,-.69,.11),pos(es-2.40,-.69,.11)]
    face(entry,vs,stone)
    for aa,bb in zip(vs,vs[1:]+vs[:1]):face(entry,[aa,bb,(bb[0],bb[1],base),(aa[0],aa[1],base)],stone)
   xs=sorted(set([s0,s1]+[v for q in holes for v in q[:2]]))
   for aa,bb in zip(xs,xs[1:]):
    mm=(aa+bb)/2;z0=0
    for lo,hi in sorted((q[2],q[3]) for q in holes if q[0]<mm<q[1]):
     if lo>z0:face(wall,[pos(aa,0,z0),pos(bb,0,z0),pos(bb,0,lo),pos(aa,0,lo)],mat)
     z0=max(z0,hi)
    if H>z0:face(wall,[pos(aa,0,z0),pos(bb,0,z0),pos(bb,0,H),pos(aa,0,H)],mat)
   for zz in ([.45,4.8,9.35,17.6,22.9,23.7] if historic else [.35,3.85,7.8,11.7,16.8]):
    if zz>H:continue
    spans=[(s0,s1)]
    if ei==17 and zz<3.55:spans=[(s0,es-2.45),(es+2.45,s1)]
    for aa,bb in spans:
     if bb>aa:bx(trim,(aa+bb)/2,.035,zz,bb-aa,.18,.20 if historic else .38,cream if historic else dark)
   if street:
    # Plain end pilasters represent the photograph's classical divisions, carving simplified.
    for ss in [s0+.16,s1-.16]:bx(trim,ss,.09,2.35,.25,.28,4.5,cream)
 objs=[m.done() for m in [wall,win,trim,roof,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'western_roof_m':23.8,'middle_roof_m':10.5,'eastern_roof_m':17.5,'full_mapped_outline_preserved':True,'detail_level':'moderate evidence-led exterior'},'interfaces':{'entrances':entrances},'evidence_source_ids':SOURCES,'uncertainty':['Roof zones inferred from native 1m DSM-DTM; exact subdivision, flat roof topology and parapets estimated.','Historic frontage seen through trees; balcony/window placement interpolated to mapped facade segments.','Jay Mews portal architecture photographed, location along mapped east edge and 0.08m ramp rise estimated. 1.48m total door opening is reported by AccessAble.','Unseen internal and rear elevations use sparse estimated openings. No neighbouring Frayling geometry included.','PBR values visually estimated; no photo textures exported.']}
