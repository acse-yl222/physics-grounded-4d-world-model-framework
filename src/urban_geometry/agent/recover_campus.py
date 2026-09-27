"""Recover editable triangulated campus geometry from the intact uncompressed GLB."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, agent_src, authoring_path
import bpy,json,hashlib,struct
from pathlib import Path
from mathutils import Vector
root=authoring_path()
source=root.parents[1]/'assets/models/Imperial_College_South_Kensington_Detailed_Phase4.glb'
out=root/'references/campus_phase4_recovered.blend'
if out.exists():raise RuntimeError('Recovery exists; do not overwrite')
before=(source.stat().st_size,source.stat().st_mtime_ns)
with source.open('rb') as f:
 magic,version,size=struct.unpack('<4sII',f.read(12));n,kind=struct.unpack('<II',f.read(8));doc=json.loads(f.read(n))
assert magic==b'glTF' and size==before[0]
assert 'KHR_draco_mesh_compression' not in doc.get('extensionsUsed',[])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert len(obs)==len([n for n in doc['nodes'] if 'mesh' in n])
ids=[o.get('research_object_id') for o in obs];assert all(ids) and len(set(ids))==len(ids)
report={'source':str(source),'source_size':before[0],'source_mtime_ns':before[1], 'objects':len(obs),'object_bounds':{},'osm_ids':sorted({str(o['osm_id']) for o in obs if 'osm_id' in o}), 'recovery':'GLB triangle meshes, materials, embedded images and extras; original procedural authoring unavailable','native_compression':False}
for o in obs:
 vs=[o.matrix_world@Vector(c) for c in o.bound_box]
 report['object_bounds'][o.name]={'lo':[min(v[i] for v in vs) for i in range(3)],'hi':[max(v[i] for v in vs) for i in range(3)],'triangles':len(o.data.polygons),'osm_id':str(o.get('osm_id',''))}
assert (source.stat().st_size,source.stat().st_mtime_ns)==before
bpy.context.scene.unit_settings.system='METRIC'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=False)
report['source_sha256']=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
(root/'docs/campus_phase4_recovery.json').write_text(json.dumps(report,indent=2))
print('CAMPUS_RECOVERED',len(obs),len(report['osm_ids']),flush=True)
