from pathlib import Path
import bpy,bmesh,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/dlr-upper-roof-001';O.mkdir(exist_ok=False);r=json.loads((R/'references/dlr_upper_roof_render.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.82;return m
brick=mat('Estimated stock brick',(.32,.20,.12));slate=mat('Estimated slate',(.09,.12,.14));allv=[];expected={}
for q in r['objects']:
 faces=q['roof_faces']+q['wall_faces']+q['bottom_faces'];mesh=bpy.data.meshes.new(q['name']);mesh.from_pydata(q['vertices'],[],faces);mesh.update();mesh.materials.append(slate);mesh.materials.append(brick)
 for i,poly in enumerate(mesh.polygons):poly.material_index=0 if i<len(q['roof_faces']) else 1
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();ob=bpy.data.objects.new('Museum_'+q['name']+'_exterior_hypothesis',mesh);bpy.context.collection.objects.link(ob);ob['basis']=r['scope'];allv+=q['vertices'];mesh.calc_loop_triangles();expected[ob.name]=len(mesh.loop_triangles)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=(.4,-.3,.6);bounds=[[min(v[i] for v in allv) for i in range(3)],[max(v[i] for v in allv) for i in range(3)]];target=(Vector(bounds[0])+Vector(bounds[1]))/2;bpy.ops.object.camera_add(location=target+Vector((-70,-100,65)));s.camera=bpy.context.object;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=75
bpy.ops.wm.save_as_mainfile(filepath=str(O/'museum.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'museum.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);s.render.filepath=str(O/'museum.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'museum.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==1
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'museum.glb'));assert {o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'}==expected
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'independent_glb_counts_verified':True,'bounds_enu_m':bounds,'scope':r['scope'],'openings_verified':False},indent=2)+'\n')
