"""Optional regional appearance study; evidence-only source run stays unchanged."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/appearance-one-canada-001';O.mkdir(exist_ok=False);source=R/'exports/appearance-newfoundland-001/region.blend';asset=R/'exports/one-canada-facade-study-001/canada.blend';bpy.ops.wm.open_mainfile(filepath=str(source));mapping={q['name']:q['building_id'] for q in json.loads((R/'references/one_canada_facade_study.json').read_text())['objects']};ids=set(mapping.values())
for ob in list(bpy.data.objects):
 if ob.get('building_id') in ids:bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(asset),link=False) as (data,dest):dest.objects=[name for name in data.objects]
col=bpy.data.collections.new('One Canada Square estimated facade');bpy.context.scene.collection.children.link(col);added=[]
for ob in dest.objects:
 if ob is None:continue
 if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True);continue
 col.objects.link(ob);ob['building_id']=mapping[ob.name];ob['research_object_id']='one-canada-appearance::'+ob.name;ob['coverage']='Estimated stainless cladding and recessed glazing; mapped pyramid retained; actual bays and entrances unresolved';added.append(ob.name)
s=bpy.context.scene;s.cycles.samples=32;bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');expected={};pts=[]
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True);ob.data.calc_loop_triangles();key=ob.get('research_object_id',ob.name);expected[key]=len(ob.data.loop_triangles);pts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
bounds=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];bpy.ops.export_scene.gltf(filepath=str(O/'region.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True);study=json.loads((R/'references/one_canada_facade_study.json').read_text());pts2=[v for q in study['objects'] for v in q['vertices']];target=Vector(tuple((min(v[i] for v in pts2)+max(v[i] for v in pts2))/2 for i in range(3)));cam=s.camera;cam.location=target+Vector((-100,-185,110));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=350;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.filepath=str(O/'one-canada-context.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(expected)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'));assert {o.get('building_id') for o in bpy.data.objects if str(o.get('research_object_id','')).startswith('one-canada-appearance::')}==ids
actual={o.get('research_object_id',o.name):len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
pts=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices];bb=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];assert max(abs(a-b) for aa,cc in zip(bounds,bb) for a,b in zip(aa,cc))<1e-3
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'independent_glb_verified':True,'objects':len(expected),'appearance_objects':len(added),'bounds_enu_m':bounds,'source_blends':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,asset]},'scope':'Optional One Canada Square facade study. Mapped194m shoulders,210m main body and235m pyramid preserved. Estimated steel frames and glazing on exterior height intervals only; exact bays and entrances unverified.'},indent=2)+'\n')
