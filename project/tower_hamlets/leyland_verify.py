from pathlib import Path
import bpy,bmesh,json,hashlib,math
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/leyland-massing-001'
def inspect():
 out=[]
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  bm=bmesh.new();bm.from_mesh(o.data);o.data.calc_loop_triangles();vs=[o.matrix_world@v.co for v in o.data.vertices]
  r={'name':o.name,'id':o.get('building_id'),'vertices':len(vs),'triangles':len(o.data.loop_triangles),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-10 for f in bm.faces),'finite':all(math.isfinite(x) for v in vs for x in v),'bounds':[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]],'material_slots':len(o.data.materials),'volume_m3':bm.calc_volume(signed=False)};bm.free();out.append(r)
 return sorted(out,key=lambda x:x['name'])
bpy.ops.wm.open_mainfile(filepath=str(O/'leyland.blend'));a=inspect();bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'leyland.glb'));b=inspect()
assert len(a)==len(b)
for x,y in zip(a,b):
 assert x['name']==y['name'] and x['id']==y['id'] and x['triangles']==y['triangles'];assert all(abs(p-q)<.0001 for aa,bb in zip(x['bounds'],y['bounds']) for p,q in zip(aa,bb));assert x['nonmanifold_edges']==0 and x['zero_area_faces']==0 and x['finite'] and y['finite'] and y['material_slots']>0
(O/'numerical_verification.json').write_text(json.dumps({'native':a,'independent_glb':b,'passed':True,'note':'GLB duplicates vertices at material/normal seams; native topology watertight, imported triangle geometry/bounds checked.','sha256':{f:hashlib.sha256((O/f).read_bytes()).hexdigest() for f in ['leyland.blend','leyland.glb']}},indent=2))
