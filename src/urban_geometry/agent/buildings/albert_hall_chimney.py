"""Independent Royal Albert Hall chimney. Photo-estimated, no invented public entry.
CC BY2.0 mira66 + CC BY-SA4.0 No Swan So Fine photographic adaptation.
"""
import math

def build(ctx,feature):
 red=ctx.material('RAH chimney inset red brick',(.40,.14,.07),.9)
 dark=ctx.material('RAH chimney dark brick piers',(.16,.15,.11),.94)
 mortar=ctx.material('RAH chimney weathered mortar',(.31,.28,.20),.95)
 iron=ctx.material('RAH chimney iron ties',(.11,.075,.05),.62,.65)
 black=ctx.material('RAH chimney unverified flue recess',(.025,.024,.020),.97)
 shell=ctx.mesh('Chimney exact mapped base and profiled shaft');detail=ctx.mesh('Chimney corner piers brick joints and top cornices')
 r=feature['geometry'][0]['outer'];cx=sum(q[0] for q in r)/4;cy=sum(q[1] for q in r)/4;base=float(feature.get('base_m',0))
 def ring(scale,z):return[(cx+(q[0]-cx)*scale,cy+(q[1]-cy)*scale,base+z) for q in r]
 # Contiguous rings, no duplicate coplanar box faces; profile stays inside mapped base.
 profile=[(1.,0),(1.,.25),(.96,.65),(.85,1.3),(.83,1.7),(.83,5.1),(.95,5.3),(.98,5.6),(.9,5.85),(.78,6.05),(.75,24.2),(.87,24.35),(.89,24.65),(.78,24.9),(.78,25.7),(.83,25.8),(.87,25.95),(.91,26.1),(.95,26.25),(.99,26.4),(.95,26.55),(.81,26.65),(.81,27.5)]
 for (s0,z0),(s1,z1) in zip(profile,profile[1:]):
  p0,p1=ring(s0,z0),ring(s1,z1)
  for i in range(4):shell.face([p0[i],p0[(i+1)%4],p1[(i+1)%4],p1[i]],red if 6<=z0<24.2 or 1.7<=z0<5.1 else dark)
 shell.surface(feature['geometry'],base,dark)
 # Actual recessed top mouth as estimated square rim and finite dark inner floor.
 top=ring(.81,27.5);inner=ring(.58,27.5);bottom=ring(.58,26.9)
 for i in range(4):
  j=(i+1)%4;shell.face([top[i],top[j],inner[j],inner[i]],dark);shell.face([inner[i],inner[j],bottom[j],bottom[i]],dark)
 shell.face(list(reversed(bottom)),black)
 # Long corner piers sit on shaft face; red central panels remain visibly recessed.
 rr=ring(.758,6.1)
 for i,(aa,bb) in enumerate(zip(rr,rr[1:]+rr[:1])):
  dx,dy=bb[0]-aa[0],bb[1]-aa[1];L=math.hypot(dx,dy);tx,ty=dx/L,dy/L;angle=math.atan2(ty,tx)
  for u in(.18,L-.18):detail.box(aa[0]+tx*u,aa[1]+ty*u,base+15.15,.32,.075,17.9,dark,angle)
  # Geometry mortar lines, shallow and spaced to represent courses without image textures.
  for j in range(1,92):
   z=6.1+j*.195
   if z>=24.1:break
   detail.box((aa[0]+bb[0])/2,(aa[1]+bb[1])/2,base+z,L-.65,.009,.008,mortar,angle)
  if i==1:
   detail.beam((aa[0]+tx*L/2,aa[1]+ty*L/2,base+.2),(aa[0]+tx*L/2,aa[1]+ty*L/2,base+27.4),.015,iron,8)
 objects=[m.done() for m in(shell,detail)]
 return {'created':[o.name for o in objects],'parameters':{'overall_height_m':27.5,'height_basis':'Visual proportion estimate from2023 photograph; native1m composite fails to resolve chimney, not a measured height','mapped_base_preserved':True},'interfaces':{'entrances':[]},'evidence_source_ids':list(dict.fromkeys(feature.get('evidence_source_ids',[])+['rah-chimney-mira66-2010','rah-chimney-noswansofine-2023','ea-lidar-composite-2022-tq27ne'])),'uncertainty':['Top mouth depth and internal flue layout estimated; no internal equipment or public door invented.','Mortar rhythm, piers and cornice dimensions simplified; full-scene ground check pending.','CC BY-SA4.0 photo-derived contribution; attribution required.']}
