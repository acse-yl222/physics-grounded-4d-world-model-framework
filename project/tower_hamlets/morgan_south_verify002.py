from pathlib import Path
import bpy,json,hashlib,bmesh
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-south-facade-002';src=R/'exports/morgan_south-facade-001/morgan_south.blend'
def sig(o):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],'f':[list(p.vertices) for p in o.data.polygons],'mat':[m.name for m in o.data.materials],'mi':[p.material_index for p in o.data.polygons],'world':[list(r) for r in o.matrix_world],'properties':dict(o.items())},sort_keys=True,default=str).encode()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(src));before={o.name:sig(o) for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('morgan_south_')};bpy.ops.wm.open_mainfile(filepath=str(O/'morgan_south002.blend'));assert all(sig(bpy.data.objects[k])==h for k,h in before.items())
def capture():
 result={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles();result[o.name]={'triangles':len(o.data.loop_triangles),'owner':o.get('building_id'),'materials':sorted({o.data.materials[p.material_index].name for p in o.data.polygons})}
 return result
expected=capture();checks=[]
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.startswith('morgan_south002_'):
  bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<1e-10 for f in bm.faces);assert bad==zero==0;checks.append(o.name);bm.free()
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'morgan_south002.glb'));actual=capture();assert actual==expected,(expected,actual)
(O/'checks.json').write_text(json.dumps({'native_reopened':True,'glb_reimported':True,'used_materials_ids_triangles_verified':True,'exact_body_roof_fingerprints':before,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'new_meshes':checks,'new_zero_area_faces':0,'new_nonmanifold_edges_per_component':0,'visual_reviewed':True,'visual_passed':False,'decision':'HOLD: source-camera body occlusion disproves exact edge13 visibility','note':'Initial verifier compared unused materialslots and failed; independent verifier correctly compares face-used materialbindings.'},indent=2))
