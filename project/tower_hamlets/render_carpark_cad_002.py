from pathlib import Path
import bpy,json
from mathutils import Vector
O=Path(__file__).resolve().parent/'input/canary_wharf_20261007/exports/carpark-cad-002';rows=json.loads((O/'mesh.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True);allv=[];expected={}
colors={'deck':(.53,.56,.59,1),'column':(.32,.36,.40,1),'rail':(.12,.18,.21,1)}
for r in rows:
 m=bpy.data.meshes.new(r['name']);m.from_pydata(r['vertices'],[],r['faces']);m.update();ob=bpy.data.objects.new(r['name'],m);bpy.context.collection.objects.link(ob);ob['basis']='Estimated structural completion; see parameters.json';mat=bpy.data.materials.get(r['kind'])
 if mat is None:mat=bpy.data.materials.new(r['kind']);mat.diffuse_color=colors[r['kind']]
 m.materials.append(mat);allv.extend(r['vertices']);expected[ob.name]=len(r['faces'])
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1400;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=(.4,-.3,.6);target=Vector((-278,306,10));bpy.ops.object.camera_add(location=target+Vector((-100,-160,90)));c=bpy.context.object;c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=185;s.camera=c
bpy.ops.wm.save_as_mainfile(filepath=str(O/'carpark.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'carpark.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);s.render.filepath=str(O/'carpark.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'carpark.blend'));assert {o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'}==expected
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'carpark.glb'));assert {o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'}==expected
(O/'render_verification.json').write_text(json.dumps({'native_reopened':True,'glb_reimport_counts_verified':True,'objects':len(expected),'scope':'Conceptual parameterized structure, not surveyed architecture'},indent=2)+'\n')
