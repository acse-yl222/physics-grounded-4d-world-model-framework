from pathlib import Path
import bpy,bmesh,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/credit-photo-study-002';O.mkdir(exist_ok=False);r=json.loads((R/'references/credit_photo_study_002.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.82;return m
brick=mat('Estimated stock brick',(.32,.20,.12));slate=mat('Estimated slate',(.20,.32,.37));allv=[];expected={}
materials={}
for kind,col,metal,rough in [('shadow',(.025,.035,.04),.10,.60),('louver',(.14,.16,.16),.55,.40),('metal',(.59,.66,.65),.45,.35),('frame',(.43,.46,.45),.45,.35),('panel',(.63,.64,.60),.18,.48),('backing',(.04,.065,.078),0,.8),('glass',(.20,.28,.30),.05,.16)]:
 m=mat('Estimated Credit Suisse '+kind,col);bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;materials[kind]=m
 if kind=='glass':bs.inputs['Transmission Weight'].default_value=.4;bs.inputs['Alpha'].default_value=.7;m.surface_render_method='DITHERED'
for q in r['objects']:
 faces=q['roof_faces']+q['wall_faces']+q['bottom_faces'];mesh=bpy.data.meshes.new(q['name']);mesh.from_pydata(q['vertices'],[],faces);mesh.update();mesh.materials.append(materials[q['kind']]);mesh.materials.append(brick)
 for i,poly in enumerate(mesh.polygons):poly.material_index=0 if i<len(q['roof_faces']) else 1
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();ob=bpy.data.objects.new(q['name'],mesh);bpy.context.collection.objects.link(ob);ob['basis']=r['scope'];ob['building_id']=q['building_id'];ob['aggregate_alias_id']=q.get('aggregate_alias_id','');allv+=q['vertices'];mesh.calc_loop_triangles();expected[ob.name]=len(mesh.loop_triangles)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.75,.83,1);bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=1.5;bpy.context.object.rotation_euler=(.4,-.3,.6);bounds=[[min(v[i] for v in allv) for i in range(3)],[max(v[i] for v in allv) for i in range(3)]];target=(Vector(bounds[0])+Vector(bounds[1]))/2;bpy.ops.object.camera_add(location=target+Vector((-160,-230,110)));s.camera=bpy.context.object;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=200
bpy.ops.wm.save_as_mainfile(filepath=str(O/'credit.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'credit.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True)
# Front/rear full and close exterior review.
s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.75,.83,1)
s.camera.location=target+Vector((180,220,100));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'rear.png');bpy.ops.render.render(write_still=True)
detail=Vector((target.x,target.y,70));s.camera.location=detail+Vector((-80,-100,30));s.camera.rotation_euler=(detail-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=50;s.render.filepath=str(O/'detail.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'credit.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(r['objects'])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'credit.glb'));assert {o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'}==expected
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'independent_glb_counts_verified':True,'bounds_enu_m':bounds,'scope':r['scope'],'openings_verified':False},indent=2)+'\n')
