"""Photo-led west terminal fragment. Scene ENU, estimated unsurveyed details."""
import bpy,math,json,shutil,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/crossrail-west-terminal-002';O.mkdir(parents=True,exist_ok=True)
d=json.loads((R/'references/crossrail_lidar_review.json').read_text());U=Vector((*d['axis_local_xy'],0));V=Vector((-U.y,U.x,0));C=Vector((*d['mapped_part_extent']['centroid_local_xy'],0));fit=d['upper_envelope_circle_fit'];rad=fit['radius_m'];zc=fit['circle_center_z_odn_m']-d['ground_scalar_m_odn'];bc=fit['cross_axis_center_m'];apex=zc+rad
bpy.ops.wm.read_factory_settings(use_empty=True)
def xyz(a,b,z):return C+a*U+b*V+Vector((0,0,z))
def mat(n,c,rough=.5,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
wood=mat('Warm laminated timber',(.58,.36,.18));white=mat('Off-white roof membranes',(.81,.83,.79),.45);silver=mat('Brushed silver metal',(.56,.61,.62),.3,.68);black=mat('Charcoal recessed screen',(.047,.062,.068),.8);concrete=mat('Light terrace structure',(.43,.46,.44),.7);glass=mat('Dark restaurant glazing',(.065,.11,.12),.21,.25)
registry=[]
def mesh(n,vs,fs,m):
 me=bpy.data.meshes.new(n);me.from_pydata([tuple(v) for v in vs],[],fs);me.update();ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(m);ob['component_id']=n;ob['owner']='Crossrail Place parent 7d04c4cc-c183-4597-bb98-063679b2ec63 and central part c9f4e448-eff2-39ad-ac25-e7f6cf708826';ob['accuracy']='Photo-supported feature; estimated dimensions; terminal study only';registry.append(ob);return ob
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
 z=zc+(rad-offset)*math.cos(t);b=bc+(rad-offset)*math.sin(t);a=158.0-.45*(apex-z)-s;return xyz(a,b,z)
tmax=math.radians(105)
# Silver continuous rim with round bevelled tube section.
curve=bpy.data.curves.new('Full terminal silver rim','CURVE');curve.dimensions='3D';curve.bevel_depth=.36;curve.bevel_resolution=4;sp=curve.splines.new('POLY');sp.points.add(160)
for i,p in enumerate(sp.points):p.co=(*shell(-tmax+2*tmax*i/160,0),1)
ob=bpy.data.objects.new('Full terminal silver rim',curve);bpy.context.collection.objects.link(ob);curve.materials.append(silver);bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.convert(target='MESH');ob=bpy.context.object;ob.select_set(False);ob['component_id']=ob.name;registry.append(ob)
# Triangulated timber and actual thin membrane panels: full end barrel fragment.
nt=14;ns=7;dt=2*tmax/nt;ds=4.8
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
 pts=[]
 for j,k in tri:pts.append(shell(-tmax+j*dt,(0 if k==0 else ns*ds if k==ns else k*ds+((j%2)*ds/2)),.035))
 cen=sum(pts,Vector())/3;pts=[cen+(p-cen)*.965 for p in pts];start=len(pv);pv.extend(pts);pf.append((start,start+1,start+2))
ob=mesh('Triangular white roof membranes',pv,pf,white);sol=ob.modifiers.new('Membrane thickness estimated','SOLIDIFY');sol.thickness=.035;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=sol.name)
# Terrace slab with fascia; no furniture/signs invented.
def box(n,a0,a1,b0,b1,z0,z1,m):
 ps=[xyz(a,b,z) for z in (z0,z1) for a,b in ((a0,b0),(a1,b0),(a1,b1),(a0,b1))];return mesh(n,ps,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m)
box('Terrace slab and silver fascia',121,150,-15.3,15.3,12.7,13.2,concrete)
# Underlying closed sloped lower volume supports terrace; fronts have real inset panels.
ps=[xyz(a,b,z) for a,z in ((147,3.4),(151,12.7),(121,12.7),(121,3.4)) for b in (-15.2,15.2)]
mesh('Lower sloping terminal body',ps,[(0,2,3,1),(2,4,5,3),(4,6,7,5),(6,0,1,7),(0,6,4,2),(1,3,5,7)],concrete)
# Rounded perimeter paths for three tall lower recesses; bevelled silver borders.
for q in range(3):
 b0=-13.5+q*9.1;b1=b0+8.3;z0=4.3;z1=11.9;roundr=.7
 path=[]
 for cy,cz,startang in [(b1-roundr,z1-roundr,0),(b0+roundr,z1-roundr,90),(b0+roundr,z0+roundr,180),(b1-roundr,z0+roundr,270)]:
  for i in range(9):
   ang=math.radians(startang+i*90/8);b=cy+roundr*math.cos(ang);z=cz+roundr*math.sin(ang);a=147+(z-3.4)/9.3*4+.06;path.append(xyz(a,b,z))
 ob=mesh('Inset dark screen '+str(q),path,[tuple(range(len(path)))],black);mod=ob.modifiers.new('Screen solid thickness estimated','SOLIDIFY');mod.thickness=.18;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
 for a,b in zip(path,path[1:]+path[:1]):beam(a+U*.08,b+U*.08,.22,.22)
flush('Rounded pale screen borders',silver)
# Fine horizontal slats cross side trapezoids and lower base, all photograph-visible classes.
for i in range(33):
 z=3.65+i*.265;a=147+(z-3.4)/9.3*4+.17
 for b0,b1 in [(-16.25,-13.7),(13.7,16.25)]:beam(xyz(a,b0,z),xyz(a,b1,z),.115,.12)
for i in range(10):
 z=1.05+i*.225;beam(xyz(147,-16.1,z),xyz(147,16.1,z),.14,.14)
flush('Horizontal pale terminal slats',silver)
# Terrace balustrade: transparent clear panels omitted, visible rails and posts.
for b in [-14.9+i*.93 for i in range(33)]:beam(xyz(150,b,13.25),xyz(150,b,14.4),.065,.065)
for z in (13.45,14.4):beam(xyz(150,-15, z),xyz(150,15,z),.08,.08)
flush('Terrace balustrade metalwork',silver)
# Recessed restaurant front known from photo, generic dark glazing without signage.
box('Recessed upper glazed front',133.8,134.0,-13.5,13.5,13.2,18.2,glass)
for b in [-13.5+i*1.5 for i in range(19)]:beam(xyz(134.1,b,13.2),xyz(134.1,b,18.2),.07,.07)
flush('Upper front mullions',black)
# Scene and exact comparable before: use older scene fragment without translating axes.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.55,.62,.69,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
ld=bpy.data.lights.new('Sun','SUN');ld.energy=2.3;ld.angle=.18;lo=bpy.data.objects.new('Sun',ld);scene.collection.objects.link(lo);lo.rotation_euler=(.5,-.5,-.7)
cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);scene.collection.objects.link(cam);scene.camera=cam
for label,a,b,z,ta,tz,scale in [('after',204,-40,22,145,13,62),('eye-level',211,-11,8,147,13,58),('roof',191,-42,64,142,13,70)]:
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
report={'scope':'West terminal fragment, rear cut at about local u121; full station incomplete','orientation':'WEST positive-u; Big Easy owner-map17; previous east interpretation rejected','native_reopened':True,'glb_ids_triangles_verified':True,'triangle_count':count,'object_owner_mapping':{n:'Crossrail Place parent+central part composite study, new footprint extent is inferred' for n in ids},'source_photo':'https://www.pexels.com/photo/building-in-canary-wharf-business-complex-in-london-10391373/','photo_credit':'Tom Whyte / Pexels; original not bundled; no photo texture','observed':['Continuous silver terminal rim descends to low levels','Triangular timber roof with white membranes','Three dark inclined rounded-frame screens','Horizontal slats around lower end','Terrace fascia and railing; dark recessed glazed front'],'estimated':['Upper circle fitted LiDAR; lower arc extended to ±105 degrees, not measured','Terminal apex u158m; rake .45; all sections, nodes, terrace and screen geometry estimated','White panels filled terminal only by visible photographic pattern; no claim about full-station openings','Study exceeds central strip; mapped parent ownership context preserved but physical boundaries not surveyed'],'unresolved':['Rear is cut fragment, no rear facade','Other end and full station not delivered','Complete station integration and exact footprint agreement need review'],'visual_reviewed':False}
(O/'review.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copy2(__file__,O/'source.py');print('WEST_TERMINAL_VERIFIED',count)
