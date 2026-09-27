"""25 Queens Gate. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""
import math

def build(ctx,feature):
 wallmat=ctx.material('25 Queens Gate estimated pale render',(.76,.735,.66),.85)
 trim=ctx.material('25 Queens Gate pale trim',(.83,.80,.72),.78)
 timber=ctx.material('25 Queens Gate white joinery',(.79,.79,.73),.63)
 roofmat=ctx.material('25 Queens Gate grey roof',(.22,.235,.23),.90)
 glass=ctx.material('25 Queens Gate recessed glazing',(.12,.19,.20),.20,0,.24)
 metal=ctx.material('25 Queens Gate dark hardware',(.035,.04,.038),.46,.60)
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
    for row,z in enumerate([.9,5.4,9.9,14.4,18.9,23.4]):
     for k in range(3):
      c=L*(k+.5)/3;door=row==0 and k==2
      holes.append((c-.65,c+.65,.10 if door else z,2.5 if door else z+2.5,door))
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
     entrances.append({'name':'25 Queens Gate estimated east entry','threshold_xyz':list(p(c,.10)),'outward_normal':[nx,ny,0],'clear_width_m':w-.16,'door_leaf_xyz':list(p(c,(lo+hi)/2,dep)),'door_leaf_depth_m':dep,'landing_depth_m':.75,'landing_z_m':.10,'supporting_surface':'finite.10m threshold; master street seam pending','estimated':True})
    else:
     face(wall,[p(le,lo,dep),p(ri,lo,dep),p(ri,hi,dep),p(le,hi,dep)],glass)
     box(detail,c,(lo+hi)/2,.06,hi-lo,timber,.10,.12);box(detail,c,(lo+hi)/2,w,.065,timber,.10,.12);box(detail,c,lo-.07,w+.15,.12,trim,-.06,.25)
   if front:
    for z,h,dep in [(4.2,.14,.18),(27.42,.15,.23),(27.68,.16,.32)]:box(detail,L/2,z,L,h,trim,-.04,dep)
 for tri in feature['geometry'][0]['triangles']:face(wall,[(x,y,base) for x,y in reversed(tri)],wallmat)
 objs=[m.done() for m in [wall,roof,detail,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'roof_heights_m':[27.7,27.7],'levels':6,'true_openings':count,'roof_status':'EA27.7m main roof; planar simplification, edge slopes unresolved'},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','jay26-txllxt-bremner-2010'],'uncertainty':['25 Queens Gate independently mapped residential six levels. Adjacent listed terrace evidence excludes rebuilt25, so classical decoration not transferred.','Full nine-point footprint retained; EA79 inset pixels median27.706m p9527.930m. Roof27.7m is planar approximation, edge slopes unresolved.','Six-storey facade openings, entry and pale palette/optics explicitly estimated without direct licensed target photograph; no balconies or sculpture invented.','Shared north/south walls and unknown rear kept blank.']}

DATA = [{'height': 27.7, 'triangles': [[[470.2287400661735, -145.2437994554639], [488.3379666240653, -142.4858030276373], [486.87200978246983, -134.02416982222348]], [[470.137695731828, -136.75143658649176], [468.8390653746901, -136.95737985242158], [469.30269092158414, -139.79002486541867]], [[470.137695731828, -136.75143658649176], [469.30269092158414, -139.79002486541867], [470.73231587489136, -139.55676266364753]], [[471.24178273417056, -142.67714608181268], [469.99172758089844, -142.88121720403433], [470.2287400661735, -145.2437994554639]], [[471.24178273417056, -142.67714608181268], [470.2287400661735, -145.2437994554639], [486.87200978246983, -134.02416982222348]], [[486.87200978246983, -134.02416982222348], [470.137695731828, -136.75143658649176], [470.73231587489136, -139.55676266364753]], [[486.87200978246983, -134.02416982222348], [470.73231587489136, -139.55676266364753], [471.24178273417056, -142.67714608181268]]], 'edges': [{'a': [486.87200978246983, -134.02416982222348], 'b': [470.137695731828, -136.75143658649176], 'bottom': 0, 'outer': True}, {'a': [470.137695731828, -136.75143658649176], 'b': [468.8390653746901, -136.95737985242158], 'bottom': 0, 'outer': True}, {'a': [468.8390653746901, -136.95737985242158], 'b': [469.30269092158414, -139.79002486541867], 'bottom': 0, 'outer': True}, {'a': [469.30269092158414, -139.79002486541867], 'b': [470.73231587489136, -139.55676266364753], 'bottom': 0, 'outer': True}, {'a': [470.73231587489136, -139.55676266364753], 'b': [471.24178273417056, -142.67714608181268], 'bottom': 0, 'outer': True}, {'a': [471.24178273417056, -142.67714608181268], 'b': [469.99172758089844, -142.88121720403433], 'bottom': 0, 'outer': True}, {'a': [469.99172758089844, -142.88121720403433], 'b': [470.2287400661735, -145.2437994554639], 'bottom': 0, 'outer': True}, {'a': [470.2287400661735, -145.2437994554639], 'b': [488.3379666240653, -142.4858030276373], 'bottom': 0, 'outer': True}, {'a': [488.3379666240653, -142.4858030276373], 'b': [486.87200978246983, -134.02416982222348], 'bottom': 0, 'outer': True}]}]
