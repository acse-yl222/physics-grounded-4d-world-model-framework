"""Measured local terrain comparison; preserves authored roof and illustrative base."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007'
O=R/'exports/fff_boundary-terrain-preview-001';O.mkdir(exist_ok=True)
src=R/'exports/fff_boundary-roof-study-001/fff_boundary-pair-context.blend'
d=R/'exports/fff_boundary-evidence-002/fff_boundary-terrain-report.json'
bpy.ops.wm.open_mainfile(filepath=str(src))
original={o.name:[tuple(v.co) for v in o.data.vertices] for o in bpy.data.objects if o.type=='MESH'}
rows=json.loads(d.read_text())['samples'];lookup={(p['x'],p['y']):i for i,p in enumerate(rows)}
assert all(p['dtm_scene_z'] is not None for p in rows)
verts=[(p['x'],p['y'],p['dtm_scene_z']) for p in rows];faces=[]
for (x,y),a in lookup.items():
 if all(k in lookup for k in [(x+1,y),(x+1,y+1),(x,y+1)]):
  b,c,e=[lookup[k] for k in [(x+1,y),(x+1,y+1),(x,y+1)]];faces.extend([(a,b,c),(a,c,e)])
me=bpy.data.meshes.new('EA DTM 1m local surface');me.from_pydata(verts,[],faces);me.update()
o=bpy.data.objects.new('Measured terrain context — open surface',me);bpy.context.scene.collection.objects.link(o)
o['building_id']='diagnostic-terrain-context';o['datum']='ODN minus 4.28000021 m';o['source']='EA OGL v3 local DTM; capture date unknown';o['integration_status']='independent comparison only; no regional site replacement';o['sampling']='nearest raster sample on 1m ENU grid; interpolated triangles, not native BNG grid'
m=bpy.data.materials.new('Measured ground');m.diffuse_color=(.32,.38,.28,1);me.materials.append(m)
s=bpy.context.scene;C=Vector((-503,362,1.8));s.camera.location=C+Vector((-25,-32,11));s.camera.rotation_euler=(C-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=28
assert all([tuple(v.co) for v in bpy.data.objects[n].data.vertices]==vs for n,vs in original.items())
bpy.ops.wm.save_as_mainfile(filepath=str(O/'terrain-context.blend'),compress=False)
bpy.ops.object.select_all(action='DESELECT')
for q in bpy.data.objects:
 if q.type=='MESH':q.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'terrain-context.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
s.render.filepath=str(O/'terrain-context.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'terrain-context.blend'));assert all([tuple(v.co) for v in bpy.data.objects[n].data.vertices]==vs for n,vs in original.items())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'terrain-context.glb'))
meshes=[q for q in bpy.data.objects if q.type=='MESH'];assert len(meshes)==len(original)+1
terrain=next(q for q in meshes if q.get('building_id')=='diagnostic-terrain-context');assert len(terrain.data.polygons)==len(faces)
report={'native_reopened':True,'glb_reimported':True,'building_vertices_unchanged':True,'terrain_vertices':len(verts),'terrain_triangles':len(faces),'terrain_is_open_surface':True,'replacement_ids':[],'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,d]},'limitations':['Existing base at zero remains illustrative; visible ground gap is unresolved.','No fabricated foundation or terrain blending.','Standalone terrain context does not replace regional ground.','DTM resampled nearest onto 1m ENU grid; unknown capture date.']}
(O/'checks.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
