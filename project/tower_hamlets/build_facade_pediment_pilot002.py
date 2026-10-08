from pathlib import Path
import bpy,bmesh,json
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/facade-pediment-pilot002';r=json.loads((O/'authoring.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True);mats={}
for kind,col in [('stone',(.38,.37,.35)),('trim',(.69,.67,.61)),('backing',(.035,.042,.046)),('joint',(.17,.16,.15))]:
 m=bpy.data.materials.new('Estimated neutral '+kind);m.diffuse_color=(*col,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*col,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.75;mats[kind]=m
expected={}
for q in r['components']:
 me=bpy.data.meshes.new(q['name']);me.from_pydata(q['vertices'],[],q['faces']);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);assert all(e.is_manifold for e in bm.edges),(q['name'],'nonmanifold');assert all(f.calc_area()>1e-10 for f in bm.faces);bm.to_mesh(me);bm.free();me.materials.append(mats[q['kind']]);o=bpy.data.objects.new(q['name'],me);bpy.context.collection.objects.link(o);o['study_id']='facade-pediment-pilot002';o['placement_status']='Unassigned local facade study; no geographic building attribution';o['basis']='Visible photo architecture, dimensions and profiles inferred';me.calc_loop_triangles();expected[o.name]=len(me.loop_triangles)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.70,.76,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6;bpy.ops.object.light_add(type='AREA',location=(-20,-30,45));light=bpy.context.object;light.data.energy=6000;light.data.shape='DISK';light.data.size=20;light.rotation_euler=(Vector((0,0,10))-light.location).to_track_quat('-Z','Y').to_euler();bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.type='ORTHO'
views=[('front',(0,-70,12),(0,0,12),49),('oblique',(-32,-65,30),(0,0,11),53),('arch-detail',(-11,-23,3.5),(0,2.2,10.3),20),('rear',(30,60,27),(0,1.5,11),53)]
for idx,(name,loc,target,scale) in enumerate(views):
 s.camera.location=loc;s.camera.rotation_euler=(Vector(target)-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale
 if idx==0:
  bpy.ops.wm.save_as_mainfile(filepath=str(O/'pediment.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
  for o in bpy.data.objects:
   if o.type=='MESH':o.select_set(True)
  bpy.ops.export_scene.gltf(filepath=str(O/'pediment.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
# Opening ray confirms actual front wall cavity; backing should be first hit, not an opaque front mass.
bpy.ops.wm.open_mainfile(filepath=str(O/'pediment.blend'));s=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get();rays=[]
for x,z in [(0,5),(0,11),(-18,4),(-11.5,4),(11.5,4),(18,4)]:
 hit,loc,n,i,o,m=s.ray_cast(deps,Vector((x,-5,z)),Vector((0,1,0)),distance=15);assert hit and loc.y>=3.39,(x,z,o.name if hit else None);rays.append({'x':x,'z':z,'first_hit':o.name,'hit_y':loc.y})
lattice_rays=[]
for i in [1,3,6,9]:
 for j in [1,3,5]:
  x=-5.15+(i+.25)*10.3/12;z=2.25+(j+.5)*9.55/10
  hit,loc,n,idx,obj,matrix=s.ray_cast(deps,Vector((x,-5,z)),Vector((0,1,0)),distance=15);assert hit and obj.name=='Plain_estimated_rear',(x,z,obj.name if hit else None);lattice_rays.append({'x':x,'z':z,'first_hit':obj.name,'hit_y':loc.y})
native={o.name:([list(o.matrix_world@v.co)for v in o.data.vertices],[m.name for m in o.data.materials])for o in bpy.data.objects if o.type=='MESH'};bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'pediment.glb'));obs=[o for o in bpy.data.objects if o.type=='MESH'];assert set(expected)=={o.name for o in obs};maxerr=0
for o in obs:
 o.data.calc_loop_triangles();assert len(o.data.loop_triangles)==expected[o.name];assert not o.get('building_id');assert o.get('study_id')=='facade-pediment-pilot002';vv,mm=native[o.name];assert [m.name for m in o.data.materials]==mm
 for ax in range(3):
  for fn in [min,max]:maxerr=max(maxerr,abs(fn(v[ax]for v in vv)-fn((o.matrix_world@v.co)[ax]for v in o.data.vertices)))
assert maxerr<.0001
(O/'checks.json').write_text(json.dumps({'native_reopened':True,'independent_glb_import':True,'meshes':len(expected),'triangles':sum(expected.values()),'closed_components':True,'max_bounds_difference_m':maxerr,'opening_rays':rays,'open_lattice_cell_rays':lattice_rays,'global_placement':False,'exact_architecture_verified':False},indent=2))
