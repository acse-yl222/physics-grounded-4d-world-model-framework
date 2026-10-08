from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-west-high001';r=json.loads((O/'evaluation.json').read_text());source=P/'runs/canary_wharf_appearance_morgan_visibility_correction_001/region.blend'
owner=r['zone']['owner']; names=['Morgan_podium_west_high','Morgan_podium_west_south','Morgan_podium_north','Morgan_podium_curved_low']
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(source),link=False) as (a,b):b.objects=[n for n in names if n in a.objects]
assert len(b.objects)==4
for o in b.objects:bpy.context.collection.objects.link(o)
def sig(o):return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],[m.name for m in o.data.materials],dict(o.items()))).encode()).hexdigest()
before={o.name:sig(o) for o in b.objects};cap=r['cap'];xy=cap['outer_xy'];n=len(xy);verts=[(x,y,z) for z in [cap['bottom_scene'],cap['top_scene']] for x,y in xy];faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];mesh=bpy.data.meshes.new('Morgan_west_high_supported_tier');mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
for m in bpy.data.objects['Morgan_podium_west_high'].data.materials:mesh.materials.append(m)
for f in mesh.polygons:f.material_index=0
ob['building_id']=owner;ob['basis']='EA DSM coherent raised tier 83.790 ODN; two step boundaries estimated, no facade claims';ob['source_study']='morgan-west-high001';ob['height_datum']='scene_z=ODN-4.28000021m'
assert before=={o.name:sig(o) for o in b.objects}
expected={}
for o in bpy.data.objects:
 if o.type!='MESH':continue
 o.data.calc_loop_triangles(); bm=bmesh.new();bm.from_mesh(o.data);non=sum(not e.is_manifold for e in bm.edges);bm.free();expected[o.name]={'triangles':len(o.data.loop_triangles),'building_id':o.get('building_id'),'materials':sorted({o.data.materials[p.material_index].name for p in o.data.polygons}),'bounds':[[min((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)],[max((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)]],'nonmanifold_edges':non}
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('Study world');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.7,.76,.82,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=(.4,-.3,.6);bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.type='ORTHO'
target=Vector((-338,-78,46));s.camera.location=target+Vector((-110,-130,90));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=115
bpy.ops.wm.save_as_mainfile(filepath=str(O/'morgan.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'morgan.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
for name,loc,tgt,scale in [('overview',(-110,-130,90),(-338,-78,46),115),('roof-detail',(25,35,26),(-354,-61,76),35),('rear',(-90,130,70),(-338,-78,46),115)]:
 target=Vector(tgt);s.camera.location=target+Vector(loc);s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'morgan.blend'));assert before=={n:sig(bpy.data.objects[n]) for n in names};native=True
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'morgan.glb'));obs=[o for o in bpy.data.objects if o.type=='MESH'];assert set(expected)=={o.name for o in obs};maxerr=0
for o in obs:
 e=expected[o.name];o.data.calc_loop_triangles();assert len(o.data.loop_triangles)==e['triangles'];assert o.get('building_id')==e['building_id'];assert sorted({o.data.materials[p.material_index].name for p in o.data.polygons})==e['materials'];bounds=[[min((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)],[max((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)]];maxerr=max(maxerr,max(abs(bounds[j][i]-e['bounds'][j][i]) for j in range(2) for i in range(3)))
assert maxerr<.0001
(O/'verification.json').write_text(json.dumps({'source_native_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'original_four_mesh_signatures':before,'native_reopened':native,'independent_glb_import':True,'max_bounds_difference_m':maxerr,'expected':expected,'limitations':['No full region assembly; no hidden facade validation','Raised tier shares original top face at its base; additive closed volume, not Boolean remesh']},indent=2))
