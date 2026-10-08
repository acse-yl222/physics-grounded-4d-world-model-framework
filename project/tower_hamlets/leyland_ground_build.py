from pathlib import Path
import bpy,bmesh,json,hashlib,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/leyland-ground-contact-001';O.mkdir(exist_ok=True);d=json.loads((R/'references/leyland_ground_input.json').read_text());src=R/'exports/appearance-leyland-001/region.blend';asset=R/'exports/leyland-massing-001/leyland.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(src)) as (a,b):b.objects=list(a.objects)
site=[]
for o in b.objects:
 if o and o.type=='MESH' and o.get('building_id')=='site-support':site.append(o)
 elif o:bpy.data.objects.remove(o,do_unlink=True)
vs=[];fs=[]
for o in site:
 o.data.calc_loop_triangles();off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in t.vertices) for t in o.data.loop_triangles)
st=BVHTree.FromPolygons(vs,fs,all_triangles=True)
for r in d['perimeter_samples']:
 hit=st.ray_cast(Vector((r['x'],r['y'],50)),Vector((0,0,-1)),100)[0];r['existing_site_z']=float(hit.z) if hit is not None else None;r['old_base_minus_DTM_m']=-r['dtm_scene_z']
for o in site:bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.wm.open_mainfile(filepath=str(asset));buildings=[o for o in bpy.data.objects if o.type=='MESH'];me=bpy.data.meshes.new('Leyland local DTM');me.from_pydata(d['terrain_vertices'],[],d['terrain_faces']);me.update();terrain=bpy.data.objects.new('Leyland_ground_measured_context',me);bpy.context.collection.objects.link(terrain);terrain['building_id']='leyland-diagnostic-terrain';terrain['source_id']='leyland_dtm_001';terrain['datum']='ODN minus4.28000021m';terrain['coverage']='Independent measuredDTM context; site seam not merged';m=bpy.data.materials.new('Leyland ground context');m.diffuse_color=(.3,.38,.25,1);me.materials.append(m);tb=BVHTree.FromPolygons([Vector(v) for v in d['terrain_vertices']],d['terrain_faces'],all_triangles=True);checks=[]
for o in buildings:
 upper=sorted(tuple(v.co) for v in o.data.vertices if v.co.z>10);bm=bmesh.new();bm.from_mesh(o.data)
 for e in list(bm.edges):
  if e.is_valid and all(abs(v.co.z)<1e-6 for v in e.verts):
   n=max(0,math.ceil(e.calc_length()/.2)-1)
   if n:bmesh.ops.subdivide_edges(bm,edges=[e],cuts=n,use_grid_fill=False)
 for v in bm.verts:
  if abs(v.co.z)<1e-6:
   w=o.matrix_world@v.co;hit=tb.ray_cast(Vector((w.x,w.y,50)),Vector((0,0,-1)),100)[0];assert hit is not None;v.co.z=hit.z-.03
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(o.data);bm.free();assert sorted(tuple(v.co) for v in o.data.vertices if v.co.z>10)==upper
 gap=[]
 for edge in o.data.edges:
  a,b=[o.matrix_world@o.data.vertices[i].co for i in edge.vertices]
  if a.z<3 and b.z<3:
   for t in [0,.25,.5,.75,1]:
    w=a.lerp(b,t);hit=tb.ray_cast(Vector((w.x,w.y,50)),Vector((0,0,-1)),100)[0];assert hit is not None;gap.append(float(w.z-hit.z))
 o['ground_contact']='Estimated lower wall clipped upward to local DTM minus0.03m display overlap; not surveyed foundation';checks.append({'name':o.name,'roof_upper_vertices_unchanged':True,'native_closed':True,'triangles':len(o.data.polygons),'all_bottom_edge_vs_terrain_m':[min(gap),max(gap)]})
s=bpy.context.scene;target=Vector((54,496,8));s.camera.location=target+Vector((-100,-140,60));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=115;s.cycles.samples=24;s.render.filepath=str(O/'ground-contact.png');bpy.ops.wm.save_as_mainfile(filepath=str(O/'ground-contact.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
expected={}
for o in buildings+[terrain]:o.select_set(True);o.data.calc_loop_triangles();expected[o.name]=len(o.data.loop_triangles)
bpy.ops.export_scene.gltf(filepath=str(O/'ground-contact.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);bpy.ops.render.render(write_still=True)
s.camera.location=Vector((84,560,10));target=Vector((68,525,7));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=42;s.render.filepath=str(O/'north-contact-detail.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'ground-contact.blend'));bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'ground-contact.glb'));assert {o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'}==expected
report={'source_native_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source_asset_sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'source_dtm_sha256':d['source_dtm_sha256'],'native_reopened':True,'independent_glb_triangles_verified':True,'building_checks':checks,'perimeter_samples':d['perimeter_samples'],'inside_DTM':d['inside_footprint_dtm_scene_stats'],'outside_ring_DTM':d['outside_3m_ring_dtm_scene_stats'],'ground_context_open_surface':True,'replacement_ids':[],'limitations':['Independent candidate only: local patch overlaps existing site insideAOI and regional seam unresolved.','Positive DTM means original zero-base walls penetrated terrain, rather than floated above it.','Lowerwalls clipped upward; roof absolute vertices unchanged. Base overlap0.03m is a displaychoice, not measured foundation.','Bottom faces interpolate terrain between samples; no belowground structure claim.','Actualcapturedateunknown; no invented ramp.']};(O/'checks.json').write_text(json.dumps(report,indent=2));print('DONE')
