"""Retain only photo-supported third grid direction; exclude terminal hypothesis."""
import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007';out=root/'exports/crossrail-grid-photo-001';out.mkdir(parents=True,exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(root/'exports/crossrail-photo-study-001/crossrail-study.blend'))
keep=['Existing estimated diagonal timber members','Photo-supported third timber direction, inferred positions','Retained measured roof patches']
for ob in list(bpy.data.objects):
 if ob.type=='MESH' and ob.name not in keep:bpy.data.objects.remove(ob,do_unlink=True)
ids=['crossrail_existing_diagrid','crossrail_photo_third_direction','crossrail_observed_roof']
for name,id_ in zip(keep,ids):
 ob=bpy.data.objects[name];ob.name=id_;ob['component_id']=id_
scene=bpy.context.scene;cam=scene.camera
rep=json.loads((root/'references/crossrail_lidar_review.json').read_text());cx,cy=rep['mapped_part_extent']['centroid_local_xy'];ux,uy=rep['axis_local_xy'];vx,vy=-uy,ux
# Same camera/light/environment/exposure for a local roof closeup.
def point(a,b,z):return Vector((cx+a*ux+b*vx,cy+a*uy+b*vy,z))
target=point(0,0,22);cam.location=point(-30,-46,42);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=58
third=bpy.data.objects[ids[1]]
for name,hidden in [('before',True),('after',False)]:
 third.hide_render=hidden;scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
third.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(out/'crossrail-grid.blend'),compress=False)
bpy.ops.object.select_all(action='DESELECT');meshes=[bpy.data.objects[n] for n in ids]
for ob in meshes:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'crossrail-grid.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
count=sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in meshes);points=[ob.matrix_world@v.co for ob in meshes for v in ob.data.vertices];bounds=[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
bpy.ops.wm.open_mainfile(filepath=str(out/'crossrail-grid.blend'));assert all(n in bpy.data.objects for n in ids)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'crossrail-grid.glb'));meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert sorted(o.name for o in meshes)==sorted(ids);assert sum(len(o.data.polygons) for o in meshes)==count
points=[ob.matrix_world@v.co for ob in meshes for v in ob.data.vertices];got=[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]];assert max(abs(a-b) for x,y in zip(bounds,got) for a,b in zip(x,y))<1e-4
report={'scope':'Only existing observed shell and estimated frame plus third-direction timber beams; no terminal hypothesis or deck','component_ids':ids,'native_reopened':True,'glb_ids_triangles_bounds_verified':True,'triangles':count,'bounds_local_enu_m':bounds,'visual_reviewed':False,'source_id':'pexels_tom_whyte_10391373','source_url':'https://www.pexels.com/photo/building-in-canary-wharf-business-complex-in-london-10391373/','attribution':'Tom Whyte / Pexels','license_url':'https://www.pexels.com/license/','actually_inspected':True,'capture_date':None,'observation':'Visible timber cells are triangular; previous diamond-only grid omitted the third beam direction','inference':'New beam positions follow existing inferred nodes; section dimensions and counts not photographically measured','no_original_photo_redistributed':True,'unresolved':['Terminal needs parent-residual and complete end-envelope reconstruction; previous silver-rim/panel hypothesis rejected and excluded','Roof data gaps are not verified cladding openings','Frame dimensions, node pattern and timber tone remain approximate'],'comparison':'before.png and after.png use identical camera lighting and exposure; only added beam visibility changes'}
(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('CROSSRAIL_GRID_PHOTO_VERIFIED',count)
