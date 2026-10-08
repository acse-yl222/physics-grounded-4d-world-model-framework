"""Editable plan-view transport centre lines; symbolic stroke, no physical road geometry."""
from pathlib import Path
import json,hashlib,bpy
from mathutils import Vector
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007';source=root/'references/transport_local_review.json';report=json.loads(source.read_text());out=root/'exports/transport-inspection-002';out.mkdir(exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;collection=bpy.data.collections.new('TRANSPORT_PLAN_ONLY_UNSURVEYED_HEIGHT');s.collection.children.link(collection)
colors={'road':(.12,.4,.7,1),'walk_cycle':(.8,.45,.08,1),'rail':(.6,.16,.65,1)};materials={}
for kind,color in colors.items():
 m=bpy.data.materials.new(kind+' symbolic centre line');m.diffuse_color=color;m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=color;bs.inputs['Emission Color'].default_value=color;bs.inputs['Emission Strength'].default_value=.4;materials[kind]=m
for f in report['features']:
 c=bpy.data.curves.new(f['id'],'CURVE');c.dimensions='3D';c.resolution_u=1;c.bevel_depth=.35;c.bevel_resolution=0;c.use_fill_caps=True;line=c.splines.new('POLY');coords=f['geometry']['coordinates'];line.points.add(len(coords)-1)
 for p,xy in zip(line.points,coords):p.co=(xy[0],xy[1],.15,1)
 o=bpy.data.objects.new(f['id'],c);collection.objects.link(o);c.materials.append(materials[f['category']]);o['source_id']=f['source_id'];o['source_properties_json']=json.dumps(f['properties']);o['category']=f['category'];o['vertical_review_required']=f['vertical_review_required'];o['representation']='Plan centreline, symbolic0.7m stroke, z0.15 display offset; neither road width nor surveyed elevation'
s.render.engine='CYCLES';s.cycles.samples=16;s.render.resolution_x=1200;s.render.resolution_y=1200;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('Inspection background');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.65,.65,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
c=bpy.data.cameras.new('Plan camera');o=bpy.data.objects.new(c.name,c);s.collection.objects.link(o);s.camera=o;o.location=(0,0,1200);o.rotation_euler=(0,0,0);c.type='ORTHO';c.ortho_scale=1070;c.clip_end=5000
bpy.ops.wm.save_as_mainfile(filepath=str(out/'transport.blend'),compress=False)
s.render.filepath=str(out/'transport-plan.png');bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT')
for o in collection.objects:o.select_set(True)
bpy.context.view_layer.objects.active=next(iter(collection.objects));bpy.ops.object.convert(target='MESH');points=[o.matrix_world@v.co for o in collection.objects for v in o.data.vertices];bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]];triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in collection.objects)
bpy.ops.export_scene.gltf(filepath=str(out/'transport.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
bpy.ops.wm.open_mainfile(filepath=str(out/'transport.blend'));assert len([o for o in bpy.data.objects if o.type=='CURVE'])==len(report['features'])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'transport.glb'));objects=[o for o in bpy.data.objects if o.type=='MESH'];assert len(objects)==len(report['features']);assert {o['source_id'] for o in objects}=={f['source_id'] for f in report['features']};assert sum(len(o.data.polygons) for o in objects)==triangles
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices];actual=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]];assert max(abs(a-b) for r,t in zip(bounds,actual) for a,b in zip(r,t))<.001
(out/'verification.json').write_text(json.dumps({'master_reopened':True,'independent_glb_import_checked':True,'curve_count':len(objects),'triangles':triangles,'bounds_enu_m':bounds,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'physical_geometry':False,'visual_reviewed':False},indent=2)+'\n');print('TRANSPORT_INSPECTION_VERIFIED',len(objects))
