"""Jay Mews 117010291. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""
import math

def build(ctx,feature):
 wallmat=ctx.material('Jay Mews 117010291 estimated pale render',(.76,.735,.66),.85)
 trim=ctx.material('Jay Mews 117010291 pale trim',(.83,.80,.72),.78)
 timber=ctx.material('Jay Mews 117010291 white joinery',(.79,.79,.73),.63)
 roofmat=ctx.material('Jay Mews 117010291 grey roof',(.22,.235,.23),.90)
 glass=ctx.material('Jay Mews 117010291 recessed glazing',(.12,.19,.20),.20,0,.24)
 metal=ctx.material('Jay Mews 117010291 dark hardware',(.035,.04,.038),.46,.60)
 wall=ctx.mesh('Partitioned mapped shell with real openings');roof=ctx.mesh('EA continuous simplified roof');detail=ctx.mesh('Estimated frames and cornice');entry=ctx.mesh('Estimated single entry leaf and threshold');base=feature.get('base_m',0);entrances=[];count=0
 def face(m,ps,mat):
  for i in range(1,len(ps)-1):m.face([ps[0],ps[i],ps[i+1]],mat)
 for zone in DATA:
  H=zone['height']
  for tri in zone['triangles']:face(roof,[(x,y,base+H) for x,y in tri],roofmat)
  for ed in zone['edges']:
   bottom=ed['bottom']
   if bottom>=H:continue
   a,b=ed['a'],ed['b'];L=math.dist(a,b);tx=(b[0]-a[0])/L;ty=(b[1]-a[1])/L;nx,ny=ty,-tx;angle=math.atan2(ty,tx)
   def p(s,z,d=0):return (a[0]+tx*s-nx*d,a[1]+ty*s-ny*d,base+z)
   def box(m,s,z,w,h,mat,d=.06,depth=.14):m.box(*p(s,z,d),w,depth,h,mat,angle)
   front=ed['outer'] and nx>.9
   holes=[]
   if front:
    holes=[(.45,3.20,.85,2.75,False),(L-1.75,L-.60,.10,2.50,True)]
    for c in [L*.25,L*.73]:holes.append((c-.65,c+.65,5.40,7.70,False))
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
     entrances.append({'name':'Jay Mews 117010291 estimated east entry','threshold_xyz':list(p(c,.10)),'outward_normal':[nx,ny,0],'clear_width_m':w-.16,'door_leaf_xyz':list(p(c,(lo+hi)/2,dep)),'door_leaf_depth_m':dep,'landing_depth_m':.75,'landing_z_m':.10,'supporting_surface':'finite.10m threshold; master street seam pending','estimated':True})
    else:
     face(wall,[p(le,lo,dep),p(ri,lo,dep),p(ri,hi,dep),p(le,hi,dep)],glass)
     box(detail,c,(lo+hi)/2,.06,hi-lo,timber,.10,.12);box(detail,c,(lo+hi)/2,w,.065,timber,.10,.12);box(detail,c,lo-.07,w+.15,.12,trim,-.06,.25)
   if front:
    for z,h,dep in [(3.2,.14,.18),(9.47,.15,.23),(9.73,.16,.32)]:box(detail,L/2,z,L,h,trim,-.04,dep)
 for tri in feature['geometry'][0]['triangles']:face(wall,[(x,y,base) for x,y in reversed(tri)],wallmat)
 objs=[m.done() for m in [wall,roof,detail,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'roof_heights_m':[9.75,9.75],'levels':2,'true_openings':count,'roof_status':'simplified flat approximation to EA 8.8–10.6m roof returns'},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','jay26-txllxt-bremner-2010'],'uncertainty':['Mapped footprint complete; EA36 inset pixels median9.725m and p9510.328m. Uniform9.75m roof is a simplified approximation; precise slope unresolved.','Two storeys and all facade openings/door positions/optical values are estimates. Licensed local mews photograph provides material context only, not this building details.','Shared north/south boundaries remain blank; no invented equipment or interiors.']}

DATA = [{'height': 9.75, 'triangles': [[[526.4037301203934, 16.272408125922084], [526.7186324003851, 11.529974700883031], [538.1308636866743, 13.128044746816158]], [[538.1308636866743, 13.128044746816158], [536.8315444957698, 21.952409075573087], [529.0943257578183, 20.93030166439712]], [[538.1308636866743, 13.128044746816158], [529.0943257578183, 20.93030166439712], [529.5335209314944, 16.749402676708996]], [[538.1308636866743, 13.128044746816158], [529.5335209314944, 16.749402676708996], [526.4037301203934, 16.272408125922084]]], 'edges': [{'a': [538.1308636866743, 13.128044746816158], 'b': [536.8315444957698, 21.952409075573087], 'bottom': 0, 'outer': True}, {'a': [536.8315444957698, 21.952409075573087], 'b': [529.0943257578183, 20.93030166439712], 'bottom': 0, 'outer': True}, {'a': [529.0943257578183, 20.93030166439712], 'b': [529.5335209314944, 16.749402676708996], 'bottom': 0, 'outer': True}, {'a': [529.5335209314944, 16.749402676708996], 'b': [526.4037301203934, 16.272408125922084], 'bottom': 0, 'outer': True}, {'a': [526.4037301203934, 16.272408125922084], 'b': [526.7186324003851, 11.529974700883031], 'bottom': 0, 'outer': True}, {'a': [526.7186324003851, 11.529974700883031], 'b': [538.1308636866743, 13.128044746816158], 'bottom': 0, 'outer': True}]}]
