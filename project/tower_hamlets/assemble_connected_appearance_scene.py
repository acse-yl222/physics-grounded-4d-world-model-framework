"""Optional regional appearance study; evidence-only source run stays unchanged."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/appearance-connected-001';O.mkdir(exist_ok=False);source=R/'exports/appearance-ledger-001/region.blend';asset=R/'exports/warehouses-connected-002/museum.blend';bpy.ops.wm.open_mainfile(filepath=str(source));mapping={'Museum_west_exterior_hypothesis': 'overture-building-dbe8f73e-e036-48c5-9059-bb6350356575', 'Museum_east_exterior_hypothesis': 'overture-building-dbe8f73e-e036-48c5-9059-bb6350356575', 'Museum_The_Sipping_Room_exterior_hypothesis': 'overture-building-4216480f-5253-4472-98b5-4aa28ff0e352', 'Museum_Burger_&_Lobster_exterior_hypothesis': 'overture-building-06f82e7c-867c-4c3e-baa1-2062e1f17b5f', 'Museum_Browns_exterior_hypothesis': 'overture-building-f8a7acd3-42b1-498e-899c-cb95937013d3', 'Museum_Port_East_exterior_hypothesis': 'overture-building-67710957-baa2-4b34-9bf4-81a97bc93397', 'Museum_Munich_exterior_hypothesis': 'overture-building-118734b4-49b7-4a0b-80f8-4f7b33801433', 'Museum_Pizza_exterior_hypothesis': 'overture-building-e998ecb0-c626-483c-a6ec-f516b693fd78', 'Museum_Ledger_exterior_hypothesis': 'overture-building-9ce5e22c-41b6-4f7b-a8d0-9d8df1e8b059'};ids=set(mapping.values())
for ob in list(bpy.data.objects):
 if ob.get('building_id') in ids:bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(asset),link=False) as (data,dest):dest.objects=[name for name in data.objects]
col=bpy.data.collections.new('Warehouse connected shells');bpy.context.scene.collection.children.link(col);added=[]
for ob in dest.objects:
 if ob is None:continue
 if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True);continue
 col.objects.link(ob);ob['building_id']=mapping[ob.name];ob['research_object_id']='connected-appearance::'+ob.name;ob['coverage']='Topology repaired estimated exterior; openings absent and Ledger high returns omitted';added.append(ob.name)
s=bpy.context.scene;s.cycles.samples=32;bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');expected={};pts=[]
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True);ob.data.calc_loop_triangles();key=ob.get('research_object_id',ob.name);expected[key]=len(ob.data.loop_triangles);pts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
bounds=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];bpy.ops.export_scene.gltf(filepath=str(O/'region.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True);target=Vector((-290,250,12));cam=s.camera;cam.location=target+Vector((-70,-145,110));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=270;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.filepath=str(O/'warehouse-context.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(expected)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'));assert {o.get('building_id') for o in bpy.data.objects if str(o.get('research_object_id','')).startswith('connected-appearance::')}==ids
actual={o.get('research_object_id',o.name):len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
pts=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices];bb=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];assert max(abs(a-b) for aa,cc in zip(bounds,bb) for a,b in zip(aa,cc))<1e-3
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'independent_glb_verified':True,'objects':len(expected),'appearance_objects':len(added),'bounds_enu_m':bounds,'source_blends':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,asset]},'scope':'Optional appearance study with estimated Ledger low envelope exterior, each retaining its source building ID. Roof perimeters extrapolated; openings absent.'},indent=2)+'\n')
