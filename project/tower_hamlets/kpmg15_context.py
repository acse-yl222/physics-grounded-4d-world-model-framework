import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/kpmg15-massing-001';r=json.loads((R/'references/kpmg15_study.json').read_text());src=R/'exports/appearance-jpm25-001/region.blend';bpy.ops.wm.open_mainfile(filepath=str(src));native=[];neighbors=[]
for o in list(bpy.data.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True);continue
 v=[o.matrix_world@p.co for p in o.data.vertices]
 if o.get('building_id') in r['replacement_ids']:
  native.append({'name':o.name,'id':o.get('building_id'),'properties':dict(o.items()),'minz':min(p.z for p in v),'maxz':max(p.z for p in v),'vertices':len(v),'faces':len(o.data.polygons)});bpy.data.objects.remove(o,do_unlink=True)
 elif max(p.x for p in v)<120 or min(p.x for p in v)>215 or max(p.y for p in v)<-50 or min(p.y for p in v)>70 or o.get('building_id')=='site-support':bpy.data.objects.remove(o,do_unlink=True)
 else:neighbors.append(o)
with bpy.data.libraries.load(str(O/'kpmg15.blend')) as (a,b):b.objects=[n for n in a.objects if n.startswith('KPMG_')]
new=[]
for o in b.objects:
 if o and o.type=='MESH':bpy.context.collection.objects.link(o);new.append(o)
def tree(o):
 o.data.calc_loop_triangles();v=[o.matrix_world@p.co for p in o.data.vertices];return BVHTree.FromPolygons(v,[list(f.vertices) for f in o.data.loop_triangles],all_triangles=True),v
pairs=[]
for a in new:
 ta,va=tree(a)
 for b in neighbors:
  tb,vb=tree(b);pairs.append({'candidate':a.name,'neighbor':b.name,'overlap_triangle_pairs':len(ta.overlap(tb)),'vertex_min_distance_m':min(tb.find_nearest(v)[3] for v in va)})
(O/'context_mesh_check.json').write_text(json.dumps({'native_source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'original_native':native,'pairs':pairs,'method':'Worldtriangle BVH and nearestvertex sampling; surface contacts/containment limitations apply. Owner partitions preserved, internal sectorwalls intentionallycoincident. No global mutation.'},indent=2))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=(.4,-.3,.6);t=Vector((167,7,42));bpy.ops.object.camera_add(location=t+Vector((-150,-230,180)));s.camera=bpy.context.object;s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=180;s.render.filepath=str(O/'context-review.png');bpy.ops.render.render(write_still=True)
