"""Editable isolated LiDAR evidence mesh, not the integrated architecture model."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
source=root/'references/crossrail_observed_roof_candidate.obj'
out=root/'exports/crossrail-candidate-002';out.mkdir(parents=True,exist_ok=False)
vertices=[];faces=[]
for line in source.read_text().splitlines():
 if line.startswith('v '):vertices.append(tuple(map(float,line.split()[1:])))
 elif line.startswith('f '):faces.append(tuple(int(i)-1 for i in line.split()[1:]))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mesh=bpy.data.meshes.new('Measured roof patches');mesh.from_pydata(vertices,[],faces);mesh.update()
obj=bpy.data.objects.new('crossrail_observed_roof_patches',mesh);bpy.context.collection.objects.link(obj)
obj['scope']='Isolated measured LiDAR patches; missing cells are not verified openings'
obj['source']='Environment Agency 1m DSM OGL; mixed survey vintage'
material=bpy.data.materials.new('Evidence surface — illustrative teal');material.diffuse_color=(.12,.42,.48,1);material.use_nodes=True;bsdf=material.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.12,.42,.48,1);bsdf.inputs['Roughness'].default_value=.65;mesh.materials.append(material)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.render.resolution_x=1600;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.4,.4,.4,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
sun_data=bpy.data.lights.new('Inspection sun','SUN');sun_data.energy=2.5;sun_data.angle=.15;sun=bpy.data.objects.new('Inspection sun',sun_data);scene.collection.objects.link(sun);sun.rotation_euler=(.4,-.3,-.4)
for location,power in [((0,-80,250),3000),((200,100,200),2200)]:
 data=bpy.data.lights.new('Inspection area light','AREA');data.energy=power;data.shape='DISK';data.size=180;light=bpy.data.objects.new(data.name,data);scene.collection.objects.link(light);light.location=location
center=sum((Vector(v) for v in vertices),Vector())/len(vertices)
camdata=bpy.data.cameras.new('Evidence inspection camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);scene.camera=cam
cam.location=center+Vector((-30,-100,170));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=330
bpy.ops.wm.save_as_mainfile(filepath=str(out/'roof-patches.blend'),compress=False)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.gltf(filepath=str(out/'roof-patches.glb'),export_format='GLB',use_selection=True,export_draco_mesh_compression_enable=False)
scene.render.filepath=str(out/'isolated-roof-patches.png');bpy.ops.render.render(write_still=True)
expected_bounds=[[min(v[i] for v in vertices) for i in range(3)],[max(v[i] for v in vertices) for i in range(3)]]
bpy.ops.wm.open_mainfile(filepath=str(out/'roof-patches.blend'))
assert len(bpy.data.objects['crossrail_observed_roof_patches'].data.polygons)==len(faces)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'roof-patches.glb'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==1
points=[meshes[0].matrix_world@v.co for v in meshes[0].data.vertices];bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]
assert all(abs(a-b)<1e-4 for row,expected in zip(bounds,expected_bounds) for a,b in zip(row,expected))
assert len(meshes[0].data.polygons)==len(faces)
report={'source_obj_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'master_reopened':True,'independent_glb_import_checked':True,'triangle_count':len(faces),'bounds_local_enu_m':bounds,'scope':'Isolated evidence mesh only; not retained whole-region model','intentional_open_surface':True,'visual_reviewed':False}
(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('CROSSRAIL_CANDIDATE_VERIFIED',len(faces))
