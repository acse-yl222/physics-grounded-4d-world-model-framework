"""Integrate Credit Suisse source-informed facade revision in regional coordinates."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/appearance-credit-photo-001';O.mkdir(exist_ok=False)
source=R/'exports/appearance-citi-newfoundland-photo-001/region.blend'
assets=[('credit',R/'exports/credit-photo-study-002/credit.blend',R/'references/credit_photo_study_002.json')]
bpy.ops.wm.open_mainfile(filepath=str(source));allids=set();contexts=[];added=[]
for label,asset,recipe in assets:
 study=json.loads(recipe.read_text());mapping={q['name']:q['building_id'] for q in study['objects']};ids=set(mapping.values());allids.update(ids)
 for ob in list(bpy.data.objects):
  if ob.get('building_id') in ids:bpy.data.objects.remove(ob,do_unlink=True)
 with bpy.data.libraries.load(str(asset),link=False) as (data,dest):dest.objects=list(data.objects)
 col=bpy.data.collections.new(label+' evidence-informed appearance');bpy.context.scene.collection.children.link(col)
 for ob in dest.objects:
  if ob is None:continue
  if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True);continue
  assert ob.name in mapping;col.objects.link(ob);ob['building_id']=mapping[ob.name];ob['research_object_id']='credit-photo::'+ob.name;ob['coverage']='Partial evidence-informed architecture; estimated dimensions, entrance unresolved';added.append(ob.name)
 pts=[v for q in study['objects'] for v in q['vertices']];contexts.append((label,Vector(tuple((min(v[i] for v in pts)+max(v[i] for v in pts))/2 for i in range(3)))))
s=bpy.context.scene;s.cycles.samples=32;bpy.ops.wm.save_as_mainfile(filepath=str(O/'region.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');expected={};points=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 ob.select_set(True);ob.data.calc_loop_triangles();key=ob.get('research_object_id',ob.name);assert key not in expected;expected[key]=len(ob.data.loop_triangles);points.extend(ob.matrix_world@v.co for v in ob.data.vertices)
bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]
bpy.ops.export_scene.gltf(filepath=str(O/'region.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
s.render.filepath=str(O/'overview.png');bpy.ops.render.render(write_still=True)
for label,target in contexts:
 cam=s.camera;cam.location=target+Vector((-170,-220,115));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=340;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.filepath=str(O/(label+'-context.png'));bpy.ops.render.render(write_still=True)
cam=s.camera;cam.location=(-760,-80,95);cam.rotation_euler=(Vector((-260,-15,110))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=26;s.render.resolution_x=1800;s.render.resolution_y=1100;s.render.filepath=str(O/'west-perspective.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(expected)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'));actual={o.get('research_object_id',o.name):len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
replaced=[o for o in bpy.data.objects if str(o.get('research_object_id','')).startswith('credit-photo::')];assert {o.get('building_id') for o in replaced}==allids;assert all(len(o.data.materials)>0 for o in replaced)
points=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices];bb=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]];assert max(abs(a-b) for aa,cc in zip(bounds,bb) for a,b in zip(aa,cc))<1e-3
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'independent_glb_verified':True,'new_material_bindings_verified':True,'objects':len(expected),'appearance_objects':len(added),'source_owner_ids':sorted(allids),'bounds_enu_m':bounds,'source_blends':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,*[a[1] for a in assets]]},'scope':'Credit Suisse revised west crown and recessed facade detail. Lower and rear architecture extrapolated; entrance and precise construction unresolved. Other regional buildings remain baseline or partial studies.'},indent=2)+'\n')
