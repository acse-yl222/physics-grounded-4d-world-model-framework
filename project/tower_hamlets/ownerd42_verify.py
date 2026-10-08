import bpy,bmesh,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/ownerd42-massing-001'
def inventory(native):
 result={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles();vs=[list(o.matrix_world@v.co) for v in o.data.vertices];bm=bmesh.new();bm.from_mesh(o.data)
  if not native:bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002)
  bad=sum(not ed.is_manifold for ed in bm.edges);zero=sum(f.calc_area()<1e-10 for f in bm.faces);vol=bm.calc_volume(signed=True);bm.free()
  result[o.name]={'triangles':len(o.data.loop_triangles),'nonmanifold_edges':bad,'degenerate_faces':zero,'signed_volume_m3':vol,'bounds':[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]],'materials':sorted(m.name for m in o.data.materials),'building_id':o.get('building_id'),'aggregate_alias_id':o.get('aggregate_alias_id')}
 return result
bpy.ops.wm.open_mainfile(filepath=str(O/'ownerd42.blend'));a=inventory(True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'ownerd42.glb'));b=inventory(False)
assert set(a)==set(b);maximum=0
for name,aa in a.items():
 bb=b[name];assert aa['nonmanifold_edges']==bb['nonmanifold_edges']==0,(name,aa,bb);assert aa['degenerate_faces']==bb['degenerate_faces']==0;assert aa['signed_volume_m3']>0
 for key in ['triangles','materials','building_id','aggregate_alias_id']:assert aa[key]==bb[key],(name,key)
 maximum=max(maximum,max(abs(x-y) for ca,cb in zip(aa['bounds'],bb['bounds']) for x,y in zip(ca,cb)))
assert maximum<.0001
report={'native_reopened':True,'independent_glb_imported':True,'all_meshes_closed':True,'objects':len(a),'triangles':sum(v['triangles'] for v in a.values()),'max_glb_bounds_difference_m':maximum,'native':a,'glb':b,'hashes':{n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in ['ownerd42.blend','ownerd42.glb']},'limitations':'Closed per-domain prisms have intentional coincident internal partition walls. Material colors are illustrative, no facade optical evidence. Geometric roundtrip precision is not geographic accuracy.'};(O/'verification.json').write_text(json.dumps(report,indent=2));print(report['objects'],report['triangles'],maximum)
