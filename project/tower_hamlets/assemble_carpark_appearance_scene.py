"""Optional regional appearance study; evidence-only source run stays unchanged."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/appearance-carpark-001';O.mkdir(exist_ok=False);source=R/'exports/refinement-016/region.blend';asset=R/'exports/carpark-exterior-005/carpark.blend';bpy.ops.wm.open_mainfile(filepath=str(source));ids={'overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c','overture-building-e79bdc61-15a7-4380-93e9-67988c7fdec6'}
for ob in list(bpy.data.objects):
 if ob.get('building_id') in ids:bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(asset),link=False) as (data,dest):dest.objects=[name for name in data.objects]
col=bpy.data.collections.new('Car Park estimated exterior');bpy.context.scene.collection.children.link(col);added=[]
for ob in dest.objects:
 if ob is None:continue
 if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True);continue
 col.objects.link(ob);ob['building_id']='overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c';ob['research_object_id']='carpark-appearance::'+ob.name;ob['coverage']='Estimated exterior completion; not verified facade';added.append(ob.name)
s=bpy.context.scene;s.cycles.samples=32;bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');expected={};pts=[]
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True);ob.data.calc_loop_triangles();key=ob.get('research_object_id',ob.name);expected[key]=len(ob.data.loop_triangles);pts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
bounds=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];bpy.ops.export_scene.gltf(filepath=str(O/'region.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True);target=Vector((-290,296,18));cam=s.camera;cam.location=target+Vector((-70,-145,110));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=270;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.filepath=str(O/'carpark-context.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(expected)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'));actual={o.get('research_object_id',o.name):len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
pts=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices];bb=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];assert max(abs(a-b) for aa,cc in zip(bounds,bb) for a,b in zip(aa,cc))<1e-3
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'independent_glb_verified':True,'objects':len(expected),'appearance_objects':len(added),'bounds_enu_m':bounds,'source_blends':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,asset]},'scope':'Optional appearance study; estimated Car Park facade/structure replaces two evidence-only owner surfaces for display. East-ring identity combined into this exterior assembly; source IDs retained in source runs.'},indent=2)+'\n')
