"""Paired measured roof candidates; original ENU placement, no inferred walls."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007';out=root/'exports/carpark-roof-001';out.mkdir(exist_ok=False);bpy.ops.wm.read_factory_settings(use_empty=True);allv=[];expected={};hashes={}
for label,file,color in [('Car_Park_native_surface','carpark_native_roof.obj',(.2,.55,.6,1))]:
 source=root/'references'/file;v=[];f=[]
 for line in source.read_text().splitlines():
  if line.startswith('v '):v.append(tuple(map(float,line.split()[1:])))
  if line.startswith('f '):f.append(tuple(int(q)-1 for q in line.split()[1:]))
 mesh=bpy.data.meshes.new(label+' measured roof');mesh.from_pydata(v,[],f);mesh.update();o=bpy.data.objects.new(label,mesh);bpy.context.collection.objects.link(o);o['scope']='Partial native roof surface observed in DSM; gaps are unsupported data, not confirmed openings';o['source_obj']=file
 m=bpy.data.materials.new(label+' illustrative');m.diffuse_color=color;m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=color;mesh.materials.append(m);allv+=v;expected[label]=len(f);hashes[file]=hashlib.sha256(source.read_bytes()).hexdigest()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
light=bpy.data.lights.new('Sun','SUN');light.energy=2;lo=bpy.data.objects.new('Sun',light);s.collection.objects.link(lo);lo.rotation_euler=(.4,-.3,.6)
bounds=[[min(v[i] for v in allv) for i in range(3)],[max(v[i] for v in allv) for i in range(3)]];target=(Vector(bounds[0])+Vector(bounds[1]))/2;c=bpy.data.cameras.new('Roof inspection');co=bpy.data.objects.new(c.name,c);s.collection.objects.link(co);s.camera=co;co.location=target+Vector((-20,-35,35));co.rotation_euler=(target-co.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=180
bpy.ops.wm.save_as_mainfile(filepath=str(out/'carpark-roof.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'carpark-roof.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);s.render.filepath=str(out/'carpark-roof.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(out/'carpark-roof.blend'));assert {o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'}==expected
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'carpark-roof.glb'));objects=[o for o in bpy.data.objects if o.type=='MESH'];assert {o.name:len(o.data.polygons) for o in objects}==expected;points=[o.matrix_world@v.co for o in objects for v in o.data.vertices];actual=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]];assert max(abs(a-b) for x,y in zip(bounds,actual) for a,b in zip(x,y))<.0001
(out/'verification.json').write_text(json.dumps({'master_reopened':True,'independent_glb_import_verified':True,'triangle_counts':expected,'source_hashes':hashes,'bounds_enu_m':bounds,'visual_reviewed':False,'scope':'partial open surfaces, not architectural envelopes'},indent=2)+'\n');print('CARPARK_ROOF_VERIFIED',expected)
