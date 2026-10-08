from pathlib import Path
import bpy,bmesh,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/owner899-roof-study-001';O.mkdir(exist_ok=True);r=json.loads((R/'references/owner899_roof_study.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
m=bpy.data.materials.new('Neutral estimated envelope - no facade claim');m.diffuse_color=(.3,.39,.41,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color;m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.75
bounds=[];expected={};checks=[]
for q in r['objects']:
 mesh=bpy.data.meshes.new(q['name']);mesh.from_pydata(q['vertices'],[],q['roof_faces']);mesh.update();mesh.materials.append(m);bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);checks.append(dict(name=q['name'],nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),zero_area_faces=sum(f.calc_area()<1e-10 for f in bm.faces)));bm.to_mesh(mesh);bm.free();ob=bpy.data.objects.new(q['name'],mesh);bpy.context.collection.objects.link(ob);ob['building_id']=q['building_id'];ob['aggregate_alias_id']=r['parent_id'];ob['basis']=r['scope'];bounds+=q['vertices'];mesh.calc_loop_triangles();expected[ob.name]=len(mesh.loop_triangles)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1000;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=(.5,-.4,.6);lo=Vector([min(v[i] for v in bounds) for i in range(3)]);hi=Vector([max(v[i] for v in bounds) for i in range(3)]);target=(lo+hi)/2;bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.type='ORTHO';s.camera.data.ortho_scale=100
for name,offset in [('overview',(180,-230,110)),('rear',(-160,210,100)),('roof',(80,50,330))]:
 s.camera.location=target+Vector(offset);s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'owner899.blend'));bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'owner899.glb'),export_format='GLB',use_selection=True,export_extras=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'owner899.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(r['objects'])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'owner899.glb'));actual={o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
(O/'verification.json').write_text(json.dumps(dict(native_reopened=True,glb_reimport_triangles_equal=True,component_checks=checks,bounds_enu_m=[list(lo),list(hi)],triangles=expected,whole_building_complete=False),indent=2)+'\n')
