"""12 Jay Mews: exact low mapped volume; explicitly estimated residential openings.
EA2022 height, licensed local context only; no claim of observed individual facade."""
import math

def build(ctx,feature):
 stucco=ctx.material('12 Jay Mews pale cream stucco',(.76,.735,.66),.85)
 trim=ctx.material('12 Jay Mews light cornice',(.83,.80,.72),.78)
 timber=ctx.material('12 Jay Mews white painted timber',(.79,.79,.73),.63)
 roofmat=ctx.material('12 Jay Mews grey flat roof',(.22,.235,.23),.90)
 glass=ctx.material('12 Jay Mews recessed glazing',(.12,.19,.20),.20,0,.24)
 metal=ctx.material('12 Jay Mews dark door hardware',(.035,.04,.038),.46,.60)
 wall=ctx.mesh('Full mapped shell real east openings');roof=ctx.mesh('EA low flat roof');detail=ctx.mesh('Mews joinery and restrained cornices');entry=ctx.mesh('Estimated pedestrian leaf and finite threshold')
 ring=feature['geometry'][0]['outer'];base=feature.get('base_m',0);H=8.12;entrances=[];count=0
 def face(m,ps,mat):
  for i in range(1,len(ps)-1):m.face([ps[0],ps[i],ps[i+1]],mat)
 for tri in feature['geometry'][0]['triangles']:
  face(roof,[(x,y,base+H) for x,y in tri],roofmat);face(wall,[(x,y,base) for x,y in reversed(tri)],stucco)
 for ei,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
  L=math.dist(a,b);tx=(b[0]-a[0])/L;ty=(b[1]-a[1])/L;nx,ny=ty,-tx;angle=math.atan2(ty,tx)
  def p(s,z,dep=0):return (a[0]+tx*s-nx*dep,a[1]+ty*s-ny*dep,base+z)
  def box(m,s,z,w,h,mat,dep=-.04,depth=.16):m.box(*p(s,z,dep),w,depth,h,mat,angle)
  holes=[]
  if ei==0:
   # Exposed Jay Mews side. Exact bay spacing and pedestrian leaf are estimates.
   holes=[(.45,3.65,.10,3.15,'garage'),(4.15,5.30,.10,2.45,'entry'),(6.15,L-.65,.85,2.65,'window')]
   for c in [L*.20,L*.50,L*.80]:holes.append((c-.65,c+.65,4.85,6.75,'window'))
  zcuts=sorted(set([0,H]+[h[j] for h in holes for j in [2,3]]))
  for lo,hi in zip(zcuts,zcuts[1:]):
   intervals=sorted((h[0],h[1]) for h in holes if h[2]<=lo and h[3]>=hi);cursor=0
   for le,ri in intervals+[(L,L)]:
    if le>cursor+1e-8:face(wall,[p(cursor,lo),p(le,lo),p(le,hi),p(cursor,hi)],stucco)
    cursor=max(cursor,ri)
  for le,ri,lo,hi,kind in holes:
   count+=1;c=(le+ri)/2;w=ri-le;dep=.45 if kind=='entry' else .27
   for q,r in [((le,lo),(ri,lo)),((ri,lo),(ri,hi)),((ri,hi),(le,hi)),((le,hi),(le,lo))]:face(wall,[p(*q),p(*r),p(*r,dep),p(*q,dep)],trim)
   for s in [le,ri]:box(detail,s,(lo+hi)/2,.075,hi-lo,timber,.07,.14)
   box(detail,c,hi,w,.08,timber,.07,.14)
   if kind=='window':
    face(wall,[p(le,lo,dep),p(ri,lo,dep),p(ri,hi,dep),p(le,hi,dep)],glass)
    box(detail,c,lo,w+.15,.10,trim,-.07,.25);box(detail,c,(lo+hi)/2,.06,hi-lo,timber,.13,.10);box(detail,c,lo+.85,w,.065,timber,.13,.10)
   elif kind=='garage':
    face(detail,[p(le,lo,dep),p(ri,lo,dep),p(ri,2.52,dep),p(le,2.52,dep)],timber)
    face(detail,[p(le,2.52,dep),p(ri,2.52,dep),p(ri,hi,dep),p(le,hi,dep)],glass)
    for k in range(1,12):box(detail,le+w*k/12,1.31,.018,2.42,trim,dep-.025,.028)
    for s in [le,c,ri]:box(detail,s,(lo+hi)/2,.075,hi-lo,timber,dep-.03,.08)
    box(detail,c,2.52,w,.075,timber,dep-.03,.08)
    for k in [1,2,3]:box(detail,le+w*k/4,2.835,.045,.63,timber,dep-.03,.08)
    box(detail,c,1.20,.08,.20,metal,dep-.075,.06)
   else:
    box(entry,c,(lo+hi)/2,w,hi-lo,timber,dep,.07)
    for s in [le+.12,ri-.12]:box(entry,s,1.23,.035,2.05,trim,dep-.05,.035)
    for z in [.23,1.0,2.30]:box(entry,c,z,w-.22,.035,trim,dep-.05,.035)
    entry.beam(p(ri-.20,.98,dep-.08),p(ri-.20,1.20,dep-.08),.018,metal,8)
    box(entry,c,.05,w+.30,.10,trim,-.28,.75)
    entrances.append({'name':'12 Jay Mews estimated east pedestrian leaf','threshold_xyz':list(p(c,.10)),'outward_normal':[nx,ny,0],'clear_width_m':w-.16,'door_leaf_xyz':list(p(c,(lo+hi)/2,dep)),'door_leaf_depth_m':dep,'landing_depth_m':.75,'landing_z_m':.10,'supporting_surface':'finite .10m stone threshold; street seam requires master coordination','estimated':True})
  if ei==0:
   for z,wdepth,h in [(3.65,.18,.16),(7.60,.20,.12),(7.87,.34,.20),(8.18,.40,.12)]:box(detail,L/2,z,L,h,trim,-.035,wdepth)
   # Low parapet, top8.32m, within mapped roof boundary.
   box(detail,L/2,8.18,L,.28,stucco,.13,.26)
 objs=[m.done() for m in [wall,roof,detail,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'roof_height_m':8.12,'maximum_parapet_m':8.32,'levels_estimated':2,'true_openings':count,'mapped_outline_preserved':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','jay26-txllxt-bremner-2010'],'uncertainty':['32 Jay Mews absent from current geometry; this independent12 Jay Mews module selected while still urban. No school footprint changed.','No direct licensed close view establishes12 exact facade. East garage-type opening, adjacent person door, upper windows, pale render and all dimensions explicitly estimated from local mews context.','EA2022 median8.116m supports low8.12m roof, estimated8.32m front parapet; whole seven-vertex outline and rear recess retained.','2021–23 official planning text mentions garage conversion, but current execution/appearance unverified; garage joinery is not asserted current.','Adjoining and hidden rear walls remain closed. No rooftop plant invented.','Constant PBR values are visual estimates, not calibration.']}
