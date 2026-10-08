"""Independent, explicitly estimated wall-to-DTM contact; roofs stay fixed."""
from pathlib import Path
import bpy,bmesh,json,hashlib,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/fff_boundary-ground-contact-001';O.mkdir(exist_ok=True)
src=R/'exports/fff_boundary-terrain-preview-001/terrain-context.blend';bpy.ops.wm.open_mainfile(filepath=str(src))
terrain=next(o for o in bpy.data.objects if o.type=='MESH' and o.get('building_id')=='diagnostic-terrain-context');terrain.data.calc_loop_triangles();tv=[terrain.matrix_world@v.co for v in terrain.data.vertices];tf=[tuple(t.vertices) for t in terrain.data.loop_triangles];bvh=BVHTree.FromPolygons(tv,tf,all_triangles=True)
buildings=[o for o in bpy.data.objects if o.type=='MESH' and o!=terrain];checks=[]
for o in buildings:
 upper=sorted(tuple(v.co) for v in o.data.vertices if v.co.z>1e-5)
 bm=bmesh.new();bm.from_mesh(o.data)
 # Only bottom edges are subdivided. Roof and upper wall vertices stay untouched.
 edges=[e for e in bm.edges if all(abs(v.co.z)<1e-5 for v in e.verts)]
 for e in edges:
  if e.is_valid:
   cuts=max(0,math.ceil(e.calc_length()/.2)-1)
   if cuts:bmesh.ops.subdivide_edges(bm,edges=[e],cuts=cuts,use_grid_fill=False)
 for v in bm.verts:
  if abs(v.co.z)<1e-5:
   w=o.matrix_world@v.co;hit=bvh.ray_cast(Vector((w.x,w.y,20)),Vector((0,0,-1)),100)[0];assert hit is not None
   v.co.z=hit.z-.03
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges)
 bm.to_mesh(o.data);bm.free();assert sorted(tuple(v.co) for v in o.data.vertices if v.co.z>1e-5)==upper
 o['ground_contact']='Estimated wall extension to sampled DTM minus 0.03m display overlap; not surveyed foundation';o['integration_status']='Independent candidate; regional site seam unresolved'
 # Verify actual mesh base edges at midpoints as well as vertices.
 gaps=[]
 for e in o.data.edges:
  a,b=[o.matrix_world@o.data.vertices[i].co for i in e.vertices]
  if a.z<0 and b.z<0:
   for t in [0,.25,.5,.75,1]:
    v=a.lerp(b,t);hit=bvh.ray_cast(Vector((v.x,v.y,20)),Vector((0,0,-1)),100)[0];assert hit is not None;gaps.append(v.z-hit.z)
 checks.append({'name':o.name,'upper_vertices_unchanged':True,'closed':True,'triangles':len(o.data.polygons),'base_minus_terrain_range_m':[min(gaps),max(gaps)]})
s=bpy.context.scene;s.render.filepath=str(O/'ground-contact.png');bpy.ops.wm.save_as_mainfile(filepath=str(O/'ground-contact.blend'),compress=False)
bpy.ops.object.select_all(action='DESELECT')
for o in buildings+[terrain]:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'ground-contact.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'ground-contact.blend'));bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'ground-contact.glb'))
for c in checks:
 o=bpy.data.objects[c['name']];assert len(o.data.polygons)==c['triangles']
report={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'native_reopened':True,'glb_reimported':True,'replacement_ids':[],'objects':checks,'limitations':['Wall extension estimated from terrain, not surveyed facade or foundation.','Terrain is resampled 1m DTM with unknown capture date.','Original roof coordinates preserved.','Regional illustrative site seam remains unresolved; independent candidate only.','Base triangles approximate interpolated terrain; measured residual reported.']}
(O/'checks.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
