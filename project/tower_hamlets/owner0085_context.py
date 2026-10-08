import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/owner0085-massing-001';r=json.loads((R/'references/owner0085_study.json').read_text());src=R.parents[1]/'runs/canary_wharf_appearance_owner1f92_001/region.blend';bpy.ops.wm.read_factory_settings(use_empty=True);native=json.loads((R/'references/owner0085_native.json').read_text())['objects'];neighbors=[]
audit=json.loads((R/'references/retained_inventory_reconciliation009.json').read_text());review=json.loads((R/'references/owner0085_roof_review.json').read_text());names={rec['mesh'] for row in review['neighbors_within_12m'] for rec in audit['representation'].get(row['id'],[])}
with bpy.data.libraries.load(str(src)) as (a,b):b.objects=[name for name in a.objects if name in names or name.startswith('Owner1f92_')]
for o in b.objects:
 if o and o.type=='MESH':bpy.context.collection.objects.link(o);neighbors.append(o)
with bpy.data.libraries.load(str(O/'owner0085.blend')) as (a,b):b.objects=[n for n in a.objects if n.startswith('Owner0085_')]
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
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=(.4,-.3,.6);t=Vector((-471,319,5));bpy.ops.object.camera_add(location=t+Vector((-80,-140,100)));s.camera=bpy.context.object;s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=60;s.render.filepath=str(O/'context-review.png');bpy.ops.render.render(write_still=True)
