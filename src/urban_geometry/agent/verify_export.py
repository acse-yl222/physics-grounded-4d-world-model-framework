"""Reopen, export uncompressed GLB, independently reimport and check object fidelity."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, agent_src, authoring_path
import bpy,json,sys,hashlib,struct,math,argparse
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=authoring_path()
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--no-reimport-cache',action='store_true',help='Verify fresh GLB import in memory without saving a redundant blend copy');args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=ROOT/'exports'/args.run;master=out/'expanded_region.blend';glb=out/'expanded_region.glb'
assert not glb.exists(),'Refusing existing export'
bpy.ops.wm.open_mainfile(filepath=str(master));scene=bpy.context.scene
obs=[o for o in scene.objects if o.type=='MESH'];assert all(o.get('research_object_id') for o in obs)
def bb(o):
 v=[o.matrix_world@Vector(p) for p in o.bound_box];return [[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]]
def records(objects):
 out={}
 for ob in objects:
  ob.data.calc_loop_triangles();oid=ob['research_object_id'];assert oid not in out
  out[oid]={'name':ob.name,'triangles':len(ob.data.loop_triangles),'bounds':bb(ob),'building_id':ob.get('building_id'),'material_slots':len(ob.data.materials)}
 return out
expected=records(obs)
# Inspect newly authored geometry; inherited campus stays exactly as supplied.
quality=[]
for ob in obs:
 if ob.get('expansion_status','').startswith('inherited'):continue
 mesh=ob.data;co=np.empty(len(mesh.vertices)*3,dtype=np.float64);mesh.vertices.foreach_get('co',co);co=co.reshape(-1,3)
 indices=np.empty(len(mesh.loop_triangles)*3,dtype=np.int32);mesh.loop_triangles.foreach_get('vertices',indices)
 tri=co[indices.reshape(-1,3)];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
 quality.append({'object':ob.name,'triangles':len(areas),'nonfinite_vertices':int(np.sum(~np.isfinite(co))),'degenerate_triangles':int(np.sum(areas<=1e-12))})
(out/'new_geometry_quality.json').write_text(json.dumps(quality,indent=2))
assert all(q['nonfinite_vertices']==0 and q['degenerate_triangles']==0 for q in quality),'New geometry quality failures: see new_geometry_quality.json'

images=[{'name':im.name,'size':list(im.size),'sha256_pixels_not_checked':True} for im in bpy.data.images if im.type=='IMAGE' and im.size[0]>0]
# Check new door approaches against the actual combined scene, before intentional leaf/frame.
build=json.loads((out/'build.json').read_text());deps=bpy.context.evaluated_depsgraph_get();rayrows=[]
for oid,r in build['buildings'].items():
 for e in r.get('interfaces',{}).get('entrances',[]):
  if 'campus_threshold_xyz' not in e:continue
  p=Vector(e['campus_threshold_xyz']);n=Vector(e['campus_outward_normal']);t=Vector((-n.y,n.x,0));w=float(e.get('clear_width_m',1));depth=float(e.get('door_leaf_depth_m',.16))
  failures=[];floor=[]
  for frac in [-.30,0,.30]:
   for dz in [.035,.12,.9,1.8]:
    start=p+n*.65+t*(w*frac)+Vector((0,0,dz));distance=.65+max(0,depth-.13)
    hit,loc,normal,index,obj,matrix=scene.ray_cast(deps,start,-n,distance=distance)
    if hit:failures.append({'lateral_fraction':frac,'z':dz,'object':obj.name,'hit':list(loc)})
   start=p+n*.35+t*(w*frac)+Vector((0,0,1.))
   hit,loc,normal,index,obj,matrix=scene.ray_cast(deps,start,Vector((0,0,-1)),distance=3)
   floor.append({'lateral_fraction':frac,'hit':bool(hit),'delta_z':float(loc.z-p.z) if hit else None,'object':obj.name if hit else None})
  rayrows.append({'building_id':oid,'threshold':list(p),'obstructions':failures,'floor':floor})
(out/'entry_checks.json').write_text(json.dumps({'results':rayrows,'review_required':[r['building_id'] for r in rayrows if r['obstructions'] or any(not x['hit'] or abs(x['delta_z'])>.15 for x in r['floor'])],'note':'Diagnostics include inherited scene; intentional door frames/sculpture require review, not automatic acceptance.'},indent=2))
bpy.ops.object.select_all(action='DESELECT')
for ob in obs:ob.select_set(True)
bpy.context.view_layer.objects.active=obs[0]
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True,export_draco_mesh_compression_enable=False)
with glb.open('rb') as f:
 magic,version,size=struct.unpack('<4sII',f.read(12));n,kind=struct.unpack('<II',f.read(8));doc=json.loads(f.read(n))
assert magic==b'glTF' and size==glb.stat().st_size and 'KHR_draco_mesh_compression' not in doc.get('extensionsUsed',[])
(out/'expected_objects.json').write_text(json.dumps(expected,indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb));bpy.context.view_layer.update();actual=records([o for o in bpy.context.scene.objects if o.type=='MESH'])
assert set(expected)==set(actual),'Object IDs changed'
errors=[]
for oid,ex in expected.items():
 ac=actual[oid];assert ex['triangles']==ac['triangles'],oid
 assert ex['building_id']==ac['building_id'],oid
 assert ac['material_slots']>0
 errors.append(max(abs(ex['bounds'][i][j]-ac['bounds'][i][j]) for i in range(2) for j in range(3)))
assert max(errors)<.003,max(errors)
actual_images=[im for im in bpy.data.images if im.type=='IMAGE' and im.size[0]>0]
assert len(actual_images)==len(images),(len(actual_images),len(images));assert sorted(tuple(im.size) for im in actual_images)==sorted(tuple(im['size']) for im in images)
assert all(len(im.pixels)>0 for im in actual_images)
# Save verified import for independent viewing; geometry remains fully editable.
if not args.no_reimport_cache:
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'expanded_region_reimport.blend'),compress=False)
report={'master':str(master),'master_size':master.stat().st_size,'master_mtime_ns':master.stat().st_mtime_ns,'glb':str(glb),'glb_size':glb.stat().st_size,'glb_sha256':hashlib.file_digest(glb.open('rb'),'sha256').hexdigest(),'objects':len(actual),'triangles':sum(v['triangles'] for v in actual.values()),'building_ids':sorted({v['building_id'] for v in actual.values() if v['building_id']}),'bounds_error_m':max(errors),'images_preserved':len(images),'image_dimensions':[im['size'] for im in images],'native_compression':False,'draco':False,'decimation':False,'texture_downsampling':False,'independent_reimport_verified':True,'reimport_cache_saved':not args.no_reimport_cache,'numerical_export_verified':True,'visual_reviewed':False,'all_buildings_at_RSM_standard':False,'limitations':'Campus recovered from GLB: original procedural shaders/hierarchy unavailable. Photo-informed landmarks include explicit estimates. Surrounding buildings still procedural baselines. Numerical identity is not geographic accuracy.'}
(out/'verification.json').write_text(json.dumps(report,indent=2));print('EXPANSION_EXPORT_VERIFIED',len(actual),max(errors),flush=True)
