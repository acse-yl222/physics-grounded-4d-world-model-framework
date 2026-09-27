"""30 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""
import math

def build(ctx,feature):
 wallmat=ctx.material('30 Queens Gate Terrace estimated pale render',(.76,.735,.66),.85)
 trim=ctx.material('30 Queens Gate Terrace pale trim',(.83,.80,.72),.78)
 timber=ctx.material('30 Queens Gate Terrace white joinery',(.79,.79,.73),.63)
 roofmat=ctx.material('30 Queens Gate Terrace grey roof',(.22,.235,.23),.90)
 glass=ctx.material('30 Queens Gate Terrace recessed glazing',(.12,.19,.20),.20,0,.24)
 metal=ctx.material('30 Queens Gate Terrace dark hardware',(.035,.04,.038),.46,.60)
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
   front=ed['outer'] and ny<-.9 and L>5
   holes=[]
   if front:
    for row,z in enumerate([.9,5.5,10.1,14.7,19.3]):
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
     entrances.append({'name':'30 Queens Gate Terrace estimated south entry','threshold_xyz':list(p(c,.10)),'outward_normal':[nx,ny,0],'clear_width_m':w-.16,'door_leaf_xyz':list(p(c,(lo+hi)/2,dep)),'door_leaf_depth_m':dep,'landing_depth_m':.75,'landing_z_m':.10,'supporting_surface':'finite.10m threshold; master street seam pending','estimated':True})
    else:
     face(wall,[p(le,lo,dep),p(ri,lo,dep),p(ri,hi,dep),p(le,hi,dep)],glass)
     box(detail,c,(lo+hi)/2,.06,hi-lo,timber,.10,.12);box(detail,c,(lo+hi)/2,w,.065,timber,.10,.12);box(detail,c,lo-.07,w+.15,.12,trim,-.06,.25)
   if front:
    for z,h,dep in [(4.2,.14,.18),(H-.28,.15,.23),(H-.02,.16,.32)]:box(detail,L/2,z,L,h,trim,-.04,dep)
 for tri in feature['geometry'][0]['triangles']:face(wall,[(x,y,base) for x,y in reversed(tri)],wallmat)
 objs=[m.done() for m in [wall,roof,detail,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'roof_heights_m':[26,22,13.5,4.5],'levels':5,'true_openings':count,'roof_status':'EA layered roof; simplified transitions3.5/18.5/23m northward from south facade'},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','jay26-txllxt-bremner-2010'],'uncertainty':['Mapped independent residential fivelevel30 Queens Gate Terrace; full5point boundary-crossing footprint retained without clipping.','EA105samples median20.253,p9524.983. Viewed native map supports elevated south edge26m,main22m,rear13.5m and farrear4.5m; transition positions approximate.','Southfive-storey3bay windows and singleentry, opticalvalues estimated; no directtargetphoto, nearbylicensedpalettecontextonly.','East shared blank; west and rear unknown blank, no hidden equipment or interior invented.']}

DATA = [{'height': 26.0, 'triangles': [[(340.90715865307, -171.702663456289), (341.46083231118973, -175.1586318248883), (348.7976776206633, -174.01863595005125)], [(340.90715865307, -171.702663456289), (348.7976776206633, -174.01863595005125), (348.2377788520098, -170.56363483645458)]], 'edges': [{'a': (348.7976776206633, -174.01863595005125), 'b': (348.2377788520098, -170.56363483645458), 'outer': True, 'bottom': 0}, {'a': (348.2377788520098, -170.56363483645458), 'b': (340.90715865307, -171.702663456289), 'outer': False, 'bottom': 22.0}, {'a': (340.90715865307, -171.702663456289), 'b': (341.46083231118973, -175.1586318248883), 'outer': True, 'bottom': 0}, {'a': (341.46083231118973, -175.1586318248883), 'b': (348.7976776206633, -174.01863595005125), 'outer': True, 'bottom': 0}]}, {'height': 22.0, 'triangles': [[(338.53427154684255, -156.89137044800637), (340.90715865307, -171.702663456289), (348.2377788520098, -170.56363483645458)], [(338.53427154684255, -156.89137044800637), (348.2377788520098, -170.56363483645458), (345.8382127006375, -155.75648720675454)]], 'edges': [{'a': (348.2377788520098, -170.56363483645458), 'b': (345.8382127006375, -155.75648720675454), 'outer': True, 'bottom': 0}, {'a': (345.8382127006375, -155.75648720675454), 'b': (338.53427154684255, -156.89137044800637), 'outer': False, 'bottom': 13.5}, {'a': (338.53427154684255, -156.89137044800637), 'b': (340.90715865307, -171.702663456289), 'outer': True, 'bottom': 0}, {'a': (340.90715865307, -171.702663456289), 'b': (348.2377788520098, -170.56363483645458), 'outer': False, 'bottom': 26.0}]}, {'height': 13.5, 'triangles': [[(338.1028765911469, -154.19865191355348), (338.53427154684255, -156.89137044800637), (345.8382127006375, -155.75648720675454)], [(338.1028765911469, -154.19865191355348), (345.8382127006375, -155.75648720675454), (345.1183428552258, -151.31434291784453)], [(338.1028765911469, -154.19865191355348), (345.1183428552258, -151.31434291784453), (337.79886316429264, -152.45164053032696)]], 'edges': [{'a': (345.8382127006375, -155.75648720675454), 'b': (345.1183428552258, -151.31434291784453), 'outer': True, 'bottom': 0}, {'a': (345.1183428552258, -151.31434291784453), 'b': (337.79886316429264, -152.45164053032696), 'outer': False, 'bottom': 4.5}, {'a': (337.79886316429264, -152.45164053032696), 'b': (338.1028765911469, -154.19865191355348), 'outer': True, 'bottom': 0}, {'a': (338.1028765911469, -154.19865191355348), 'b': (338.53427154684255, -156.89137044800637), 'outer': True, 'bottom': 0}, {'a': (338.53427154684255, -156.89137044800637), 'b': (345.8382127006375, -155.75648720675454), 'outer': False, 'bottom': 22.0}]}, {'height': 4.5, 'triangles': [[(345.1183428552258, -151.31434291784453), (344.4580065240152, -147.23956567700952), (337.09429819870275, -148.40286206733435)], [(345.1183428552258, -151.31434291784453), (337.09429819870275, -148.40286206733435), (337.79886316429264, -152.45164053032696)]], 'edges': [{'a': (337.09429819870275, -148.40286206733435), 'b': (337.79886316429264, -152.45164053032696), 'outer': True, 'bottom': 0}, {'a': (337.79886316429264, -152.45164053032696), 'b': (345.1183428552258, -151.31434291784453), 'outer': False, 'bottom': 13.5}, {'a': (345.1183428552258, -151.31434291784453), 'b': (344.4580065240152, -147.23956567700952), 'outer': True, 'bottom': 0}, {'a': (344.4580065240152, -147.23956567700952), 'b': (337.09429819870275, -148.40286206733435), 'outer': True, 'bottom': 0}]}]
