"""23 Queens Gate Terrace. EA roof level with simplified continuous planar cover.
Authoring UTM only; all facade openings and optical values explicitly estimated.
"""
import math

def build(ctx,feature):
 wallmat=ctx.material('23 Queens Gate Terrace estimated pale render',(.76,.735,.66),.85)
 trim=ctx.material('23 Queens Gate Terrace pale trim',(.83,.80,.72),.78)
 timber=ctx.material('23 Queens Gate Terrace white joinery',(.79,.79,.73),.63)
 roofmat=ctx.material('23 Queens Gate Terrace grey roof',(.22,.235,.23),.90)
 glass=ctx.material('23 Queens Gate Terrace recessed glazing',(.12,.19,.20),.20,0,.24)
 metal=ctx.material('23 Queens Gate Terrace dark hardware',(.035,.04,.038),.46,.60)
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
   front=ny>.9 and a[1]>-203 and L>2.5
   holes=[]
   if front:
    for row,z in enumerate([.9,5.5,10.1,14.7,19.3]):
     for k in range(1 if L<4 else 2):
      c=L*(k+.5)/(1 if L<4 else 2);door=feature['id']=='way-213454218' and row==0 and k==0
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
     entrances.append({'name':'23 Queens Gate Terrace estimated east entry','threshold_xyz':list(p(c,.10)),'outward_normal':[nx,ny,0],'clear_width_m':w-.16,'door_leaf_xyz':list(p(c,(lo+hi)/2,dep)),'door_leaf_depth_m':dep,'landing_depth_m':.75,'landing_z_m':.10,'supporting_surface':'finite.10m threshold; master street seam pending','estimated':True})
    else:
     face(wall,[p(le,lo,dep),p(ri,lo,dep),p(ri,hi,dep),p(le,hi,dep)],glass)
     box(detail,c,(lo+hi)/2,.06,hi-lo,timber,.10,.12);box(detail,c,(lo+hi)/2,w,.065,timber,.10,.12);box(detail,c,lo-.07,w+.15,.12,trim,-.06,.25)
   if front:
    for z,h,dep in [(H-.28,.15,.23),(H-.02,.16,.32)]:box(detail,L/2,z,L,h,trim,-.04,dep)
 for geo in feature['geometry']:
  for tri in geo['triangles']:face(wall,[(x,y,base) for x,y in reversed(tri)],wallmat)
 objs=[m.done() for m in [wall,roof,detail,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'zone_heights_m':[z['height'] for z in DATA[feature['id']]],'true_openings':count,'five_storeys_estimated':True},'interfaces':{'entrances':entrances},'evidence_source_ids':['osm-20260908','ea-lidar-composite-2022-tq27ne','jay26-txllxt-bremner-2010'],'uncertainty':['23 consists parentresidual213454218 plus explicitlinkedmain809947756. EachID preservesowngeometry; root registers both.','EA main48samplesmedian24.606 p9525.729; main25.5mplanarapproximation,frontportico4m/rear12.2m estimated frommap; portico height typology estimate due contaminatededge returns.','Northwindows/doorposition/optics estimated; no directtargetphoto, contextuallicensedpaletteonly. Sharedpartywallsblank, no equipment/interiorinvented.']}

DATA = {'way-213454218': [{'height': 4.0, 'triangles': [[[372.15360911388416, -201.011596089229], [371.9452575079631, -198.67017769161612], [369.1618755379459, -199.1225859383121]], [[372.15360911388416, -201.011596089229], [369.1618755379459, -199.1225859383121], [369.5428593737306, -201.43508417531848]]], 'edges': [{'a': [369.1618755379459, -199.1225859383121], 'b': [369.5428593737306, -201.43508417531848], 'outer': True, 'bottom': 0}, {'a': [369.5428593737306, -201.43508417531848], 'b': [372.15360911388416, -201.011596089229], 'outer': False, 'bottom': 25.5}, {'a': [372.15360911388416, -201.011596089229], 'b': [371.9452575079631, -198.67017769161612], 'outer': True, 'bottom': 0}, {'a': [371.9452575079631, -198.67017769161612], 'b': [369.1618755379459, -199.1225859383121], 'outer': True, 'bottom': 0}]}, {'height': 12.2, 'triangles': [[[367.6905057897093, -219.1996584571898], [368.88425922056194, -226.91463293135166], [376.4046918179374, -225.6673158565536]], [[376.4046918179374, -225.6673158565536], [375.596881750389, -220.75458100996912], [371.62415394955315, -221.36415791790932]], [[371.62415394955315, -221.36415791790932], [371.13933324057143, -218.52118914574385], [367.6905057897093, -219.1996584571898]], [[371.62415394955315, -221.36415791790932], [367.6905057897093, -219.1996584571898], [376.4046918179374, -225.6673158565536]]], 'edges': [{'a': [376.4046918179374, -225.6673158565536], 'b': [375.596881750389, -220.75458100996912], 'outer': True, 'bottom': 0}, {'a': [375.596881750389, -220.75458100996912], 'b': [371.62415394955315, -221.36415791790932], 'outer': False, 'bottom': 25.5}, {'a': [371.62415394955315, -221.36415791790932], 'b': [371.13933324057143, -218.52118914574385], 'outer': False, 'bottom': 25.5}, {'a': [371.13933324057143, -218.52118914574385], 'b': [367.6905057897093, -219.1996584571898], 'outer': True, 'bottom': 0}, {'a': [367.6905057897093, -219.1996584571898], 'b': [368.88425922056194, -226.91463293135166], 'outer': True, 'bottom': 0}, {'a': [368.88425922056194, -226.91463293135166], 'b': [376.4046918179374, -225.6673158565536], 'outer': True, 'bottom': 0}]}], 'way-809947756': [{'height': 25.5, 'triangles': [[[372.15360911388416, -201.011596089229], [369.5428593737306, -201.43508417531848], [365.21965299837757, -202.14723749645054]], [[372.15360911388416, -201.011596089229], [365.21965299837757, -202.14723749645054], [367.37078876874875, -214.86939926072955]], [[372.15360911388416, -201.011596089229], [367.37078876874875, -214.86939926072955], [370.4365625529317, -214.35043949913234]], [[372.15360911388416, -201.011596089229], [370.4365625529317, -214.35043949913234], [371.13933324057143, -218.52118914574385]], [[372.15360911388416, -201.011596089229], [371.13933324057143, -218.52118914574385], [371.62415394955315, -221.36415791790932]], [[372.15360911388416, -201.011596089229], [371.62415394955315, -221.36415791790932], [375.596881750389, -220.75458100996912]]], 'edges': [{'a': [365.21965299837757, -202.14723749645054], 'b': [367.37078876874875, -214.86939926072955], 'outer': True, 'bottom': 0}, {'a': [367.37078876874875, -214.86939926072955], 'b': [370.4365625529317, -214.35043949913234], 'outer': True, 'bottom': 0}, {'a': [370.4365625529317, -214.35043949913234], 'b': [371.13933324057143, -218.52118914574385], 'outer': True, 'bottom': 0}, {'a': [371.13933324057143, -218.52118914574385], 'b': [371.62415394955315, -221.36415791790932], 'outer': False, 'bottom': 12.2}, {'a': [371.62415394955315, -221.36415791790932], 'b': [375.596881750389, -220.75458100996912], 'outer': False, 'bottom': 12.2}, {'a': [375.596881750389, -220.75458100996912], 'b': [372.15360911388416, -201.011596089229], 'outer': True, 'bottom': 0}, {'a': [372.15360911388416, -201.011596089229], 'b': [369.5428593737306, -201.43508417531848], 'outer': False, 'bottom': 4.0}, {'a': [369.5428593737306, -201.43508417531848], 'b': [365.21965299837757, -202.14723749645054], 'outer': True, 'bottom': 0}]}]}
