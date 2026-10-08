"""Paired measured roof candidates; original ENU placement, no inferred walls."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007';out=root/'exports/north-quay-expanded-roofs-003';out.mkdir(exist_ok=False);bpy.ops.wm.read_factory_settings(use_empty=True);allv=[];expected={};hashes={}
rows=json.loads((root/'references/north_quay_expanded_constrained_roof_candidate.json').read_text())['objects']
for label,file,color in [(q['id'],q['obj'],((.2,.5,.58,1) if q['representation']=='fitted_supported_roof' else (.48,.4,.3,1))) for i,q in enumerate(rows)]:
 source=root/'references'/file;v=[];f=[]
 for line in source.read_text().splitlines():
  if line.startswith('v '):v.append(tuple(map(float,line.split()[1:])))
  if line.startswith('f '):f.append(tuple(int(q)-1 for q in line.split()[1:]))
 mesh=bpy.data.meshes.new(label+' measured roof');mesh.from_pydata(v,[],f);mesh.update();o=bpy.data.objects.new(label.replace('overture-building-','b-').replace('overture-part-','p-'),mesh);bpy.context.collection.objects.link(o);o['scope']='Partial roof surface; fitted boundary triangles are estimated transitions to raw DSM; gaps remain unknown';o['source_obj']=file
 o['source_feature_id']=label.split('__')[0]
 o['representation']=next(q['representation'] for q in rows if q['id']==label)
 m=bpy.data.materials.new(label+' illustrative');m.diffuse_color=color;m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=color;mesh.materials.append(m);allv+=v;expected[o.name]=len(f);hashes[file]=hashlib.sha256(source.read_bytes()).hexdigest()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
light=bpy.data.lights.new('Sun','SUN');light.energy=2;lo=bpy.data.objects.new('Sun',light);s.collection.objects.link(lo);lo.rotation_euler=(.4,-.3,.6)
bounds=[[min(v[i] for v in allv) for i in range(3)],[max(v[i] for v in allv) for i in range(3)]];target=(Vector(bounds[0])+Vector(bounds[1]))/2;c=bpy.data.cameras.new('Roof inspection');co=bpy.data.objects.new(c.name,c);s.collection.objects.link(co);s.camera=co;co.location=target+Vector((-90,-170,140));co.rotation_euler=(target-co.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=245
bpy.ops.wm.save_as_mainfile(filepath=str(out/'north-quay-roof.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'north-quay-roof.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);s.render.filepath=str(out/'north-quay-roof.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(out/'north-quay-roof.blend'));assert {o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'}==expected
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'north-quay-roof.glb'));objects=[o for o in bpy.data.objects if o.type=='MESH'];assert {o.name:len(o.data.polygons) for o in objects}==expected;points=[o.matrix_world@v.co for o in objects for v in o.data.vertices];actual=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]];assert max(abs(a-b) for x,y in zip(bounds,actual) for a,b in zip(x,y))<.0001
(out/'verification.json').write_text(json.dumps({'master_reopened':True,'independent_glb_import_verified':True,'triangle_counts':expected,'source_hashes':hashes,'bounds_enu_m':bounds,'visual_reviewed':False,'scope':'partial open surfaces, not architectural envelopes'},indent=2)+'\n');print('PAIRED_ROOFS_VERIFIED',expected)
