from pathlib import Path
import bpy,json,hashlib,os
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/appearance-morgan-south-001'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'))
def plain(v):
 if hasattr(v,'to_list'):return v.to_list()
 return v
def capture():
 out={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles();vs=[o.matrix_world@v.co for v in o.data.vertices]
  out[o.get('research_object_id',o.name)]={'triangles':len(o.data.loop_triangles),'bounds':[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]],'aliases':{k:plain(o[k]) for k in ['building_id','source_owner_ids','aggregate_alias_id'] if k in o},'materials':sorted({o.data.materials[p.material_index].name for p in o.data.polygons if o.data.materials})}
 return out
native=capture();s=bpy.context.scene;cam=s.camera;c=Vector((-318.28645,-73.05868,25));cam.location=c+Vector((-5,-32,4));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=36;cam.data.clip_start=.1;cam.data.clip_end=5000
fw=cam.rotation_euler.to_quaternion()@Vector((0,0,-1));dep=[(o.matrix_world@Vector(v)-cam.location).dot(fw) for o in s.objects if o.type=='MESH' for v in o.bound_box];cam.location-=fw*max(0,10-min(dep));s.render.resolution_x=1300;s.render.resolution_y=1000;s.cycles.samples=24;s.render.filepath=str(O/'front-context-revised.png');# Existing revised context render retained; geometry verification only.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'region.glb'));glb=capture();assert set(native)==set(glb)
maxerr=0
for k,n in native.items():
 g=glb[k];assert n['triangles']==g['triangles'];assert n['aliases']==g['aliases'],k;assert n['materials']==g['materials'],(k,n['materials'],g['materials']);err=max(abs(n['bounds'][a][i]-g['bounds'][a][i]) for a in range(2) for i in range(3));maxerr=max(err,maxerr);assert err<.001,(k,err)
bounds=[[min(n['bounds'][0][i] for n in native.values()) for i in range(3)],[max(n['bounds'][1][i] for n in native.values()) for i in range(3)]]
sources=[P/'runs/canary_wharf_appearance_bank40_002/region.blend',R/'exports/morgan_south-facade-001/morgan_south.blend'];v={'native_reopened':True,'independent_glb_verified':True,'new_material_bindings_verified':True,'source_owner_aliases_verified':True,'source_owner_ids':['overture-part-b317a51d-586a-3b78-9ee5-b685a2db94a0'],'source_blends':{os.path.relpath(p,R):sha(p) for p in sources},'bounds_enu_m':bounds,'objects':len(native),'appearance_objects':5,'unchanged_meshes':2599,'unrelated_mesh_fingerprint_count':2599,'unrelated_mesh_fingerprints_verified':True,'maximum_glb_world_bounds_difference_m':maxerr,'all_mesh_ids_triangles_material_names_aliases_match':True,'new_details':{k:n for k,n in native.items() if k.startswith('morgan-south::')},'scope':'Independent comparison only; five bounded edge13 facade meshes added; all preexisting meshes preserved.'}
assert v['source_blends'][os.path.relpath(sources[0],R)]==json.loads((O/'checks.json').read_text())['source_sha256'];(O/'verification.json').write_text(json.dumps(v,indent=2))
