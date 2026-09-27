"""194 Queen Gate only: EA-informed layered roof, explicitly estimated residential elevation."""
import math
ROOF=[[(494.6023743932601, 26.002983671613038, 22.2), (493.2504560148809, 34.391068113036454, 22.2), (496.41779874281025, 34.84991355837289, 26.4)], [(496.41779874281025, 34.84991355837289, 26.4), (497.76620768448373, 26.48360369439437, 26.4), (494.6023743932601, 26.002983671613038, 22.2)], [(497.76620768448373, 26.48360369439437, 26.4), (496.41779874281025, 34.84991355837289, 26.4), (504.1381966421379, 35.968349331380445, 26.4)], [(504.1381966421379, 35.968349331380445, 26.4), (505.4780513318413, 27.655114999923857, 26.4), (497.76620768448373, 26.48360369439437, 26.4)], [(505.4780513318413, 27.655114999923857, 26.4), (504.1381966421379, 35.968349331380445, 26.4), (509.0871696545275, 36.68529533971862, 22.599999999999998)], [(509.0871696545275, 36.68529533971862, 22.599999999999998), (510.4215408493782, 28.406083785519687, 22.599999999999998), (505.4780513318413, 27.655114999923857, 26.4)], [(509.48440131230745, 36.74284134991467, 22.599999999999998), (521.6777165484382, 38.448936462402344, 22.599999999999998), (522.4750439083437, 33.09041828755289, 22.599999999999998)], [(522.4750439083437, 33.09041828755289, 22.599999999999998), (523.0887860675575, 30.330373444594443, 22.599999999999998), (510.4215408493782, 28.406083785519687, 22.599999999999998)], [(510.4215408493782, 28.406083785519687, 22.599999999999998), (509.0871696545275, 36.68529533971862, 22.599999999999998), (509.48440131230745, 36.74284134991467, 22.599999999999998)], [(509.48440131230745, 36.74284134991467, 22.599999999999998), (522.4750439083437, 33.09041828755289, 22.599999999999998), (510.4215408493782, 28.406083785519687, 22.599999999999998)]]
def build(ctx,feature):
 base=float(feature.get('base_m',0));ring=feature['geometry'][0]['outer'];a,b=ring[:2];L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L
 def rh(x,y):
  v=-(x-a[0])*uy+(y-a[1])*ux
  return 22.2+4.2*max(0,min(1,v/3.2))-3.8*max(0,min(1,(v-11)/5))
 plaster=ctx.material('194 estimated pale stucco',(.73,.71,.65),.86)
 trimat=ctx.material('194 estimated pale dressings',(.79,.77,.71),.72)
 slate=ctx.material('194 dark slate roof',(.12,.14,.15),.84)
 glass=ctx.material('194 blue grey glass',(.14,.20,.22),.2,0,.28)
 iron=ctx.material('194 painted black metal',(.025,.03,.03),.44,.65)
 timber=ctx.material('194 estimated dark timber',(.09,.045,.027),.69)
 stone=ctx.material('194 estimated threshold stone',(.52,.50,.45),.87)
 wall=ctx.mesh('complete footprint party walls and real openings');roof=ctx.mesh('EA layered continuous roof');windows=ctx.mesh('estimated sash windows');details=ctx.mesh('simplified frontage bands and portico');entry=ctx.mesh('estimated street door and low threshold')
 for tr in ROOF:roof.face([(x,y,base+z) for x,y,z in tr],slate)
 entrances=[]
 for ei,(A,B) in enumerate(zip(ring,ring[1:]+ring[:1])):
  ll=math.dist(A,B);tx,ty=(B[0]-A[0])/ll,(B[1]-A[1])/ll;nx,ny=ty,-tx
  def p(s,d,z):return(A[0]+tx*s+nx*d,A[1]+ty*s+ny*d,base+z)
  def bx(m,s,d,z,w,dep,hh,mat):m.box(*p(s,d,z),w,dep,hh,mat,math.atan2(ty,tx))
  apertures=[]
  if ei in [0,2]:
   count=3 if ei==0 else 1
   for k in range(count):
    c=ll*(k+.5)/count
    for row,lo in enumerate([1.05,5.45,9.85,14.25,18.65]):
     hi=lo+(2.8 if row<3 else 2.5);door=ei==0 and k==0 and row==0
     if hi>min(rh(*A),rh(*B))-.4:continue
     apertures.append((c-(.79 if door else .67),c+(.79 if door else .67),.08 if door else lo,3.4 if door else hi,door))
  xs=[0,ll]+[xx for op in apertures for xx in op[:2]]
  # Split boundary wherever a roof plane changes so all sloping wall closures remain planar.
  va=-(A[0]-a[0])*uy+(A[1]-a[1])*ux;vb=-(B[0]-a[0])*uy+(B[1]-a[1])*ux
  if abs(vb-va)>1e-8:
   for cut in [3.2,11,16]:
    t=(cut-va)/(vb-va)
    if 0<t<1:xs.append(t*ll)
  xs=sorted(set(xs))
  for l,r in zip(xs,xs[1:]):
   aps=sorted([op for op in apertures if op[0]<(l+r)/2<op[1]],key=lambda x:x[2]);z=0
   for op in aps:
    if op[2]>z:wall.face([p(l,0,z),p(r,0,z),p(r,0,op[2]),p(l,0,op[2])],plaster)
    z=op[3]
   wall.face([p(l,0,z),p(r,0,z),p(r,0,rh(*p(r,0,0)[:2])),p(l,0,rh(*p(l,0,0)[:2]))],plaster)
  for l,r,lo,hi,door in apertures:
   c=(l+r)/2;w=r-l;d=.43 if door else .22
   bx(entry if door else windows,c,-d,(lo+hi)/2,w,.06,hi-lo,timber if door else glass)
   for ss in [l,r]:wall.face([p(ss,0,lo),p(ss,-d,lo),p(ss,-d,hi),p(ss,0,hi)],trimat)
   for zz in [lo,hi]:wall.face([p(l,0,zz),p(r,0,zz),p(r,-d,zz),p(l,-d,zz)],trimat)
   for ss in [l-.055,r+.055]:bx(windows,ss,.005,(lo+hi)/2,.11,.16,hi-lo+.14,trimat)
   bx(windows,c,.035,hi+.08,w+.26,.24,.16,trimat)
   if not door:
    bx(windows,c,.04,lo-.07,w+.28,.26,.14,trimat);bx(windows,c,-d+.05,(lo+hi)/2,.045,.05,hi-lo,trimat);bx(windows,c,-d+.05,(lo+hi)/2,w,.05,.05,trimat)
   else:
    bx(entry,c,.31,.04,w+.25,.94,.08,stone)
    bx(details,c,.32,3.73,w+.58,.9,.24,trimat)
    # Plain rectangular portico pilasters sit outside the door approach width.
    for ss in [l-.24,r+.24]:bx(details,ss,.25,1.79,.20,.34,3.58,trimat)
    entrances.append({'name':'Estimated194 Queen Gate street entrance','threshold_xyz':p(c,0,.08),'outward_normal':[nx,ny,0],'clear_width_m':1.4,'door_leaf_xyz':p(c,-.43,1.74),'door_leaf_depth_m':.4,'estimated':True,'supporting_surface':'finite authored threshold .08m; precise step/entrance arrangement unverified'})
  if ei==0:
   for zz in [4.65,9.05,13.45,17.85,21.85,22.13]:bx(details,ll/2,.025,zz,ll,.20,.20,trimat)
 roof.surface(feature['geometry'],base,plaster)
 obs=[m.done() for m in [wall,roof,windows,details,entry]]
 return {'created':[o.name for o in obs if o],'parameters':{'front_eaves_m':22.2,'main_roof_m':26.4,'rear_roof_m':22.6,'full_mapped_outline':True,'facade_confidence':'low: exact194licensedfacade unavailable; pale residential type is neighbourhood analogy'},'interfaces':{'entrances':entrances},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','va-praefcke-aerial-a-2011'],'uncertainty':['EA140inset samples median23.629,p9526.413 supports26.4main roof and~22.6rear. Roof break axes/eaves22.2estimated.','Existing licensed186–188/197–200photos actually inspected only as neighbourhood architectural analogy, not misidentified as194. Limitedtargetsearch did not obtain a verified194street photo.','Three-bayfive-level pale stucco sash frontage, portico and west entrance are low-confidence editable estimates. Fine ornamental and dormer features omitted.','South193/north195/eastJayMews common walls left blank. One recessed rear lightwell edge has estimated windows; no adjacent footprint merged.','194urban residential is separate from protected campus; neighboring193 remains frozen.','Full-scene ground and doorway clearance remains coordinator review.']}
