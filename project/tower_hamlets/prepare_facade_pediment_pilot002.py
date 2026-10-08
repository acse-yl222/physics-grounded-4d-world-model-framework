from pathlib import Path
import json,math,hashlib
from shapely.geometry import Polygon,box
from shapely import constrained_delaunay_triangles
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/facade-pediment-pilot002';O.mkdir(exist_ok=True);parts=[]
def extrude(name,p,front,back,kind):
 if p.is_empty:return
 for k,poly in enumerate(getattr(p,'geoms',[p])):
  if not isinstance(poly,Polygon):continue
  vv=[];ff=[];index={}
  def idx(x,z,y):
   key=(round(x,8),round(y,8),round(z,8))
   if key not in index:index[key]=len(vv);vv.append(key)
   return index[key]
  for t in constrained_delaunay_triangles(poly).geoms:
   coords=list(t.exterior.coords)[:-1];ff.append([idx(x,z,front) for x,z in coords]);ff.append([idx(x,z,back) for x,z in reversed(coords)])
  for ring in [poly.exterior,*poly.interiors]:
   coords=list(ring.coords)
   for (a,b),(c,d) in zip(coords,coords[1:]):ff.append([idx(a,b,front),idx(c,d,front),idx(c,d,back),idx(a,b,back)])
  parts.append({'name':name+('_'+str(k) if k else ''),'vertices':vv,'faces':ff,'kind':kind})
def arch(radius,spring,base):return Polygon([(-radius,base),(radius,base),(radius,spring)]+[(radius*math.cos(t),spring+radius*math.sin(t))for t in [i*math.pi/48 for i in range(1,49)]])
outer=Polygon([(-22,0),(22,0),(22,8),(0,23),(-22,8)]);opening=arch(5.5,8,0);squares=[box(c-2.4,.8,c+2.4,6.5) for c in [-18,-11.5,11.5,18]];wall=outer.difference(opening)
for square in squares:wall=wall.difference(square)
extrude('Pediment_wall_true_openings',wall,0,1.2,'stone')
for i,(outerr,innerr,depth)in enumerate([(5.75,5.5,-.15),(6.05,5.75,-.28),(6.35,6.05,-.38)]):extrude('Arch_moulding_'+str(i),arch(outerr,8,0).difference(arch(innerr,8,0)),depth,.02,'trim')
for i,b in enumerate(squares):
 for k,w in enumerate([.15,.32,.5]):extrude('Square_reveal_frame_%d_%d'%(i,k),b.buffer(w,join_style=2).difference(b.buffer(max(0,w-.15),join_style=2)),-.08-.12*k,.03,'trim')
# Gable sloping cornice strips follow the facade silhouette; no guessed rear roof.
from shapely.geometry import LineString
# Mitred continuous V profiles: no overlapping left/right caps at the apex.
for k,width in enumerate([.28,.24,.18]):
 off=k*.24
 line=LineString([(-22,8-off),(0,23-off),(22,8-off)])
 profile=line.buffer(width/2,cap_style=2,join_style=2)
 extrude('Gable_cornice_'+str(k),profile,-.22-.13*k,.1,'trim')
# Horizontal cornices split around the arch rather than bridging the void.
for k in range(3):
 strip=box(-22,7.55+k*.2,22,7.75+k*.2).difference(arch(6.4,8,0));extrude('Spring_cornice_'+str(k),strip,-.15-k*.12,.1,'trim')
# Loggia slab, rear backing and visible central balustrade. Depths unmeasured.
extrude('Loggia_slab',box(-22,-.35,22,0),-.05,3.7,'stone');extrude('Plain_estimated_rear',outer,4.1,4.25,'backing')
extrude('Central_rail',box(-5.3,1.7,5.3,2.0),.20,.55,'trim');extrude('Central_lower_rail',box(-5.3,.15,5.3,.35),.20,.55,'trim')
for i in range(15):
 x=-5.0+i*10/14
 # Straight restrained balusters; exact turned section not recovered.
 extrude('Baluster_%02d'%i,Polygon([(x-.14,.35),(x+.14,.35),(x+.10,.65),(x+.08,1.45),(x+.16,1.7),(x-.16,1.7),(x-.08,1.45),(x-.10,.65)]),.25,.5,'trim')
extrude('Arch_vault_soffit',arch(5.8,8,0).difference(arch(5.5,8,0)).intersection(box(-10,8,10,20)),1.2,3.5,'stone')
# Panel joints visible on pediment, shallow dark strips; no inferred brick color.
for x in [-12,-6,0,6,12]:extrude('Pediment_panel_joint_'+str(x),box(x-.015,8,x+.015,23).intersection(wall),-.012,-.003,'joint')
# Source-visible orthogonal/cross lattice: count and 0.045m bars are estimates.
lattice_clip=arch(5.15,8,2.25).intersection(box(-5.15,2.25,5.15,11.8))
barpolys=[]
def bar(a,b):
 p=LineString([a,b]).buffer(.0225,cap_style=2).intersection(lattice_clip)
 if not p.is_empty:barpolys.append(p)
nx,ny=12,10;xs=[-5.15+i*10.3/nx for i in range(nx+1)];zs=[2.25+i*9.55/ny for i in range(ny+1)]
for x in xs:bar((x,zs[0]),(x,zs[-1]))
for z in zs:bar((xs[0],z),(xs[-1],z))
for i in range(nx):
 for j in range(ny):
  bar((xs[i],zs[j]),(xs[i+1],zs[j+1]));bar((xs[i+1],zs[j]),(xs[i],zs[j+1]))
# Union intersections into actual open lattice, rather than stacked coplanar bars.
from shapely.ops import unary_union
from shapely import set_precision
lattice=set_precision(unary_union(barpolys+[lattice_clip.difference(lattice_clip.buffer(-.06))]),.00001)
extrude('Rear_open_cross_lattice',lattice,3.40,3.47,'trim')
# Curved soffit coffers: recess is base R5.5, raised framing projects to R5.33.
def sector(r0,r1,t0,t1):
 n=max(2,math.ceil((t1-t0)/(math.pi/96)))
 ts=[t0+(t1-t0)*i/n for i in range(n+1)]
 return Polygon([(r1*math.cos(t),8+r1*math.sin(t))for t in ts]+[(r0*math.cos(t),8+r0*math.sin(t))for t in reversed(ts)])
for i in range(9):
 t=math.pi*i/8;half=.011
 for j,(ya,yb) in enumerate([(1.32,2.36),(2.46,3.40)]):extrude('Coffer_longitudinal_rib_%02d_%d'%(i,j),sector(5.33,5.52,max(0,t-half),min(math.pi,t+half)),ya,yb,'trim')
for i,y in enumerate([1.22,2.36,3.40]):extrude('Coffer_curved_cross_rib_%02d'%i,sector(5.33,5.52,0,math.pi),y,y+.10,'trim')
# Additional source-visible horizontal panel breaks, clipped to masonry only.
for z in [14.5,19.0]:extrude('Pediment_horizontal_joint_'+str(z),box(-22,z-.015,22,z+.015).intersection(wall),-.012,-.003,'joint')
r={'coordinate_system':'LOCAL FACADE ONLY; x right,y inward,z up,m; no georeferenced transform','placement':'Unassigned; candidate10Cabot identity/orientation still unproven. No building_id','dimensions_status':'All dimensions visually inferred;44m width provisional mapped-face scale, not correspondence proof','components':parts,'source_photo':'pexels-altaf-shah-19330277.jpeg','source_sha256':hashlib.sha256((R/'references/pexels-altaf-shah-19330277.jpeg').read_bytes()).hexdigest(),'license':'Existing Pexels photo permissions ledger; photograph not embedded','uncertainties':['Global owner and edge pending','Single facade silhouette only; roof volume unmodeled','Widths heights depths profile and baluster count estimated','Rear dark backing moved to4.1m and slab schematic','Lattice12columns10rows,coffer8angularby2depthcells andmemberthicknesses inferred; no exactcount claim','No actual entrance or ground threshold inferred']};(O/'authoring.json').write_text(json.dumps(r,indent=2));print(len(parts))
