"""19 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""
import math

def build(ctx,feature):
 wallmat=ctx.material('19 Queens Gate Terrace estimated pale render',(.76,.735,.66),.85)
 trim=ctx.material('19 Queens Gate Terrace pale trim',(.83,.80,.72),.78)
 timber=ctx.material('19 Queens Gate Terrace white joinery',(.79,.79,.73),.63)
 roofmat=ctx.material('19 Queens Gate Terrace grey roof',(.22,.235,.23),.90)
 glass=ctx.material('19 Queens Gate Terrace recessed glazing',(.12,.19,.20),.20,0,.24)
 metal=ctx.material('19 Queens Gate Terrace dark hardware',(.035,.04,.038),.46,.60)
 wall=ctx.mesh('Partitioned mapped shell with real openings');roof=ctx.mesh('EA continuous simplified roof');detail=ctx.mesh('Estimated frames and cornice');entry=ctx.mesh('Estimated single entry leaf and threshold');base=feature.get('base_m',0);entrances=[];count=0
 def face(m,ps,mat):
  for i in range(1,len(ps)-1):m.face([ps[0],ps[i],ps[i+1]],mat)
 for zone in DATA[feature['id']]:
  H=zone['height']
  for tri in zone['triangles']:face(roof,[(x,y,base+H) for x,y in tri],roofmat)
  for ed in zone['edges']:
   bottom=ed['bottom']
   if bottom>=H:continue
   a,b=ed['a'],ed['b'];L=math.dist(a,b);tx=(b[0]-a[0])/L;ty=(b[1]-a[1])/L;nx,ny=ty,-tx;angle=math.atan2(ty,tx)
   def p(s,z,d=0):return (a[0]+tx*s-nx*d,a[1]+ty*s-ny*d,base+z)
   def box(m,s,z,w,h,mat,d=.06,depth=.14):m.box(*p(s,z,d),w,depth,h,mat,angle)
   front=ny>.9 and a[1]>-201 and L>3
   holes=[]
   if front:
    for row,z in enumerate([.9,5.9,10.9,15.9,20.9]):
     for k in range(1 if L<4 else 2):
      c=L*(k+.5)/(1 if L<4 else 2);door=feature['id']=='way-213454226' and row==0 and k==0
      if z>=bottom and z+2.5<H-.2:holes.append((c-.65,c+.65,.10 if door else z,2.5 if door else z+2.5,door))
   cuts=sorted(set([bottom,H]+[h[j] for h in holes for j in [2,3]]))
   for lo,hi in zip(cuts,cuts[1:]):
    cursor=0;intervals=sorted((h[0],h[1]) for h in holes if h[2]<=lo and h[3]>=hi)
    for le,ri in intervals+[(L,L)]:
     if le>cursor:face(wall,[p(cursor,lo),p(le,lo),p(le,hi),p(cursor,hi)],wallmat)
     cursor=max(cursor,ri)
   for le,ri,lo,hi,door in holes:
    count+=1;c=(le+ri)/2;w=ri-le;dep=.45 if door else .27
    for q,r in [((le,lo),(ri,lo)),((ri,lo),(ri,hi)),((ri,hi),(le,hi)),((le,hi),(le,lo))]:face(wall,[p(*q),p(*r),p(*r,dep),p(*q,dep)],trim)
    for s in [le,ri]:box(detail,s,(lo+hi)/2,.065,hi-lo,timber)
    box(detail,c,hi,w,.075,timber)
    if door:
     box(entry,c,(lo+hi)/2,w,hi-lo,timber,dep,.07)
     for s in [le+.10,ri-.10]:box(entry,s,1.3,.04,2.1,timber,dep-.045,.04)
     for z in [.22,1.03,2.35]:box(entry,c,z,w-.18,.04,timber,dep-.045,.04)
     entry.beam(p(ri-.18,1.0,dep-.1),p(ri-.18,1.22,dep-.1),.018,metal,8)
     box(entry,c,.05,w+.30,.10,trim,-.28,.75)
     entrances.append({'name':'19 Queens Gate Terrace estimated east entry','threshold_xyz':list(p(c,.10)),'outward_normal':[nx,ny,0],'clear_width_m':w-.16,'door_leaf_xyz':list(p(c,(lo+hi)/2,dep)),'door_leaf_depth_m':dep,'landing_depth_m':.75,'landing_z_m':.10,'supporting_surface':'finite.10m threshold; master street seam pending','estimated':True})
    else:
     face(wall,[p(le,lo,dep),p(ri,lo,dep),p(ri,hi,dep),p(le,hi,dep)],glass)
     box(detail,c,(lo+hi)/2,.06,hi-lo,timber,.10,.12);box(detail,c,(lo+hi)/2,w,.065,timber,.10,.12);box(detail,c,lo-.07,w+.15,.12,trim,-.06,.25)
   if front:
    for z,h,dep in [(H-.28,.15,.23),(H-.02,.16,.32)]:box(detail,L/2,z,L,h,trim,-.04,dep)
 for geo in feature['geometry']:
  for tri in geo['triangles']:face(wall,[(x,y,base) for x,y in reversed(tri)],wallmat)
 objs=[m.done() for m in [wall,roof,detail,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'zone_heights_m':[z['height'] for z in DATA[feature['id']]],'true_openings':count,'five_storeys_estimated':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','jay26-txllxt-bremner-2010'],'uncertainty':['19 consists parentresidual213454226 plus explicitlinkedmain809947758. EachID preservesowngeometry; root registers both.','EA main55samplesmedian26.793 p9527.539; main27.3mplanarapproximation,frontportico4m/rear11m estimated frommap; portico height typology estimate due contaminatededge returns.','Northwindows/doorposition/optics estimated; no directtargetphoto, contextuallicensedpaletteonly. Sharedpartywallsblank, no equipment/interiorinvented.']}

DATA = {'way-213454226': [{'height': 4.0, 'triangles': [[[387.2507661167765, -198.53703673183918], [386.8486128185177, -196.0360631076619], [383.7685437311884, -196.54444951284677]], [[387.2507661167765, -198.53703673183918], [383.7685437311884, -196.54444951284677], [384.1845747254556, -199.0448886146769]]], 'edges': [{'a': [383.7685437311884, -196.54444951284677], 'b': [384.1845747254556, -199.0448886146769], 'outer': True, 'bottom': 0}, {'a': [384.1845747254556, -199.0448886146769], 'b': [387.2507661167765, -198.53703673183918], 'outer': False, 'bottom': 27.3}, {'a': [387.2507661167765, -198.53703673183918], 'b': [386.8486128185177, -196.0360631076619], 'outer': True, 'bottom': 0}, {'a': [386.8486128185177, -196.0360631076619], 'b': [383.7685437311884, -196.54444951284677], 'outer': True, 'bottom': 0}]}, {'height': 11.0, 'triangles': [[[381.83801852271426, -216.42765837348998], [383.2068257974461, -224.536739830859], [391.4320970700355, -223.184301096946]], [[391.4320970700355, -223.184301096946], [390.3744458114961, -218.28119371645153], [386.41954137035646, -218.81215200666338]], [[386.41954137035646, -218.81215200666338], [385.9122659332352, -215.74735299590975], [381.83801852271426, -216.42765837348998]], [[386.41954137035646, -218.81215200666338], [381.83801852271426, -216.42765837348998], [391.4320970700355, -223.184301096946]]], 'edges': [{'a': [391.4320970700355, -223.184301096946], 'b': [390.3744458114961, -218.28119371645153], 'outer': True, 'bottom': 0}, {'a': [390.3744458114961, -218.28119371645153], 'b': [386.41954137035646, -218.81215200666338], 'outer': False, 'bottom': 27.3}, {'a': [386.41954137035646, -218.81215200666338], 'b': [385.9122659332352, -215.74735299590975], 'outer': False, 'bottom': 27.3}, {'a': [385.9122659332352, -215.74735299590975], 'b': [381.83801852271426, -216.42765837348998], 'outer': True, 'bottom': 0}, {'a': [381.83801852271426, -216.42765837348998], 'b': [383.2068257974461, -224.536739830859], 'outer': True, 'bottom': 0}, {'a': [383.2068257974461, -224.536739830859], 'b': [391.4320970700355, -223.184301096946], 'outer': True, 'bottom': 0}]}], 'way-809947758': [{'height': 27.3, 'triangles': [[[384.1845747254556, -199.0448886146769], [379.3222242332995, -199.83350003138185], [381.40057215769775, -212.46938382741064]], [[384.1845747254556, -199.0448886146769], [381.40057215769775, -212.46938382741064], [385.2679128192831, -211.83045464009047]], [[384.1845747254556, -199.0448886146769], [385.2679128192831, -211.83045464009047], [385.9122659332352, -215.74735299590975]], [[384.1845747254556, -199.0448886146769], [385.9122659332352, -215.74735299590975], [386.41954137035646, -218.81215200666338]], [[384.1845747254556, -199.0448886146769], [386.41954137035646, -218.81215200666338], [390.3744458114961, -218.28119371645153]], [[384.1845747254556, -199.0448886146769], [390.3744458114961, -218.28119371645153], [387.2507661167765, -198.53703673183918]]], 'edges': [{'a': [379.3222242332995, -199.83350003138185], 'b': [381.40057215769775, -212.46938382741064], 'outer': True, 'bottom': 0}, {'a': [381.40057215769775, -212.46938382741064], 'b': [385.2679128192831, -211.83045464009047], 'outer': True, 'bottom': 0}, {'a': [385.2679128192831, -211.83045464009047], 'b': [385.9122659332352, -215.74735299590975], 'outer': True, 'bottom': 0}, {'a': [385.9122659332352, -215.74735299590975], 'b': [386.41954137035646, -218.81215200666338], 'outer': False, 'bottom': 11.0}, {'a': [386.41954137035646, -218.81215200666338], 'b': [390.3744458114961, -218.28119371645153], 'outer': False, 'bottom': 11.0}, {'a': [390.3744458114961, -218.28119371645153], 'b': [387.2507661167765, -198.53703673183918], 'outer': True, 'bottom': 0}, {'a': [387.2507661167765, -198.53703673183918], 'b': [384.1845747254556, -199.0448886146769], 'outer': False, 'bottom': 4.0}, {'a': [384.1845747254556, -199.0448886146769], 'b': [379.3222242332995, -199.83350003138185], 'outer': True, 'bottom': 0}]}]}
