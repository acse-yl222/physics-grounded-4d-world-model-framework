"""RCM South Building only. Roof steps EA-supported; facade rhythm explicitly estimated."""
import math
ORIGIN=[708.4499971116893, -129.41957763954997]
AXIS=(0.9927377723973813, 0.12029844244829357)
ZONES=[{'height': 10.3, 'triangles': [[(5.0, 4.0), (5.0, 9.56070905565004e-17), (23.07159441873938, 4.0)], [(5.0, 9.56070905565004e-17), (23.224700556472932, 4.440892098500626e-16), (23.07159441873938, 4.0)]], 'edges': [[(23.224700556472932, 4.440892098500626e-16), (5.0, 9.56070905565004e-17), 0, 1], [(23.07159441873938, 4.0), (23.224700556472932, 4.440892098500626e-16), 0, 2]]}, {'height': 23.3, 'triangles': [[(-0.14833769437282762, 15.74241785360307), (0.0, 0.0), (5.0, 4.0)], [(-0.14833769437282762, 15.74241785360307), (5.0, 4.0), (16.67020769853194, 13.254679445519704)], [(-0.14833769437282762, 15.74241785360307), (16.67020769853194, 13.254679445519704), (16.688083576921848, 16.100056389428275)], [(17.0, 6.0), (23.07159441873938, 4.0), (22.995041349872604, 6.0)], [(13.0, 4.0), (23.07159441873938, 4.0), (17.0, 6.0)], [(5.0, 4.0), (13.0, 4.0), (17.0, 6.0)], [(0.0, 0.0), (5.0, 9.56070905565004e-17), (5.0, 4.0)], [(5.0, 4.0), (17.0, 6.0), (16.67020769853194, 13.254679445519704)], [(16.67020769853194, 13.254679445519704), (17.0, 6.0), (17.0, 13.260471371184234)]], 'edges': [[(0.0, 0.0), (-0.14833769437282762, 15.74241785360307), 0, 0], [(-0.14833769437282762, 15.74241785360307), (16.688083576921848, 16.100056389428275), 0, 5], [(16.688083576921848, 16.100056389428275), (16.67020769853194, 13.254679445519704), 0, 4], [(16.67020769853194, 13.254679445519704), (17.0, 13.260471371184234), 0, 3], [(22.995041349872604, 6.0), (23.07159441873938, 4.0), 0, 2], [(23.07159441873938, 4.0), (5.0, 4.0), 10.3, -1], [(5.0, 4.0), (5.0, 9.56070905565004e-17), 10.3, -1], [(5.0, 9.56070905565004e-17), (0.0, 0.0), 0, 1]]}, {'height': 26.0, 'triangles': [[(17.0, 13.260471371184234), (17.0, 6.0), (22.713295043992378, 13.360810220960367)], [(22.713295043992378, 13.360810220960367), (17.0, 6.0), (22.995041349872604, 6.0)]], 'edges': [[(22.713295043992378, 13.360810220960367), (22.995041349872604, 6.0), 0, 2], [(22.995041349872604, 6.0), (17.0, 6.0), 23.3, -1], [(17.0, 6.0), (17.0, 13.260471371184234), 23.3, -1], [(17.0, 13.260471371184234), (22.713295043992378, 13.360810220960367), 0, 3]]}]
SOURCES=['va-praefcke-aerial-a-2011','va-praefcke-aerial-b-2011','ea-lidar-composite-2022-tq27ne']
def build(ctx,feature):
 base=float(feature.get('base_m',0));tx,ty=AXIS
 def p(u,v,z):return(ORIGIN[0]+tx*u-ty*v,ORIGIN[1]+ty*u+tx*v,base+z)
 brick=ctx.material('RCM South estimated reddish masonry',(.32,.19,.135),.86)
 trim=ctx.material('RCM South estimated pale concrete',(.59,.57,.51),.86)
 membrane=ctx.material('RCM South grey roof membrane',(.17,.19,.19),.87)
 glass=ctx.material('RCM South estimated grey glass',(.13,.21,.24),.19,0,.28)
 metal=ctx.material('RCM South dark coated metal',(.07,.075,.08),.43,.55)
 wall=ctx.mesh('complete mapped outline and stepped closed walls');roof=ctx.mesh('EA interpreted flat roof levels');windows=ctx.mesh('estimated recessed windows and frames');bands=ctx.mesh('simplified concrete floor bands');entry=ctx.mesh('estimated north courtyard entrance')
 entrances=[]
 for zone in ZONES:
  h=zone['height']
  for tri in zone['triangles']:roof.face([p(u,v,h) for u,v in tri],membrane)
  for aa,bb,z0,edge in zone['edges']:
   length=math.dist(aa,bb);sx,sy=(bb[0]-aa[0])/length,(bb[1]-aa[1])/length
   # Polygon ordering may be clockwise. Original boundary identifies outward normal unambiguously.
   midpoint=((aa[0]+bb[0])/2,(aa[1]+bb[1])/2)
   # derive outward with original ring orientation (source is counterclockwise)
   ring=feature['geometry'][0]['outer']
   if edge>=0:
    A,B=ring[edge],ring[(edge+1)%len(ring)];ll=math.dist(A,B);out=((B[1]-A[1])/ll,-(B[0]-A[0])/ll)
    nu,nv=out[0]*tx+out[1]*ty,-out[0]*ty+out[1]*tx
   else:nu,nv=sy,-sx
   def q(s,d,z):return p(aa[0]+sx*s+nu*d,aa[1]+sy*s+nv*d,z)
   angle=math.atan2(ty*sx+tx*sy,tx*sx-ty*sy)
   def bx(m,s,d,z,w,dep,hei,mat):m.box(*q(s,d,z),w,dep,hei,mat,angle)
   apertures=[]
   if edge in [1,3,5] and length>3 and z0==0:
    count=max(1,int(length/3.4));centers=[length*(i+.5)/count for i in range(count)]
    for k,c in enumerate(centers):
     for lo in [.95,5.25,9.55,13.85,18.15]:
      if lo+2.7<h-.7:apertures.append((c-.88,c+.88,lo,lo+2.7,False))
    if edge==5:
     c=centers[len(centers)//2];apertures=[v for v in apertures if not(abs((v[0]+v[1])/2-c)<.1 and v[2]<2)]
     apertures.append((c-.85,c+.85,.08,2.9,True))
   xs=sorted(set([0,length]+[x for ap in apertures for x in ap[:2]]))
   for left,right in zip(xs,xs[1:]):
    mid=(left+right)/2;aps=sorted([ap for ap in apertures if ap[0]<mid<ap[1]],key=lambda x:x[2]);zz=z0
    for ap in aps+[(0,0,h,h,False)]:
     if ap[2]>zz:wall.face([q(left,0,zz),q(right,0,zz),q(right,0,ap[2]),q(left,0,ap[2])],brick if h<25 else trim)
     zz=ap[3]
   for left,right,lo,hi,isdoor in apertures:
    depth=.40 if isdoor else .16;c=(left+right)/2;w=right-left
    for s in [left,right]:wall.face([q(s,0,lo),q(s,-depth,lo),q(s,-depth,hi),q(s,0,hi)],trim)
    for z in [lo,hi]:wall.face([q(left,0,z),q(right,0,z),q(right,-depth,z),q(left,-depth,z)],trim)
    bx(entry if isdoor else windows,c,-depth,(lo+hi)/2,w,.045,hi-lo,glass)
    for s in [left+.035,right-.035]:bx(windows,s,-depth+.04,(lo+hi)/2,.07,.055,hi-lo,metal)
    for z in [lo+.035,hi-.035]:bx(windows,c,-depth+.04,z,w,.055,.07,metal)
    if not isdoor:bx(windows,c,-depth+.04,(lo+hi)/2,.04,.055,hi-lo,metal)
    else:
     bx(entry,c,.30,.04,w+.24,.90,.08,trim)
     worldn=(tx*nu-ty*nv,ty*nu+tx*nv,0)
     entrances.append({'name':'Estimated north courtyard access','threshold_xyz':q(c,0,.08),'outward_normal':worldn,'clear_width_m':1.52,'door_leaf_xyz':q(c,-depth,1.49),'door_leaf_depth_m':.3325,'door_glass_front_depth_m':.3775,'estimated':True,'supporting_surface':'finite authored threshold at .08 m; courtyard approach to be checked in assembly'})
   if edge>=0:
    for z in [4.55,8.85,13.15,17.45,21.75,h-.10]:
     if z0+.1<z<h:bx(bands,length/2,-.025,z,length,.10,.18,trim)
 # Original footprint floor closes the mapped envelope without extending into adjacent buildings.
 roof.surface(feature['geometry'],base,membrane)
 objs=[m.done() for m in [wall,roof,windows,bands,entry]]
 return {'created':[o.name for o in objs if o],'parameters':{'main_roof_m':23.3,'south_low_roof_m':10.3,'northeast_high_roof_m':26.,'full_mapped_outline_preserved':True,'facade_confidence':'low: editable estimated modern five-level rhythm'},'interfaces':{'entrances':entrances},'evidence_source_ids':SOURCES,'uncertainty':['EA 1 m roof levels support three broad height zones; exact step boundaries estimated rather than surveyed.','2011 licensed aerials resolve broad modern roof mass only; five-level window rhythm, reddish masonry, concrete strips and optical values estimated.','North courtyard door location and threshold estimated; no public street entrance claim.','West/east adjoining walls have no speculative apertures. Modern 1965 South Building not the Victorian main RCM or neighbouring concert hall.','Later courtyard redevelopment may differ from 2011 aerials; concealed elevations kept simple.']}
