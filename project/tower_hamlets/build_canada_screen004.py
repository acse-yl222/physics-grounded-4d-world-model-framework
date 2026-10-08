from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/one_canada_detail_gap004';src=R/'exports/one_canada_detail_gap003/canada-crown.blend';d=json.loads((O/'authoring.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(src));base=bpy.data.objects['Canada_317cf479fcef_steel'];post=bpy.data.objects['Canada_roofscreen_west_uprights_estimated003'];oldpost=[list(v.co)for v in post.data.vertices];materials=list(base.data.materials);s=bpy.context.scene;cam=s.camera
ring=json.loads((R/'geometry.json').read_text());f=next(q for q in ring['buildings'] if q['id']==d['owner_id']);a,b=map(Vector,f['geometry'][0]['outer'][:2]);mid=(a+b)/2;t=(b-a).normalized();n=Vector((t.y,-t.x));views=[('whole',Vector((-47,-41,222)),Vector((-70,35,24)),57),('close',Vector((mid.x,mid.y,211)),Vector((-13,6,3)),9),('corner',Vector((a.x,a.y,210.8)),Vector((-9,10,3)),5)]
def render(prefix):
 for key,c,off,scale in views:
  cam.location=c+off;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;s.render.filepath=str(O/(prefix+'-'+key+'.png'));bpy.ops.render.render(write_still=True)
render('before');me=bpy.data.meshes.new('Canada sixwest slats preservedpyramid');me.from_pydata(d['vertices'],[],d['faces']);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert all(f.calc_area()>1e-10 for f in bm.faces);bm.to_mesh(me);bm.free();base.data=me
for m in materials:me.materials.append(m)
base['coverage']='Originalpyramid andotherfacefivebandgeometry preserved; westbandsegments replacedwithsixslats forfivecrossviewestimatedslots';base['research_object_id']='one_canada_detail_gap004::roof_with_west_sixslats';base['scope']='Westslatcountcrossviewestimated, notexactwestmeasurement';assert oldpost==[list(v.co)for v in post.data.vertices]
# Physical occupancy proves old slats do not remain within new slot centers.
tree=BVHTree.FromPolygons([v.co for v in me.vertices],[list(p.vertices)for p in me.polygons]);rays=[]
for ratio in [.1,.3,.5,.7,.9]:
 p=a+(b-a)*ratio
 for j in range(5):
  z=210+j*.256+.09+(.256-.09)/2;origin=Vector((p.x+n.x,p.y+n.y,z));hit=tree.ray_cast(origin,Vector((-n.x,-n.y,0)),2);rays.append({'along':ratio,'slot':j,'z':z,'first_depth_m':None if hit[0] is None else hit[3]});assert hit[0] is None or hit[3]>1.105,(ratio,j,hit[3])
render('after');bpy.ops.wm.save_as_mainfile(filepath=str(O/'canada-crown.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');base.select_set(True);post.select_set(True);bpy.ops.export_scene.gltf(filepath=str(O/'canada-crown.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);expected={}
for o in [base,post]:o.data.calc_loop_triangles();expected[o.name]=len(o.data.loop_triangles)
bpy.ops.wm.open_mainfile(filepath=str(O/'canada-crown.blend'));assert oldpost==[list(v.co)for v in bpy.data.objects['Canada_roofscreen_west_uprights_estimated003'].data.vertices];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'canada-crown.glb'));actual={o.name:len(o.data.polygons)for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
(O/'checks.json').write_text(json.dumps({'source_sha256':hashlib.file_digest(src.open('rb'),'sha256').hexdigest(),'native_sha256':hashlib.file_digest((O/'canada-crown.blend').open('rb'),'sha256').hexdigest(),'native_reopened':True,'independent_glb_verified':True,'mesh_triangles':actual,'posts_unchanged':True,'slot_rays':rays,'partition':d['partition'],'source_owner_ids':[d['owner_id']]},indent=2));print('DONE',actual)
