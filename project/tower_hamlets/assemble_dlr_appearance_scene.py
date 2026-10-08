"""Optional regional appearance study; evidence-only source run stays unchanged."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/appearance-dlr-002';O.mkdir(exist_ok=False);source=R/'exports/appearance-connected-001/region.blend';asset=R/'exports/dlr-support-study-001/museum.blend';bpy.ops.wm.open_mainfile(filepath=str(source));mapping={'Museum_Red_roof_frame_exterior_hypothesis': 'overture-part-7749b3ac-a94f-3524-8984-bd87bd73129f', 'Museum_Grey_square_supports_exterior_hypothesis': 'overture-part-7749b3ac-a94f-3524-8984-bd87bd73129f'};ids=set(mapping.values())
for ob in list(bpy.data.objects):
 if ob.get('building_id') in ids and '__red_arched_' in ob.name:bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(asset),link=False) as (data,dest):dest.objects=[name for name in data.objects]
col=bpy.data.collections.new('DLR revised frame');bpy.context.scene.collection.children.link(col);added=[]
for ob in dest.objects:
 if ob is None:continue
 if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True);continue
 col.objects.link(ob);ob['building_id']=mapping[ob.name];ob['research_object_id']='dlr-appearance::'+ob.name;ob['coverage']='Photo-informed grey square supports; member sizes and spacing estimated';added.append(ob.name)
assert sum(o.get('building_id') in ids for o in bpy.data.objects)==3
s=bpy.context.scene;s.cycles.samples=32;bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');expected={};pts=[]
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True);ob.data.calc_loop_triangles();key=ob.get('research_object_id',ob.name);expected[key]=len(ob.data.loop_triangles);pts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
bounds=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];bpy.ops.export_scene.gltf(filepath=str(O/'region.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True);target=sum((Vector(v) for q in json.loads((R/'references/dlr_support_study.json').read_text())['objects'] for v in q['vertices']),Vector())/sum(len(q['vertices']) for q in json.loads((R/'references/dlr_support_study.json').read_text())['objects']);cam=s.camera;cam.location=target+Vector((-70,-145,110));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=120;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.filepath=str(O/'dlr-context.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(expected)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'));assert {o.get('building_id') for o in bpy.data.objects if str(o.get('research_object_id','')).startswith('dlr-appearance::')}==ids
actual={o.get('research_object_id',o.name):len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
pts=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices];bb=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];assert max(abs(a-b) for aa,cc in zip(bounds,bb) for a,b in zip(aa,cc))<1e-3
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'independent_glb_verified':True,'objects':len(expected),'appearance_objects':len(added),'bounds_enu_m':bounds,'source_blends':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,asset]},'scope':'Optional appearance study with estimated Ledger low envelope exterior, each retaining its source building ID. Roof perimeters extrapolated; openings absent.'},indent=2)+'\n')
