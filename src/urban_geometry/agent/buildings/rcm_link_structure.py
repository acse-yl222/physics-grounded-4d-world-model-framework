"""RCM narrow Link Structure; sparse evidence, no asserted independent entrance."""
import math
ORIGIN=[715.7463632603176, -69.78918328694999]
AXIS=(0.17345339934597245, -0.9848420778253367)
ZONES=[{'height': 16.8, 'triangles': [[(0.062484954079093984, 4.1), (0.0, 0.0), (42.195668405363435, 4.1)], [(42.195668405363435, 4.1), (0.0, 0.0), (42.28059575529322, 0.0)]], 'edges': [[(42.28059575529322, 0.0), (0.0, 0.0), 0, False], [(0.0, 0.0), (0.062484954079093984, 4.1), 0, False], [(0.062484954079093984, 4.1), (42.195668405363435, 4.1), 6.5, True], [(42.195668405363435, 4.1), (42.28059575529322, 0.0), 0, False]]}, {'height': 6.5, 'triangles': [[(0.08602486098710527, 5.644589729563992), (0.062484954079093984, 4.1), (42.16673695413621, 5.496710837317826)], [(42.16673695413621, 5.496710837317826), (0.062484954079093984, 4.1), (42.195668405363435, 4.1)]], 'edges': [[(0.08602486098710527, 5.644589729563992), (42.16673695413621, 5.496710837317826), 0, False], [(42.16673695413621, 5.496710837317826), (42.195668405363435, 4.1), 0, False], [(0.062484954079093984, 4.1), (0.08602486098710527, 5.644589729563992), 0, False]]}]
def build(ctx,feature):
 base=float(feature.get('base_m',0));tx,ty=AXIS
 def p(u,v,z):return(ORIGIN[0]+tx*u-ty*v,ORIGIN[1]+ty*u+tx*v,base+z)
 concrete=ctx.material('RCM Link estimated pale structure',(.61,.60,.55),.82)
 metal=ctx.material('RCM Link estimated coated framing',(.12,.14,.15),.39,.55)
 glass=ctx.material('RCM Link estimated blue grey glazing',(.17,.25,.28),.20,0,.30)
 roofmat=ctx.material('RCM Link grey roof membrane',(.18,.20,.21),.88)
 wall=ctx.mesh('complete narrow mapped envelope');roof=ctx.mesh('EA interpreted roof and eastern low strip');glazing=ctx.mesh('estimated recessed linear glazing');frames=ctx.mesh('simplified exportable metal curtain framing')
 for zone in ZONES:
  h=zone['height']
  for t in zone['triangles']:roof.face([p(u,v,h) for u,v in t],roofmat)
  for a,b,z0,internal in zone['edges']:
   ll=math.dist(a,b);sx,sy=(b[0]-a[0])/ll,(b[1]-a[1])/ll
   def q(s,d,z):return p(a[0]+sx*s-sy*d,a[1]+sy*s+sx*d,z)
   angle=math.atan2(ty*sx+tx*sy,tx*sx-ty*sy)
   def bx(m,s,d,z,w,dep,hei,mat):m.box(*q(s,d,z),w,dep,hei,mat,angle)
   # Short ends close to the main/south buildings remain plain, with no external door claim.
   if ll<10 or internal:
    wall.face([q(0,0,z0),q(ll,0,z0),q(ll,0,h),q(0,0,h)],concrete);continue
   # Glazing replaces the wall plane. Thin outer reveals separate glass from opaque structure.
   for lo,hi in [(0,.65),(h-.55,h)]:wall.face([q(0,0,lo),q(ll,0,lo),q(ll,0,hi),q(0,0,hi)],concrete)
   for ss in [0,ll]:wall.face([q(ss,0,.65),q(ss,-.12,.65),q(ss,-.12,h-.55),q(ss,0,h-.55)],concrete)
   # Zone exterior order is clockwise: left normal points outside. Glass is recessed inward.
   bx(glazing,ll/2,-.12,h/2+.05,ll,.035,h-1.2,glass)
   count=max(1,round(ll/2.8))
   for k in range(count+1):bx(frames,ll*k/count,-.07,h/2,.075,.065,h-1.2,metal)
   for z in [.70,h-.60]+([4.5,8.5,12.5] if h>10 else [3.2]):bx(frames,ll/2,-.07,z,ll,.065,.09,metal)
   for z in [.55,h-.30]:bx(frames,ll/2,0,z,ll,.15,.16,concrete)
 roof.surface(feature['geometry'],base,concrete)
 obs=[m.done() for m in [wall,roof,glazing,frames]]
 return {'created':[o.name for o in obs if o],'parameters':{'main_roof_m':16.8,'east_low_strip_roof_m':6.5,'complete_mapped_outline':True,'height_confidence':'moderate native1m mass; low interpretation of narrow eastern strip','facade_confidence':'low estimated curtain glazing; not confirmed panel or occupied storey count'},'interfaces':{'entrances':[]},'evidence_source_ids':['ea-lidar-composite-2022-tq27ne','va-praefcke-aerial-b-2011'],'uncertainty':['OSM one-level tag conflicts with EA inset median16.45m/p9517.54m; interpreted roof envelope does not assert four occupied storeys.','Main height16.8 and eastern1.4m low strip6.5 are approximate. DSM may include adjacent roofs or later courtyard redevelopment.','2011 PD aerial does not resolve this narrow facade. Glass, framing rhythm and all PBR optical values are estimated reversible completion.','Short connecting ends are plain closure faces; no independent public entrance is invented.','Adjacent full-scene occlusion and connection seams require assembly review.']}
