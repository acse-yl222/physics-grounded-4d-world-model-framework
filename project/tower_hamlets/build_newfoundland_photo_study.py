from pathlib import Path
import bpy,bmesh,json,math
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/newfoundland-photo-study-001';O.mkdir(exist_ok=False);r=json.loads((R/'references/newfoundland_photo_study.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
p=[Vector((*a,0)) for a in r['footprint'][0]['outer']];center=sum(p,Vector())/len(p);H=r['total_height_m'];step=H/62;crown=step*58;groups={}
def material(name,col,metal,rough,alpha=1,trans=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*col,alpha);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*col,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;b.inputs['Alpha'].default_value=alpha;b.inputs['Transmission Weight'].default_value=trans
 if alpha<1:m.surface_render_method='DITHERED'
 return m
mats={'diagrid':material('Estimated champagne aluminium',(.49,.48,.43),.65,.3),'frame':material('Estimated dark frames',(.11,.14,.15),.65,.28),'glass':material('Estimated cool glazing',(.40,.53,.59),.05,.13,.7,.5),'backing':material('Estimated interior darkness',(.04,.065,.08),0,.8),'crown':material('Estimated enclosed technical crown',(.34,.38,.39),.4,.4)}
def mesh(name,verts,faces,kind):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(mats[kind]);groups.setdefault(kind,[]).append(ob);return ob
def beam(a,b,width,depth,kind,face_normal=None):
 a,b=Vector(a),Vector(b);direction=(b-a).normalized();normal=Vector(face_normal).normalized() if face_normal is not None else Vector((-(b.y-a.y),b.x-a.x,0)).normalized();side=direction.cross(normal).normalized();normal=side.cross(direction).normalized();verts=[]
 for q in [a,b]:
  for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]:verts.append(tuple(q+side*s*width/2+normal*t*depth/2))
 verts=[(x,y,min(H,max(0,z))) for x,y,z in verts]
 mesh(kind,verts,[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]],kind)
def inset(d):return [q+(center-q).normalized()*d for q in p]
def shell(coords,lo,hi,kind):
 n=len(coords);v=[(q.x,q.y,z) for z in [lo,hi] for q in coords];faces=[list(reversed(range(n))),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)];mesh(kind,v,faces,kind)
shell(inset(.45),0,crown,'backing');shell(inset(.25),0,crown,'glass');shell(inset(.12),crown,H,'crown')
q=inset(.20)
for i,a in enumerate(q):
 b=q[(i+1)%len(q)];length=(b-a).length;n=max(1,round(length/1.6))
 for k in range(n):
  v=a+(b-a)*k/n;beam((v.x,v.y,0),(v.x,v.y,crown),.065,.08,'frame',(-(b.y-a.y),b.x-a.x,0))
 for k in range(4,59):beam((a.x,a.y,k*step),(b.x,b.y,k*step),.085,.10,'frame')
# Perimeter parameterization wraps continuously through corners, same global phase on every face.
lengths=[(p[(i+1)%len(p)]-a).length for i,a in enumerate(p)];cum=[0]
for l in lengths:cum.append(cum[-1]+l)
L=cum[-1];period=L/12;dz=8*step;slope=period/dz
def perimeter(s):
 s=s%L
 for i in range(len(p)):
  if s<=cum[i+1]+1e-8:return p[i]+(p[(i+1)%len(p)]-p[i])*((s-cum[i])/lengths[i])
for sign in [-1,1]:
 for k in range(12):
  s0=k*period+sign*slope*(2*step);cuts=[0.,H]
  for boundary in cum[:-1]:
   for wrap in range(-12,13):
    z=(boundary+wrap*L-s0)/(sign*slope)
    if 0<z<H:cuts.append(z)
  cuts.sort()
  for a,b in zip(cuts,cuts[1:]):
   aa=perimeter(s0+sign*slope*a);bb=perimeter(s0+sign*slope*b);beam((aa.x,aa.y,a),(bb.x,bb.y,b),.75,.30,'diagrid')
# Photo-supported framed crown; dimensions and spacing estimated, no emissive lighting inferred.
for i,a in enumerate(p):
 b=p[(i+1)%len(p)];normal=(-(b.y-a.y),b.x-a.x,0)
 for z in [crown,H-.25]:beam((a.x,a.y,z),(b.x,b.y,z),.50,.38,'diagrid',normal)
 n=max(1,round((b-a).length/.7))
 for k in range(n):
  v=a+(b-a)*k/n;v=v+(center-v).normalized()*.10
  beam((v.x,v.y,crown),(v.x,v.y,H-.5),.045,.065,'frame',normal)
obs=[]
for kind,items in groups.items():
 bpy.ops.object.select_all(action='DESELECT')
 for ob in items:ob.select_set(True)
 bpy.context.view_layer.objects.active=items[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='Newfoundland_'+kind;ob['building_id']=r['building_id'];ob['component_kind']=kind;ob['basis']=r['scope'];bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(ob.data);bm.free()
 if kind in ['diagrid','frame']:
  mod=ob.modifiers.new('Applied small bevel','BEVEL');mod.width=.008 if kind=='diagrid' else .004;mod.segments=2;mod.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=mod.name)
 obs.append(ob)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.render.resolution_x=1200;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('Neutral daylight');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.75,.83,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=1.5;bpy.context.object.rotation_euler=(.55,-.4,-.65);bpy.context.object.data.angle=.12
bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.type='ORTHO'
def camera(target,offset,scale):s.camera.location=target+Vector(offset);s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale
camera(Vector((center.x,center.y,H/2)),(-160,-230,100),320)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'newfoundland.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for ob in obs:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'newfoundland.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
for name,target,off,scale in [('overview',Vector((center.x,center.y,H/2)),(-160,-230,100),320),('rear',Vector((center.x,center.y,H/2)),(160,230,100),320),('detail',Vector((center.x,center.y,110)),(-60,-90,18),45)]:
 camera(target,off,scale);s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
expected={}
for ob in obs:
 ob.data.calc_loop_triangles();v=[tuple(ob.matrix_world@v.co) for v in ob.data.vertices];expected[ob.name]={'triangles':len(ob.data.loop_triangles),'bounds':[[min(a[i] for a in v) for i in range(3)],[max(a[i] for a in v) for i in range(3)]],'material':ob.data.materials[0].name}
(O/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
