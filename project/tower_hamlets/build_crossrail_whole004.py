"""Photo-led west terminal fragment. Scene ENU, estimated unsurveyed details."""
import bpy,math,json,shutil,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/crossrail-whole-building-004';O.mkdir(parents=True,exist_ok=True)
d=json.loads((R/'references/crossrail_lidar_review.json').read_text());U=Vector((*d['axis_local_xy'],0));V=Vector((-U.y,U.x,0));C=Vector((*d['mapped_part_extent']['centroid_local_xy'],0));fit=d['upper_envelope_circle_fit'];rad=fit['radius_m'];zc=fit['circle_center_z_odn_m']-d['ground_scalar_m_odn'];bc=fit['cross_axis_center_m'];apex=zc+rad
bpy.ops.wm.read_factory_settings(use_empty=True)
def xyz(a,b,z):return C+a*U+b*V+Vector((0,0,z))
def mat(n,c,rough=.5,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
wood=mat('Warm laminated timber',(.58,.36,.18));white=mat('Off-white roof membranes',(.81,.83,.79),.45);silver=mat('Brushed silver metal',(.56,.61,.62),.3,.68);black=mat('Charcoal recessed screen',(.047,.062,.068),.8);concrete=mat('Light terrace structure',(.43,.46,.44),.7);glass=mat('Dark restaurant glazing',(.065,.11,.12),.21,.25)
OWNER_IDS=['overture-building-7d04c4cc-c183-4597-bb98-063679b2ec63','overture-part-c9f4e448-eff2-39ad-ac25-e7f6cf708826']
registry=[]
def mesh(n,vs,fs,m):
 me=bpy.data.meshes.new(n);me.from_pydata([tuple(v) for v in vs],[],fs);me.update();ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(m);ob['component_id']=n;ob['building_id']=OWNER_IDS[0];ob['source_owner_ids']=OWNER_IDS;ob['owner']='Crossrail Place parent 7d04c4cc-c183-4597-bb98-063679b2ec63 and central part c9f4e448-eff2-39ad-ac25-e7f6cf708826';ob['accuracy']='Photo-supported feature; estimated dimensions; terminal study only';registry.append(ob);return ob
verts=[];faces=[]
def beam(a,b,w,h):
 t=(b-a).normalized();side=t.cross(Vector((0,0,1)))
 if side.length<.001:side=U.copy()
 side.normalize();normal=side.cross(t).normalized();start=len(verts)
 for p in (a,b):
  for x,y in ((-1,-1),(1,-1),(1,1),(-1,1)):verts.append(p+side*x*w/2+normal*y*h/2)
 faces.extend(tuple(start+k for k in f) for f in ((0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)))
def flush(n,m):
 global verts,faces
 ob=mesh(n,verts,faces,m);verts=[];faces=[];return ob
# Complete tilted terminal arch, extended below fitted upper LiDAR band.
def shell(t,s,offset=0):
 z=zc+(rad-offset)*math.cos(t);b=bc+(rad-offset)*math.sin(t);a=158.0-s-.45*(apex-z)*(1-2*s/299.1);return xyz(a,b,z)
tmax=math.radians(105)
# Silver continuous rim with round bevelled tube section.
curve=bpy.data.curves.new('Full terminal silver rim','CURVE');curve.dimensions='3D';curve.bevel_depth=.36;curve.bevel_resolution=4;sp=curve.splines.new('POLY');sp.points.add(160)
for i,p in enumerate(sp.points):p.co=(*shell(-tmax+2*tmax*i/160,0),1)
ob=bpy.data.objects.new('Full terminal silver rim',curve);bpy.context.collection.objects.link(ob);curve.materials.append(silver);bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.convert(target='MESH');ob=bpy.context.object;ob.select_set(False);ob['component_id']=ob.name;ob['building_id']=OWNER_IDS[0];ob['source_owner_ids']=OWNER_IDS;registry.append(ob)
# Triangulated timber and actual thin membrane panels: full end barrel fragment.
nt=14;ns=62;dt=2*tmax/nt;ds=299.1/ns
nodes={}
for j in range(nt+1):
 for k in range(ns+1):nodes[j,k]=shell(-tmax+j*dt,(0 if k==0 else ns*ds if k==ns else k*ds+((j%2)*ds/2)),.34)
edge_set=set();triangles=[]
for j in range(nt):
 for k in range(ns):
  a=(j,k);b=(j,k+1);c=(j+1,k);e=(j+1,k+1)
  pair=[(a,b,c),(b,e,c)] if j%2==0 else [(a,b,e),(a,e,c)]
  for tri in pair:
   triangles.append(tri)
   for x,y in zip(tri,tri[1:]+tri[:1]):edge_set.add(tuple(sorted((x,y))))
for a,b in edge_set:beam(nodes[a],nodes[b],.23,.48)
flush('Triangular timber barrel frame',wood)
# White panels lie outside timber, triangles inset slightly to show beams.
pv=[];pf=[]
for tri in triangles:
 avg_s=sum((0 if k==0 else ns*ds if k==ns else k*ds+((j%2)*ds/2)) for j,k in tri)/3
 avg_theta=sum(-tmax+j*dt for j,k in tri)/3
 # Explicit completion hypothesis: central crown opening and open side bands.
 if 105<avg_s<195 and abs(avg_theta)<.70:continue
 if 36<avg_s<265 and abs(avg_theta)>.92:continue
 pts=[]
 for j,k in tri:pts.append(shell(-tmax+j*dt,(0 if k==0 else ns*ds if k==ns else k*ds+((j%2)*ds/2)),.035))
 cen=sum(pts,Vector())/3;pts=[cen+(p-cen)*.965 for p in pts];start=len(pv);pv.extend(pts);pf.append((start,start+1,start+2))
ob=mesh('Triangular white roof membranes',pv,pf,white);sol=ob.modifiers.new('Membrane thickness estimated','SOLIDIFY');sol.thickness=.035;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=sol.name)
# Terrace slab with fascia; no furniture/signs invented.
def box(n,a0,a1,b0,b1,z0,z1,m):
 ps=[xyz(a,b,z) for z in (z0,z1) for a,b in ((a0,b0),(a1,b0),(a1,b1),(a0,b1))];return mesh(n,ps,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m)
box('Terrace slab and silver fascia',146.7,150,-15.3,15.3,12.8209019184,13.1209019184,concrete)
# Underlying closed sloped lower volume supports terrace; fronts have real inset panels.
ps=[xyz(a,b,z) for a,z in ((147,3.4),(151,12.8209019184),(146.7,12.8209019184),(146.7,3.4)) for b in (-15.2,15.2)]
mesh('Lower sloping terminal body',ps,[(0,2,3,1),(2,4,5,3),(4,6,7,5),(6,0,1,7),(0,6,4,2),(1,3,5,7)],concrete)
# Rounded perimeter paths for three tall lower recesses; bevelled silver borders.
for q in range(3):
 b0=-13.5+q*9.1;b1=b0+8.3;z0=4.3;z1=11.9;roundr=.7
 path=[]
 for cy,cz,startang in [(b1-roundr,z1-roundr,0),(b0+roundr,z1-roundr,90),(b0+roundr,z0+roundr,180),(b1-roundr,z0+roundr,270)]:
  for i in range(25):
   ang=math.radians(startang+i*90/24);b=cy+roundr*math.cos(ang);z=cz+roundr*math.sin(ang);a=147+(z-3.4)/9.3*4+.06;path.append(xyz(a,b,z))
 ob=mesh('Inset dark screen '+str(q),path,[tuple(range(len(path)))],black);mod=ob.modifiers.new('Screen solid thickness estimated','SOLIDIFY');mod.thickness=.18;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
 # Welded closed rectangular ring swept with constant screen-plane normal.
 normal=(U-Vector((0,0,4/9.3))).normalized();start=len(verts);N=len(path)
 for i,p in enumerate(path):
  tangent=(path[(i+1)%N]-path[(i-1)%N]).normalized();side=tangent.cross(normal).normalized()
  for sw,sd in ((-1,-1),(1,-1),(1,1),(-1,1)):verts.append(p+normal*(.08+sd*.11)+side*(sw*.11))
 for i in range(N):
  j=(i+1)%N
  for k in range(4):faces.append((start+4*i+k,start+4*j+k,start+4*j+(k+1)%4,start+4*i+(k+1)%4))
flush('Rounded pale screen borders',silver)
# Fine horizontal slats cross side trapezoids and lower base, all photograph-visible classes.
for i in range(33):
 z=3.65+i*.265;a=147+(z-3.4)/9.3*4+.17
 limit=min(15.2-.2,math.sqrt(max(0,rad**2-(z-zc)**2))-.65)
 for b0,b1 in [(-limit,-13.7),(13.7,limit)]:beam(xyz(a,b0,z),xyz(a,b1,z),.115,.12)
# Former low slats at z1.05-3.075 had no supporting body (starts z3.4).
# Omitted rather than adding an unobserved support or changing body dimensions.
flush('Horizontal pale terminal slats',silver)
# Terrace balustrade: transparent clear panels omitted, visible rails and posts.
for b in [-14.9+i*.93 for i in range(33)]:beam(xyz(150,b,13.12090191845),xyz(150,b,14.4),.065,.065)
for z in (13.45,14.4):beam(xyz(150,-15, z),xyz(150,15,z),.08,.08)
flush('Terrace balustrade metalwork',silver)
# Recessed restaurant front known from photo, generic dark glazing without signage.
box('Recessed upper glazed front',133.8,134.0,-13.5,13.5,13.1209019184,18.2,glass)
for b in [-13.5+i*1.5 for i in range(19)]:beam(xyz(134.1,b,13.1209019184),xyz(134.1,b,18.2),.07,.07)
flush('Upper front mullions',black)
# Full lower building with a real supported deck; mapped union clipped to an
# explicitly estimated inward footprint. Original evidence remains separate.
import sys
sys.path.insert(0,str(R/'src'))
from buildings.crossrail_partial_assembly import slab_mesh
lower=json.loads((R/'references/crossrail_whole004_input.json').read_text())
vv,ff=slab_mesh(lower,12.8209019184,12.8209019184-3.4);mesh('Whole lower building inferred inset mass',vv,ff,concrete)
vv,ff=slab_mesh(lower,13.1209019184,.3);mesh('Whole continuous garden deck',vv,ff,concrete)
# Recessed side glazed strips; no doors or local businesses guessed.
for poly in lower['geometry']:
 ring=poly['outer'];area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))
 for index,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
  A=Vector((*a,0));B=Vector((*b,0));delta=B-A
  if abs(delta.dot(U))<.2:continue
  normal=Vector((delta.y,-delta.x,0)).normalized()*(1 if area>0 else -1);A+=normal*.025;B+=normal*.025
  mesh('Estimated side glazing boundary '+str(index),[A+Vector((0,0,5)),B+Vector((0,0,5)),B+Vector((0,0,11.9)),A+Vector((0,0,11.9))],[(0,1,2,3)],glass)
  for k in range(math.ceil(delta.length/4)+1):
   q=A+(B-A)*k/math.ceil(delta.length/4);beam(q+Vector((0,0,5)),q+Vector((0,0,11.9)),.09,.09)
flush('Estimated side facade verticals',silver)
# East end is open, no mirrored west dark-screen facade.
box('East recessed glazing estimated',-131,-130.8,-12,12,13.1209019184,18,glass)
for b in range(-12,13,2):beam(xyz(-131.1,b,13.1209019184),xyz(-131.1,b,18),.09,.09)
flush('East recessed glazing mullions estimated',silver)
# Continuous east edge rim consistent with shared roof surface.
for i in range(160):beam(shell(-tmax+2*tmax*i/160,299.1),shell(-tmax+2*tmax*(i+1)/160,299.1),.45,.45)
flush('East open terminal rim estimated',silver)

# Scene and exact comparable before: use older scene fragment without translating axes.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.55,.62,.69,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
ld=bpy.data.lights.new('Sun','SUN');ld.energy=2.3;ld.angle=.18;lo=bpy.data.objects.new('Sun',ld);scene.collection.objects.link(lo);lo.rotation_euler=(.5,-.5,-.7)
cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);scene.collection.objects.link(cam);scene.camera=cam
for label,a,b,z,ta,tz,scale in [('after',204,-40,22,145,13,62),('eye-level',211,-11,8,147,13,58),('roof',0,-135,215,0,13,345),('whole-oblique',35,-160,95,0,13,340),('east',-195,-40,23,-125,13,68)]:
 cam.location=xyz(a,b,z);target=xyz(ta,0,tz);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=scale
 if label=='after':
  bpy.ops.wm.save_as_mainfile(filepath=str(O/'terminal.blend'),compress=False)
  bpy.ops.object.select_all(action='DESELECT')
  for ob in registry:ob.select_set(True)
  bpy.ops.export_scene.gltf(filepath=str(O/'terminal.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
 scene.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
ids=[o.name for o in registry];count=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in registry)
bpy.ops.wm.open_mainfile(filepath=str(O/'terminal.blend'));assert all(n in bpy.data.objects for n in ids)
# Load legacy model only for a same-camera actual-before rendering.
for ob in list(bpy.data.objects):
 if ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(R/'exports/crossrail-grid-photo-001/crossrail-grid.blend'),link=False) as (a,b):b.objects=[n for n in a.objects if n.startswith('crossrail_')]
for ob in b.objects:
 if ob:scene=bpy.context.scene;scene.collection.objects.link(ob)
bpy.context.scene.render.filepath=str(O/'before.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'terminal.glb'));ms=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert sorted(o.name for o in ms)==sorted(ids);assert sum(len(o.data.polygons) for o in ms)==count
report={'scope':'Whole Crossrail Place exterior completion study; metric geometry and opening limits estimated','orientation':'WEST positive-u; Big Easy owner-map17; previous east interpretation rejected','native_reopened':True,'glb_ids_triangles_verified':True,'triangle_count':count,'deck_top_scene_z_m':13.1209019184,'opening_hypothesis':{'longitudinal_s_m':[105,195],'crown_angle_rad':[-.7,.7],'side_open_s_m':[36,265],'side_open_angle_above_rad':.92},'architect_text':'https://cdn.archilovers.com/projects/73ed617f-98d5-4839-9016-557a66639d7a.pdf','object_owner_mapping':{n:{'source_owner_ids':OWNER_IDS,'ownership_kind':'whole_building_composite_estimated_extent'} for n in ids},'source_photo':'https://www.pexels.com/photo/building-in-canary-wharf-business-complex-in-london-10391373/','photo_credit':'Tom Whyte / Pexels; original not bundled; no photo texture','observed':['Continuous silver terminal rim descends to low levels','Triangular timber roof with white membranes','Three dark inclined rounded-frame screens','Horizontal slats around lower end','Terrace fascia and railing; dark recessed glazed front'],'estimated':['Upper circle fitted LiDAR; lower arc extended to ±105 degrees, not measured','Terminal apex u158m; rake .45; all sections, nodes, terrace and screen geometry estimated','Whole-station membrane completion is estimated; central crown s105-195m with angular range +/-0.70rad and side openings s36-265m above |angle|0.92rad are explicit hypotheses, not measured or inferred from DSM gaps','Study exceeds central strip; mapped parent ownership context preserved but physical boundaries not surveyed'],'unresolved':['Central crown opening s105-195m and angular±.70rad explicitly estimated; not DSM-derived openings','East facade and side glazing illustrative completion; no photographic elevation verification','Complete station integration and exact footprint agreement need review'],'visual_reviewed':False}
(O/'review.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copy2(__file__,O/'source.py');print('WEST_TERMINAL_VERIFIED',count)
